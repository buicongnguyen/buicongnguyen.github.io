"""Aggregate named JSON evidence files into one deterministic CI gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def evaluate(requirements: list[str]) -> dict:
    results = []
    for requirement in requirements:
        if "=" not in requirement:
            raise ValueError(f"requirement must use name=path: {requirement}")
        name, raw_path = requirement.split("=", 1)
        path = Path(raw_path)
        try:
            # utf-8-sig also accepts reports saved with a BOM by Windows PowerShell.
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
            if not isinstance(payload, dict):
                raise ValueError("evidence report must be a JSON object")
            passed = payload.get("ok") is True
            results.append({"name": name, "path": str(path), "ok": passed, "reported_ok": payload.get("ok")})
        except (OSError, ValueError) as error:  # ValueError covers JSONDecodeError and UnicodeDecodeError
            results.append({"name": name, "path": str(path), "ok": False, "error": str(error)})
    return {"ok": bool(results) and all(item["ok"] for item in results), "requirements": results}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require", action="append", default=[])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = evaluate(args.require)
    except ValueError as error:
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
