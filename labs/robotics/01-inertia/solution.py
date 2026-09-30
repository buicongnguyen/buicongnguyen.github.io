import numpy as np


def validate_inertia(tensor, atol=1e-10):
    """Return principal moments or raise ValueError for a non-physical tensor."""
    if (
        isinstance(atol, (bool, np.bool_))
        or not isinstance(atol, (int, float, np.integer, np.floating))
        or not np.isfinite(atol)
        or atol < 0
    ):
        raise ValueError("atol must be a finite non-negative scalar")
    values = np.asarray(tensor, dtype=float)
    if values.shape != (3, 3) or not np.isfinite(values).all():
        raise ValueError("inertia must be a finite 3x3 matrix")
    if not np.allclose(values, values.T, atol=atol, rtol=0):
        raise ValueError("inertia must be symmetric")
    principal = np.linalg.eigvalsh(values)
    # eigvalsh sorts ascending; comparing differences cannot overflow the way 2 * max can.
    if np.any(principal <= 0) or principal[2] - principal[1] > principal[0] + atol:
        raise ValueError("principal moments are not physically consistent")
    return principal
