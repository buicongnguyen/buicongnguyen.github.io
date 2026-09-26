# Drill 1 — Mass and inertia validator

Implement `validate_inertia` in `starter.py`. It returns the principal moments of a physical inertia tensor. It must reject non-finite, asymmetric, and non-positive tensors, and tensors whose principal moments violate the triangle inequality. A flat plate sits exactly on that boundary and is valid.

## Run

```powershell
python -m pytest test_lab.py -q                                                          # your starter.py
$env:LAB_IMPL = "solution"; python -m pytest test_lab.py -q; Remove-Item Env:LAB_IMPL   # the reference
```

The tests fail until `starter.py` is complete. The docstring there is the specification. Record the first assumption that failed before you read `solution.py`.

Follow-up: validate a URDF `<inertia>` block, including the case where the declared moments disagree with the collision geometry (see Isaac Lab 06).
