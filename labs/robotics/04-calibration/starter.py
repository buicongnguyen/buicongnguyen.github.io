import numpy as np


def fit_grid(candidates, calibration_x, calibration_y, model):
    parameters = np.asarray(candidates, dtype=float)
    expected = np.asarray(calibration_y, dtype=float)
    features = np.asarray(calibration_x)
    if parameters.ndim != 1 or parameters.size == 0 or not np.isfinite(parameters).all():
        raise ValueError("candidates must be a non-empty finite one-dimensional sequence")
    if expected.size == 0 or not np.isfinite(expected).all():
        raise ValueError("calibration targets must be non-empty and finite")
    if features.ndim == 0 or features.shape[0] != expected.shape[0]:
        raise ValueError("calibration features and targets must have the same sample count")

    scores = []
    for parameter in parameters:
        prediction = np.asarray(model(calibration_x, float(parameter)), dtype=float)
        if prediction.shape != expected.shape or not np.isfinite(prediction).all():
            raise ValueError("model output must match the finite target shape")
        with np.errstate(over="ignore", invalid="ignore"):
            score = np.mean((prediction - expected) ** 2)
        if not np.isfinite(score):
            raise ValueError("calibration error must remain finite")
        scores.append(score)
    return float(parameters[int(np.argmin(scores))])


def rmse(expected, observed):
    expected_values = np.asarray(expected, dtype=float)
    observed_values = np.asarray(observed, dtype=float)
    if (
        expected_values.shape != observed_values.shape
        or expected_values.size == 0
        or not np.isfinite(expected_values).all()
        or not np.isfinite(observed_values).all()
    ):
        raise ValueError("expected and observed must be non-empty finite arrays with matching shapes")
    with np.errstate(over="ignore", invalid="ignore"):
        result = np.sqrt(np.mean((expected_values - observed_values) ** 2))
    if not np.isfinite(result):
        raise ValueError("RMSE must remain finite")
    return float(result)
