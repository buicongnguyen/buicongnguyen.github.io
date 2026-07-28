import numpy as np


def rollout(seed, steps=100):
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
    if left_values.size == 0:
        return None
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
    matches = np.isclose(left_values, right_values, atol=atol, rtol=rtol, equal_nan=False)
    return None if matches.all() else int(np.flatnonzero(~matches)[0])
