import numpy as np
import pytest

from readiness import box_inertia, compose, normalize_rows


def test_normalize_rows_and_reject_zero():
    output = normalize_rows(np.array([[3.0, 4.0], [1.0, 0.0]]))
    np.testing.assert_allclose(np.linalg.norm(output, axis=1), [1.0, 1.0])
    huge = normalize_rows(np.array([[1e308, 1e308]]))
    np.testing.assert_allclose(huge, [[2 ** -0.5, 2 ** -0.5]])
    with pytest.raises(ValueError):
        normalize_rows(np.array([[0.0, 0.0]]))
    with pytest.raises(ValueError):
        normalize_rows(np.array([[np.nan, 1.0]]))
    with pytest.raises(ValueError):
        normalize_rows(np.empty((0, 2)))


def test_transform_round_trip():
    a_from_b = np.eye(4)
    a_from_b[:3, :3] = [[0, -1, 0], [1, 0, 0], [0, 0, 1]]
    a_from_b[:3, 3] = [1.0, 0.0, 0.0]
    b_from_c = np.eye(4)
    b_from_c[:3, 3] = [2.0, 0.0, 0.0]
    a_from_c = compose(a_from_b, b_from_c)
    point_c = np.array([0.0, 0.0, 0.0, 1.0])
    np.testing.assert_allclose(a_from_c @ point_c, [1.0, 2.0, 0.0, 1.0])
    np.testing.assert_allclose(np.linalg.inv(a_from_c) @ (a_from_c @ point_c), point_c, atol=1e-12)
    invalid = np.eye(4)
    invalid[0, 0] = 2.0
    with pytest.raises(ValueError):
        compose(invalid, b_from_c)


def test_box_inertia():
    np.testing.assert_allclose(box_inertia(12.0, 2.0, 4.0, 6.0), np.diag([52.0, 40.0, 20.0]))
    with pytest.raises(ValueError):
        box_inertia(float("nan"), 2.0, 4.0, 6.0)
