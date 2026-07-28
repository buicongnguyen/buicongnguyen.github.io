import numpy as np
import pytest

from step_response import simulate


def test_simulation_returns_finite_trace():
    trace = simulate(dt=0.01, duration=1.0)
    assert trace.shape == (100, 3)
    assert np.isfinite(trace).all()
    np.testing.assert_allclose(trace[[0, -1], 0], [0.01, 1.0])
    assert trace[-1, 1] > trace[0, 1]


@pytest.mark.parametrize(
    "arguments",
    [
        {"mass": 0},
        {"dt": -0.1},
        {"duration": 0},
        {"duration": 0.001, "dt": 0.01},
        {"kp": -1},
        {"kd": float("nan")},
    ],
)
def test_invalid_parameters_are_rejected(arguments):
    with pytest.raises(ValueError):
        simulate(**arguments)
