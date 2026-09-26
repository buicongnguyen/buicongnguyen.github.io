"""Static checks for the published site (standard library only).

1. Every internal link and #anchor in HTML pages and course Markdown resolves.
2. Every page that loads book-layout.js is a chapter in its spine, and every chapter exists.
3. Published text never contains a machine-specific user path.
4. All pages reference one version of the shared book assets, so caches cannot mix them.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
USER_PATH = re.compile(r"[A-Za-z]:\\Users\\[^\\\s\"'<>`]+\\")
# Anchors that a page's own script creates at runtime, confirmed in a browser. Keep this
# list short: a static id is always better than an allowlist entry.
RUNTIME_IDS = {"interview-practice.html": {"deep-learning", "os", "embedded"}}
MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        for key in ("id", "name"):
            if values.get(key):
                self.ids.add(values[key])
        for key in ("href", "src"):
            if values.get(key):
                self.links.append(values[key])


def tracked(*patterns: str) -> list[Path]:
    output = subprocess.run(["git", "ls-files", *patterns], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [ROOT / line for line in output.splitlines() if (ROOT / line).exists()]


def parse(path: Path, cache: dict[Path, PageParser]) -> PageParser:
    if path not in cache:
        parser = PageParser()
        parser.feed(path.read_text(encoding="utf-8"))
        cache[path] = parser
    return cache[path]


def markdown_ids(path: Path) -> set[str]:
    """Anchors of a Markdown file, from its generated HTML twin when there is one."""
    twin = path.with_suffix(".html")
    if twin.exists() and "scripts/build_lab_pages.py" in twin.read_text(encoding="utf-8"):
        return parse(twin, {}).ids
    return set()


def exists_exact(path: Path) -> bool:
    """Like Path.exists, but case-sensitive everywhere, because GitHub Pages is."""
    if not path.exists():
        return False
    relative = path.relative_to(ROOT)
    current = ROOT
    for part in relative.parts:
        if part not in {entry.name for entry in current.iterdir()}:
            return False
        current = current / part
    return True


def check_link(source: Path, link: str, cache: dict[Path, PageParser]) -> str | None:
    parts = urlsplit(link)
    if parts.scheme or link.startswith(("//", "mailto:", "javascript:", "data:")):
        return None
    # normpath, not resolve(): on Windows resolve() rewrites the case to match the disk,
    # which would hide exactly the mismatch that breaks on GitHub Pages.
    target = source if not parts.path else Path(os.path.normpath(source.parent / unquote(parts.path)))
    if parts.path.endswith("/") or target.is_dir():
        target = target / "index.html"
    try:
        target.relative_to(ROOT)
    except ValueError:
        return f"{link}: points outside the site"
    if not exists_exact(target):
        return f"{link}: target does not exist (paths are case-sensitive on GitHub Pages)"
    if parts.fragment:
        if target.suffix == ".html":
            runtime = RUNTIME_IDS.get(target.relative_to(ROOT).as_posix(), set())
            if parts.fragment not in parse(target, cache).ids | runtime:
                return f"{link}: no id={parts.fragment!r} in {target.relative_to(ROOT).as_posix()}"
        elif target.suffix == ".md" and source.suffix == ".html":
            return f"{link}: GitHub Pages serves Markdown as plain text, so the #anchor cannot work"
        elif target.suffix == ".md" and parts.fragment not in markdown_ids(target):
            return f"{link}: no heading anchor {parts.fragment!r}"
    return None


def spine_paths() -> list[str]:
    source = (ROOT / "book-layout.js").read_text(encoding="utf-8")
    return re.findall(r'\[\s*"[^"]+",\s*"([^"]+\.html)"\s*\]', source)


def main() -> int:
    problems: list[str] = []
    cache: dict[Path, PageParser] = {}
    pages = tracked("*.html")
    for page in pages:
        for link in parse(page, cache).links:
            problem = check_link(page, link, cache)
            if problem:
                problems.append(f"{page.relative_to(ROOT).as_posix()}: {problem}")
    for document in tracked("robotics-simulation-engineer/*.md", "labs/*.md", "labs/**/*.md", "README.md"):
        for link in MARKDOWN_LINK.findall(document.read_text(encoding="utf-8")):
            problem = check_link(document, link, cache)
            if problem:
                problems.append(f"{document.relative_to(ROOT).as_posix()}: {problem}")

    spine = spine_paths()
    if len(spine) != len(set(spine)):
        problems.append("book-layout.js: a chapter appears twice in the spine")
    for path in spine:
        if not (ROOT / path).exists():
            problems.append(f"book-layout.js: spine chapter {path} does not exist")
    for page in pages:
        relative = page.relative_to(ROOT).as_posix()
        if "book-layout.js" in page.read_text(encoding="utf-8") and relative not in spine:
            problems.append(f"{relative}: loads book-layout.js but is not a chapter in its spine (no outline or prev/next)")

    for document in tracked("*.html", "*.md", "*.ps1", "*.js", "*.py", "*.json", "*.yaml"):
        for number, line in enumerate(document.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if USER_PATH.search(line):
                problems.append(f"{document.relative_to(ROOT).as_posix()}:{number}: machine-specific user path")

    versions = {}
    for page in pages:
        for asset, version in re.findall(r"(book-layout\.(?:js|css))\?v=([\w-]+)", page.read_text(encoding="utf-8")):
            versions.setdefault(asset, set()).add(version)
    for asset, found in versions.items():
        if len(found) > 1:
            problems.append(f"{asset}: pages reference several versions {sorted(found)}")

    for problem in problems:
        print(problem)
    print(f"site check: {len(pages)} pages, {len(spine)} spine chapters, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
