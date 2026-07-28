"""Entry task: replace the sample transforms, explain the frame order, and test the round trip."""
import numpy as np

from readiness import compose

T_W_B = np.eye(4)
T_W_B[:3, :3] = np.array([
    [0.0, -1.0, 0.0],
    [1.0, 0.0, 0.0],
    [0.0, 0.0, 1.0],
])
T_W_B[:3, 3] = [1.0, 0.0, 0.0]
T_B_C = np.eye(4)
T_B_C[:3, 3] = [2.0, 0.0, 0.0]
T_W_C = compose(T_W_B, T_B_C)
POINT_C = np.array([0.0, 0.0, 0.0, 1.0])
np.testing.assert_allclose(T_W_C @ POINT_C, [1.0, 2.0, 0.0, 1.0])
ROUND_TRIP_ERROR = np.linalg.norm(np.linalg.inv(T_W_C) @ (T_W_C @ POINT_C) - POINT_C)
assert ROUND_TRIP_ERROR < 1e-9
