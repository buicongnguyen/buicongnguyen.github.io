# Applied Lab — Trace and Repair a Concurrency Failure

`broken_locking.py` contains AB/BA lock ordering. Reproduce the deadlock deterministically, draw the wait-for graph, explain why sleeps are not a repair, impose a global account-lock order, and verify bounded completion plus balance conservation.

## 1. Reproduce before repairing

```powershell
python repro_deadlock.py            # planted defect: prints the event log and the wait-for cycle, exits 1
```

`lock_trace.py` wraps each account lock and uses a two-thread barrier so both threads hold their first lock before either asks for its second. The deadlock then happens on every run, not occasionally. Record the first blocked acquisition and the cycle it prints.

## 2. Repair `broken_locking.py` and test it

The tests import your file by default. Threads run as daemons with timeouts, so an unrepaired deadlock fails the test instead of hanging pytest.

```powershell
python -m pytest test_solution.py -q -k "interleaving or opposing"   # Part 1: deadlock freedom
python -m pytest test_solution.py -q                                 # Part 2: also reject invalid, self, and overdraft transfers
python repro_deadlock.py broken_locking                              # should now exit 0
$env:LAB_IMPL = "solution"; python -m pytest test_solution.py -q; Remove-Item Env:LAB_IMPL   # reference
```

Part 2 includes a self-transfer. With a non-reentrant lock, `transfer(a, a, 1)` blocks forever on the lock it already holds, which is a second deadlock shape.

Retain the first blocked acquisition, the wait-for cycle, the repaired invariant (one global lock order), and the regression result.
