"""Offline regression tests for the robotics simulation lab tools (standard library only).

Every planted fault named in Lab 08 has a test here, so "the validator can fail" is itself
checked in CI. ROS-environment tests live in tests/ros and are skipped without rclpy.
"""

from __future__ import annotations

import csv
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[1]
FIXTURES = ASSETS / "fixtures"
sys.path.insert(0, str(ASSETS))

from benchmark_summary import compare, p_value_greater, summarize
from evidence_gate import evaluate as evaluate_evidence
from lab_contracts import (
    build_camera_info_report,
    build_image_report,
    check_clock,
    check_joint_states,
    check_tf_tree,
    check_watchdog,
    is_stale,
)
from robustness_scenarios import evaluate as evaluate_robustness
from robustness_scenarios import generate, wilson_interval
from score_parameter_sweep import calibrate, validate_holdout
from urdf_audit import audit_urdf, symmetric_eigenvalues


def image_samples(count: int = 3) -> list[dict]:
    return [
        {"stamp_ns": 100 * (index + 1), "width": 2, "height": 2, "step": 6, "encoding": "rgb8", "frame_id": "camera_optical", "payload_bytes": 12}
        for index in range(count)
    ]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


class ContractTests(unittest.TestCase):
    def test_watchdog_timeout_boundary(self):
        self.assertTrue(is_stale(None, 1.0, 0.5))
        self.assertFalse(is_stale(1.0, 1.5, 0.5))
        self.assertTrue(is_stale(1.0, 1.5001, 0.5))

    def test_watchdog_rejects_timeouts_that_would_fail_open(self):
        for timeout in (float("nan"), float("inf"), 0.0, -1.0, True):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                is_stale(1.0, 100.0, timeout)

    def test_image_contract_requires_advancing_consistent_samples(self):
        samples = image_samples()
        self.assertTrue(build_image_report("/camera", samples)["ok"])
        samples[1]["frame_id"] = "wrong"
        self.assertFalse(build_image_report("/camera", samples)["ok"])

    def test_image_planted_faults(self):
        faults = {
            "repeated timestamp": lambda s: s[2].update(stamp_ns=s[1]["stamp_ns"]),
            "truncated payload": lambda s: s[0].update(payload_bytes=11),
            "padded payload": lambda s: s[0].update(payload_bytes=13),
            "stride shorter than width": lambda s: [item.update(step=4, payload_bytes=8) for item in s],
            "empty encoding": lambda s: [item.update(encoding="") for item in s],
        }
        for name, plant in faults.items():
            with self.subTest(fault=name):
                samples = image_samples()
                plant(samples)
                self.assertFalse(build_image_report("/camera", samples)["ok"])

    def test_camera_info_must_describe_the_image(self):
        report = build_image_report("/camera", image_samples())
        info = {"frame_id": "camera_optical", "width": 2, "height": 2, "k": [1, 0, 1, 0, 1, 1, 0, 0, 1]}
        self.assertTrue(build_camera_info_report(report, info)["ok"])
        self.assertFalse(build_camera_info_report(report, {**info, "frame_id": "camera_link"})["ok"])
        self.assertFalse(build_camera_info_report(report, {**info, "width": 4})["ok"])
        self.assertFalse(build_camera_info_report(report, {**info, "k": [0] * 9})["ok"])

    def test_clock_contract(self):
        self.assertTrue(check_clock([0, 16, 16, 33])["ok"])
        self.assertFalse(check_clock([0, 16, 8, 33])["ok"])
        self.assertEqual(check_clock([0, 16, 8, 33])["first_backward_index"], 2)
        self.assertFalse(check_clock([5, 5, 5])["ok"])
        self.assertFalse(check_clock([1])["ok"])

    def test_joint_state_contract(self):
        good = {"stamp_ns": 1, "name": ["a", "b"], "position": [0.0, 1.0], "velocity": [], "effort": [0.0, 0.0]}
        self.assertTrue(check_joint_states([good, {**good, "stamp_ns": 2}])["ok"])
        faults = {
            "short positions": {**good, "position": [0.0]},
            "velocity length": {**good, "velocity": [1.0]},
            "duplicate names": {**good, "name": ["a", "a"]},
            "non-finite": {**good, "position": [0.0, math.nan]},
            "stamp backward": {**good, "stamp_ns": 0},
            "order changed": {**good, "name": ["b", "a"]},
        }
        for name, bad in faults.items():
            with self.subTest(fault=name):
                self.assertFalse(check_joint_states([good, bad])["ok"])

    def test_tf_contract(self):
        tree = [{"parent": "odom", "child": "base_link"}, {"parent": "/base_link", "child": "camera", "static": True}]
        report = check_tf_tree(tree, [("odom", "base_link")])
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["roots"], ["odom"])
        self.assertFalse(check_tf_tree(tree + [{"parent": "map", "child": "base_link"}])["ok"])
        self.assertFalse(check_tf_tree(tree + [{"parent": "camera", "child": "odom"}])["ok"])
        self.assertFalse(check_tf_tree(tree + [{"parent": "world", "child": "lidar"}])["ok"])
        self.assertFalse(check_tf_tree(tree, [("map", "odom")])["ok"])
        self.assertFalse(check_tf_tree([])["ok"])

    def test_watchdog_latency_contract(self):
        ms = 1_000_000
        raw = [index * 100 * ms for index in range(10)]
        safe = [(index * 50 * ms, index * 50 * ms - 900 * ms > 500 * ms) for index in range(40)]
        report = check_watchdog(raw, safe, 0.5, 20.0)
        self.assertTrue(report["ok"], report)
        self.assertAlmostEqual(report["stale_to_zero_s"], 0.55)
        late = [(stamp, stamp > 1_600 * ms) for stamp, _ in safe]
        self.assertFalse(check_watchdog(raw, late, 0.5, 20.0)["ok"])
        never = [(stamp, False) for stamp, _ in safe]
        self.assertFalse(check_watchdog(raw, never, 0.5, 20.0)["ok"])
        self.assertTrue(check_watchdog([], safe, 0.5, 20.0)["ok"])
        with self.assertRaises(ValueError):
            check_watchdog(raw, safe, float("nan"), 20.0)


class UrdfAuditTests(unittest.TestCase):
    def audit_text(self, text: str) -> dict:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "robot.urdf"
            path.write_text(text, encoding="utf-8")
            return audit_urdf(path)

    def test_shipped_fixture_is_clean(self):
        report = audit_urdf(FIXTURES / "valid_robot.urdf")
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["warnings"], [])

    def test_eigenvalues_match_known_matrix(self):
        values = symmetric_eigenvalues(2.0, 1.0, 0.0, 2.0, 0.0, 3.0)
        for got, expected in zip(values, [1.0, 3.0, 3.0]):
            self.assertAlmostEqual(got, expected, places=12)

    def test_planted_faults(self):
        good = (FIXTURES / "valid_robot.urdf").read_text(encoding="utf-8")
        errors = {
            "zero mass": good.replace('<mass value="8.0"/>', '<mass value="0"/>'),
            "unknown child link": good.replace('<child link="wheel_link"/>', '<child link="ghost"/>'),
            "negative ixx": good.replace('ixx="0.075"', 'ixx="-0.075"'),
            "triangle inequality": good.replace('izz="0.1667"', 'izz="0.25"'),
            "zero joint axis": good.replace('<axis xyz="0 0 1"/>', '<axis xyz="0 0 0"/>'),
        }
        for name, text in errors.items():
            with self.subTest(fault=name):
                self.assertFalse(self.audit_text(text)["ok"])
        missing_collider = good.replace(
            '<collision><geometry><cylinder radius="0.05" length="0.03"/></geometry></collision>', ""
        )
        report = self.audit_text(missing_collider)
        self.assertTrue(report["ok"])
        self.assertTrue(any("no collision" in item for item in report["warnings"]))

    def test_inertia_on_the_wrong_axis_is_flagged_for_review(self):
        good = (FIXTURES / "valid_robot.urdf").read_text(encoding="utf-8")
        swapped = good.replace('iyy="0.00028" iyz="0" izz="0.0005"', 'iyy="0.0005" iyz="0" izz="0.00028"')
        report = self.audit_text(swapped)
        self.assertTrue(report["ok"])
        self.assertTrue(any("uniform cylinder" in item for item in report["warnings"]), report)


class ParameterSweepTests(unittest.TestCase):
    contract = json.loads((FIXTURES / "physics_targets.json").read_text(encoding="utf-8"))

    def test_fixture_selects_an_identifiable_candidate_that_wins_on_holdout(self):
        report = calibrate(read_csv(FIXTURES / "physics_sweep.csv"), self.contract, ["friction"], 3)
        self.assertTrue(report["ok"], report["errors"])
        self.assertEqual(report["selected"]["parameters"]["friction"], 0.7)
        self.assertTrue(report["identifiable"])
        holdout = validate_holdout(read_csv(FIXTURES / "physics_holdout.csv"), self.contract, report["selected"], 3)
        self.assertTrue(holdout["improves_beyond_repeat_noise"], holdout)

    def test_confounded_sweep_is_rejected(self):
        rows = read_csv(FIXTURES / "physics_sweep.csv")
        for row in rows:
            row["damping"] = str(float(row["friction"]) / 5)
        report = calibrate(rows, self.contract, None, 3)
        self.assertFalse(report["ok"])
        self.assertIn("confounded", " ".join(report["errors"]))
        self.assertFalse(calibrate(rows, self.contract, ["friction"], 3)["ok"])
        self.assertTrue(calibrate(rows, self.contract, ["friction", "damping"], 3)["ok"])

    def test_single_runs_are_rejected(self):
        rows = [row for row in read_csv(FIXTURES / "physics_sweep.csv") if row["repeat"] == "1"]
        self.assertFalse(calibrate(rows, self.contract, None, 3)["ok"])

    def test_overlapping_candidates_are_reported_as_not_identifiable(self):
        rows = read_csv(FIXTURES / "physics_sweep.csv")
        noisy = [row for row in rows if row["friction"] != "0.9"]
        for row in noisy:
            if row["friction"] == "0.5":
                row["stop_distance"] = str(0.43 + (int(row["repeat"]) - 2) * 0.2)
                row["yaw_error"], row["settling_time"] = "0.04", "0.85"
        report = calibrate(noisy, self.contract, None, 3)
        self.assertFalse(report["identifiable"])

    def test_holdout_that_does_not_beat_noise_fails(self):
        report = calibrate(read_csv(FIXTURES / "physics_sweep.csv"), self.contract, None, 3)
        rows = read_csv(FIXTURES / "physics_holdout.csv")
        for row in rows:
            if row["friction"] == "0.5":
                twin = next(item for item in rows if item["friction"] == "0.7" and item["repeat"] == row["repeat"])
                row.update({key: twin[key] for key in ("stop_distance", "yaw_error", "settling_time")})
        self.assertFalse(validate_holdout(rows, self.contract, report["selected"], 3)["ok"])


class BenchmarkTests(unittest.TestCase):
    def test_summary_math(self):
        report = summarize(read_csv(FIXTURES / "benchmark_runs.csv"))
        self.assertEqual(report["runs"], 5)
        self.assertAlmostEqual(report["rtf"]["median"], 30 / 24.8)
        self.assertLess(report["rtf"]["cv"], 0.01)

    def test_zero_wall_duration_is_rejected(self):
        rows = read_csv(FIXTURES / "benchmark_runs.csv")
        rows[0]["wall_seconds"] = "0"
        with self.assertRaises(ValueError):
            summarize(rows)

    def test_permutation_p_value(self):
        self.assertAlmostEqual(p_value_greater([2, 3, 4, 5, 6], [0, 0.5, 1, 1.5, 1.9]), 1 / 252)
        self.assertGreater(p_value_greater([1, 2, 3], [1, 2, 3]), 0.4)

    def test_speedup_claim_needs_significance_and_same_workload(self):
        baseline = {**summarize(read_csv(FIXTURES / "benchmark_runs.csv")), "workload": {"scene": "a"}}
        faster = {**summarize(read_csv(FIXTURES / "benchmark_optimized.csv")), "workload": {"scene": "a"}}
        self.assertTrue(compare(faster, baseline, 0.05, True, 0.05)["improvement_supported"])
        self.assertFalse(compare(baseline, baseline, 0.05, True, 0.05)["ok"])
        self.assertFalse(compare({**faster, "workload": {"scene": "b"}}, baseline, 0.05, False, 0.05)["ok"])


class RobustnessTests(unittest.TestCase):
    def test_every_stratum_is_sampled_once_per_dimension(self):
        manifest = generate({"friction": [0.2, 1.0], "mass": [1.0, 2.0]}, 8, 7)
        for name, (low, high) in {"friction": (0.2, 1.0), "mass": (1.0, 2.0)}.items():
            strata = sorted(int((item[name] - low) / (high - low) * 8) for item in manifest["scenarios"])
            self.assertEqual(strata, list(range(8)))
        self.assertEqual(manifest, generate({"friction": [0.2, 1.0], "mass": [1.0, 2.0]}, 8, 7))

    def test_wilson_interval_known_value(self):
        low, high = wilson_interval(28, 32)
        self.assertAlmostEqual(low, 0.7193, places=3)
        self.assertAlmostEqual(high, 0.9504, places=3)

    def test_completeness_duplicates_and_success_values(self):
        manifest = generate({"friction": [0.2, 1.0]}, 4, 7)
        rows = [{"scenario_id": item["scenario_id"], "success": "1"} for item in manifest["scenarios"]]
        self.assertTrue(evaluate_robustness(manifest, rows, 0.9)["ok"])
        duplicate = evaluate_robustness(manifest, rows + [{"scenario_id": "s0000", "success": "1"}], 0.5)
        self.assertFalse(duplicate["ok"])
        self.assertEqual(duplicate["duplicates"], ["s0000"])
        missing = evaluate_robustness(manifest, rows[:-1], 0.5)
        self.assertFalse(missing["ok"])
        self.assertEqual(missing["pass_rate"], 0.75)
        with self.assertRaises(ValueError):
            evaluate_robustness(manifest, [{**rows[0], "success": "0.7"}] + rows[1:], 0.5)

    def test_lower_bound_gate_and_failure_bins(self):
        manifest = generate({"friction": [0.0, 1.0]}, 32, 3)
        rows = [
            {"scenario_id": item["scenario_id"], "success": "0" if item["friction"] < 0.125 else "1"}
            for item in manifest["scenarios"]
        ]
        point = evaluate_robustness(manifest, rows, 0.85)
        self.assertTrue(point["ok"])
        self.assertFalse(evaluate_robustness(manifest, rows, 0.85, require_lower_bound=True)["ok"])
        self.assertEqual(point["weakest_bins"][0]["range"], [0.0, 0.25])


class EvidenceGateTests(unittest.TestCase):
    def test_missing_false_malformed_and_non_object_reports_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "good.json").write_text(json.dumps({"ok": True}), encoding="utf-8")
            (folder / "bad.json").write_text(json.dumps({"ok": False}), encoding="utf-8")
            (folder / "list.json").write_text("[1, 2]", encoding="utf-8")
            (folder / "broken.json").write_text("{", encoding="utf-8")
            (folder / "truthy.json").write_text(json.dumps({"ok": "true"}), encoding="utf-8")
            self.assertTrue(evaluate_evidence([f"good={folder / 'good.json'}"])["ok"])
            for name in ("bad", "list", "broken", "truthy", "absent"):
                with self.subTest(report=name):
                    self.assertFalse(evaluate_evidence([f"good={folder / 'good.json'}", f"x={folder / (name + '.json')}"])["ok"])
            self.assertFalse(evaluate_evidence([])["ok"])
            with self.assertRaises(ValueError):
                evaluate_evidence([f"a={folder / 'good.json'}", f"a={folder / 'good.json'}"])

    def test_powershell_utf16_output_is_readable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ps51.json"
            path.write_bytes(json.dumps({"ok": True}).encode("utf-16"))
            self.assertTrue(evaluate_evidence([f"camera={path}"])["ok"])


class CommandLineTests(unittest.TestCase):
    """Run each lab command exactly as documented, against the shipped fixtures."""

    def run_tool(self, *arguments: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, *arguments], capture_output=True, text=True, cwd=ASSETS, timeout=60)

    def test_documented_pipeline_produces_a_passing_evidence_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            steps = [
                ("urdf_audit.py", "fixtures/valid_robot.urdf", "--output", str(run / "model_audit.json")),
                ("score_parameter_sweep.py", "fixtures/physics_sweep.csv", "fixtures/physics_targets.json",
                 "--holdout", "fixtures/physics_holdout.csv", "--family", "friction", "--output", str(run / "physics_fit.json")),
                ("benchmark_summary.py", "fixtures/benchmark_runs.csv", "--workload", "scene=demo", "--output", str(run / "baseline.json")),
                ("benchmark_summary.py", "fixtures/benchmark_optimized.csv", "--workload", "scene=demo",
                 "--baseline", str(run / "baseline.json"), "--claim-improvement", "--output", str(run / "optimized.json")),
                ("robustness_scenarios.py", "generate", "fixtures/robustness_bounds.json", "--count", "32",
                 "--seed", "20260803", "--output", str(run / "scenarios.json")),
                ("robustness_scenarios.py", "evaluate", str(run / "scenarios.json"), "fixtures/robustness_results_example.csv",
                 "--minimum-pass-rate", "0.85", "--output", str(run / "robustness.json")),
                ("evidence_gate.py", "--require", f"model={run / 'model_audit.json'}", "--require", f"physics={run / 'physics_fit.json'}",
                 "--require", f"performance={run / 'optimized.json'}", "--require", f"robustness={run / 'robustness.json'}",
                 "--output", str(run / "gate.json")),
            ]
            for step in steps:
                with self.subTest(step=" ".join(step[:2])):
                    result = self.run_tool(*step)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(json.loads((run / "gate.json").read_text(encoding="utf-8"))["ok"])

    def test_failing_tools_exit_nonzero(self):
        with tempfile.TemporaryDirectory() as directory:
            bad_bounds = Path(directory) / "bounds.json"
            bad_bounds.write_text(json.dumps({"x": [1, 1]}), encoding="utf-8")
            cases = [
                ("robustness_scenarios.py", "generate", str(bad_bounds), "--output", str(Path(directory) / "s.json")),
                ("score_parameter_sweep.py", "fixtures/physics_sweep.csv", "fixtures/physics_targets.json"),
                ("evidence_gate.py", "--require", f"missing={Path(directory) / 'none.json'}"),
                ("urdf_audit.py", str(Path(directory) / "none.urdf")),
            ]
            for case in cases:
                with self.subTest(tool=case[0]):
                    self.assertNotEqual(self.run_tool(*case).returncode, 0)


if __name__ == "__main__":
    unittest.main()
