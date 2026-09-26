"""Tests for the lock-ordering lab.

By default these exercise *your* repair in broken_locking.py; LAB_IMPL=solution checks
the reference. Its argument checks are already sound, so the deadlock tests are the ones
that fail until the lock order is repaired. Threads are daemons with deadlines, so an
unrepaired deadlock fails a test instead of hanging pytest.
"""

import importlib
import os
import threading
import time

import pytest

from broken_locking import Account
from lock_trace import run_opposing_pair, wait_for_graph

lab = importlib.import_module(os.environ.get("LAB_IMPL", "broken_locking"))


class SlowLock:
    """A Lock that holds briefly after each acquisition so an AB/BA order deadlocks reliably."""

    def __init__(self):
        self._lock = threading.Lock()

    def acquire(self, blocking=True, timeout=-1):
        acquired = self._lock.acquire(blocking, timeout)
        if acquired:
            time.sleep(0.001)
        return acquired

    def release(self):
        self._lock.release()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *_exc):
        self.release()
        return False


def call_bounded(function, *args, timeout=2.0):
    """Call in a daemon thread; re-raise its exception, or fail if it blocks on a lock."""
    outcome = {}

    def target():
        try:
            outcome["value"] = function(*args)
        except BaseException as error:  # noqa: BLE001 - re-raised in the test thread
            outcome["error"] = error

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        pytest.fail(f"{function.__name__}{args!r} blocked for {timeout}s: a thread is waiting on a lock it holds")
    if "error" in outcome:
        raise outcome["error"]
    return outcome.get("value")


def test_forced_ab_ba_interleaving_completes():
    # Deterministic: both threads hold their first lock before either asks for its second.
    completed, events, (left, right) = run_opposing_pair(lab.transfer, Account)
    assert completed, f"deadlock; wait-for graph: {wait_for_graph(events)}"
    assert left.balance + right.balance == 200


def test_opposing_transfers_complete_and_conserve_balance():
    # Equal names prove that the lock order does not depend on a non-unique label.
    left = Account("account", 1000, SlowLock())
    right = Account("account", 1000, SlowLock())

    def worker(source, target):
        for _ in range(20):
            lab.transfer(source, target, 1)

    threads = [
        threading.Thread(target=worker, args=pair, daemon=True)
        for pair in [(left, right), (right, left)] * 2
    ]
    for thread in threads:
        thread.start()
    deadline = time.monotonic() + 10
    for thread in threads:
        thread.join(max(0.0, deadline - time.monotonic()))
    assert not any(thread.is_alive() for thread in threads), "opposing transfers deadlocked (wait-for cycle)"
    assert (left.balance, right.balance) == (1000, 1000)


@pytest.mark.parametrize("amount", [0, -1, float("nan"), float("inf"), True])
def test_invalid_amount_is_rejected_without_mutation(amount):
    left = Account("A", 10)
    right = Account("B", 5)
    with pytest.raises(ValueError):
        call_bounded(lab.transfer, left, right, amount)
    assert (left.balance, right.balance) == (10, 5)


def test_self_transfer_and_overdraft_are_rejected():
    left = Account("A", 10)
    right = Account("B", 5)
    with pytest.raises(ValueError):
        call_bounded(lab.transfer, left, left, 1)
    with pytest.raises(ValueError):
        call_bounded(lab.transfer, left, right, 11)
    assert (left.balance, right.balance) == (10, 5)
