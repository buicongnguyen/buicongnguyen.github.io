# Drill 3 — Transform composition

Implement `compose` and `transform_point` in `starter.py` with explicit `A_from_B` naming. Both functions accept only finite 4x4 rigid transforms: no scale, no reflection. The tests check frame order, reject reversed composition, and round-trip a point through the inverse.

## Run

```powershell
python -m pytest test_lab.py -q                                                          # your starter.py
$env:LAB_IMPL = "solution"; python -m pytest test_lab.py -q; Remove-Item Env:LAB_IMPL   # the reference
```

The tests fail until `starter.py` is complete. The docstring there is the specification. Record the first assumption that failed before you read `solution.py`.

Follow-up: add `invert(a_from_b)` without `np.linalg.inv`, using the rotation transpose.
