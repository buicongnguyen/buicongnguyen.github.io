"""Parse a simple linker map and check whether a section fits in a memory region."""
from __future__ import annotations

import argparse
import re
from pathlib import Path


MEMORY_LINE = re.compile(r"^\s*([A-Za-z_]\w*)\s+(0x[0-9a-fA-F]+)\s+(0x[0-9a-fA-F]+)\s*$")
SECTION_LINE = re.compile(r"^\s*(\.[^\s]+)\s+(0x[0-9a-fA-F]+)\s+(0x[0-9a-fA-F]+)\s*$")


def _insert_unique(table, name, value, kind):
    if name in table:
        raise ValueError(f"duplicate {kind} entry: {name}")
    table[name] = value


def analyze_map(text: str, section_name: str = ".dma_buffer", memory_name: str = "SRAM") -> dict:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("map text must be a non-empty string")

    memories = {}
    sections = {}
    for line in text.splitlines():
        section_match = SECTION_LINE.match(line)
        if section_match:
            name, address, size = section_match.groups()
            _insert_unique(sections, name, (int(address, 16), int(size, 16)), "section")
            continue
        memory_match = MEMORY_LINE.match(line)
        if memory_match:
            name, origin, length = memory_match.groups()
            _insert_unique(memories, name, (int(origin, 16), int(length, 16)), "memory")

    if memory_name not in memories:
        raise ValueError(f"memory region not found: {memory_name}")
    if section_name not in sections:
        raise ValueError(f"section not found: {section_name}")

    origin, length = memories[memory_name]
    section_start, section_size = sections[section_name]
    region_end = origin + length
    section_end = section_start + section_size
    fits = section_start >= origin and section_end <= region_end
    overflow_bytes = max(0, section_end - region_end)
    before_region_bytes = max(0, origin - section_start)
    return {
        "memory": memory_name,
        "section": section_name,
        "region_start": origin,
        "region_end": region_end,
        "section_start": section_start,
        "section_end": section_end,
        "fits": fits,
        "overflow_bytes": overflow_bytes,
        "before_region_bytes": before_region_bytes,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("map_file", nargs="?", default=Path(__file__).with_name("sample.map"))
    parser.add_argument("--section", default=".dma_buffer")
    parser.add_argument("--memory", default="SRAM")
    args = parser.parse_args()
    report = analyze_map(Path(args.map_file).read_text(encoding="utf-8"), args.section, args.memory)
    print(report)
    return 0 if report["fits"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
