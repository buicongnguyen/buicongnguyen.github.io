import math
from numbers import Real


def transfer(source, target, amount):
    """Transfer a positive finite amount while acquiring locks in one global order."""
    if source is target:
        raise ValueError("source and target must be different accounts")
    if isinstance(amount, bool) or not isinstance(amount, Real) or not math.isfinite(amount) or amount <= 0:
        raise ValueError("amount must be a positive finite number")

    # Names are not unique. Object identity supplies a strict process-local order,
    # so opposing transfers cannot form a wait-for cycle.
    first, second = sorted((source, target), key=id)
    with first.lock:
        with second.lock:
            if source.balance < amount:
                raise ValueError("insufficient balance")
            source.balance -= amount
            target.balance += amount
