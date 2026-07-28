# Drill 2 — URDF joint graph validator

Pass a list of `(parent, child)` joints to `validate_tree`. Reject duplicate children, cycles, disconnected components, and multiple roots. Tests are executable with `python -m pytest test_lab.py -q`. Extend the starter to parse XML as the interview follow-up.
