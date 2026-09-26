"""Aggregate named JSON evidence files into one deterministic CI gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def read_json(path: Path):
    """Read JSON written by any common tool, including Windows PowerShell 5.1 `>` (UTF-16 + BOM)."""
    raw = path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        text = raw.decode("utf-16")
    else:
        text = raw.decode("utf-8-sig")
    return json.loads(text)


def evaluate(requirements: list[str]) -> dict:
    results = []
    seen: set[str] = set()
    for requirement in requirements:
        if "=" not in requirement:
            raise ValueError(f"requirement must use name=path: {requirement}")
        name, raw_path = requirement.split("=", 1)
        if not name or name in seen:
            raise ValueError(f"requirement names must be non-empty and unique: {name!r}")
        seen.add(name)
        path = Path(raw_path)
        try:
            payload = read_json(path)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            results.append({"name": name, "path": str(path), "ok": False, "error": str(error)})
            continue
        if not isinstance(payload, dict):
            results.append({"name": name, "path": str(path), "ok": False, "error": "report must be a JSON object"})
            continue
        results.append({"name": name, "path": str(path), "ok": payload.get("ok") is True, "reported_ok": payload.get("ok")})
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
    print(rendered)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    if not report["ok"]:
        sys.exit(2)


if __name__ == "__main__":
    main()
