"""Tests for this drill. They exercise starter.py (your work) by default and fail until it is
complete; LAB_IMPL=solution runs them against the reference implementation.
"""

import importlib
import os

import numpy as np
import pytest

lab = importlib.import_module(os.environ.get("LAB_IMPL", "starter"))
first_divergence = lab.first_divergence
rollout = lab.rollout


def test_seed_and_divergence_contract():
    a = rollout(42)
    b = rollout(42)
    c = rollout(43)
    np.testing.assert_array_equal(a, b)
    assert first_divergence(a, b) is None
    assert first_divergence(a, c) == 0
    assert np.isfinite(a).all()


def test_repeated_resets_reproduce_the_reference():
    reference = rollout(42)
    for _ in range(100):
        assert first_divergence(rollout(42), reference) is None


def test_rejects_non_finite_state_and_unseeded_rollout():
    with pytest.raises(ValueError):
        first_divergence([0.0, float("inf")], [0.0, float("inf")])
    with pytest.raises(ValueError):
        first_divergence([0.0, float("nan")], [0.0, 1.0])
    with pytest.raises(ValueError):
        rollout(None)


def test_rejects_invalid_lengths_shapes_and_tolerances():
    with pytest.raises(ValueError):
        rollout(42, steps=0)
    with pytest.raises(ValueError):
        first_divergence([1, 2], [[1, 2]])
    with pytest.raises(ValueError):
        first_divergence([1], [1], atol=-1)
    with pytest.raises(ValueError):
        first_divergence(["not-a-number"], ["not-a-number"])
    with pytest.raises(ValueError):
        first_divergence([1], [1], atol="1e-12")


def test_reports_the_first_divergent_sample_not_just_a_mismatch():
    reference = rollout(42)
    perturbed = reference.copy()
    perturbed[37] += 1e-6
    perturbed[80] += 1.0
    assert first_divergence(reference, perturbed) == 37
    assert first_divergence(reference, reference + 1e-15, atol=1e-12, rtol=0) is None
