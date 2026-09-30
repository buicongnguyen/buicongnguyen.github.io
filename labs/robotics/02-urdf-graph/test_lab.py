"""Tests for this drill. They exercise starter.py (your work) by default and fail until it is
complete; LAB_IMPL=solution runs them against the reference implementation.
"""

import importlib
import os

import pytest

lab = importlib.import_module(os.environ.get("LAB_IMPL", "starter"))
validate_tree = lab.validate_tree


def test_tree_contracts():
    assert validate_tree([("base", "arm"), ("arm", "tool")]) == "base"
    with pytest.raises(ValueError):
        validate_tree([("a", "b"), ("c", "b")])
    with pytest.raises(ValueError):
        validate_tree([("a", "b"), ("b", "a")])
    # Multiple roots: two separate trees.
    with pytest.raises(ValueError):
        validate_tree([("base", "arm"), ("cart", "wheel")])
    # One root, plus a detached cycle that only a traversal can find.
    with pytest.raises(ValueError):
        validate_tree([("base", "arm"), ("x", "y"), ("y", "x")])
    with pytest.raises(ValueError):
        validate_tree([("", "arm")])
    with pytest.raises(ValueError):
        validate_tree([("base",)])


def test_multiple_parents_are_rejected_even_with_one_root():
    # "tool" has two parents, yet "base" is still the only root.
    with pytest.raises(ValueError):
        validate_tree([("base", "arm"), ("base", "tool"), ("arm", "tool")])


def test_detached_cycles_of_any_length_are_rejected():
    with pytest.raises(ValueError):
        validate_tree([("base", "arm"), ("x", "y"), ("y", "z"), ("z", "x")])
