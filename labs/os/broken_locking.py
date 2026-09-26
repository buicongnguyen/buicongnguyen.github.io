import math
from dataclasses import dataclass, field
from numbers import Real
from threading import Lock


@dataclass
class Account:
    name: str
    balance: int
    lock: Lock = field(default_factory=Lock)


def transfer(source, target, amount):
    """Deliberately broken: the argument checks are sound; the lock order is the planted defect."""
    if source is target:
        raise ValueError("source and target must be different accounts")
    if isinstance(amount, bool) or not isinstance(amount, Real) or not math.isfinite(amount) or amount <= 0:
        raise ValueError("amount must be a positive finite number")
    with source.lock:
        with target.lock:
            if source.balance < amount:
                raise ValueError("insufficient balance")
            source.balance -= amount; target.balance += amount
