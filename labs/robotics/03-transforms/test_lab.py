"""Tests for this drill. They exercise starter.py (your work) by default and fail until it is
complete; LAB_IMPL=solution runs them against the reference implementation.
"""

import importlib
import os

import numpy as np
import pytest

lab = importlib.import_module(os.environ.get("LAB_IMPL", "starter"))
compose = lab.compose
transform_point = lab.transform_point


def test_frame_order_and_round_trip():
    w_b = np.eye(4)
    w_b[:3, :3] = [[0, -1, 0], [1, 0, 0], [0, 0, 1]]
    w_b[:3, 3] = [1, 0, 0]
    b_c = np.eye(4)
    b_c[:3, 3] = [2, 0, 0]
    w_c = compose(w_b, b_c)
    np.testing.assert_allclose(transform_point(w_c, [0, 0, 0]), [1, 2, 0])
    # Reversed composition (C from W order) lands somewhere else.
    assert not np.allclose(transform_point(compose(b_c, w_b), [0, 0, 0]), [1, 2, 0])
    # Round trip through the implementation under test, not only through NumPy.
    point_c = np.array([1.0, 2.0, 3.0])
    np.testing.assert_allclose(transform_point(np.linalg.inv(w_c), transform_point(w_c, point_c)), point_c, atol=1e-12)


def test_rejects_non_rigid_transform_and_non_finite_point():
    scaled = np.eye(4)
    scaled[0, 0] = 2
    with pytest.raises(ValueError):
        compose(scaled, np.eye(4))
    with pytest.raises(ValueError):
        compose(np.eye(3), np.eye(4))
    with pytest.raises(ValueError):
        transform_point(np.eye(4)[:3], [0, 0, 0])
    with pytest.raises(ValueError):
        transform_point(np.eye(4), [np.nan, 0, 0])
