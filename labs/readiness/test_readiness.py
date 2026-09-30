"""Readiness tests. They exercise starter.py (your work) by default and fail until it is
complete; LAB_IMPL=solution runs them against the reference implementation.
"""

import ast
import importlib
import inspect
import os
import textwrap

import numpy as np
import pytest

lab = importlib.import_module(os.environ.get("LAB_IMPL", "starter"))
box_inertia = lab.box_inertia
compose = lab.compose
normalize_rows = lab.normalize_rows


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


def test_normalize_rows_uses_array_operations_not_a_python_loop():
    tree = ast.parse(textwrap.dedent(inspect.getsource(normalize_rows)))
    loops = [node for node in ast.walk(tree)
             if isinstance(node, (ast.For, ast.While, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp))]
    assert not loops, "normalize_rows must use NumPy array operations, not a Python loop"


def test_box_inertia_rejects_non_positive_mass_and_dimensions():
    for arguments in ((-12.0, 2.0, 4.0, 6.0), (12.0, 0.0, 4.0, 6.0)):
        with pytest.raises(ValueError):
            box_inertia(*arguments)


def test_compose_checks_both_arguments_and_rejects_reflections():
    with pytest.raises(ValueError):
        compose(np.eye(4), np.diag([-1.0, 1.0, 1.0, 1.0]))
    scaled = np.eye(4)
    scaled[2, 2] = 3.0
    with pytest.raises(ValueError):
        compose(np.eye(4), scaled)
