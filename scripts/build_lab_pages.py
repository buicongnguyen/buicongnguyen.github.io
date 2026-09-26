"""Generate the Isaac Sim lab chapters (HTML) from their Markdown sources.

The Markdown is the single source of truth; the HTML pages are build output and must not
be edited by hand. CI runs this with --check and fails when a page is stale.

    python scripts/build_lab_pages.py          # regenerate
    python scripts/build_lab_pages.py --check  # verify generated pages match their sources

Requires the `markdown` package (see requirements-learning.txt).
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]
COURSE = ROOT / "robotics-simulation-engineer"
SITE = "https://buicongnguyen.github.io/robotics-simulation-engineer/"
ASSET_VERSION = "20260926-1"

# Book order: the hub, then the ten labs.
PAGES = [
    "ros2-labs",
    "isaac-sim-gui-clock-test",
    "lab-02-joint-states-tf",
    "lab-03-cmd-vel-watchdog",
    "lab-04-camera-depth",
    "lab-05-rosbag-validation",
    "lab-06-urdf-model-audit",
    "lab-07-physics-identification",
    "lab-08-regression-ci",
    "lab-09-performance-profiling",
    "lab-10-domain-randomization",
]

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{description}">
<meta name="theme-color" content="#087968">
<meta name="generator" content="scripts/build_lab_pages.py from {name}.md">
<link rel="canonical" href="{site}{name}.html">
<title>{title} | Robotics Simulation Engineering</title>
<link rel="stylesheet" href="course.css?v=20260713-3">
<link rel="stylesheet" href="lab-chapter.css?v={version}">
<link rel="stylesheet" href="../book-layout.css?v={version}">
</head>
<body>
<a class="skip-link" href="#main">Skip to the lab</a>
<header class="site-header">
<a class="brand" href="ros2-labs.html"><img src="https://avatars.githubusercontent.com/u/72680210?v=4" alt=""><span>Isaac Sim + ROS 2 Labs</span></a>
<nav aria-label="Lab navigation"><a href="dashboard.html">Dashboard</a><a href="ros2-labs.html">Ten labs</a><a href="{name}.md">Markdown source</a></nav>
</header>
<main id="main" class="lab-chapter">
<!-- Generated from {name}.md by scripts/build_lab_pages.py. Edit the Markdown, not this file. -->
{body}
<p class="chapter-source">This chapter is generated from <a href="{name}.md">{name}.md</a>; diagrams render with Mermaid and fall back to their text source.</p>
</main>
<script type="module">
import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
const dark = window.matchMedia("(prefers-color-scheme: dark)").matches;
mermaid.initialize({{ startOnLoad: true, securityLevel: "strict", theme: dark ? "dark" : "neutral" }});
</script>
<script src="../book-layout.js?v={version}"></script>
</body>
</html>
"""


def describe(source: str) -> str:
    goal = re.search(r"^- \*\*Goal:\*\*\s*(.+)$", source, re.M)
    if goal:
        text = goal.group(1)
    else:
        paragraphs = [block.strip() for block in source.split("\n\n")]
        text = next((block for block in paragraphs if block and block[0] not in "#-`|>"), "")
    text = re.sub(r"[`*]|\[([^\]]+)\]\([^)]+\)", lambda m: m.group(1) or "", text)
    return html.escape(" ".join(text.split())[:200], quote=True)


def render(name: str) -> str:
    source = (COURSE / f"{name}.md").read_text(encoding="utf-8")
    title_match = re.search(r"^# (.+)$", source, re.M)
    if not title_match:
        raise ValueError(f"{name}.md has no level-1 heading")
    body = markdown.markdown(
        source,
        extensions=["tables", "fenced_code", "sane_lists", "toc"],
        extension_configs={"toc": {"permalink": False}},
        output_format="html",
    )
    # Mermaid renders <pre class="mermaid">; its textContent un-escapes the entities.
    body = re.sub(
        r'<pre><code class="language-mermaid">(.*?)</code></pre>',
        r'<pre class="mermaid">\1</pre>',
        body,
        flags=re.S,
    )
    # Sibling chapters link to each other as .md in the source and as .html here.
    generated = "|".join(re.escape(page) for page in PAGES)
    body = re.sub(rf'href="({generated})\.md(#[^"]*)?"', r'href="\1.html\2"', body)
    # A "Live page" bullet would link a generated page to itself.
    body = re.sub(
        rf'<li>\s*(?:<p>)?Live [^<]*<a href="{re.escape(SITE)}{re.escape(name)}\.html">[^<]*</a>(?:</p>)?\s*</li>\n?',
        "",
        body,
    )
    body = re.sub(r"<table>", '<div class="table-wrap"><table>', body)
    body = body.replace("</table>", "</table></div>")
    title = re.sub(r"[`*]", "", title_match.group(1)).strip()
    return TEMPLATE.format(
        name=name,
        site=SITE,
        title=html.escape(title),
        description=describe(source),
        body=body,
        version=ASSET_VERSION,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if any generated page is stale")
    args = parser.parse_args()
    stale = []
    for name in PAGES:
        target = COURSE / f"{name}.html"
        page = render(name)
        # Compare without line endings: a Windows checkout with core.autocrlf yields CRLF.
        current = target.read_text(encoding="utf-8").replace("\r\n", "\n") if target.exists() else None
        if current == page:
            continue
        if args.check:
            stale.append(target.relative_to(ROOT).as_posix())
        else:
            target.write_text(page, encoding="utf-8", newline="\n")
            print(f"wrote {target.relative_to(ROOT).as_posix()}")
    if stale:
        print("Stale generated pages (run python scripts/build_lab_pages.py):", *stale, sep="\n  ")
        return 1
    if args.check:
        print(f"{len(PAGES)} generated lab pages match their Markdown sources")
    return 0


if __name__ == "__main__":
    sys.exit(main())
