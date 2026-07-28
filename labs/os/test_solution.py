from concurrent.futures import ThreadPoolExecutor
import pytest

from broken_locking import Account
from solution import transfer


def test_opposing_transfers_complete_and_conserve_balance():
    # Equal names prove that the lock order does not depend on a non-unique label.
    left = Account("account", 1000)
    right = Account("account", 1000)
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = []
        for _ in range(200):
            futures.append(pool.submit(transfer, left, right, 1))
            futures.append(pool.submit(transfer, right, left, 1))
        for future in futures:
            future.result(timeout=2)
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
