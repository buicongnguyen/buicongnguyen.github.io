import numpy as np
import pytest
from starter import validate_inertia


def test_valid_and_invalid_inertia():
    np.testing.assert_allclose(validate_inertia(np.diag([2.0, 3.0, 4.0])), [2.0, 3.0, 4.0])
    with pytest.raises(ValueError):
        validate_inertia(np.diag([1.0, 1.0, 3.0]))
    with pytest.raises(ValueError):
        validate_inertia([[1, 0.1, 0], [0, 1, 0], [0, 0, 1]])
    # Symmetric with a positive diagonal, but indefinite (eigenvalues -1, 1, 3):
    # a check that inspects only the diagonal accepts it.
    with pytest.raises(ValueError):
        validate_inertia([[1, 2, 0], [2, 1, 0], [0, 0, 1]])
    rotated = validate_inertia([[2.5, 0.5, 0], [0.5, 2.5, 0], [0, 0, 4]])
    np.testing.assert_allclose(rotated, [2.0, 3.0, 4.0])
    with pytest.raises(ValueError):
        validate_inertia(np.eye(3), atol=float("nan"))
    with pytest.raises(ValueError):
        validate_inertia(np.eye(3), atol="1e-10")
