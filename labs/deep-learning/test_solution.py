"""Tests for the broken-training lab.

By default these test *your* repair in broken_training.py; run the reference with
LAB_IMPL=solution. Part 1 is the causal repair; Part 2 is input hardening.
"""

import importlib
import os

import pytest

lab = importlib.import_module(os.environ.get("LAB_IMPL", "broken_training"))


# Part 1: the planted defect
def test_training_converges():
    losses, accuracy = lab.train()
    assert losses[-1] < 0.3 * losses[0]
    assert accuracy > 0.95


def test_loss_decreases_monotonically_for_a_small_step():
    losses, _ = lab.train(steps=50, learning_rate=0.05)
    assert all(later <= earlier + 1e-12 for earlier, later in zip(losses, losses[1:]))


# Part 2: hardening
@pytest.mark.parametrize(
    "arguments",
    [
        {"steps": 0},
        {"steps": True},
        {"learning_rate": 0},
        {"learning_rate": float("nan")},
        {"learning_rate": "0.2"},
        {"learning_rate": 1 + 2j},
    ],
)
def test_invalid_training_configuration_is_rejected(arguments):
    with pytest.raises(ValueError):
        lab.train(**arguments)
