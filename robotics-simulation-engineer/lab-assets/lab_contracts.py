"""Pure validation logic shared by ROS-facing probes, the bag checker, and offline CI tests.

Nothing here imports ROS. Probes normalize messages into plain dicts and lists, then
call these functions, so every rule can be unit-tested without a simulator.
"""

from __future__ import annotations

import math
from typing import Any

# Bytes per pixel for the sensor_msgs/Image encodings the labs publish or record.
# Encoding names are case-sensitive in sensor_msgs/image_encodings.
BYTES_PER_PIXEL = {
    "mono8": 1,
    "8UC1": 1,
    "mono16": 2,
    "16UC1": 2,
    "rgb8": 3,
    "bgr8": 3,
    "rgba8": 4,
    "bgra8": 4,
    "32FC1": 4,
}


def _finite_positive(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0.0:
        raise ValueError(f"{name} must be positive and finite")
    return float(value)


def is_stale(last_receipt: float | None, now: float, timeout: float) -> bool:
    """Return whether a command has exceeded its steady-clock receipt timeout.

    NaN compares False with everything, so an unchecked NaN timeout would never go
    stale and the watchdog would forward commands forever: invalid input fails closed.
    """
    _finite_positive(timeout, "timeout")
    if not math.isfinite(now):
        raise ValueError("now must be finite")
    if last_receipt is None or not math.isfinite(last_receipt):
        return True
    return now - last_receipt > timeout


def build_image_report(topic: str, samples: list[dict[str, Any]]) -> dict[str, Any]:
    """Validate a bounded sequence of normalized sensor_msgs/Image samples."""
    if len(samples) < 2:
        raise ValueError("at least two image samples are required")

    first = samples[0]
    stamps = [int(sample["stamp_ns"]) for sample in samples]
    structural = all(
        int(sample["width"]) > 0
        and int(sample["height"]) > 0
        and int(sample["step"]) > 0
        # sensor_msgs/Image defines data as exactly step * height bytes.
        and int(sample["payload_bytes"]) == int(sample["step"]) * int(sample["height"])
        for sample in samples
    )
    # A row must hold width * bytes-per-pixel; unknown encodings still need at least one byte per pixel.
    row_stride = all(
        int(sample["step"]) >= int(sample["width"]) * BYTES_PER_PIXEL.get(sample["encoding"], 1)
        for sample in samples
    )
    bytes_per_pixel = BYTES_PER_PIXEL.get(first["encoding"])
    identity = ("width", "height", "step", "encoding", "frame_id")
    consistent = all(tuple(sample[key] for key in identity) == tuple(first[key] for key in identity) for sample in samples)
    stamps_increase = all(current > previous for previous, current in zip(stamps, stamps[1:]))
    stamp_span_ns = stamps[-1] - stamps[0]
    sim_rate_hz = None if stamp_span_ns <= 0 else (len(stamps) - 1) * 1_000_000_000 / stamp_span_ns
    checks = {
        "sample_count": len(samples) >= 2,
        "structural_payload": structural,
        "step_covers_row": row_stride,
        "encoding_nonempty": bool(first["encoding"]),
        "frame_id_nonempty": bool(first["frame_id"]),
        "geometry_consistent": consistent,
        "timestamps_strictly_increase": stamps_increase,
        "estimated_rate_finite": sim_rate_hz is not None and math.isfinite(sim_rate_hz),
    }
    return {
        "ok": all(checks.values()),
        "topic": topic,
        "checks": checks,
        "samples": len(samples),
        "frame_id": first["frame_id"],
        "first_stamp_ns": stamps[0],
        "last_stamp_ns": stamps[-1],
        "stamp_span_ns": stamp_span_ns,
        "estimated_sim_stamp_rate_hz": sim_rate_hz,
        "width": int(first["width"]),
        "height": int(first["height"]),
        "encoding": first["encoding"],
        "step": int(first["step"]),
        "bytes_per_pixel": bytes_per_pixel,
        "minimum_step": int(first["width"]) * (bytes_per_pixel or 1),
        "payload_bytes": int(first["payload_bytes"]),
        "expected_payload_bytes": int(first["step"]) * int(first["height"]),
    }


def build_camera_info_report(image_report: dict[str, Any], info: dict[str, Any]) -> dict[str, Any]:
    """Check that one normalized CameraInfo sample describes the validated image stream."""
    k = [float(value) for value in info["k"]]
    checks = {
        "frame_id_matches_image": info["frame_id"] == image_report["frame_id"],
        "width_matches_image": int(info["width"]) == image_report["width"],
        "height_matches_image": int(info["height"]) == image_report["height"],
        "focal_lengths_positive": len(k) == 9 and k[0] > 0.0 and k[4] > 0.0,
        "principal_point_inside_image": len(k) == 9
        and 0.0 <= k[2] <= image_report["width"]
        and 0.0 <= k[5] <= image_report["height"],
    }
    return {"ok": all(checks.values()), "checks": checks, "k": k}


def check_clock(stamps_ns: list[int]) -> dict[str, Any]:
    """Lab 01 contract: simulation time never moves backward and does advance."""
    if len(stamps_ns) < 2:
        return {"ok": False, "samples": len(stamps_ns), "error": "at least two /clock samples are required"}
    backward = [index for index in range(1, len(stamps_ns)) if stamps_ns[index] < stamps_ns[index - 1]]
    repeats = sum(1 for index in range(1, len(stamps_ns)) if stamps_ns[index] == stamps_ns[index - 1])
    checks = {"never_moves_backward": not backward, "advances": stamps_ns[-1] > stamps_ns[0]}
    return {
        "ok": all(checks.values()),
        "checks": checks,
        "samples": len(stamps_ns),
        "first_ns": stamps_ns[0],
        "last_ns": stamps_ns[-1],
        "repeated_values": repeats,
        "first_backward_index": backward[0] if backward else None,
    }


def check_joint_states(samples: list[dict[str, Any]]) -> dict[str, Any]:
    """Lab 02 contract: JointState arrays are structurally valid and time does not run backward."""
    if not samples:
        return {"ok": False, "samples": 0, "violations": ["no JointState samples"]}
    violations: list[str] = []
    names = list(samples[0]["name"])
    for index, sample in enumerate(samples):
        joint_names = list(sample["name"])
        count = len(joint_names)
        if count == 0:
            violations.append(f"sample {index}: empty name array")
        if len(set(joint_names)) != count:
            violations.append(f"sample {index}: duplicate joint names")
        if len(sample["position"]) != count:
            violations.append(f"sample {index}: len(position) != len(name)")
        for field in ("velocity", "effort"):
            if len(sample[field]) not in (0, count):
                violations.append(f"sample {index}: {field} is neither empty nor len(name)")
        values = [*sample["position"], *sample["velocity"], *sample["effort"]]
        if not all(math.isfinite(float(value)) for value in values):
            violations.append(f"sample {index}: non-finite value")
        if joint_names != names:
            violations.append(f"sample {index}: joint name order changed")
        if index and int(sample["stamp_ns"]) < int(samples[index - 1]["stamp_ns"]):
            violations.append(f"sample {index}: header stamp moved backward")
    return {"ok": not violations, "samples": len(samples), "joint_names": names, "violations": violations[:20]}


def _frame(name: str) -> str:
    return name[1:] if name.startswith("/") else name


def check_tf_tree(edges: list[dict[str, Any]], required_edges: list[tuple[str, str]] | None = None) -> dict[str, Any]:
    """Lab 02 contract: every observed TF edge forms one connected, acyclic tree.

    ``edges`` holds every (parent, child, static) triple seen during an episode. A child
    published under two different parents is an ownership conflict even if each
    individual message is valid.
    """
    parents: dict[str, set[str]] = {}
    static: dict[tuple[str, str], bool] = {}
    for edge in edges:
        parent, child = _frame(str(edge["parent"])), _frame(str(edge["child"]))
        parents.setdefault(child, set()).add(parent)
        static[(parent, child)] = static.get((parent, child), False) or bool(edge.get("static", False))
    violations: list[str] = []
    for child, owners in sorted(parents.items()):
        if len(owners) > 1:
            violations.append(f"frame {child!r} has multiple parents: {sorted(owners)}")
        if child in owners:
            violations.append(f"frame {child!r} is its own parent")
    frames = set(parents) | {parent for owners in parents.values() for parent in owners}
    roots = sorted(frames - set(parents))
    if frames and len(roots) != 1:
        violations.append(f"expected one TF root, found {roots}")
    # Walk each frame up its first parent; revisiting a frame on the same walk is a cycle.
    for start in sorted(frames):
        seen = {start}
        node = start
        while node in parents:
            node = sorted(parents[node])[0]
            if node in seen:
                violations.append(f"cycle through frame {node!r}")
                break
            seen.add(node)
    missing = [
        f"{parent}->{child}"
        for parent, child in (required_edges or [])
        if (_frame(parent), _frame(child)) not in static
    ]
    if missing:
        violations.append(f"required edges missing: {missing}")
    return {
        "ok": bool(frames) and not violations,
        "frames": sorted(frames),
        "roots": roots,
        "edges": [
            {"parent": parent, "child": child, "static": is_static}
            for (parent, child), is_static in sorted(static.items())
        ],
        "violations": sorted(set(violations)),
    }


def check_watchdog(
    raw_ns: list[int],
    safe: list[tuple[int, bool]],
    timeout_s: float,
    rate_hz: float,
    slack_s: float = 0.05,
) -> dict[str, Any]:
    """Lab 03 contract: after the raw command stream stops, a zero command follows within the bound.

    ``raw_ns`` are receipt times of /cmd_vel_raw; ``safe`` holds (receipt time, is_zero) for
    /cmd_vel. The bound is timeout + one publish period + slack. Times come from the
    recorder, so the slack absorbs recorder-side receipt jitter.
    """
    _finite_positive(timeout_s, "timeout_s")
    _finite_positive(rate_hz, "rate_hz")
    if not safe:
        return {"ok": False, "error": "no safe command samples"}
    bound_s = timeout_s + 1.0 / rate_hz + slack_s
    if not raw_ns:
        last_motion = max((stamp for stamp, is_zero in safe if not is_zero), default=None)
        zero_after = last_motion is not None and any(is_zero and stamp > last_motion for stamp, is_zero in safe)
        return {
            "ok": zero_after,
            "mode": "safe-stream-only",
            "zero_after_last_motion": zero_after,
            "note": "record /cmd_vel_raw as well to measure stale-to-zero latency",
        }
    last_raw = max(raw_ns)
    first_zero = min((stamp for stamp, is_zero in safe if is_zero and stamp > last_raw), default=None)
    latency_s = None if first_zero is None else (first_zero - last_raw) / 1e9
    return {
        "ok": latency_s is not None and latency_s <= bound_s,
        "mode": "raw-and-safe",
        "last_raw_ns": last_raw,
        "first_zero_after_raw_ns": first_zero,
        "stale_to_zero_s": latency_s,
        "bound_s": bound_s,
    }
