import numpy as np
import pytest

from starter import first_divergence, rollout


def test_seed_and_divergence_contract():
    a = rollout(42)
    b = rollout(42)
    c = rollout(43)
    np.testing.assert_array_equal(a, b)
    assert first_divergence(a, b) is None
    assert first_divergence(a, c) == 0
    assert np.isfinite(a).all()


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
