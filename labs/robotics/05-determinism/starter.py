"""Drill 5: reset and determinism regression. Implement rollout and first_divergence.

    python -m pytest test_lab.py -q      # tests this file; they fail until you finish
"""

import numpy as np  # noqa: F401 - you will need it


def rollout(seed, steps=100):
    """Return a length-`steps` trace of the process state = 0.98 * state + N(0, 0.01).

    Use one np.random.default_rng(seed) per rollout, starting from state 0.0, so the same
    seed always reproduces the same trace. Raise ValueError when:
    - seed is not an integer (None would draw fresh OS entropy: silently nondeterministic);
    - steps is not a positive integer (a bool is not an integer here).
    """
    raise NotImplementedError("implement rollout")


def first_divergence(left, right, atol=1e-12, rtol=1e-12):
    """Return the index of the first sample where two traces disagree, or None.

    Samples agree when np.isclose(left, right, atol=atol, rtol=rtol). Report the first
    divergent index, not only whether the final checksums match. Raise ValueError when:
    - a trace is not numeric, or the shapes differ;
    - a trace contains NaN or infinity (inf == inf would otherwise look like agreement);
    - atol or rtol is not a finite, non-negative number.
    """
    raise NotImplementedError("implement first_divergence")
