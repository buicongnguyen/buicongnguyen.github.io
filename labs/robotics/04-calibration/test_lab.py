"""Tests for this drill. They exercise starter.py (your work) by default and fail until it is
complete; LAB_IMPL=solution runs them against the reference implementation.
"""

import importlib
import os

import numpy as np
import pytest

lab = importlib.import_module(os.environ.get("LAB_IMPL", "starter"))
fit_grid = lab.fit_grid
rmse = lab.rmse


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
    with pytest.raises(ValueError):
        fit_grid([1.0], [1.0], 2.0, lambda x, p: p * np.asarray(x))


def test_selection_minimizes_squared_error_not_worst_case_error():
    # Squared error prefers p=0 (0.968 vs 1.088); a max-abs-error fit would pick p=1.
    chosen = fit_grid([0.0, 1.0], [1.0] * 5, [0.0, 0.0, 0.0, 0.0, 2.2], lambda x, p: p * np.asarray(x))
    assert chosen == 0.0


def test_rmse_of_large_finite_errors_does_not_overflow():
    np.testing.assert_allclose(rmse([1e200], [-1e200]), 2e200)
