"""Rank a controlled physics sweep against a declared contract, then check it on held-out data.

A *candidate* is one combination of parameter values. Every candidate needs repeated
runs so that ranking compares means, not the luckiest single run. The sweep must vary one
declared parameter family; otherwise a better score cannot be attributed to a parameter.
Selection is only accepted when the chosen candidate beats the declared baseline on a
held-out episode by more than two standard errors of the difference.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from pathlib import Path

RESERVED_COLUMNS = {"scenario_id", "repeat", "notes"}


def _finite(value: object, what: str) -> float:
    number = float(value)  # type: ignore[arg-type]
    if not math.isfinite(number):
        raise ValueError(f"{what} must be finite")
    return number


def _metric_contract(contract: dict, targets: dict) -> tuple[dict[str, float], dict[str, float], dict[str, float]]:
    scales = contract["scales"]
    weights = contract.get("weights", {name: 1.0 for name in targets})
    if set(targets) != set(scales) or not set(targets).issubset(weights):
        raise ValueError("targets, scales, and weights must describe the same metrics")
    numeric_targets = {name: _finite(value, f"target {name}") for name, value in targets.items()}
    numeric_scales = {name: _finite(scales[name], f"scale {name}") for name in targets}
    numeric_weights = {name: _finite(weights[name], f"weight {name}") for name in targets}
    if any(value <= 0.0 for value in numeric_scales.values()):
        raise ValueError("all metric scales must be positive")
    if any(value < 0.0 for value in numeric_weights.values()):
        raise ValueError("metric weights must be non-negative")
    return numeric_targets, numeric_scales, numeric_weights


def score_rows(rows: list[dict[str, str]], contract: dict, targets: dict | None = None) -> list[dict]:
    """Score each raw row: sum of weight * |observed - target| / scale. Lower is better."""
    numeric_targets, numeric_scales, numeric_weights = _metric_contract(contract, targets or contract["targets"])
    scored = []
    for row in rows:
        contributions = {}
        for name, target in numeric_targets.items():
            observed = _finite(row[name], f"{name} in scenario {row.get('scenario_id')}")
            contributions[name] = numeric_weights[name] * abs(observed - target) / numeric_scales[name]
        scored.append({**row, "score": sum(contributions.values()), "contributions": contributions})
    return sorted(scored, key=lambda item: (item["score"], item.get("scenario_id", "")))


def parameter_columns(rows: list[dict[str, str]], metrics: set[str]) -> list[str]:
    if not rows:
        raise ValueError("no rows to score")
    return [name for name in rows[0] if name not in metrics and name not in RESERVED_COLUMNS]


def candidate_key(row: dict[str, str], parameters: list[str]) -> tuple[float, ...]:
    return tuple(_finite(row[name], f"parameter {name}") for name in parameters)


def label(key: tuple[float, ...], parameters: list[str]) -> str:
    return ", ".join(f"{name}={value:g}" for name, value in zip(parameters, key))


def summarize_candidates(scored: list[dict], parameters: list[str]) -> list[dict]:
    groups: dict[tuple[float, ...], list[dict]] = {}
    for row in scored:
        groups.setdefault(candidate_key(row, parameters), []).append(row)
    summaries = []
    for key, members in groups.items():
        scores = [row["score"] for row in members]
        spread = statistics.stdev(scores) if len(scores) > 1 else 0.0
        summaries.append({
            "candidate": label(key, parameters),
            "parameters": dict(zip(parameters, key)),
            "runs": len(scores),
            "mean_score": statistics.fmean(scores),
            "stdev_score": spread,
            "standard_error": spread / math.sqrt(len(scores)),
            "scenario_ids": sorted(row.get("scenario_id", "") for row in members),
        })
    return sorted(summaries, key=lambda item: (item["mean_score"], item["candidate"]))


def separated(better: dict, worse: dict) -> tuple[float, float, bool]:
    """Difference in mean score, two standard errors of that difference, and whether it clears them."""
    difference = worse["mean_score"] - better["mean_score"]
    noise = 2.0 * math.hypot(better["standard_error"], worse["standard_error"])
    return difference, noise, difference > noise


def calibrate(rows: list[dict[str, str]], contract: dict, family: list[str] | None, min_repeats: int) -> dict:
    scored = score_rows(rows, contract)
    parameters = parameter_columns(rows, set(contract["targets"]))
    candidates = summarize_candidates(scored, parameters)
    errors: list[str] = []
    varied = [
        name for index, name in enumerate(parameters)
        if len({tuple(item["parameters"].values())[index] for item in candidates}) > 1
    ]
    if family:
        unknown = sorted(set(family) - set(parameters))
        if unknown:
            errors.append(f"declared family columns not in CSV: {unknown}")
        confounded = sorted(set(varied) - set(family))
        if confounded:
            errors.append(f"parameters outside the declared family also vary: {confounded}")
    elif len(varied) > 1:
        errors.append(
            f"sweep varies {varied} together, so any gain is confounded; "
            "sweep one family or declare it with --family"
        )
    short = [item["candidate"] for item in candidates if item["runs"] < min_repeats]
    if short:
        errors.append(f"candidates with fewer than {min_repeats} repeats: {short}")
    best = candidates[0]
    indistinguishable = [
        other["candidate"] for other in candidates[1:] if not separated(best, other)[2]
    ]
    return {
        "ok": not errors,
        "errors": errors,
        "parameters": parameters,
        "varied_parameters": varied,
        "row_count": len(scored),
        "selected": best,
        "identifiable": not indistinguishable,
        "indistinguishable_from_selected": indistinguishable,
        "candidates": candidates,
        "rows": scored,
    }


def validate_holdout(rows: list[dict[str, str]], contract: dict, selected: dict, min_repeats: int) -> dict:
    baseline = contract.get("baseline")
    if not isinstance(baseline, dict):
        raise ValueError("contract needs a 'baseline' object naming the pre-calibration parameters")
    targets = contract.get("holdout_targets", contract["targets"])
    scored = score_rows(rows, contract, targets)
    parameters = parameter_columns(rows, set(targets))
    if set(parameters) != set(selected["parameters"]):
        raise ValueError("holdout CSV must use the same parameter columns as the calibration sweep")
    candidates = {item["candidate"]: item for item in summarize_candidates(scored, parameters)}
    wanted = {
        "baseline": label(tuple(_finite(baseline[name], f"baseline {name}") for name in parameters), parameters),
        "selected": label(tuple(selected["parameters"][name] for name in parameters), parameters),
    }
    missing = [role for role, name in wanted.items() if name not in candidates]
    if missing:
        return {"ok": False, "error": f"holdout rows missing for: {missing}", "expected": wanted}
    base, chosen = candidates[wanted["baseline"]], candidates[wanted["selected"]]
    short = [item["candidate"] for item in (base, chosen) if item["runs"] < min_repeats]
    improvement, noise, clears = separated(chosen, base)
    return {
        "ok": clears and not short,
        "targets": targets,
        "baseline": base,
        "selected": chosen,
        "improvement": improvement,
        "two_standard_errors": noise,
        "improves_beyond_repeat_noise": clears,
        "too_few_repeats": short,
    }


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("csv", type=Path, help="calibration sweep rows")
    parser.add_argument("contract", type=Path, help="targets, scales, weights, baseline (JSON)")
    parser.add_argument("--holdout", type=Path, help="held-out episode rows for baseline and selected candidates")
    parser.add_argument("--calibration-only", action="store_true", help="explore without the held-out gate")
    parser.add_argument("--family", help="comma-separated parameter columns that form the swept family")
    parser.add_argument("--min-repeats", type=int, default=3)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if args.min_repeats < 1:
            raise ValueError("--min-repeats must be at least 1")
        contract = json.loads(args.contract.read_text(encoding="utf-8-sig"))
        family = [name.strip() for name in args.family.split(",")] if args.family else None
        report = calibrate(read_rows(args.csv), contract, family, args.min_repeats)
        if args.holdout:
            report["holdout"] = validate_holdout(read_rows(args.holdout), contract, report["selected"], args.min_repeats)
            report["ok"] = report["ok"] and report["holdout"]["ok"]
        elif not args.calibration_only:
            report["ok"] = False
            report["errors"].append("no --holdout rows: selection is unvalidated (use --calibration-only to explore)")
    except (OSError, ValueError, KeyError, json.JSONDecodeError, statistics.StatisticsError) as error:
        report = {"ok": False, "error": str(error)}
    rendered = json.dumps(report, indent=2)
    print(rendered)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    if not report["ok"]:
        sys.exit(2)


if __name__ == "__main__":
    main()
