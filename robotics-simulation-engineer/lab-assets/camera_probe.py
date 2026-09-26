"""Receive multiple sensor_msgs/Image messages and emit a bounded contract report."""

import argparse
import json
import math
import sys
import time
from pathlib import Path

import rclpy
from lab_contracts import build_camera_info_report, build_image_report
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image


class ImageProbe(Node):
    def __init__(self, topic: str, target_samples: int, info_topic: str | None):
        super().__init__("camera_contract_probe")
        self.target_samples = target_samples
        self.messages = []
        self.info = None
        self.subscription = self.create_subscription(
            Image, topic, self.on_image, qos_profile_sensor_data
        )
        if info_topic:
            self.info_subscription = self.create_subscription(
                CameraInfo, info_topic, self.on_info, qos_profile_sensor_data
            )

    def on_image(self, message: Image) -> None:
        if len(self.messages) < self.target_samples:
            self.messages.append(message)

    def on_info(self, message: CameraInfo) -> None:
        if self.info is None:
            self.info = message


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


def normalize_info(message: CameraInfo) -> dict:
    return {
        "frame_id": message.header.frame_id,
        "width": int(message.width),
        "height": int(message.height),
        "k": [float(value) for value in message.k],
    }


def emit(report: dict, output: Path | None) -> None:
    rendered = json.dumps(report, indent=2)
    print(rendered)
    if output:
        output.write_text(rendered + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True)
    parser.add_argument("--camera-info", help="CameraInfo topic that must describe the same image stream")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--samples", type=int, default=5)
    parser.add_argument("--output", type=Path, help="also write the JSON report here (UTF-8)")
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0.0 or args.samples < 2:
        parser.error("--timeout must be finite and positive and --samples must be at least 2")

    rclpy.init()
    node = ImageProbe(args.topic, args.samples, args.camera_info)
    deadline = time.monotonic() + args.timeout
    try:
        def waiting() -> bool:
            return len(node.messages) < args.samples or (args.camera_info is not None and node.info is None)

        while waiting() and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.2)
        if waiting():
            emit(
                {
                    "ok": False,
                    "topic": args.topic,
                    "error": "timeout",
                    "received": len(node.messages),
                    "required": args.samples,
                    "camera_info_received": node.info is not None,
                },
                args.output,
            )
            sys.exit(2)

        report = build_image_report(args.topic, [normalize(message) for message in node.messages])
        if args.camera_info:
            report["camera_info"] = build_camera_info_report(report, normalize_info(node.info))
            report["ok"] = report["ok"] and report["camera_info"]["ok"]
        emit(report, args.output)
        if not report["ok"]:
            sys.exit(3)
    except KeyboardInterrupt:
        sys.exit(130)
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
