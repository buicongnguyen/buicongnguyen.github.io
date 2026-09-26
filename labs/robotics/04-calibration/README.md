# Drill 4 — Calibration sweep

Implement `fit_grid` and `rmse` in `starter.py`. Fit a declared parameter on calibration rows only, then report error on untouched held-out rows. Reject empty grids, scalar targets, mismatched sample counts, and predictions that NumPy would silently broadcast.

## Run

```powershell
python -m pytest test_lab.py -q                                                          # your starter.py
$env:LAB_IMPL = "solution"; python -m pytest test_lab.py -q; Remove-Item Env:LAB_IMPL   # the reference
```

The tests fail until `starter.py` is complete. The docstring there is the specification. Record the first assumption that failed before you read `solution.py`.

Follow-up: report a bootstrap confidence interval for the held-out error and try a robust loss. Isaac Lab 07 applies the same discipline to a physics sweep.
