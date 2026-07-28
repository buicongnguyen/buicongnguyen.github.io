"""Small executable prerequisite tasks."""
from __future__ import annotations

import numpy as np


def normalize_rows(vectors: np.ndarray) -> np.ndarray:
    values = np.asarray(vectors, dtype=float)
    if values.ndim != 2:
        raise ValueError("expected a two-dimensional array")
    if values.shape[0] == 0 or values.shape[1] == 0:
        raise ValueError("expected at least one non-empty vector")
    if not np.isfinite(values).all():
        raise ValueError("vectors must contain only finite values")
    scales = np.max(np.abs(values), axis=1, keepdims=True)
    if np.any(scales == 0):
        raise ValueError("cannot normalize a zero vector")
    # Scaling first avoids overflow for finite vectors near the dtype limit.
    scaled = values / scales
    return scaled / np.linalg.norm(scaled, axis=1, keepdims=True)


def _as_rigid_transform(value: np.ndarray) -> np.ndarray:
    transform = np.asarray(value, dtype=float)
    if transform.shape != (4, 4) or not np.isfinite(transform).all():
        raise ValueError("transforms must be finite 4x4 matrices")
    if not np.allclose(transform[3], [0.0, 0.0, 0.0, 1.0], atol=1e-10, rtol=0):
        raise ValueError("transform must have a homogeneous [0, 0, 0, 1] final row")
    rotation = transform[:3, :3]
    if (
        not np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-10, rtol=0)
        or not np.isclose(np.linalg.det(rotation), 1.0, atol=1e-10, rtol=0)
    ):
        raise ValueError("transform rotation must be orthonormal with determinant +1")
    return transform


def compose(a_from_b: np.ndarray, b_from_c: np.ndarray) -> np.ndarray:
    first = _as_rigid_transform(a_from_b)
    second = _as_rigid_transform(b_from_c)
    result = first @ second
    if not np.isfinite(result).all():
        raise ValueError("composed transform must remain finite")
    return result


def box_inertia(mass: float, x: float, y: float, z: float) -> np.ndarray:
    values = np.asarray([mass, x, y, z], dtype=float)
    if not np.isfinite(values).all() or np.any(values <= 0):
        raise ValueError("mass and dimensions must be positive")
    with np.errstate(over="ignore", invalid="ignore"):
        inertia = np.diag([
            mass * (y * y + z * z) / 12,
            mass * (x * x + z * z) / 12,
            mass * (x * x + y * y) / 12,
        ])
    if not np.isfinite(inertia).all():
        raise ValueError("mass and dimensions produce non-finite inertia")
    return inertia
