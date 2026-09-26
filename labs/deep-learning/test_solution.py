"""Tests for the broken-training lab.

By default these exercise *your* repair in broken_training.py; LAB_IMPL=solution checks
the reference. The argument checks in broken_training.py are already sound, so every
failure here traces back to the planted update-rule defect.
"""

import importlib
import os

import pytest

lab = importlib.import_module(os.environ.get("LAB_IMPL", "broken_training"))


def test_training_converges():
    losses, accuracy = lab.train()
    assert losses[-1] < 0.3 * losses[0]
    assert accuracy > 0.95


def test_loss_decreases_monotonically_for_a_small_step():
    losses, _ = lab.train(steps=50, learning_rate=0.05)
    assert all(later <= earlier + 1e-12 for earlier, later in zip(losses, losses[1:]))


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
