"""Generate a measurable second-order step response without simulator dependencies."""
from __future__ import annotations

import numpy as np


def simulate(kp=25.0, kd=10.0, mass=1.0, dt=0.001, duration=3.0, target=1.0):
    parameters = np.asarray([kp, kd, mass, dt, duration, target], dtype=float)
    if not np.isfinite(parameters).all():
        raise ValueError("simulation parameters must be finite")
    if mass <= 0 or dt <= 0 or duration <= 0:
        raise ValueError("mass, dt, and duration must be positive")
    if kp < 0 or kd < 0:
        raise ValueError("controller gains must be non-negative")
    steps = int(duration / dt)
    if steps < 1:
        raise ValueError("duration must include at least one timestep")

    position = velocity = 0.0
    rows = []
    for step in range(steps):
        acceleration = (kp * (target - position) - kd * velocity) / mass
        velocity += acceleration * dt
        position += velocity * dt
        if not np.isfinite([acceleration, velocity, position]).all():
            raise ValueError("simulation became non-finite; reduce gains or timestep")
        rows.append(((step + 1) * dt, position, velocity))
    return np.asarray(rows)


if __name__ == "__main__":
    trace = simulate()
    peak = float(trace[:, 1].max())
    print({"peak": peak, "overshoot_percent": max(0.0, peak - 1.0) * 100, "final_error": abs(1.0 - trace[-1, 1])})
