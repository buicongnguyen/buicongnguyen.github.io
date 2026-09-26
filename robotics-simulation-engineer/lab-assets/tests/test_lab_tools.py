"""Offline regression tests for the robotics simulation lab tools (standard library only).

Every planted fault named in Lab 08 has a test here, so "the validator can fail" is itself
checked in CI. ROS scripts run offline against fake rclpy modules; tests that need real
ROS (MCAP bags, the live watchdog node) live in tests/ros and skip without rclpy.
"""

from __future__ import annotations

import contextlib
import csv
import importlib
import io
import json
import math
import subprocess
import sys
import tempfile
import types
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

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
from score_parameter_sweep import calibrate, score_rows, validate_holdout
from urdf_audit import audit_urdf, symmetric_eigenvalues


def run_tool(script: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(ASSETS / script), *args], capture_output=True, text=True, encoding="utf-8")


def image_sample(stamp: int, width: int = 2, height: int = 2, step: int = 6, encoding: str = "rgb8", payload: int = 12) -> dict:
    return {"stamp_ns": stamp, "width": width, "height": height, "step": step, "encoding": encoding, "frame_id": "camera_optical", "payload_bytes": payload}


def inertia_urdf(ixx="1", ixy="0", ixz="0", iyy="1", iyz="0", izz="1", joint_type="continuous") -> str:
    inertial = f'<inertial><mass value="1"/><inertia ixx="{ixx}" ixy="{ixy}" ixz="{ixz}" iyy="{iyy}" iyz="{iyz}" izz="{izz}"/></inertial>'
    collision = '<collision><geometry><box size="1 1 1"/></geometry></collision>'
    return (
        f'<robot name="r"><link name="base">{inertial}{collision}</link><link name="tip">{inertial}{collision}</link>'
        f'<joint name="j" type="{joint_type}"><parent link="base"/><child link="tip"/><axis xyz="0 0 1"/></joint></robot>'
    )


class FakeExternalShutdown(Exception):
    """Stands in for rclpy.executors.ExternalShutdownException."""


class FakeRos:
    """Minimal rclpy/message stand-ins so the ROS-facing scripts run offline.

    The context starts invalid, becomes valid on init(), and spin() can model
    an external shutdown invalidating the context before raising.
    """

    def __init__(self, spin_error: BaseException | None = None, context_ok_after_spin: bool = True, images: list | None = None):
        fake = self
        self.context_ok = False
        self.events: list[str] = []
        self.images = list(images or [])
        self.callback = None
        self.init_options: dict = {}

        class Publisher:
            def publish(self, message):
                if not fake.context_ok:
                    raise RuntimeError("publisher's context is invalid")
                fake.events.append("publish")

        class Node:
            def __init__(self, name):
                self.logger = mock.Mock()

            def create_publisher(self, *args):
                return Publisher()

            def create_subscription(self, message_type, topic, callback, qos):
                fake.callback = callback

            def create_timer(self, *args, **kwargs):
                return None

            def get_logger(self):
                return self.logger

            def destroy_node(self):
                fake.events.append("destroy")

        def init(**options):
            fake.events.append("init")
            fake.init_options = options
            fake.context_ok = True

        def spin(node):
            fake.context_ok = context_ok_after_spin
            raise spin_error

        def spin_once(node, timeout_sec):
            if fake.images:
                fake.callback(fake.images.pop(0))

        def shutdown():
            if not fake.context_ok:
                raise RuntimeError("rcl_shutdown already called on the given context")
            fake.context_ok = False

        def try_shutdown():
            fake.events.append("try_shutdown")
            fake.context_ok = False

        def module(name, **attributes):
            created = types.ModuleType(name)
            created.__dict__.update(attributes)
            return created

        rclpy = module("rclpy", init=init, spin=spin, spin_once=spin_once, ok=lambda: fake.context_ok, shutdown=shutdown, try_shutdown=try_shutdown)
        self.modules = {
            "rclpy": rclpy,
            "rclpy.node": module("rclpy.node", Node=Node),
            "rclpy.clock": module("rclpy.clock", Clock=mock.Mock(), ClockType=mock.Mock()),
            "rclpy.executors": module("rclpy.executors", ExternalShutdownException=FakeExternalShutdown),
            "rclpy.qos": module("rclpy.qos", qos_profile_sensor_data=None),
            "rclpy.signals": module("rclpy.signals", SignalHandlerOptions=types.SimpleNamespace(NO="NO", ALL="ALL")),
            "geometry_msgs": module("geometry_msgs"),
            "geometry_msgs.msg": module("geometry_msgs.msg", Twist=type("Twist", (), {})),
            "sensor_msgs": module("sensor_msgs"),
            "sensor_msgs.msg": module("sensor_msgs.msg", Image=object, CameraInfo=object),
        }

    def load(self, module_name: str):
        with mock.patch.dict(sys.modules, self.modules):
            sys.modules.pop(module_name, None)
            return importlib.import_module(module_name)


def fake_image(stamp_nanosec: int, step: int = 6, payload: int = 12) -> types.SimpleNamespace:
    header = types.SimpleNamespace(stamp=types.SimpleNamespace(sec=1, nanosec=stamp_nanosec), frame_id="camera_optical")
    return types.SimpleNamespace(header=header, width=2, height=2, step=step, encoding="rgb8", data=bytes(payload))


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

    def test_watchdog_rejects_non_finite_timeout(self):
        # A NaN timeout used to return "fresh" forever, so the zero Twist was never sent.
        for timeout in (math.nan, math.inf, -math.inf, 0.0, -1.0):
            with self.assertRaises(ValueError):
                is_stale(0.0, 1e9, timeout)

    def test_image_contract_checks_row_stride_and_exact_payload(self):
        def report(**sample):
            return build_image_report("/camera", [image_sample(stamp, **sample) for stamp in (100, 200, 300)])

        rgb_row_too_short = report(width=640, height=480, step=640, payload=640 * 480)
        self.assertFalse(rgb_row_too_short["ok"])
        self.assertFalse(rgb_row_too_short["checks"]["step_covers_row"])
        self.assertTrue(report(width=640, height=480, step=1920, payload=1920 * 480)["ok"])
        self.assertTrue(report(width=640, height=480, step=1936, payload=1936 * 480)["ok"])  # padded rows are legal
        oversize = report(width=640, height=480, step=1920, payload=1920 * 480 * 2)
        self.assertFalse(oversize["ok"])
        self.assertFalse(oversize["checks"]["structural_payload"])
        self.assertFalse(report(step=6, payload=11)["ok"])
        self.assertTrue(report(width=4, height=3, step=16, encoding="32FC1", payload=48)["ok"])
        self.assertFalse(report(width=4, height=3, step=8, encoding="32FC1", payload=24)["ok"])
        self.assertTrue(report(width=4, height=3, step=8, encoding="16UC1", payload=24)["ok"])
        self.assertTrue(report(width=4, height=3, step=4, encoding="mono8", payload=12)["ok"])
        unknown = report(width=4, height=3, step=8, encoding="yuv422", payload=24)
        self.assertTrue(unknown["ok"])
        self.assertIsNone(unknown["bytes_per_pixel"])
        self.assertFalse(report(width=4, height=3, step=3, encoding="yuv422", payload=9)["ok"])


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

    def test_urdf_audit_enforces_inertia_triangle_and_joint_type(self):
        cases = {
            "valid": (inertia_urdf(), True),
            "thin_plate_equality": (inertia_urdf(izz="2"), True),
            "rounded_thin_plate": (inertia_urdf(ixx="0.0833", iyy="0.0833", izz="0.1667"), True),
            "diag_1_1_3": (inertia_urdf(izz="3"), False),
            # Rotated tensors: eigenvalues (1, 1, 3) and (1, 2, 3.3) violate; (1, 2, 2.9) is valid.
            "rotated_violation": (inertia_urdf(iyy="2", iyz="1", izz="2"), False),
            "general_violation": (inertia_urdf("1.5107", "-0.4568", "0.8346", "2.0916", "-0.2692", "2.6977"), False),
            "general_valid": (inertia_urdf("1.423", "-0.3899", "0.6832", "2.0406", "-0.1537", "2.4364"), True),
            "misspelled_joint_type": (inertia_urdf(joint_type="revolut"), False),
            "missing_joint_type": (inertia_urdf().replace(' type="continuous"', ""), False),
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "robot.urdf"
            for label, (text, expected) in cases.items():
                with self.subTest(label):
                    path.write_text(text, encoding="utf-8")
                    self.assertEqual(audit_urdf(path)["ok"], expected, audit_urdf(path)["errors"])
            for joint_type in ("revolute", "prismatic"):
                path.write_text(inertia_urdf(joint_type=joint_type).replace("</joint>", '<limit lower="-1" upper="1" effort="1" velocity="1"/></joint>'), encoding="utf-8")
                self.assertTrue(audit_urdf(path)["ok"])
            path.write_text(inertia_urdf(izz="3"), encoding="utf-8")
            self.assertIn("triangle inequality", " ".join(audit_urdf(path)["errors"]))

    def test_valid_robot_fixture_matches_declared_geometry(self):
        fixture = ASSETS / "fixtures" / "valid_robot.urdf"
        self.assertTrue(audit_urdf(fixture)["ok"])
        robot = ET.parse(fixture).getroot()
        for link in robot.findall("link"):
            geometry = link.find("collision/geometry")
            self.assertIsNone(link.find("collision/origin"), "fixture geometry is expressed in the link frame")
            mass = float(link.find("inertial/mass").get("value"))
            inertia = {key: float(link.find("inertial/inertia").get(key)) for key in ("ixx", "iyy", "izz")}
            box, cylinder = geometry.find("box"), geometry.find("cylinder")
            if box is not None:
                x, y, z = map(float, box.get("size").split())
                expected = {"ixx": mass * (y * y + z * z) / 12, "iyy": mass * (x * x + z * z) / 12, "izz": mass * (x * x + y * y) / 12}
            else:
                radius, length = float(cylinder.get("radius")), float(cylinder.get("length"))
                # URDF cylinders lie along the link z axis, which is also the wheel joint axis.
                transverse = mass * (3 * radius * radius + length * length) / 12
                expected = {"ixx": transverse, "iyy": transverse, "izz": mass * radius * radius / 2}
            for key, value in expected.items():
                self.assertTrue(math.isclose(inertia[key], value, rel_tol=1e-4), f"{link.get('name')} {key}={inertia[key]} expected {value:.6g}")
        self.assertEqual(robot.find("joint/axis").get("xyz"), "0 0 1")

    def test_robustness_generate_exits_nonzero_on_error(self):
        bounds = str(ASSETS / "fixtures" / "robustness_bounds.json")
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "manifest.json"
            self.assertEqual(run_tool("robustness_scenarios.py", "generate", bounds, "--count", "4", "--output", str(manifest)).returncode, 0)
            self.assertEqual(len(json.loads(manifest.read_text(encoding="utf-8"))["scenarios"]), 4)
            array_bounds = Path(directory) / "array.json"
            array_bounds.write_text("[0, 1]", encoding="utf-8")
            failures = {
                "zero_count": (bounds, "--count", "0", "--output", str(manifest)),
                "missing_bounds": (str(Path(directory) / "missing.json"), "--output", str(manifest)),
                "unwritable_output": (bounds, "--output", str(Path(directory) / "no_such_dir" / "manifest.json")),
                "array_bounds": (str(array_bounds), "--output", str(manifest)),
            }
            for label, args in failures.items():
                with self.subTest(label):
                    result = run_tool("robustness_scenarios.py", "generate", *args)
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertFalse(json.loads(result.stdout)["ok"])

    def test_cli_tools_accept_utf8_bom_and_report_malformed_input(self):
        bom = "﻿"
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            benchmark = folder / "benchmark.csv"
            benchmark.write_text(bom + (ASSETS / "fixtures" / "benchmark_runs.csv").read_text(encoding="utf-8"), encoding="utf-8")
            sweep = folder / "sweep.csv"
            sweep.write_text(bom + (ASSETS / "fixtures" / "physics_sweep.csv").read_text(encoding="utf-8"), encoding="utf-8")
            contract = folder / "contract.json"
            contract.write_text(bom + (ASSETS / "fixtures" / "physics_targets.json").read_text(encoding="utf-8"), encoding="utf-8")
            evidence = folder / "evidence.json"
            evidence.write_text(bom + '{"ok": true}', encoding="utf-8")
            short = folder / "short.csv"
            short.write_text("run,sim_seconds,wall_seconds,frames\na,10,5\n", encoding="utf-8")
            short_sweep = folder / "short_sweep.csv"
            short_sweep.write_text("scenario_id,stop_distance,yaw_error,settling_time\np0,0.4\n", encoding="utf-8")
            array = folder / "array.json"
            array.write_text("[1, 2]", encoding="utf-8")
            missing_dir_output = str(folder / "no_such_dir" / "report.json")

            result = run_tool("benchmark_summary.py", str(benchmark))
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertEqual(json.loads(result.stdout)["runs"], 5)
            result = run_tool("score_parameter_sweep.py", str(sweep), str(contract), "--calibration-only")
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn("candidate", json.loads(result.stdout)["selected"])
            self.assertEqual(run_tool("evidence_gate.py", "--require", f"camera={evidence}").returncode, 0)

            failures = {
                "benchmark_short_row": ("benchmark_summary.py", str(short)),
                "benchmark_array_baseline": ("benchmark_summary.py", str(benchmark), "--baseline", str(array)),
                "benchmark_missing_output_dir": ("benchmark_summary.py", str(benchmark), "--output", missing_dir_output),
                "sweep_short_row": ("score_parameter_sweep.py", str(short_sweep), str(contract)),
                "sweep_array_contract": ("score_parameter_sweep.py", str(sweep), str(array)),
                "sweep_missing_output_dir": ("score_parameter_sweep.py", str(sweep), str(contract), "--output", missing_dir_output),
                "evidence_array": ("evidence_gate.py", "--require", f"camera={array}"),
                "evidence_missing_output_dir": ("evidence_gate.py", "--require", f"camera={evidence}", "--output", missing_dir_output),
                "urdf_missing_output_dir": ("urdf_audit.py", str(ASSETS / "fixtures" / "valid_robot.urdf"), "--output", missing_dir_output),
            }
            for label, (script, *args) in failures.items():
                with self.subTest(label):
                    result = run_tool(script, *args)
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertNotIn("Traceback", result.stderr)
                    self.assertFalse(json.loads(result.stdout)["ok"])

    def test_rosbag_qos_keeps_all_static_transforms(self):
        blocks, current = {}, None
        for line in (ASSETS / "rosbag_qos_overrides.yaml").read_text(encoding="utf-8").splitlines():
            if line and not line.startswith(" "):
                current = line.rstrip(":")
                blocks[current] = {}
            elif line.strip():
                key, value = line.strip().split(":", 1)
                blocks[current][key] = value.strip()
        self.assertEqual(blocks["/tf_static"], {"reliability": "reliable", "durability": "transient_local", "history": "keep_last", "depth": "100"})


class RosScriptTests(unittest.TestCase):
    def run_main(self, fake: FakeRos, module_name: str, *argv: str) -> tuple[int, str]:
        module = fake.load(module_name)
        stdout = io.StringIO()
        with mock.patch.object(sys, "argv", [module_name, *argv]), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(io.StringIO()):
            try:
                module.main()
            except SystemExit as exit_request:
                return exit_request.code, stdout.getvalue()
        return 0, stdout.getvalue()

    def test_watchdog_rejects_non_finite_arguments_before_ros_init(self):
        for argv in (("--timeout", "nan"), ("--timeout", "inf"), ("--rate", "nan"), ("--rate", "inf"), ("--timeout", "0")):
            with self.subTest(argv):
                fake = FakeRos(spin_error=KeyboardInterrupt())
                code, _ = self.run_main(fake, "cmd_vel_watchdog", *argv)
                self.assertEqual(code, 2)
                self.assertNotIn("init", fake.events)

    def test_watchdog_keeps_context_alive_on_ctrl_c(self):
        # rclpy's default SIGINT handler would shut the context down before spin returns,
        # making the final zero command impossible (reproduced on Jazzy).
        fake = FakeRos(spin_error=KeyboardInterrupt())
        self.run_main(fake, "cmd_vel_watchdog")
        self.assertEqual(fake.init_options.get("signal_handler_options"), "NO")

    def test_watchdog_shutdown_after_context_already_shut_down(self):
        # An external shutdown can invalidate the context before spin returns.
        for error in (KeyboardInterrupt(), FakeExternalShutdown()):
            with self.subTest(type(error).__name__):
                fake = FakeRos(spin_error=error, context_ok_after_spin=False)
                code, _ = self.run_main(fake, "cmd_vel_watchdog")
                self.assertEqual(code, 0)
                self.assertEqual(fake.events, ["init", "destroy", "try_shutdown"])

    def test_watchdog_publishes_final_zero_while_context_is_valid(self):
        fake = FakeRos(spin_error=KeyboardInterrupt(), context_ok_after_spin=True)
        code, _ = self.run_main(fake, "cmd_vel_watchdog")
        self.assertEqual(code, 0)
        self.assertEqual(fake.events, ["init", "publish", "destroy", "try_shutdown"])

    def test_camera_probe_writes_utf8_report_file(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "camera_probe.json"
            fake = FakeRos(images=[fake_image(stamp) for stamp in (100, 200, 300)])
            code, stdout = self.run_main(fake, "camera_probe", "--topic", "/camera", "--samples", "3", "--output", str(output))
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output.read_bytes().decode("utf-8")), json.loads(stdout))
            self.assertTrue(evaluate_evidence([f"camera={output}"])["ok"])
            self.assertEqual(fake.events, ["init", "destroy", "try_shutdown"])

            fake = FakeRos(images=[fake_image(stamp, step=2, payload=4) for stamp in (100, 200, 300)])
            code, _ = self.run_main(fake, "camera_probe", "--topic", "/camera", "--samples", "3", "--output", str(output))
            self.assertEqual(code, 3)
            self.assertFalse(json.loads(output.read_text(encoding="utf-8"))["ok"])

            fake = FakeRos(images=[])
            code, _ = self.run_main(fake, "camera_probe", "--topic", "/camera", "--timeout", "0.01", "--output", str(output))
            self.assertEqual(code, 2)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["error"], "timeout")

            fake = FakeRos(images=[fake_image(stamp) for stamp in (100, 200)])
            code, stdout = self.run_main(fake, "camera_probe", "--topic", "/camera", "--samples", "2", "--output", str(Path(directory) / "missing" / "x.json"))
            self.assertEqual(code, 2)
            self.assertIn("cannot write --output", json.loads(stdout)["error"])

            fake = FakeRos()
            code, _ = self.run_main(fake, "camera_probe", "--topic", "/camera", "--timeout", "nan")
            self.assertEqual(code, 2)
            self.assertNotIn("init", fake.events)


def image_samples(count: int = 3) -> list[dict]:
    return [
        {"stamp_ns": 100 * (index + 1), "width": 2, "height": 2, "step": 6, "encoding": "rgb8", "frame_id": "camera_optical", "payload_bytes": 12}
        for index in range(count)
    ]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


class RuntimeContractTests(unittest.TestCase):
    def test_watchdog_rejects_timeouts_that_would_fail_open(self):
        for timeout in (float("nan"), float("inf"), 0.0, -1.0, True):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                is_stale(1.0, 100.0, timeout)

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
            "triangle inequality": good.replace('izz="0.16667"', 'izz="0.25"'),
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
        swapped = good.replace('iyy="0.00028" iyz="0" izz="0.00050"', 'iyy="0.00050" iyz="0" izz="0.00028"')
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
