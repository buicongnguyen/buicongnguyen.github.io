"""Run every repository check: the single entry point for CI and for local work.

    python -m pip install -r requirements-learning.txt
    python scripts/check_all.py

Exercises are checked in both directions by scripts/check_labs.py: where a lab's tests
select their target with LAB_IMPL, the reference (LAB_IMPL=solution) must pass and the
learner's file (a starter stub or a planted defect) must fail. A test suite that passes on
the defect proves nothing.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(label: str, command: list[str], timeout: float = 120) -> bool:
    started = time.monotonic()
    try:
        result = subprocess.run(command, cwd=ROOT, env=dict(os.environ), capture_output=True, text=True, timeout=timeout)
        succeeded = result.returncode == 0
        output = result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        succeeded, output = False, f"timed out after {timeout:.0f}s (a hanging test is a failure)"
    print(f"{'PASS' if succeeded else 'FAIL'}  {label}  [{time.monotonic() - started:.1f}s]")
    if not succeeded:
        print("      " + "\n      ".join(output.strip().splitlines()[-25:]))
    return succeeded


def main() -> int:
    python = sys.executable
    tests = ROOT / "robotics-simulation-engineer" / "lab-assets" / "tests"
    results = [
        run("lab-assets offline suite", [python, "-m", "unittest", "discover", "-s", str(tests)]),
        run("lab-assets ROS suite (skips without rclpy)", [python, "-m", "unittest", "discover", "-s", str(tests / "ros")]),
        run("coding labs in both directions", [python, str(ROOT / "scripts" / "check_labs.py")], timeout=900),
        run("generated lab pages are current", [python, str(ROOT / "scripts" / "build_lab_pages.py"), "--check"]),
        run("site links, spine, and paths", [python, str(ROOT / "scripts" / "check_site.py")]),
    ]
    failed = results.count(False)
    print(f"\n{len(results) - failed}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
