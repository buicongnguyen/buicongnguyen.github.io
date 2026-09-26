"""Drill 3: rigid transform composition. Implement compose and transform_point.

    python -m pytest test_lab.py -q      # tests this file; they fail until you finish

Name every transform A_from_B: it maps coordinates expressed in frame B into frame A.
Then A_from_C = A_from_B @ B_from_C, and the inner frame names must match.
"""

import numpy as np  # noqa: F401 - you will need it


def compose(a_from_b, b_from_c):
    """Return the 4x4 A_from_C transform.

    Raise ValueError unless both inputs are finite 4x4 homogeneous rigid transforms:
    last row [0, 0, 0, 1], rotation block orthonormal (R.T @ R == I) with det(R) == +1.
    A scale or a reflection is not a rigid transform.
    """
    raise NotImplementedError("implement compose")


def transform_point(a_from_b, point_b):
    """Return point_b (a finite xyz point in frame B) expressed in frame A.

    Raise ValueError for a non-rigid transform or a point that is not three finite numbers.
    Hint: append 1 to make the point homogeneous, multiply, and drop the last element.
    """
    raise NotImplementedError("implement transform_point")
