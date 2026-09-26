# Drill 5 — Reset and determinism regression

Implement `rollout` and `first_divergence` in `starter.py`. The tests check four things:
- the same seed reproduces the same trace, and a different seed does not;
- 100 repeated resets reproduce the reference;
- non-finite state and unseeded rollouts are rejected;
- the *first* divergent sample is reported, not only a final checksum mismatch.

## Run

```powershell
python -m pytest test_lab.py -q                                                          # your starter.py
$env:LAB_IMPL = "solution"; python -m pytest test_lab.py -q; Remove-Item Env:LAB_IMPL   # the reference
```

The tests fail until `starter.py` is complete. The docstring there is the specification. Record the first assumption that failed before you read `solution.py`.

Follow-up: apply `first_divergence` to two headless Isaac Sim runs of the same scene and seed.
