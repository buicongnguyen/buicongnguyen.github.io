"""Generate deterministic stratified parameter scenarios and evaluate outcomes.

`generate` draws a Latin-hypercube design: every dimension is split into `count` equal
strata and each stratum is sampled once, with the strata shuffled independently.
`evaluate` checks completeness, reports the pass rate with a Wilson 95% interval, and
bins failures by parameter so a failing corner cannot hide inside a good average.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
from pathlib import Path

BINS_PER_PARAMETER = 4
TRUE_VALUES = {"1", "true", "pass", "yes"}
FALSE_VALUES = {"0", "false", "fail", "no"}


def generate(bounds: dict[str, list[float]], count: int, seed: int) -> dict:
    if count <= 0:
        raise ValueError("count must be positive")
    if not bounds:
        raise ValueError("bounds must declare at least one parameter")
    rng = random.Random(seed)
    values: dict[str, list[float]] = {}
    for name, limits in sorted(bounds.items()):
        if len(limits) != 2:
            raise ValueError(f"invalid bounds for {name}")
        low, high = map(float, limits)
        if not math.isfinite(low) or not math.isfinite(high) or low >= high:
            raise ValueError(f"invalid bounds for {name}")
        samples = [low + (high - low) * ((index + rng.random()) / count) for index in range(count)]
        rng.shuffle(samples)
        values[name] = samples
    scenarios = [{"scenario_id": f"s{index:04d}", **{name: values[name][index] for name in values}} for index in range(count)]
    return {"schema_version": 1, "seed": seed, "count": count, "bounds": bounds, "scenarios": scenarios}


def wilson_interval(passed: int, total: int, z: float = 1.959964) -> tuple[float, float]:
    """95% Wilson score interval; unlike the normal approximation it stays inside [0, 1]."""
    if total == 0:
        return 0.0, 0.0
    rate = passed / total
    denominator = 1.0 + z * z / total
    center = (rate + z * z / (2 * total)) / denominator
    half = z * math.sqrt(rate * (1.0 - rate) / total + z * z / (4 * total * total)) / denominator
    return max(0.0, center - half), min(1.0, center + half)


def parse_success(value: str, scenario_id: str) -> bool:
    text = str(value).strip().lower()
    if text in TRUE_VALUES:
        return True
    if text in FALSE_VALUES:
        return False
    raise ValueError(f"success must be 0/1 or true/false for {scenario_id}, got {value!r}")


def failure_bins(manifest: dict, outcomes: dict[str, bool]) -> list[dict]:
    """Pass rate per equal-width bin of each declared parameter, weakest first."""
    rows = []
    for name, limits in sorted(manifest["bounds"].items()):
        low, high = map(float, limits)
        width = (high - low) / BINS_PER_PARAMETER
        counts = [[0, 0] for _ in range(BINS_PER_PARAMETER)]
        for scenario in manifest["scenarios"]:
            if scenario["scenario_id"] not in outcomes:
                continue
            index = min(BINS_PER_PARAMETER - 1, max(0, int((float(scenario[name]) - low) / width)))
            counts[index][0] += outcomes[scenario["scenario_id"]]
            counts[index][1] += 1
        for index, (passed, total) in enumerate(counts):
            if total:
                rows.append({
                    "parameter": name,
                    "range": [low + index * width, low + (index + 1) * width],
                    "scenarios": total,
                    "passed": passed,
                    "pass_rate": passed / total,
                })
    return sorted(rows, key=lambda row: (row["pass_rate"], -row["scenarios"], row["parameter"]))


def evaluate(manifest: dict, result_rows: list[dict[str, str]], minimum_pass_rate: float, require_lower_bound: bool = False) -> dict:
    if not 0.0 <= minimum_pass_rate <= 1.0:
        raise ValueError("minimum_pass_rate must be between 0 and 1")
    scenarios = {item["scenario_id"]: item for item in manifest["scenarios"]}
    expected = set(scenarios)
    observed_ids = [row["scenario_id"] for row in result_rows]
    observed = set(observed_ids)
    missing = sorted(expected - observed)
    extra = sorted(observed - expected)
    duplicates = sorted({name for name in observed if observed_ids.count(name) > 1})
    outcomes: dict[str, bool] = {}
    reasons: dict[str, str] = {}
    for row in result_rows:
        success = parse_success(row["success"], row["scenario_id"])
        if row["scenario_id"] in expected and row["scenario_id"] not in outcomes:
            outcomes[row["scenario_id"]] = success
            reasons[row["scenario_id"]] = row.get("failure_reason", "")
    passed = sum(outcomes.values())
    # Missing scenarios count as failures in the denominator: absent evidence is not a pass.
    denominator = len(expected)
    pass_rate = passed / denominator if denominator else 0.0
    lower, upper = wilson_interval(passed, denominator)
    complete = not missing and not extra and not duplicates
    meets_rate = (lower if require_lower_bound else pass_rate) >= minimum_pass_rate
    failed = [
        {"scenario_id": sid, **{k: v for k, v in scenarios[sid].items() if k != "scenario_id"}, "failure_reason": reasons[sid]}
        for sid in sorted(outcomes)
        if not outcomes[sid]
    ]
    bins = failure_bins(manifest, outcomes)
    return {
        "ok": complete and meets_rate,
        "expected": denominator,
        "observed": len(result_rows),
        "passed": passed,
        "pass_rate": pass_rate,
        "pass_rate_wilson95": [lower, upper],
        "minimum_pass_rate": minimum_pass_rate,
        "gate_uses": "wilson_lower_bound" if require_lower_bound else "point_estimate",
        "missing": missing,
        "extra": extra,
        "duplicates": duplicates,
        "failed_scenarios": failed[:25],
        "weakest_bins": [row for row in bins if row["pass_rate"] < 1.0][:8],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("generate")
    create.add_argument("bounds", type=Path)
    create.add_argument("--count", type=int, default=32)
    create.add_argument("--seed", type=int, default=20260803)
    create.add_argument("--output", type=Path, required=True)
    check = subparsers.add_parser("evaluate")
    check.add_argument("manifest", type=Path)
    check.add_argument("results", type=Path)
    check.add_argument("--minimum-pass-rate", type=float, default=0.9)
    check.add_argument("--require-lower-bound", action="store_true", help="gate on the Wilson 95%% lower bound")
    check.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "generate":
            bounds = json.loads(args.bounds.read_text(encoding="utf-8-sig"))
            report = generate(bounds, args.count, args.seed)
            args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            report = {"ok": True, **report}
        else:
            manifest = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
            with args.results.open(newline="", encoding="utf-8-sig") as stream:
                report = evaluate(manifest, list(csv.DictReader(stream)), args.minimum_pass_rate, args.require_lower_bound)
            if args.output:
                args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        report = {"ok": False, "error": str(error)}
        print(json.dumps(report, indent=2))
    if not report.get("ok", False):
        sys.exit(2)


if __name__ == "__main__":
    main()
