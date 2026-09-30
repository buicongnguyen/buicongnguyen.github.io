"""Run every lab test file and prove the labs still discriminate.

Each test file runs from its own directory because the labs reuse module
names such as ``starter`` and ``test_lab``. Test files that read ``LAB_IMPL``
run twice: against the reference (``LAB_IMPL=solution``, must pass) and
against the learner's file (the default, must fail on the planted defect).
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# LAB_IMPL used in code, not only mentioned in a comment.
SELECTS_TARGET = re.compile(r"^[^#\n]*\bLAB_IMPL\b", re.M)


def targets_learner(test_file: Path) -> bool:
    """Whether a test file (or the conftest.py beside it) selects its target with LAB_IMPL."""
    sources = [test_file, test_file.parent / "conftest.py"]
    return any(path.exists() and SELECTS_TARGET.search(path.read_text(encoding="utf-8")) for path in sources)


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
        elif targets_learner(test_file) and run(test_file, None):
            failures.append(f"{name}: learner file passes, so the tests no longer catch the planted defect")
        else:
            print(f"ok    {name}")
    # A lab that ships a starter or planted defect beside solution.py must test the learner's
    # file; otherwise the reference passing proves nothing about the exercise.
    learner_dirs = {path.parent for pattern in ("starter.py", "broken_*.py") for path in (ROOT / "labs").rglob(pattern)}
    for directory in sorted(learner_dirs):
        if (directory / "solution.py").exists() and not any(targets_learner(test) for test in directory.glob("test_*.py")):
            failures.append(f"{directory.relative_to(ROOT).as_posix()}: no test selects its target with LAB_IMPL")
    for failure in failures:
        print(f"FAIL  {failure}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
