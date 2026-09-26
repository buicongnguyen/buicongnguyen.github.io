# Applied Lab — Diagnose a Broken Training Loop

`broken_training.py` trains a binary logistic classifier, but the loss rises. Its argument checks are sound; the planted defect is in the update rule. Diagnose it before reading `solution.py`.

1. Fix the seed and record the baseline loss curve.
2. Print parameter and gradient norms for five steps.
3. State the expected update direction for **every** parameter, then compare it with the code.
4. Repair only the update rule, rerun the same data, and keep the before/after curves.
5. Add a regression test for loss and accuracy.

The tests exercise your file by default, so they fail until the repair is right:

```powershell
python -m pytest test_solution.py -q
$env:LAB_IMPL = "solution"; python -m pytest test_solution.py -q; Remove-Item Env:LAB_IMPL   # reference
```

Hint, if you are stuck after step 3: fixing only the weight update leaves the loss at about 4.5 and accuracy near 0.55. Ask which other parameter is updated.

Submit observation → invariant → discriminating check → repair → regression. The artifact is the causal diagnosis, not only the corrected lines.
