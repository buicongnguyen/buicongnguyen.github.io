# Applied Lab — Trace and Repair a Concurrency Failure

`broken_locking.py` contains AB/BA lock ordering. Draw the wait-for graph, capture thread stacks under a watchdog, explain why sleeps are not a repair, impose a global account-lock order, and repeatedly verify bounded completion plus balance conservation.

Pass `python -m pytest test_solution.py -q`. Retain the first blocked acquisition, wait-for cycle, repaired invariant, and regression result.
