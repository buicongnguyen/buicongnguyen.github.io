"""Tests for this drill. They exercise starter.py (your work) by default and fail until it is
complete; LAB_IMPL=solution runs them against the reference implementation.
"""

import importlib
import os

import pytest

lab = importlib.import_module(os.environ.get("LAB_IMPL", "starter"))
benchmark = lab.benchmark


def test_warmup_and_measurement_counts():
    calls = []
    synchronizations = []
    result = benchmark(
        lambda: calls.append(1),
        warmup=2,
        repeats=5,
        synchronize=lambda: synchronizations.append(1),
    )
    assert len(calls) == 7
    assert len(synchronizations) == 12
    assert result["operation"] == "test_warmup_and_measurement_counts.<locals>.<lambda>"
    assert result["warmup"] == 2
    assert result["repeats"] == 5
    assert result["median_s"] >= 0
    assert result["p90_s"] >= result["median_s"]


def test_p90_uses_nearest_rank(monkeypatch):
    timestamps = iter([0, 1, 1, 3, 3, 6, 6, 10, 10, 110])
    monkeypatch.setattr(lab.time, "perf_counter", lambda: next(timestamps))
    result = benchmark(lambda: None, warmup=0, repeats=5)
    assert result["median_s"] == 3
    assert result["p90_s"] == 100


@pytest.mark.parametrize(
    "arguments",
    [
        {"warmup": -1},
        {"warmup": 1.5},
        {"repeats": 0},
        {"repeats": True},
    ],
)
def test_invalid_counts_are_rejected(arguments):
    with pytest.raises(ValueError):
        benchmark(lambda: None, **arguments)


def test_p90_is_the_nearest_rank_not_the_maximum(monkeypatch):
    # Ten samples of 1..10 s: the nearest-rank p90 is the 9th smallest, 9 s, not the maximum.
    ticks = iter([tick for duration in range(1, 11) for tick in (0, duration)])
    monkeypatch.setattr(lab.time, "perf_counter", lambda: next(ticks))
    result = benchmark(lambda: None, warmup=0, repeats=10)
    assert result["p90_s"] == 9
    assert result["median_s"] == 5.5


def test_the_clock_stops_after_synchronizing(monkeypatch):
    # synchronize() drains 1 s of pending asynchronous work; that time belongs to the sample.
    now = [0.0]
    monkeypatch.setattr(lab.time, "perf_counter", lambda: now[0])

    def synchronize():
        now[0] += 1.0

    result = benchmark(lambda: None, warmup=0, repeats=3, synchronize=synchronize)
    assert result["median_s"] == 1.0
