import pytest

from starter import benchmark


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
    monkeypatch.setattr("starter.time.perf_counter", lambda: next(timestamps))
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
