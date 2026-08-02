"""Receive multiple sensor_msgs/Image messages and emit a bounded contract report."""

import argparse
import json
import sys
import time

import rclpy
from lab_contracts import build_image_report
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image


class ImageProbe(Node):
    def __init__(self, topic: str, target_samples: int):
        super().__init__("camera_contract_probe")
        self.target_samples = target_samples
        self.messages = []
        self.subscription = self.create_subscription(
            Image, topic, self.on_image, qos_profile_sensor_data
        )

    def on_image(self, message: Image) -> None:
        if len(self.messages) < self.target_samples:
            self.messages.append(message)


def normalize(message: Image) -> dict:
    return {
        "stamp_ns": int(message.header.stamp.sec) * 1_000_000_000 + int(message.header.stamp.nanosec),
        "width": int(message.width),
        "height": int(message.height),
        "step": int(message.step),
        "encoding": message.encoding,
        "frame_id": message.header.frame_id,
        "payload_bytes": len(message.data),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--samples", type=int, default=5)
    args = parser.parse_args()
    if args.timeout <= 0.0 or args.samples < 2:
        parser.error("--timeout must be positive and --samples must be at least 2")

    rclpy.init()
    node = ImageProbe(args.topic, args.samples)
    deadline = time.monotonic() + args.timeout
    try:
        while len(node.messages) < args.samples and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.2)
        if len(node.messages) < args.samples:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "topic": args.topic,
                        "error": "timeout",
                        "received": len(node.messages),
                        "required": args.samples,
                    },
                    indent=2,
                )
            )
            sys.exit(2)

        report = build_image_report(args.topic, [normalize(message) for message in node.messages])
        print(json.dumps(report, indent=2))
        if not report["ok"]:
            sys.exit(3)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
