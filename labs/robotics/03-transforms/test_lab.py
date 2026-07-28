import numpy as np
import pytest

from starter import compose, transform_point


def test_frame_order_and_round_trip():
    w_b = np.eye(4)
    w_b[:3, :3] = [[0, -1, 0], [1, 0, 0], [0, 0, 1]]
    w_b[:3, 3] = [1, 0, 0]
    b_c = np.eye(4)
    b_c[:3, 3] = [2, 0, 0]
    w_c = compose(w_b, b_c)
    np.testing.assert_allclose(transform_point(w_c, [0, 0, 0]), [1, 2, 0])
    np.testing.assert_allclose(np.linalg.inv(w_c) @ (w_c @ [1, 2, 3, 1]), [1, 2, 3, 1])


def test_rejects_non_rigid_transform_and_non_finite_point():
    scaled = np.eye(4)
    scaled[0, 0] = 2
    with pytest.raises(ValueError):
        compose(scaled, np.eye(4))
    with pytest.raises(ValueError):
        transform_point(np.eye(4), [np.nan, 0, 0])
