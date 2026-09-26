"""Deterministically reproduce the AB/BA deadlock and print the wait-for cycle.

    python repro_deadlock.py                 # the planted defect: exits 1 and prints the cycle
    python repro_deadlock.py solution        # a repair: exits 0
"""

import importlib
import sys

from broken_locking import Account
from lock_trace import run_opposing_pair, wait_for_graph


def main() -> int:
    module = sys.argv[1] if len(sys.argv) > 1 else "broken_locking"
    transfer = importlib.import_module(module).transfer
    completed, events, (left, right) = run_opposing_pair(transfer, Account)
    print(f"target: {module}.transfer")
    for thread, kind, lock in events:
        print(f"  {thread:>2} {kind:<7} {lock}")
    if completed:
        print(f"completed; balances {left.balance} + {right.balance} = {left.balance + right.balance}")
        return 0
    print("DEADLOCK: wait-for graph")
    for thread, entry in sorted(wait_for_graph(events).items()):
        print(f"  {thread} holds {entry['holds']} and waits for {entry['waiting_for']}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
