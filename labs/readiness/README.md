# Robotics Simulation Readiness Lab

Run these tasks before Module 1. Retain the command output, calculation, diagram, or contract named by each gate.

## Python, NumPy, and pytest

Implement and test vector normalization. Pass when `pytest -q` exits successfully, a zero vector raises `ValueError`, and vector elements are not processed in a Python loop.

```powershell
python -m pytest .\labs\readiness\test_readiness.py -q
```

## Git and command line

Create a temporary practice repository, make two focused commits on a branch, inspect `git diff HEAD~2..HEAD`, deliberately change two files, and restore only one. Pass with a clean, intelligible history and the intended final content.

## ROS contract

Create a table with columns: owner, topic, message type, QoS, source frame, target frame, acquisition stamp, clock, expected rate, tolerance, and failure behavior. Add a diagram that distinguishes DDS message movement from TF lookup.

## Experimental design

Compare two configurations with at least five repeated measurements each. State the independent variable, frozen controls, sample count, mean, confidence interval, held-out case, decision threshold, and the narrowest supported conclusion.

## Placement evidence

Record each result in `readiness-report.md`; link it from the capstone repository. A failed task is useful placement evidence, not a reason to mark it complete.
