"""Drill 4: calibration sweep with a held-out check. Implement fit_grid and rmse.

    python -m pytest test_lab.py -q      # tests this file; they fail until you finish

Fit on calibration rows only, then report error on untouched held-out rows. A parameter
chosen by looking at the held-out rows is no longer validated by them.
"""

import numpy as np  # noqa: F401 - you will need it


def fit_grid(candidates, calibration_x, calibration_y, model):
    """Return the candidate parameter with the lowest mean squared calibration error.

    `model(calibration_x, parameter)` returns predictions shaped like calibration_y.
    Raise ValueError when:
    - candidates is empty, not one-dimensional, or not finite;
    - calibration_y is a scalar, empty, or not finite;
    - calibration_x and calibration_y have different sample counts;
    - a prediction's shape differs from calibration_y (do not let NumPy broadcast it) or
      a prediction or score is not finite.
    """
    raise NotImplementedError("implement fit_grid")


def rmse(expected, observed):
    """Return the root-mean-square error of two non-empty, finite, same-shape arrays.

    Raise ValueError otherwise. Hint: [1, 2] versus [[1], [2]] broadcasts to 2x2 in
    NumPy, which silently turns a shape bug into a wrong number.
    """
    raise NotImplementedError("implement rmse")
