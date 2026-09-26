# Robotics Simulation Readiness Lab

Run these tasks before Module 0. Retain the command output, calculation, diagram, or contract named by each gate.

## Python, NumPy, transforms, and inertia

Implement `normalize_rows`, `compose`, and `box_inertia` in `starter.py`; each docstring is the specification. Pass when the tests below exit successfully. `normalize_rows` must not loop over vector elements in Python, and a zero vector must raise `ValueError`.

```powershell
python -m pytest .\labs\readiness\test_readiness.py -q                                   # your starter.py
$env:LAB_IMPL = "solution"; python -m pytest .\labs\readiness\test_readiness.py -q; Remove-Item Env:LAB_IMPL   # reference
```

Then do the calculations by hand:
- Box inertia: calculate it for new dimensions, then check your numbers with `python .\labs\readiness\inertia_task.py`.
- Transform order: explain it, then run `python .\labs\readiness\transform_task.py`.
- Step response: change gains and mass in `python .\labs\readiness\step_response.py` and predict the overshoot first.

## Git and command line

Create a temporary practice repository, make two focused commits on a branch, inspect `git diff HEAD~2..HEAD`, deliberately change two files, and restore only one. Pass when `git status` shows exactly the one change you kept, the history is intelligible, and the final content is what you intended.

## ROS contract

Create a table with columns: owner, topic, message type, QoS, source frame, target frame, acquisition stamp, clock, expected rate, tolerance, and failure behavior. Add a diagram that distinguishes DDS message movement from TF lookup.

## Experimental design

Compare two configurations with at least five repeated measurements each. State the independent variable, frozen controls, sample count, mean, confidence interval, held-out case, decision threshold, and the narrowest supported conclusion.

## Placement evidence

Record each result in `readiness-report.md`; link it from the capstone repository. A failed task is useful placement evidence, not a reason to mark it complete.
