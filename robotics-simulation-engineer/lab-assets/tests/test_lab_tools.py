"""Offline regression tests for the robotics simulation lab tools."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ASSETS))

from benchmark_summary import summarize
from evidence_gate import evaluate as evaluate_evidence
from lab_contracts import build_image_report, is_stale
from robustness_scenarios import evaluate as evaluate_robustness
from robustness_scenarios import generate
from score_parameter_sweep import score_rows
from urdf_audit import audit_urdf


class ContractTests(unittest.TestCase):
    def test_image_contract_requires_advancing_consistent_samples(self):
        samples = [
            {"stamp_ns": stamp, "width": 2, "height": 2, "step": 6, "encoding": "rgb8", "frame_id": "camera_optical", "payload_bytes": 12}
            for stamp in (100, 200, 300)
        ]
        self.assertTrue(build_image_report("/camera", samples)["ok"])
        samples[1]["frame_id"] = "wrong"
        self.assertFalse(build_image_report("/camera", samples)["ok"])

    def test_watchdog_timeout_boundary(self):
        self.assertTrue(is_stale(None, 1.0, 0.5))
        self.assertFalse(is_stale(1.0, 1.5, 0.5))
        self.assertTrue(is_stale(1.0, 1.5001, 0.5))


class OfflineToolTests(unittest.TestCase):
    def test_urdf_audit_detects_valid_tree_and_bad_mass(self):
        valid = """<robot name="r"><link name="base"><inertial><mass value="1"/><inertia ixx="1" ixy="0" ixz="0" iyy="1" iyz="0" izz="1"/></inertial><collision><geometry><box size="1 1 1"/></geometry></collision></link></robot>"""
        bad = valid.replace('mass value="1"', 'mass value="0"')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "robot.urdf"
            path.write_text(valid, encoding="utf-8")
            self.assertTrue(audit_urdf(path)["ok"])
            path.write_text(bad, encoding="utf-8")
            self.assertFalse(audit_urdf(path)["ok"])

    def test_parameter_sweep_ranks_nearest_row(self):
        rows = [{"scenario_id": "far", "distance": "3"}, {"scenario_id": "near", "distance": "1.1"}]
        contract = {"targets": {"distance": 1.0}, "scales": {"distance": 1.0}, "weights": {"distance": 1.0}}
        self.assertEqual(score_rows(rows, contract)[0]["scenario_id"], "near")

    def test_benchmark_and_robustness_summaries(self):
        benchmark = summarize([
            {"run": "a", "sim_seconds": "10", "wall_seconds": "5", "frames": "300"},
            {"run": "b", "sim_seconds": "10", "wall_seconds": "4", "frames": "300"},
        ])
        self.assertTrue(benchmark["ok"])
        manifest = generate({"friction": [0.2, 1.0]}, 4, 7)
        rows = [{"scenario_id": item["scenario_id"], "success": "1"} for item in manifest["scenarios"]]
        self.assertTrue(evaluate_robustness(manifest, rows, 0.9)["ok"])
        duplicate_rows = rows + [{"scenario_id": "s0000", "success": "1"}]
        duplicate_report = evaluate_robustness(manifest, duplicate_rows, 0.5)
        self.assertFalse(duplicate_report["ok"])
        self.assertEqual(duplicate_report["duplicates"], ["s0000"])

    def test_evidence_gate_fails_missing_or_false_report(self):
        with tempfile.TemporaryDirectory() as directory:
            good = Path(directory) / "good.json"
            bad = Path(directory) / "bad.json"
            good.write_text(json.dumps({"ok": True}), encoding="utf-8")
            bad.write_text(json.dumps({"ok": False}), encoding="utf-8")
            self.assertTrue(evaluate_evidence([f"good={good}"])["ok"])
            self.assertFalse(evaluate_evidence([f"good={good}", f"bad={bad}"])["ok"])


if __name__ == "__main__":
    unittest.main()
