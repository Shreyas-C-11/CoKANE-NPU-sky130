#include "cokane_scheduler.h"
typedef uint32_t (*read_fn)(unsigned);
typedef void (*write_fn)(unsigned,uint32_t);
static read_fn reader;
static write_fn writer;
void ck_bind(read_fn r, write_fn w) { reader=r; writer=w; }
uint32_t ck_test_read(unsigned off) { return reader(off); }
void ck_test_write(unsigned off, uint32_t value) { writer(off,value); }
unsigned ck_conv_size(void) { return sizeof(ck_conv_pool_descriptor); }
unsigned ck_dense_size(void) { return sizeof(ck_dense_descriptor); }
