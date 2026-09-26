"""Summarize repeatable simulation benchmark rows, detect regressions, and test speedup claims.

RTF (simulated seconds per wall second) is the primary metric. `frames` counts application
update frames, so `fps` is app-update FPS, not the physics step rate.

A comparison is only meaningful for the same workload, so each report records the
`--workload key=value` identity and a comparison refuses to run against a different one.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
import random
import statistics
import sys
from pathlib import Path

from report_io import emit

EXACT_PERMUTATION_LIMIT = 200_000
MONTE_CARLO_PERMUTATIONS = 20_000


def percentile(values: list[float], fraction: float) -> float:
    """Linear-interpolated percentile (numpy's default), so small samples are not over-stated."""
    ordered = sorted(values)
    index = (len(ordered) - 1) * fraction
    lower, upper = math.floor(index), math.ceil(index)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


def summarize(rows: list[dict[str, str]]) -> dict:
    metrics = []
    for index, row in enumerate(rows, start=1):
        # csv.DictReader fills cells missing from a short row with None.
        missing = [name for name in ("run", "sim_seconds", "wall_seconds", "frames") if row.get(name) is None]
        if missing:
            raise ValueError(f"benchmark row {index} is missing {', '.join(missing)}")
        wall = float(row["wall_seconds"])
        sim = float(row["sim_seconds"])
        frames = float(row["frames"])
        if not all(math.isfinite(value) for value in (wall, sim, frames)):
            raise ValueError("benchmark values must be finite")
        if wall <= 0.0 or sim < 0.0 or frames < 0.0:
            raise ValueError("wall_seconds must be positive; sim_seconds and frames non-negative")
        metrics.append({"run": row["run"], "rtf": sim / wall, "fps": frames / wall})
    if not metrics:
        raise ValueError("no benchmark rows")
    rtfs = [item["rtf"] for item in metrics]
    fps_values = [item["fps"] for item in metrics]
    mean_rtf = statistics.fmean(rtfs)
    return {
        "ok": True,
        "runs": len(metrics),
        "rtf": {
            "median": statistics.median(rtfs),
            "p05": percentile(rtfs, 0.05),
            "p95": percentile(rtfs, 0.95),
            "cv": 0.0 if mean_rtf == 0.0 else statistics.pstdev(rtfs) / mean_rtf,
        },
        "fps": {"median": statistics.median(fps_values), "p05": percentile(fps_values, 0.05), "p95": percentile(fps_values, 0.95)},
        "rows": metrics,
    }


def _midranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start
        while end + 1 < len(order) and values[order[end + 1]] == values[order[start]]:
            end += 1
        for position in range(start, end + 1):
            ranks[order[position]] = (start + end) / 2.0 + 1.0
        start = end + 1
    return ranks


def p_value_greater(candidate: list[float], reference: list[float], seed: int = 0) -> float:
    """One-sided Mann-Whitney permutation p-value that `candidate` tends to exceed `reference`.

    Exact over all label assignments when feasible, otherwise a seeded Monte Carlo estimate.
    With five runs on each side, complete separation gives p = 1/252 ~ 0.004.
    """
    pooled = candidate + reference
    ranks = _midranks(pooled)
    size = len(candidate)
    observed = sum(ranks[:size])
    total = math.comb(len(pooled), size)
    if total <= EXACT_PERMUTATION_LIMIT:
        hits = sum(1 for chosen in itertools.combinations(ranks, size) if sum(chosen) >= observed - 1e-9)
        return hits / total
    rng = random.Random(seed)
    hits = 0
    for _ in range(MONTE_CARLO_PERMUTATIONS):
        if sum(rng.sample(ranks, size)) >= observed - 1e-9:
            hits += 1
    return (hits + 1) / (MONTE_CARLO_PERMUTATIONS + 1)


def compare(report: dict, baseline: dict, max_regression: float, claim_improvement: bool, alpha: float) -> dict:
    if baseline.get("workload", {}) != report.get("workload", {}):
        return {
            "comparable": False,
            "error": "workload identity differs from the baseline; a faster run on a different workload is not a speedup",
            "baseline_workload": baseline.get("workload", {}),
            "current_workload": report.get("workload", {}),
            "ok": False,
        }
    old_values = [float(row["rtf"]) for row in baseline["rows"]]
    new_values = [row["rtf"] for row in report["rows"]]
    old, new = statistics.median(old_values), statistics.median(new_values)
    change = 0.0 if old == 0.0 else (new - old) / old
    p_faster = p_value_greater(new_values, old_values)
    ok = -change <= max_regression
    if claim_improvement:
        ok = ok and change > 0.0 and p_faster < alpha
    return {
        "comparable": True,
        "baseline_rtf_median": old,
        "current_rtf_median": new,
        "change_fraction": change,
        "regression_fraction": max(0.0, -change),
        "max_regression_fraction": max_regression,
        "p_value_current_faster": p_faster,
        "alpha": alpha,
        "improvement_claimed": claim_improvement,
        "improvement_supported": change > 0.0 and p_faster < alpha,
        "ok": ok,
    }


def parse_workload(pairs: list[str]) -> dict[str, str]:
    workload = {}
    for pair in pairs:
        key, separator, value = pair.partition("=")
        if not separator or not key:
            raise ValueError(f"--workload must use key=value: {pair}")
        workload[key] = value
    return workload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("csv", type=Path)
    parser.add_argument("--workload", action="append", default=[], help="workload identity key=value (repeat)")
    parser.add_argument("--baseline", type=Path, help="report JSON from a previous run of this tool")
    parser.add_argument("--max-rtf-regression", type=float, default=0.05)
    parser.add_argument("--claim-improvement", action="store_true", help="fail unless the speedup beats run variability")
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if not 0.0 <= args.max_rtf_regression <= 1.0:
            raise ValueError("--max-rtf-regression must be between 0 and 1")
        if not 0.0 < args.alpha < 1.0:
            raise ValueError("--alpha must be between 0 and 1")
        with args.csv.open(newline="", encoding="utf-8-sig") as stream:
            report = summarize(list(csv.DictReader(stream)))
        report["workload"] = parse_workload(args.workload)
        if args.baseline:
            baseline = json.loads(args.baseline.read_text(encoding="utf-8-sig"))
            if not isinstance(baseline, dict) or not isinstance(baseline.get("rows"), list):
                raise ValueError("--baseline must be a report JSON object written by this tool")
            report["comparison"] = compare(report, baseline, args.max_rtf_regression, args.claim_improvement, args.alpha)
            report["ok"] = report["comparison"]["ok"]
        elif args.claim_improvement:
            raise ValueError("--claim-improvement needs --baseline")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        report = {"ok": False, "error": str(error)}
    report, _ = emit(report, args.output)
    if not report["ok"]:
        sys.exit(2)


if __name__ == "__main__":
    main()
