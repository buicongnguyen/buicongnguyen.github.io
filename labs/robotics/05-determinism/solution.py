import numpy as np


def rollout(seed, steps=100):
    # seed=None would draw fresh OS entropy and silently make the rollout nondeterministic.
    if isinstance(seed, bool) or not isinstance(seed, (int, np.integer)):
        raise ValueError("seed must be an integer")
    if isinstance(steps, bool) or not isinstance(steps, (int, np.integer)) or steps <= 0:
        raise ValueError("steps must be a positive integer")
    rng = np.random.default_rng(seed)
    state = 0.0
    rows = []
    for _ in range(steps):
        state = 0.98 * state + rng.normal(0, 0.01)
        rows.append(state)
    return np.asarray(rows)


def first_divergence(left, right, atol=1e-12, rtol=1e-12):
    try:
        left_values = np.asarray(left, dtype=float)
        right_values = np.asarray(right, dtype=float)
    except (TypeError, ValueError) as error:
        raise ValueError("traces must contain numeric values") from error
    if left_values.shape != right_values.shape:
        raise ValueError("traces must have matching shapes")
    # inf == inf would otherwise count as agreement and NaN as an ordinary divergence.
    if not np.isfinite(left_values).all() or not np.isfinite(right_values).all():
        raise ValueError("traces must contain only finite state")
    if (
        isinstance(atol, (bool, np.bool_))
        or isinstance(rtol, (bool, np.bool_))
        or not isinstance(atol, (int, float, np.integer, np.floating))
        or not isinstance(rtol, (int, float, np.integer, np.floating))
        or not np.isfinite([atol, rtol]).all()
        or atol < 0
        or rtol < 0
    ):
        raise ValueError("tolerances must be finite and non-negative")
    if left_values.size == 0:
        return None
    matches = np.isclose(left_values, right_values, atol=atol, rtol=rtol, equal_nan=False)
    # One sample is one row of a multi-joint trace: report the sample, not the flattened element.
    per_sample = matches.reshape(matches.shape[0], -1).all(axis=1) if matches.ndim else matches.reshape(1)
    return None if per_sample.all() else int(np.flatnonzero(~per_sample)[0])
