#ifndef COKANE_SCHEDULER_H
#define COKANE_SCHEDULER_H
#include "cokane.h"

enum { CK_OK=0, CK_INVALID=-1, CK_DEVICE_BUSY=-2, CK_DEVICE_ERROR=-3,
       CK_TIMEOUT=-4, CK_QUANTIZATION=-5 };
typedef struct {
    uint32_t jobs, lut_entries, input_values, output_values;
    uint32_t mmio_reads, mmio_writes, compute_cycles, context_cycles;
} ck_statistics;
typedef struct {
    uint32_t poll_limit; /* Maximum status reads per wait, not clock cycles. */
    ck_statistics stats;
} ck_scheduler;
typedef struct {
    const int8_t *input, *tables;
    int8_t *output;
    uint32_t input_count, table_count, output_capacity;
    uint16_t width, height;
    uint8_t input_channels, output_channels, input_bits;
} ck_conv_pool_descriptor;
typedef struct {
    const int8_t *input, *tables;
    int8_t *output;
    uint32_t input_count, table_count, output_capacity;
    uint16_t features, outputs;
    uint8_t input_bits;
} ck_dense_descriptor;

/* Inputs/features are signed bytes in C,H,W order. LUT entries are signed
 * six-bit values stored one per byte, functions in out,in,ky,kx order and
 * entries in raw two's-complement input-code order. No in-place output.
 * On runtime failure, discard the entire layer's possibly partial output.
 * An already-active/busy device is never aborted by another layer call.
 */
void ck_scheduler_init(ck_scheduler *s, uint32_t poll_limit);
int ck_convolution_pool(ck_scheduler *s, const ck_conv_pool_descriptor *d);
int ck_dense(ck_scheduler *s, const ck_dense_descriptor *d);
unsigned ck_argmax(const int8_t *scores, unsigned count); /* First index wins ties. */
#endif
