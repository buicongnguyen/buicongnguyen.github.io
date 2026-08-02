"""Pure validation logic shared by ROS-facing probes and offline CI tests."""

from __future__ import annotations

import math
from typing import Any


def is_stale(last_receipt: float | None, now: float, timeout: float) -> bool:
    """Return whether a command has exceeded its steady-clock receipt timeout."""
    if timeout <= 0.0:
        raise ValueError("timeout must be positive")
    return last_receipt is None or now - last_receipt > timeout


def build_image_report(topic: str, samples: list[dict[str, Any]]) -> dict[str, Any]:
    """Validate a bounded sequence of normalized Image message samples."""
    if len(samples) < 2:
        raise ValueError("at least two image samples are required")

    first = samples[0]
    stamps = [int(sample["stamp_ns"]) for sample in samples]
    structural = all(
        int(sample["width"]) > 0
        and int(sample["height"]) > 0
        and int(sample["step"]) > 0
        and int(sample["payload_bytes"]) >= int(sample["step"]) * int(sample["height"])
        for sample in samples
    )
    identity = ("width", "height", "step", "encoding", "frame_id")
    consistent = all(tuple(sample[key] for key in identity) == tuple(first[key] for key in identity) for sample in samples)
    stamps_increase = all(current > previous for previous, current in zip(stamps, stamps[1:]))
    stamp_span_ns = stamps[-1] - stamps[0]
    sim_rate_hz = None if stamp_span_ns <= 0 else (len(stamps) - 1) * 1_000_000_000 / stamp_span_ns
    checks = {
        "sample_count": len(samples) >= 2,
        "structural_payload": structural,
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
        "payload_bytes": int(first["payload_bytes"]),
        "minimum_expected_bytes": int(first["step"]) * int(first["height"]),
    }
