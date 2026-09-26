"""Run every repository check: the single entry point for CI and for local work.

    python -m pip install -r requirements-learning.txt
    python scripts/check_all.py

Exercises are checked in both directions. Where a lab's tests select their target with
LAB_IMPL, the reference (LAB_IMPL=solution) must pass and the learner's file (the default:
a starter stub or a planted defect) must fail. A test suite that passes on the defect
proves nothing.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEARNER_RUN_TIMEOUT = 120


def run(label: str, command: list[str], cwd: Path = ROOT, env: dict | None = None, expect_success: bool = True) -> bool:
    started = time.monotonic()
    try:
        result = subprocess.run(
            command, cwd=cwd, env={**os.environ, **(env or {})}, capture_output=True, text=True, timeout=LEARNER_RUN_TIMEOUT
        )
        succeeded = result.returncode == 0
        output = result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        succeeded, output = False, f"timed out after {LEARNER_RUN_TIMEOUT}s (a hanging test is a failure)"
    ok = succeeded == expect_success
    expectation = "" if expect_success else " (expected to fail)"
    print(f"{'PASS' if ok else 'FAIL'}  {label}{expectation}  [{time.monotonic() - started:.1f}s]")
    if not ok:
        print("      " + "\n      ".join(output.strip().splitlines()[-25:]))
    return ok


def lab_directories() -> list[Path]:
    return sorted({path.parent for path in (ROOT / "labs").rglob("test_*.py")})


def main() -> int:
    python = sys.executable
    results = [
        run("lab-assets offline suite", [python, "-m", "unittest", "discover", "-s",
                                         str(ROOT / "robotics-simulation-engineer" / "lab-assets" / "tests")]),
        run("lab-assets ROS suite (skips without rclpy)", [python, "-m", "unittest", "discover", "-s",
                                                           str(ROOT / "robotics-simulation-engineer" / "lab-assets" / "tests" / "ros")]),
    ]
    for directory in lab_directories():
        label = directory.relative_to(ROOT).as_posix()
        pytest = [python, "-m", "pytest", "-q", "-p", "no:cacheprovider"]
        uses_target = any("LAB_IMPL" in path.read_text(encoding="utf-8") for path in directory.glob("test_*.py"))
        if uses_target:
            results.append(run(f"{label}: reference solution", pytest, directory, {"LAB_IMPL": "solution"}))
            results.append(run(f"{label}: learner file", pytest, directory, expect_success=False))
        else:
            results.append(run(f"{label}", pytest, directory))
    results.append(run("generated lab pages are current", [python, str(ROOT / "scripts" / "build_lab_pages.py"), "--check"]))
    results.append(run("site links, spine, and paths", [python, str(ROOT / "scripts" / "check_site.py")]))
    failed = results.count(False)
    print(f"\n{len(results) - failed}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
