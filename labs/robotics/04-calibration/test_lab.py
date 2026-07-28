import numpy as np
import pytest

from starter import fit_grid, rmse


def test_calibration_uses_declared_split():
    model = lambda x, p: p * np.asarray(x)
    chosen = fit_grid([1.0, 2.0, 3.0], np.array([1, 2, 3]), np.array([2, 4, 6]), model)
    assert chosen == 2.0
    assert rmse(model([4, 5], chosen), [8, 10]) == 0.0


def test_rejects_empty_grid_and_shape_broadcasting():
    with pytest.raises(ValueError):
        fit_grid([], [1, 2], [2, 4], lambda x, p: np.asarray(x) * p)
    with pytest.raises(ValueError):
        fit_grid([1], [1, 2], [2, 4], lambda _x, _p: np.asarray([[2], [4]]))
    with pytest.raises(ValueError):
        rmse([1, 2], [[1], [2]])
