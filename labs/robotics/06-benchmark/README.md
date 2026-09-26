# Drill 6 — Fair benchmark harness

Implement `benchmark` in `starter.py`. It separates warmup from measured calls and synchronizes around every timed call, so asynchronous work counts. It reports the median and the nearest-rank 90th percentile. The tests replace `time.perf_counter` with a fake clock, so time with that function.

## Run

```powershell
python -m pytest test_lab.py -q                                                          # your starter.py
$env:LAB_IMPL = "solution"; python -m pytest test_lab.py -q; Remove-Item Env:LAB_IMPL   # the reference
```

The tests fail until `starter.py` is complete. The docstring there is the specification. Record the first assumption that failed before you read `solution.py`.

Follow-up: serialize the hardware and configuration identity with each result, and compare two runs statistically. Isaac Lab 09 does both.
