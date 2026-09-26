"""Readiness tasks: implement these three functions, then run the tests.

    python -m pytest test_readiness.py -q      # tests this file; they fail until you finish

solution.py is the reference; inertia_task.py and transform_task.py use it as an oracle to
check your hand calculations.
"""

from __future__ import annotations

import numpy as np


def normalize_rows(vectors: np.ndarray) -> np.ndarray:
    """Return each row scaled to unit Euclidean length, without a Python loop over elements.

    Raise ValueError for anything that is not a non-empty 2-D array of finite values, and
    for a zero row. A row such as [1e308, 1e308] must normalize correctly: squaring it
    overflows, so scale each row by its largest absolute value first.
    """
    raise NotImplementedError("implement normalize_rows")


def compose(a_from_b: np.ndarray, b_from_c: np.ndarray) -> np.ndarray:
    """Return A_from_C = A_from_B @ B_from_C for finite 4x4 rigid transforms.

    Raise ValueError unless both inputs have the final row [0, 0, 0, 1] and an orthonormal
    rotation block with determinant +1 (no scale, no reflection).
    """
    raise NotImplementedError("implement compose")


def box_inertia(mass: float, x: float, y: float, z: float) -> np.ndarray:
    """Return the 3x3 diagonal inertia of a solid box about its center.

    ixx = m (y^2 + z^2) / 12, iyy = m (x^2 + z^2) / 12, izz = m (x^2 + y^2) / 12.
    Raise ValueError unless the mass and every dimension are finite and positive.
    """
    raise NotImplementedError("implement box_inertia")
