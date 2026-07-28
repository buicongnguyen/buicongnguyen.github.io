import numpy as np


def _as_transform(value):
    transform = np.asarray(value, float)
    if transform.shape != (4, 4) or not np.isfinite(transform).all():
        raise ValueError("expected a finite 4x4 transform")
    if not np.allclose(transform[3], [0, 0, 0, 1], atol=1e-10, rtol=0):
        raise ValueError("expected a homogeneous final row")
    rotation = transform[:3, :3]
    if (
        not np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-10, rtol=0)
        or not np.isclose(np.linalg.det(rotation), 1.0, atol=1e-10, rtol=0)
    ):
        raise ValueError("rotation must be orthonormal with determinant +1")
    return transform


def compose(a_from_b, b_from_c):
    result = _as_transform(a_from_b) @ _as_transform(b_from_c)
    if not np.isfinite(result).all():
        raise ValueError("composed transform must remain finite")
    return result


def transform_point(a_from_b, point_b):
    point = np.asarray(point_b, float)
    if point.shape != (3,) or not np.isfinite(point).all():
        raise ValueError("expected a finite xyz point")
    return (_as_transform(a_from_b) @ np.r_[point, 1.0])[:3]
