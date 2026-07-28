#include <stdatomic.h>
#include <stdint.h>

typedef struct {
    atomic_uint_least32_t sequence;
    atomic_int_least32_t value;
} sample_t;

static sample_t latest;

void DMA_IRQHandler(void) {
    /* This sequence-counter pattern assumes exactly one writer. */
    atomic_fetch_add_explicit(&latest.sequence, 1, memory_order_relaxed);
    atomic_store_explicit(&latest.value, read_dma_value(), memory_order_relaxed);
    atomic_fetch_add_explicit(&latest.sequence, 1, memory_order_release);
}

int32_t consume(void) {
    uint_least32_t before;
    uint_least32_t after;
    int_least32_t value;
    do {
        before = atomic_load_explicit(&latest.sequence, memory_order_acquire);
        value = atomic_load_explicit(&latest.value, memory_order_relaxed);
        after = atomic_load_explicit(&latest.sequence, memory_order_acquire);
    } while ((before & 1u) || before != after);
    return value;
}

/* Linker gate: ASSERT(__dma_end__ <= ORIGIN(SRAM)+LENGTH(SRAM), "SRAM overflow") */
