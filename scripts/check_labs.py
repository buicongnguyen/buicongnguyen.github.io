"""Run every lab test file and prove the labs still discriminate.

Each test file runs from its own directory because the labs reuse module
names such as ``starter`` and ``test_lab``. Test files that read ``LAB_IMPL``
run twice: against the reference (``LAB_IMPL=solution``, must pass) and
against the learner's file (the default, must fail on the planted defect).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(test_file: Path, lab_impl: str | None) -> bool:
    env = dict(os.environ)
    env.pop("LAB_IMPL", None)
    if lab_impl:
        env["LAB_IMPL"] = lab_impl
    command = [sys.executable, "-m", "pytest", test_file.name, "-q", "-p", "no:cacheprovider"]
    return subprocess.run(command, cwd=test_file.parent, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0


def main() -> int:
    failures = []
    for test_file in sorted((ROOT / "labs").rglob("test_*.py")):
        name = test_file.relative_to(ROOT).as_posix()
        if not run(test_file, "solution"):
            failures.append(f"{name}: reference implementation fails its tests")
        elif "LAB_IMPL" in test_file.read_text(encoding="utf-8") and run(test_file, None):
            failures.append(f"{name}: learner file passes, so the tests no longer catch the planted defect")
        else:
            print(f"ok    {name}")
    for failure in failures:
        print(f"FAIL  {failure}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
