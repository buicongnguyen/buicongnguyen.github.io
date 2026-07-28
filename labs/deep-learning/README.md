# Applied Lab — Diagnose a Broken Training Loop

`broken_training.py` trains a binary classifier, but loss rises. Diagnose it before reading `solution.py`.

1. Fix the seed and record baseline loss.
2. Print parameter and gradient norms for five steps.
3. State the expected update direction.
4. Change one line, rerun the same data, and retain before/after curves.
5. Add a regression for loss and accuracy.

Pass `python -m pytest test_solution.py -q`. Submit observation → invariant → discriminating check → repair → regression. The artifact is the causal diagnosis, not only the corrected line.
