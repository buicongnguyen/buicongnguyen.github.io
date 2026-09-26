"""ROS-environment integration tests for the lab tools. Skipped when rclpy is unavailable.

Run inside the pixi Jazzy environment:

    pwsh -File Start-IsaacRosJazzy.ps1 python -m unittest discover -s <repo>/robotics-simulation-engineer/lab-assets/tests/ros -v
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ASSETS))

try:
    import rclpy
    import rosbag2_py
    from builtin_interfaces.msg import Time
    from geometry_msgs.msg import TransformStamped, Twist
    from rclpy.serialization import serialize_message
    from rosgraph_msgs.msg import Clock
    from sensor_msgs.msg import CameraInfo, Image, JointState
    from tf2_msgs.msg import TFMessage
except ImportError:  # pragma: no cover - exercised only outside the ROS environment
    rclpy = None

MANIFEST = {
    "required_topics": {
        "/clock": "rosgraph_msgs/msg/Clock",
        "/joint_states": "sensor_msgs/msg/JointState",
        "/tf": "tf2_msgs/msg/TFMessage",
        "/cmd_vel_raw": "geometry_msgs/msg/Twist",
        "/cmd_vel": "geometry_msgs/msg/Twist",
        "/camera/image": "sensor_msgs/msg/Image",
        "/camera/info": "sensor_msgs/msg/CameraInfo",
    },
    "required_tf_edges": [["odom", "base_link"]],
    "watchdog": {"raw": "/cmd_vel_raw", "safe": "/cmd_vel", "timeout_s": 0.5, "rate_hz": 20},
    "image": {"topic": "/camera/image", "camera_info": "/camera/info"},
}
MS = 1_000_000


def stamp(ns: int) -> "Time":
    return Time(sec=ns // 1_000_000_000, nanosec=ns % 1_000_000_000)


def twist(x: float = 0.0) -> "Twist":
    message = Twist()
    message.linear.x = x
    return message


def write_episode(path: Path, faults: set[str] = frozenset()) -> None:
    """Write a 2 s synthetic episode shaped like the Lab 05 recording, with optional planted faults."""
    writer = rosbag2_py.SequentialWriter()
    writer.open(rosbag2_py.StorageOptions(uri=str(path), storage_id="mcap"), rosbag2_py.ConverterOptions("cdr", "cdr"))
    for index, (name, kind) in enumerate(MANIFEST["required_topics"].items()):
        try:
            metadata = rosbag2_py.TopicMetadata(id=index, name=name, type=kind, serialization_format="cdr")
        except TypeError:  # rosbag2 builds before the id field existed
            metadata = rosbag2_py.TopicMetadata(name=name, type=kind, serialization_format="cdr")
        writer.create_topic(metadata)

    def put(topic: str, message, t_ns: int) -> None:
        writer.write(topic, serialize_message(message), t_ns)

    base = 1_700_000_000 * 1_000_000_000
    for tick in range(120):  # 60 Hz for 2 s
        wall = base + tick * 16_666_667
        sim = tick * 16_666_667
        clock = sim - 100 * MS if "clock_backward" in faults and tick == 60 else sim
        put("/clock", Clock(clock=stamp(clock)), wall)
        joints = JointState(name=["wheel_left_joint", "wheel_right_joint"], position=[tick * 0.01, tick * 0.01], velocity=[1.0, 1.0])
        joints.header.stamp = stamp(sim)
        put("/joint_states", joints, wall)
        edges = [("odom", "base_link"), ("base_link", "wheel_left_link"), ("base_link", "wheel_right_link")]
        if "tf_two_parents" in faults:
            edges.append(("world", "base_link"))
        tf = TFMessage()
        for parent, child in edges:
            item = TransformStamped()
            item.header.stamp = stamp(sim)
            item.header.frame_id = parent
            item.child_frame_id = child
            item.transform.rotation.w = 1.0
            tf.transforms.append(item)
        put("/tf", tf, wall)
        if tick % 2 == 0:
            image = Image(width=4, height=2, encoding="rgb8", step=12, data=bytes(24))
            image.header.stamp = stamp(sim)
            image.header.frame_id = "camera_optical"
            put("/camera/image", image, wall)
            info = CameraInfo(width=4, height=2, k=[2.0, 0.0, 2.0, 0.0, 2.0, 1.0, 0.0, 0.0, 1.0])
            info.header.stamp = stamp(sim)
            info.header.frame_id = "camera_optical"
            put("/camera/info", info, wall)
    # Raw commands at 10 Hz for the first 1.0 s, watchdog output at 20 Hz for 2 s.
    last_raw = base + 900 * MS
    for index in range(10):
        put("/cmd_vel_raw", twist(0.2), base + index * 100 * MS)
    for index in range(40):
        t_ns = base + index * 50 * MS
        stale = t_ns - last_raw > 500 * MS
        moving = not stale or "watchdog_never_zero" in faults
        put("/cmd_vel", twist(0.2 if moving else 0.0), t_ns)
    del writer  # closes the bag and writes metadata


@unittest.skipIf(rclpy is None, "rclpy/rosbag2_py not available; run inside the ROS environment")
class BagContractCheckTests(unittest.TestCase):
    def check(self, faults: set[str]) -> dict:
        from bag_contract_check import evaluate, read_bag

        with tempfile.TemporaryDirectory() as directory:
            bag = Path(directory) / "episode"
            write_episode(bag, faults)
            return evaluate(read_bag(bag, MANIFEST), MANIFEST)

    def test_clean_episode_passes_every_contract(self):
        report = self.check(set())
        self.assertTrue(report["ok"], report)
        self.assertAlmostEqual(report["checks"]["watchdog"]["stale_to_zero_s"], 0.55, places=6)

    def test_each_planted_fault_fails_its_own_contract(self):
        expectations = {"clock_backward": "clock", "tf_two_parents": "tf", "watchdog_never_zero": "watchdog"}
        for fault, contract in expectations.items():
            with self.subTest(fault=fault):
                report = self.check({fault})
                self.assertFalse(report["ok"])
                failed = sorted(name for name, check in report["checks"].items() if not check["ok"])
                self.assertEqual(failed, [contract])


@unittest.skipIf(rclpy is None, "rclpy not available; run inside the ROS environment")
class WatchdogNodeTests(unittest.TestCase):
    def test_fresh_commands_forward_then_stale_input_becomes_zero(self):
        from cmd_vel_watchdog import TwistWatchdog
        from rclpy.executors import SingleThreadedExecutor

        rclpy.init()
        try:
            watchdog = TwistWatchdog("/it_raw", "/it_safe", timeout=0.3, rate=50.0)
            probe = rclpy.create_node("watchdog_probe")
            received: list[tuple[float, float]] = []
            probe.create_subscription(Twist, "/it_safe", lambda m: received.append((time.monotonic(), m.linear.x)), 10)
            raw = probe.create_publisher(Twist, "/it_raw", 10)
            executor = SingleThreadedExecutor()
            executor.add_node(watchdog)
            executor.add_node(probe)

            def spin_for(seconds: float, publish: bool) -> None:
                end = time.monotonic() + seconds
                next_publish = 0.0
                while time.monotonic() < end:
                    if publish and time.monotonic() >= next_publish:
                        raw.publish(twist(0.2))
                        next_publish = time.monotonic() + 0.05
                    executor.spin_once(timeout_sec=0.01)

            spin_for(1.0, publish=True)
            last_raw = time.monotonic()
            spin_for(1.0, publish=False)
            forwarded = [x for t, x in received if t < last_raw and x == 0.2]
            first_zero = min((t for t, x in received if t > last_raw and x == 0.0), default=None)
            self.assertTrue(forwarded, "fresh commands were never forwarded (is discovery working?)")
            self.assertIsNotNone(first_zero, "stale input never produced a zero command")
            self.assertLessEqual(first_zero - last_raw, 0.3 + 1 / 50 + 0.1)
            executor.shutdown()
            watchdog.destroy_node()
            probe.destroy_node()
        finally:
            rclpy.try_shutdown()

    def test_ctrl_c_still_publishes_the_final_zero(self):
        wrapper = textwrap.dedent(
            """
            import signal, sys
            import rclpy
            sys.path.insert(0, sys.argv[1])
            sys.argv = ["cmd_vel_watchdog.py", "--input", "/it_raw2", "--output", "/it_safe2"]
            spin = rclpy.spin
            def spin_then_interrupt(node, *args, **kwargs):
                # Deliver Ctrl+C once the node is running, like an operator stopping it.
                node.create_timer(1.0, lambda: signal.raise_signal(signal.SIGINT))
                return spin(node, *args, **kwargs)
            rclpy.spin = spin_then_interrupt
            import cmd_vel_watchdog
            cmd_vel_watchdog.main()
            print("WATCHDOG_EXITED_CLEANLY")
            """
        )
        result = subprocess.run(
            [sys.executable, "-c", wrapper, str(ASSETS)],
            capture_output=True, text=True, timeout=60, env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        self.assertIn("Published final zero Twist", output)
        self.assertIn("WATCHDOG_EXITED_CLEANLY", output)
        self.assertNotIn("RCLError", output)


if __name__ == "__main__":
    unittest.main()
