#include <stdatomic.h>
#include <stdint.h>

int32_t read_dma_value(void);

typedef struct {
    atomic_uint_least32_t sequence;
    atomic_int_least32_t value;
} sample_t;

static sample_t latest;

/* Single-writer sequence lock (Boehm, "Can seqlocks get along with programming language
 * memory models?", 2012). An odd sequence means a write is in progress. */
void DMA_IRQHandler(void) {
    /* Exactly one writer, so a plain load+store replaces an RMW. That also avoids the
     * library fallback some cores (for example Cortex-M0) need for atomic_fetch_add. */
    uint_least32_t sequence = atomic_load_explicit(&latest.sequence, memory_order_relaxed);
    atomic_store_explicit(&latest.sequence, sequence + 1u, memory_order_relaxed);
    /* Keep the payload store after the odd sequence becomes visible. */
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
        /* An acquire *load* of `after` would not stop the value load from moving below it;
         * the acquire fence orders the payload read before the second sequence read. */
        atomic_thread_fence(memory_order_acquire);
        after = atomic_load_explicit(&latest.sequence, memory_order_relaxed);
    } while ((before & 1u) || before != after);
    return value;
}

/* Linker gate: ASSERT(__dma_end__ <= ORIGIN(SRAM)+LENGTH(SRAM), "SRAM overflow") */
