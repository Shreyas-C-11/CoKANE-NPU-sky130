#ifndef COKANE_H
#define COKANE_H
#include <stdint.h>
#define COKANE_BASE 0x10000000u
enum { CK_ID=0, CK_STATUS=4, CK_COMMAND=8, CK_BATCH=12, CK_TERMS=16,
       CK_TERMS_DONE=20, CK_COMPUTE_CYCLES=24, CK_ELAPSED_CYCLES=28,
       CK_LUT_ADDR=32, CK_INPUT_BITS=36, CK_LUT_DATA=40, CK_RESULT_COUNT=44,
       CK_POOL_COUNT=48, CK_INPUT=64, CK_PSUM=128, CK_RESULT=192, CK_POOL_RESULT=224 };
enum { CK_BEGIN=1, CK_ADD=2, CK_FINALIZE=3, CK_ABORT=4,
       CK_CLEAR_ERROR=5, CK_POOL=6, CK_LUT_CLEAR=7 };
static inline void ck_write(unsigned off, uint32_t value) {
    *(volatile uint32_t *)(uintptr_t)(COKANE_BASE+off)=value;
}
static inline uint32_t ck_read(unsigned off) {
    return *(volatile uint32_t *)(uintptr_t)(COKANE_BASE+off);
}
/* Bounded polling: returns 0 on idle/no error, -1 on sticky error, -2 timeout. */
static inline int ck_wait(unsigned budget) {
    while (budget--) {
        uint32_t status=ck_read(CK_STATUS);
        if (!(status&1u)) return status&8u ? -1 : 0;
    }
    return -2;
}
/* Logical table function is supplied in raw two's-complement code order. */
static inline int ck_load_function(const int8_t *table, unsigned bits) {
    if (bits!=4 && bits!=6) return -1;
    ck_write(CK_COMMAND,CK_LUT_CLEAR); ck_write(CK_LUT_ADDR,0);
    for (unsigned i=0;i<(1u<<bits);++i) ck_write(CK_LUT_DATA,(uint8_t)table[i]&63u);
    return 0;
}
#endif
