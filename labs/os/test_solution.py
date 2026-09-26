"""Tests for the lock-ordering lab.

By default these test *your* repair in broken_locking.py. Run the reference with
LAB_IMPL=solution. Part 1 (deadlock freedom) is the causal repair; Part 2 (input
hardening) is the follow-up. Threads are daemons with join timeouts, so an unrepaired
deadlock fails the test instead of hanging pytest.
"""

import importlib
import os
import threading

import pytest

from broken_locking import Account
from lock_trace import run_opposing_pair, wait_for_graph

lab = importlib.import_module(os.environ.get("LAB_IMPL", "broken_locking"))


def call_bounded(function, *args, timeout=2.0):
    """Call in a daemon thread; re-raise its exception, or fail if it blocks (self-deadlock)."""
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


# Part 1: the planted defect
def test_forced_ab_ba_interleaving_completes():
    completed, events, (left, right) = run_opposing_pair(lab.transfer, Account)
    assert completed, f"deadlock; wait-for graph: {wait_for_graph(events)}"
    assert left.balance + right.balance == 200


def test_many_opposing_transfers_complete_and_conserve_balance():
    # Equal names prove that the lock order does not depend on a non-unique label.
    left = Account("account", 1000)
    right = Account("account", 1000)

    def worker(source, target):
        for _ in range(200):
            lab.transfer(source, target, 1)

    threads = [
        threading.Thread(target=worker, args=pair, daemon=True)
        for pair in [(left, right), (right, left)] * 4
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(5)
    assert not any(thread.is_alive() for thread in threads), "transfers did not finish: deadlock"
    assert (left.balance, right.balance) == (1000, 1000)


# Part 2: hardening
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
        call_bounded(lab.transfer, Account("C", 10), right, 11)
    assert (left.balance, right.balance) == (10, 5)
