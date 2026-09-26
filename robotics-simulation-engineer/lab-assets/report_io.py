"""Shared report output for the lab tools: print JSON and optionally save it as UTF-8."""

from __future__ import annotations

import json
from pathlib import Path


def emit(report: dict, output: Path | None) -> tuple[dict, bool]:
    """Save the report to `output` (if given), print it, and return (printed report, saved).

    Prefer --output over shell redirection: Windows PowerShell 5.1 ">" writes UTF-16.
    An unwritable --output becomes a structured {"ok": false} report instead of a traceback,
    so a caller always receives one JSON document and a non-zero exit.
    """
    rendered = json.dumps(report, indent=2)
    saved = True
    if output:
        try:
            output.write_text(rendered + "\n", encoding="utf-8")
        except OSError as error:
            report = {"ok": False, "error": f"cannot write --output: {error}"}
            rendered = json.dumps(report, indent=2)
            saved = False
    print(rendered)
    return report, saved
