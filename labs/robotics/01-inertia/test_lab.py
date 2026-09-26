"""Tests for this drill. They exercise starter.py (your work) by default and fail until it is
complete; LAB_IMPL=solution runs them against the reference implementation.
"""

import importlib
import os

import numpy as np
import pytest

lab = importlib.import_module(os.environ.get("LAB_IMPL", "starter"))
validate_inertia = lab.validate_inertia


def test_valid_and_invalid_inertia():
    np.testing.assert_allclose(validate_inertia(np.diag([2.0, 3.0, 4.0])), [2.0, 3.0, 4.0])
    with pytest.raises(ValueError):
        validate_inertia(np.diag([1.0, 1.0, 3.0]))
    with pytest.raises(ValueError):
        validate_inertia([[1, 0.1, 0], [0, 1, 0], [0, 0, 1]])
    # Symmetric with a positive diagonal, but indefinite (eigenvalues -1, 1, 3):
    # a check that inspects only the diagonal accepts it.
    with pytest.raises(ValueError):
        validate_inertia([[1, 2, 0], [2, 1, 0], [0, 0, 1]])
    rotated = validate_inertia([[2.5, 0.5, 0], [0.5, 2.5, 0], [0, 0, 4]])
    np.testing.assert_allclose(rotated, [2.0, 3.0, 4.0])
    with pytest.raises(ValueError):
        validate_inertia(np.eye(3), atol=float("nan"))
    with pytest.raises(ValueError):
        validate_inertia(np.eye(3), atol="1e-10")


def test_flat_plate_on_the_triangle_boundary_is_valid():
    # A thin plate has I3 == I1 + I2 exactly; it is a real body, not a violation.
    np.testing.assert_allclose(validate_inertia(np.diag([1.0, 1.0, 2.0])), [1.0, 1.0, 2.0])
