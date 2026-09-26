"""Instrumented lock that records acquisitions and can force the AB/BA interleaving.

With a shared two-party barrier, each thread pauses right after taking its first lock
until the other thread has taken its own first lock. Code that locks in argument order
then deadlocks every time instead of occasionally. Code that locks in one global order
never gets both threads past the barrier: the second thread blocks on the first lock,
the barrier times out, and the first thread finishes.
"""

from __future__ import annotations

import threading


class TracedLock:
    def __init__(self, name: str, events: list, barrier: threading.Barrier | None = None, pause: float = 0.2):
        self.name = name
        self._lock = threading.Lock()
        self._events = events
        self._barrier = barrier
        self._pause = pause

    def acquire(self, blocking: bool = True, timeout: float = -1) -> bool:
        thread = threading.current_thread().name
        self._events.append((thread, "wait", self.name))
        acquired = self._lock.acquire(blocking, timeout)
        if acquired:
            self._events.append((thread, "hold", self.name))
            if self._barrier is not None:
                try:
                    self._barrier.wait(timeout=self._pause)
                except threading.BrokenBarrierError:
                    pass
        return acquired

    def release(self) -> None:
        self._events.append((threading.current_thread().name, "release", self.name))
        self._lock.release()

    def __enter__(self) -> "TracedLock":
        self.acquire()
        return self

    def __exit__(self, *exc) -> bool:
        self.release()
        return False


def wait_for_graph(events: list) -> dict[str, dict]:
    """Reduce the event log to what each thread holds and which lock it is blocked on."""
    state: dict[str, dict] = {}
    for thread, kind, lock in events:
        entry = state.setdefault(thread, {"holds": [], "waiting_for": None})
        if kind == "wait":
            entry["waiting_for"] = lock
        elif kind == "hold":
            entry["holds"].append(lock)
            entry["waiting_for"] = None
        elif kind == "release" and lock in entry["holds"]:
            entry["holds"].remove(lock)
    return state


def run_opposing_pair(transfer, account_type, timeout: float = 2.0) -> tuple[bool, list, tuple]:
    """Run transfer(a, b) and transfer(b, a) under the forced interleaving.

    Returns (completed, events, (left, right)). Threads are daemons, so a deadlock
    is reported instead of hanging the interpreter.
    """
    events: list = []
    barrier = threading.Barrier(2)
    left = account_type("left", 100, lock=TracedLock("L1", events, barrier))
    right = account_type("right", 100, lock=TracedLock("L2", events, barrier))
    threads = [
        threading.Thread(target=transfer, args=(left, right, 1), name="T1", daemon=True),
        threading.Thread(target=transfer, args=(right, left, 1), name="T2", daemon=True),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout)
    return not any(thread.is_alive() for thread in threads), events, (left, right)
