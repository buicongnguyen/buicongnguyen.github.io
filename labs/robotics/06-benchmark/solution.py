import math
import statistics
import time
from numbers import Integral


def benchmark(operation, warmup=3, repeats=10, synchronize=lambda: None):
    if not callable(operation) or not callable(synchronize):
        raise ValueError("operation and synchronize must be callable")
    if isinstance(warmup, bool) or not isinstance(warmup, Integral) or warmup < 0:
        raise ValueError("warmup must be a non-negative integer")
    if isinstance(repeats, bool) or not isinstance(repeats, Integral) or repeats <= 0:
        raise ValueError("repeats must be a positive integer")
    warmup = int(warmup)
    repeats = int(repeats)
    for _ in range(warmup):
        operation()
        synchronize()
    samples = []
    for _ in range(repeats):
        synchronize()
        start = time.perf_counter()
        operation()
        synchronize()
        samples.append(time.perf_counter() - start)
    ordered = sorted(samples)
    p90_index = math.ceil(0.9 * len(ordered)) - 1
    return {
        "operation": getattr(operation, "__qualname__", type(operation).__name__),
        "warmup": warmup,
        "repeats": repeats,
        "median_s": statistics.median(samples),
        "p90_s": ordered[p90_index],
    }
