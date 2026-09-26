"""Re-run the Lab 01-04 contracts offline against a recorded rosbag2 episode.

Run it inside the ROS environment (it needs rosbag2_py), for example:

    pwsh -File Start-IsaacRosJazzy.ps1 python lab-assets/bag_contract_check.py <bag_dir> \
        --manifest lab-assets/lab05_bag_manifest.json --output <run>/bag_contract.json

The rules themselves live in lab_contracts.py and are unit-tested without ROS; this file
only reads the bag and normalizes messages into plain values.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from lab_contracts import (
    build_camera_info_report,
    build_image_report,
    check_clock,
    check_joint_states,
    check_tf_tree,
    check_watchdog,
)

IMAGE_SAMPLE_LIMIT = 30


def stamp_ns(stamp) -> int:
    return int(stamp.sec) * 1_000_000_000 + int(stamp.nanosec)


def is_zero_twist(message) -> bool:
    return all(
        value == 0.0
        for vector in (message.linear, message.angular)
        for value in (vector.x, vector.y, vector.z)
    )


def read_bag(path: Path, manifest: dict) -> dict:
    import rosbag2_py
    from rclpy.serialization import deserialize_message
    from rosidl_runtime_py.utilities import get_message

    reader = rosbag2_py.SequentialReader()
    reader.open(rosbag2_py.StorageOptions(uri=str(path), storage_id=""), rosbag2_py.ConverterOptions("", ""))
    types = {topic.name: topic.type for topic in reader.get_all_topics_and_types()}
    classes = {name: get_message(kind) for name, kind in types.items()}
    watchdog = manifest.get("watchdog", {})
    image = manifest.get("image", {})
    tf_topics = {"/tf": False, "/tf_static": True}
    data = {
        "types": types,
        "counts": {name: 0 for name in types},
        "clock": [],
        "joint_states": [],
        "tf_edges": [],
        "raw_ns": [],
        "safe": [],
        "images": [],
        "camera_info": None,
    }
    while reader.has_next():
        topic, raw, received_ns = reader.read_next()
        data["counts"][topic] = data["counts"].get(topic, 0) + 1
        if topic == image.get("topic") and len(data["images"]) >= IMAGE_SAMPLE_LIMIT:
            continue  # counting is enough once the image probe has its samples
        if topic not in classes:
            continue
        message = deserialize_message(raw, classes[topic])
        if topic == "/clock":
            data["clock"].append(stamp_ns(message.clock))
        elif topic == manifest.get("joint_states", "/joint_states"):
            data["joint_states"].append({
                "stamp_ns": stamp_ns(message.header.stamp),
                "name": list(message.name),
                "position": list(message.position),
                "velocity": list(message.velocity),
                "effort": list(message.effort),
            })
        elif topic in tf_topics:
            data["tf_edges"].extend(
                {"parent": item.header.frame_id, "child": item.child_frame_id, "static": tf_topics[topic]}
                for item in message.transforms
            )
        elif topic == watchdog.get("raw"):
            data["raw_ns"].append(received_ns)
        elif topic == watchdog.get("safe"):
            data["safe"].append((received_ns, is_zero_twist(message)))
        elif topic == image.get("topic"):
            data["images"].append({
                "stamp_ns": stamp_ns(message.header.stamp),
                "width": message.width,
                "height": message.height,
                "step": message.step,
                "encoding": message.encoding,
                "frame_id": message.header.frame_id,
                "payload_bytes": len(message.data),
            })
        elif topic == image.get("camera_info") and data["camera_info"] is None:
            data["camera_info"] = {
                "frame_id": message.header.frame_id,
                "width": message.width,
                "height": message.height,
                "k": list(message.k),
            }
    return data


def check_topics(data: dict, required: dict[str, str]) -> dict:
    missing = sorted(name for name in required if name not in data["types"])
    wrong_type = sorted(
        f"{name}: {data['types'][name]} != {kind}"
        for name, kind in required.items()
        if name in data["types"] and data["types"][name] != kind
    )
    empty = sorted(name for name in required if data["counts"].get(name, 0) == 0 and name not in missing)
    return {
        "ok": not missing and not wrong_type and not empty,
        "missing": missing,
        "wrong_type": wrong_type,
        "empty": empty,
        "counts": {name: data["counts"].get(name, 0) for name in sorted(required)},
    }


def evaluate(data: dict, manifest: dict) -> dict:
    """Apply every contract the manifest declares; undeclared contracts are not run."""
    required = manifest.get("required_topics", {})
    checks: dict[str, dict] = {"topics": check_topics(data, required)}
    if "/clock" in required:
        checks["clock"] = check_clock(data["clock"])
    if manifest.get("joint_states", "/joint_states") in required:
        checks["joint_states"] = check_joint_states(data["joint_states"])
    if "/tf" in required or "/tf_static" in required:
        edges = [tuple(edge) for edge in manifest.get("required_tf_edges", [])]
        checks["tf"] = check_tf_tree(data["tf_edges"], edges)
    watchdog = manifest.get("watchdog")
    if watchdog:
        checks["watchdog"] = check_watchdog(
            data["raw_ns"], data["safe"], float(watchdog["timeout_s"]), float(watchdog["rate_hz"]),
            float(watchdog.get("slack_s", 0.05)),
        )
    image = manifest.get("image")
    if image:
        if len(data["images"]) < 2:
            checks["image"] = {"ok": False, "error": f"fewer than two samples on {image['topic']}"}
        else:
            report = build_image_report(image["topic"], data["images"])
            if image.get("camera_info"):
                if data["camera_info"] is None:
                    report["camera_info"] = {"ok": False, "error": "no CameraInfo sample"}
                else:
                    report["camera_info"] = build_camera_info_report(report, data["camera_info"])
                report["ok"] = report["ok"] and report["camera_info"]["ok"]
            checks["image"] = report
    return {"ok": all(check["ok"] for check in checks.values()), "checks": checks}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("bag", type=Path, help="rosbag2 directory (mcap or sqlite3)")
    parser.add_argument("--manifest", type=Path, default=Path(__file__).with_name("lab05_bag_manifest.json"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
        report = {"bag": str(args.bag), "manifest": str(args.manifest), **evaluate(read_bag(args.bag, manifest), manifest)}
    except (OSError, RuntimeError, ValueError, KeyError, json.JSONDecodeError) as error:
        report = {"ok": False, "bag": str(args.bag), "error": str(error)}
    rendered = json.dumps(report, indent=2)
    print(rendered)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    if not report["ok"]:
        sys.exit(2)


if __name__ == "__main__":
    main()
