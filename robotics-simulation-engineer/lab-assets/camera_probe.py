"""Receive one sensor_msgs/Image and emit a bounded JSON contract report."""

import argparse
import json
import sys
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image


class ImageProbe(Node):
    def __init__(self, topic: str):
        super().__init__("camera_contract_probe")
        self.message = None
        self.subscription = self.create_subscription(
            Image, topic, self.on_image, qos_profile_sensor_data
        )

    def on_image(self, message: Image) -> None:
        self.message = message


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True)
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()

    rclpy.init()
    node = ImageProbe(args.topic)
    deadline = time.monotonic() + args.timeout
    try:
        while node.message is None and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.2)
        if node.message is None:
            print(json.dumps({"ok": False, "topic": args.topic, "error": "timeout"}, indent=2))
            sys.exit(2)

        msg = node.message
        expected_bytes = int(msg.step) * int(msg.height)
        report = {
            "ok": bool(msg.width and msg.height and msg.step and len(msg.data) >= expected_bytes),
            "topic": args.topic,
            "frame_id": msg.header.frame_id,
            "stamp": {"sec": msg.header.stamp.sec, "nanosec": msg.header.stamp.nanosec},
            "width": msg.width,
            "height": msg.height,
            "encoding": msg.encoding,
            "step": msg.step,
            "payload_bytes": len(msg.data),
            "minimum_expected_bytes": expected_bytes,
        }
        print(json.dumps(report, indent=2))
        if not report["ok"]:
            sys.exit(3)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
