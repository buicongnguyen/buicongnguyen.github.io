# Applied Lab — Linker Map and ISR Shared-State Defect

1. Read `sample.map`; calculate the end of `.dma_buffer` and compare it with SRAM bounds.
2. Explain why `volatile` does not make a multi-field update atomic.
3. Identify ISR/main-loop ownership.
4. Repair publication with a critical section or a single-writer sequence counter using C11 atomics. Confirm that the target implements the selected atomic widths without an unsafe library fallback.
5. Add a linker size assertion and reject inconsistent samples.

Submit the corrected assertion, firmware, map calculation, and an explanation distinguishing visibility, atomicity, ordering, and mutual exclusion. `solution.c` is one reference approach.

Use the executable oracle after calculating the addresses by hand:

```powershell
python .\map_check.py .\sample.map
python -m pytest .\test_map_check.py -q
```

The supplied broken map must exit nonzero and report a `0x1000` (4096-byte) SRAM overflow. A repaired map must exit zero.
