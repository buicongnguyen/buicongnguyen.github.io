"""Drill 6: fair benchmark harness. Implement benchmark.

    python -m pytest test_lab.py -q      # tests this file; they fail until you finish
"""

import math  # noqa: F401 - you will need these
import statistics  # noqa: F401
import time  # noqa: F401 - call time.perf_counter(); the tests replace it with a fake clock


def benchmark(operation, warmup=3, repeats=10, synchronize=lambda: None):
    """Time `operation` and return a result dictionary.

    - Run `warmup` untimed calls first, each followed by synchronize().
    - For each of `repeats` measured calls: synchronize(), read time.perf_counter(), call
      operation(), synchronize(), read time.perf_counter() again. Synchronizing before
      the second read makes asynchronous work (for example a GPU kernel) count.
    - Return {"operation": its __qualname__, "warmup", "repeats", "median_s", "p90_s"},
      where p90_s is the nearest-rank 90th percentile: the ceil(0.9 * n)-th smallest sample.

    Raise ValueError when operation or synchronize is not callable, warmup is not a
    non-negative integer, or repeats is not a positive integer (a bool is not an integer).
    """
    raise NotImplementedError("implement benchmark")
