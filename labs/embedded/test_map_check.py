from pathlib import Path

import pytest

from map_check import analyze_map


def test_sample_map_detects_exact_sram_overflow():
    report = analyze_map(Path(__file__).with_name("sample.map").read_text(encoding="utf-8"))
    assert report["region_end"] == 0x20010000
    assert report["section_end"] == 0x20011000
    assert report["fits"] is False
    assert report["overflow_bytes"] == 0x1000


def test_valid_section_fits():
    text = """
Memory Configuration
SRAM 0x20000000 0x00010000
Linker script and memory map
.dma_buffer 0x2000e000 0x00002000
"""
    report = analyze_map(text)
    assert report["fits"] is True
    assert report["overflow_bytes"] == 0


def test_gnu_ld_attributes_column_is_accepted():
    text = """
Memory Configuration
Name             Origin             Length             Attributes
FLASH            0x08000000         0x00040000         xr
SRAM             0x20000000         0x00010000         xrw
Linker script and memory map
.dma_buffer      0x2000e000         0x00002000
"""
    report = analyze_map(text)
    assert report["region_end"] == 0x20010000
    assert report["fits"] is True


@pytest.mark.parametrize(
    "text",
    [
        "",
        "SRAM 0x20000000 0x10000",
        ".dma_buffer 0x20000000 0x100",
        "SRAM 0x20000000 0x10000\nSRAM 0x20000000 0x10000\n.dma_buffer 0x20000000 0x100",
    ],
)
def test_malformed_or_incomplete_map_is_rejected(text):
    with pytest.raises(ValueError):
        analyze_map(text)
