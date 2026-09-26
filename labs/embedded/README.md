# Applied Lab — Linker Map and ISR Shared-State Defect

1. Read `sample.map`; calculate the end of `.dma_buffer` and compare it with SRAM bounds.
2. Explain why `volatile` does not make a multi-field update atomic.
3. Identify ISR/main-loop ownership.
4. Repair publication with a critical section or a single-writer sequence counter using C11 atomics. Confirm that the target implements the selected atomic widths without an unsafe library fallback.
5. Add a linker size assertion and reject inconsistent samples.

Submit the corrected assertion, firmware, map calculation, and an explanation distinguishing visibility, atomicity, ordering, and mutual exclusion. `solution.c` is one reference approach.

A common mistake in the reader is making the second sequence load `memory_order_acquire` and assuming that orders the payload load before it. An acquire operation only prevents *later* accesses from moving above it. The payload load can still sink below the second sequence read and return a torn sample. `solution.c` puts an `atomic_thread_fence(memory_order_acquire)` between the two, and the writer uses a plain load and store instead of a read-modify-write. Check the objects your compiler emits for any `__atomic_*` library call on your target.

Use the executable oracle after calculating the addresses by hand:

```powershell
python .\map_check.py .\sample.map
python -m pytest .\test_map_check.py -q
```

The supplied broken map must exit nonzero and report a `0x1000` (4096-byte) SRAM overflow. A repaired map must exit zero.
