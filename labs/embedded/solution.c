#include <stdatomic.h>
#include <stdint.h>

/* Provided by the board support package. */
int32_t read_dma_value(void);

typedef struct {
    atomic_uint_least32_t sequence;
    atomic_int_least32_t value;
} sample_t;

static sample_t latest;

void DMA_IRQHandler(void) {
    /* Single writer, so a plain load and store replace a read-modify-write:
       no LDREX/STREX loop and no libatomic fallback on cores such as Cortex-M0. */
    uint_least32_t sequence = atomic_load_explicit(&latest.sequence, memory_order_relaxed);
    atomic_store_explicit(&latest.sequence, sequence + 1u, memory_order_relaxed);
    /* The odd sequence must become visible before any data store. */
    atomic_thread_fence(memory_order_release);
    atomic_store_explicit(&latest.value, read_dma_value(), memory_order_relaxed);
    atomic_store_explicit(&latest.sequence, sequence + 2u, memory_order_release);
}

int32_t consume(void) {
    uint_least32_t before;
    uint_least32_t after;
    int_least32_t value;
    do {
        before = atomic_load_explicit(&latest.sequence, memory_order_acquire);
        value = atomic_load_explicit(&latest.value, memory_order_relaxed);
        /* Every data load must complete before the sequence is re-read. */
        atomic_thread_fence(memory_order_acquire);
        after = atomic_load_explicit(&latest.sequence, memory_order_relaxed);
    } while ((before & 1u) || before != after);
    return value;
}

/* Linker gate: ASSERT(__dma_end__ <= ORIGIN(SRAM)+LENGTH(SRAM), "SRAM overflow") */
