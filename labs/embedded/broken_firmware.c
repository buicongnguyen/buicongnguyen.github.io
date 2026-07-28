#include <stdint.h>
typedef struct { uint32_t sequence; int32_t value; } sample_t;
volatile sample_t latest;
void DMA_IRQHandler(void) { latest.sequence++; latest.value = read_dma_value(); }
int32_t consume(void) {
    uint32_t sequence=latest.sequence; int32_t value=latest.value;
    return valid_pair(sequence,value) ? value : ERROR_PARTIAL_SAMPLE;
}
