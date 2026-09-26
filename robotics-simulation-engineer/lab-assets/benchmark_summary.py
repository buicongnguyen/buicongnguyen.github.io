"""Summarize repeatable simulation benchmark rows and detect regressions."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from pathlib import Path


def percentile(values: list[float], fraction: float) -> float:
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
    rtfs = [item["rtf"] for item in metrics]
    fps_values = [item["fps"] for item in metrics]
    return {
        "ok": bool(metrics),
        "runs": len(metrics),
        "rtf": {
            "median": statistics.median(rtfs),
            "p05": percentile(rtfs, 0.05),
            "p95": percentile(rtfs, 0.95),
            "cv": 0.0 if statistics.mean(rtfs) == 0.0 else statistics.pstdev(rtfs) / statistics.mean(rtfs),
        },
        "fps": {"median": statistics.median(fps_values), "p05": percentile(fps_values, 0.05), "p95": percentile(fps_values, 0.95)},
        "rows": metrics,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--max-rtf-regression", type=float, default=0.05)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if not 0.0 <= args.max_rtf_regression <= 1.0:
            raise ValueError("--max-rtf-regression must be between 0 and 1")
        # utf-8-sig also accepts files saved with a BOM by Excel or Windows PowerShell.
        with args.csv.open(newline="", encoding="utf-8-sig") as stream:
            report = summarize(list(csv.DictReader(stream)))
        if args.baseline:
            baseline = json.loads(args.baseline.read_text(encoding="utf-8-sig"))
            old = float(baseline["rtf"]["median"])
            new = float(report["rtf"]["median"])
            regression = 0.0 if old == 0.0 else (old - new) / old
            report["comparison"] = {"baseline_rtf": old, "current_rtf": new, "regression_fraction": regression}
            report["ok"] = report["ok"] and regression <= args.max_rtf_regression
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        report = {"ok": False, "error": str(error)}
    rendered = json.dumps(report, indent=2)
    if args.output:
        try:
            args.output.write_text(rendered + "\n", encoding="utf-8")
        except OSError as error:
            report = {"ok": False, "error": f"cannot write --output: {error}"}
            rendered = json.dumps(report, indent=2)
    print(rendered)
    if not report["ok"]:
        sys.exit(2)


if __name__ == "__main__":
    main()
