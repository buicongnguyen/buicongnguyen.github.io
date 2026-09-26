"""Drill 1: mass and inertia validator. Implement validate_inertia, then run the tests.

    python -m pytest test_lab.py -q      # tests this file; they fail until you finish
"""

import numpy as np  # noqa: F401 - you will need it


def validate_inertia(tensor, atol=1e-10):
    """Return the principal moments (ascending) of a physical inertia tensor.

    Raise ValueError when:
    - atol is not a finite, non-negative number (a bool is not a number here);
    - tensor is not a finite 3x3 matrix;
    - tensor is not symmetric within atol;
    - any principal moment is not positive;
    - the largest principal moment exceeds the sum of the other two by more than atol
      (the triangle inequality every rigid body satisfies).

    Hints:
    - np.linalg.eigvalsh returns the eigenvalues of a symmetric matrix in ascending order.
    - Check the eigenvalues, not the diagonal: [[1, 2, 0], [2, 1, 0], [0, 0, 1]] has a
      positive diagonal but a negative principal moment.
    - A flat plate sits exactly on the triangle boundary (I3 == I1 + I2) and is valid.
    """
    raise NotImplementedError("implement validate_inertia")
