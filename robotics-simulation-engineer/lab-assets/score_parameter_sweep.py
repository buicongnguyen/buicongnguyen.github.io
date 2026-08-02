"""Rank controlled physics sweep rows against a declared target contract."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path


def score_rows(rows: list[dict[str, str]], contract: dict) -> list[dict]:
    targets = contract["targets"]
    scales = contract["scales"]
    weights = contract.get("weights", {name: 1.0 for name in targets})
    if set(targets) != set(scales) or not set(targets).issubset(weights):
        raise ValueError("targets, scales, and weights must describe the same metrics")
    numeric_targets = {name: float(value) for name, value in targets.items()}
    numeric_scales = {name: float(value) for name, value in scales.items()}
    numeric_weights = {name: float(weights[name]) for name in targets}
    if any(not math.isfinite(value) for value in (*numeric_targets.values(), *numeric_scales.values(), *numeric_weights.values())):
        raise ValueError("targets, scales, and weights must be finite")
    if any(value <= 0.0 for value in numeric_scales.values()):
        raise ValueError("all metric scales must be positive")
    if any(value < 0.0 for value in numeric_weights.values()):
        raise ValueError("metric weights must be non-negative")

    ranked = []
    for row in rows:
        contributions = {}
        for name, target in numeric_targets.items():
            observed = float(row[name])
            if not math.isfinite(observed):
                raise ValueError(f"non-finite {name} in scenario {row.get('scenario_id')}")
            contributions[name] = numeric_weights[name] * abs(observed - target) / numeric_scales[name]
        ranked.append({**row, "score": sum(contributions.values()), "contributions": contributions})
    return sorted(ranked, key=lambda item: (item["score"], item.get("scenario_id", "")))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path)
    parser.add_argument("contract", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        with args.csv.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        contract = json.loads(args.contract.read_text(encoding="utf-8"))
        ranked = score_rows(rows, contract)
        report = {"ok": bool(ranked), "row_count": len(ranked), "best": ranked[0] if ranked else None, "ranking": ranked}
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        report = {"ok": False, "error": str(error)}
    rendered = json.dumps(report, indent=2)
    print(rendered)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    if not report["ok"]:
        sys.exit(2)


if __name__ == "__main__":
    main()
