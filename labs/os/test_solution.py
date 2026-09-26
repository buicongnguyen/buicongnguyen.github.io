import importlib
import os
import threading
import time

import pytest

from broken_locking import Account

# The tests exercise the file you repair; LAB_IMPL=solution checks the reference.
transfer = importlib.import_module(os.environ.get("LAB_IMPL", "broken_locking")).transfer


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


def test_opposing_transfers_complete_and_conserve_balance():
    # Equal names prove that the lock order does not depend on a non-unique label.
    left = Account("account", 1000, SlowLock())
    right = Account("account", 1000, SlowLock())

    def worker(source, target):
        for _ in range(20):
            transfer(source, target, 1)

    # Daemon threads: a deadlocked run fails the test instead of hanging pytest.
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
    assert left.balance + right.balance == 2000


@pytest.mark.parametrize("amount", [0, -1, float("nan"), float("inf"), True])
def test_invalid_amount_is_rejected_without_mutation(amount):
    left = Account("A", 10)
    right = Account("B", 5)
    with pytest.raises(ValueError):
        transfer(left, right, amount)
    assert (left.balance, right.balance) == (10, 5)


def test_self_transfer_and_overdraft_are_rejected():
    left = Account("A", 10)
    right = Account("B", 5)
    with pytest.raises(ValueError):
        transfer(left, left, 1)
    with pytest.raises(ValueError):
        transfer(left, right, 11)
    assert (left.balance, right.balance) == (10, 5)
