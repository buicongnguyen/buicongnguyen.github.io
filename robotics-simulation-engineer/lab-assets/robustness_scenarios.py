"""Generate deterministic stratified parameter scenarios and evaluate outcomes."""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
from pathlib import Path


def generate(bounds: dict[str, list[float]], count: int, seed: int) -> dict:
    if count <= 0:
        raise ValueError("count must be positive")
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


def evaluate(manifest: dict, result_rows: list[dict[str, str]], minimum_pass_rate: float) -> dict:
    if not 0.0 <= minimum_pass_rate <= 1.0:
        raise ValueError("minimum_pass_rate must be between 0 and 1")
    expected = {item["scenario_id"] for item in manifest["scenarios"]}
    observed_ids = [row["scenario_id"] for row in result_rows]
    observed = set(observed_ids)
    missing = sorted(expected - observed)
    extra = sorted(observed - expected)
    duplicates = sorted({name for name in observed if observed_ids.count(name) > 1})
    parsed_success = []
    for row in result_rows:
        value = float(row["success"])
        if not math.isfinite(value) or not 0.0 <= value <= 1.0:
            raise ValueError(f"success must be finite and between 0 and 1 for {row['scenario_id']}")
        if row["scenario_id"] in expected:
            parsed_success.append(value)
    passed = sum(value >= 0.5 for value in parsed_success)
    denominator = len(expected)
    pass_rate = passed / denominator if denominator else 0.0
    return {
        "ok": not missing and not extra and not duplicates and pass_rate >= minimum_pass_rate,
        "expected": denominator,
        "observed": len(result_rows),
        "passed": passed,
        "pass_rate": pass_rate,
        "minimum_pass_rate": minimum_pass_rate,
        "missing": missing,
        "extra": extra,
        "duplicates": duplicates,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
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
    check.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "generate":
            bounds = json.loads(args.bounds.read_text(encoding="utf-8"))
            report = generate(bounds, args.count, args.seed)
            args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        else:
            manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
            with args.results.open(newline="", encoding="utf-8") as stream:
                report = evaluate(manifest, list(csv.DictReader(stream)), args.minimum_pass_rate)
            if args.output:
                args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        report = {"ok": False, "error": str(error)}
        print(json.dumps(report, indent=2))
    if args.command == "evaluate" and not report.get("ok", False):
        sys.exit(2)


if __name__ == "__main__":
    main()
