from dataclasses import dataclass, field
from threading import Lock


@dataclass
class Account:
    name: str
    balance: int
    lock: Lock = field(default_factory=Lock)


def transfer(source, target, amount):
    with source.lock:
        with target.lock:
            source.balance -= amount; target.balance += amount
