#include "cokane_scheduler.h"

static void wr(ck_scheduler *s, unsigned off, uint32_t value) {
    ck_write(off,value); s->stats.mmio_writes++;
}
static uint32_t rd(ck_scheduler *s, unsigned off) {
    s->stats.mmio_reads++; return ck_read(off);
}
void ck_scheduler_init(ck_scheduler *s, uint32_t poll_limit) {
    ck_statistics zero={0}; s->poll_limit=poll_limit; s->stats=zero;
}
static int wait_idle(ck_scheduler *s) {
    uint32_t reads=0, status=1;
    while (reads<s->poll_limit) {
        status=ck_read(CK_STATUS); reads++;
        if (!(status&1u)) break;
    }
    s->stats.mmio_reads+=reads;
    if (status&1u) return CK_TIMEOUT;
    return status&8u ? CK_DEVICE_ERROR : CK_OK;
}
static int device_available(ck_scheduler *s) {
    uint32_t status=rd(s,CK_STATUS);
    if (status&3u) return CK_DEVICE_BUSY;
    return status&8u ? CK_DEVICE_ERROR : CK_OK;
}
static int stop_failed_job(ck_scheduler *s, int error) {
    wr(s,CK_COMMAND,CK_ABORT); return error;
}
static int valid_range(const void *p, uint32_t count) {
    return p && count && (uintptr_t)p<=UINTPTR_MAX-count;
}
static int overlaps(const void *a, uint32_t n, const void *b, uint32_t m) {
    return (uintptr_t)a<(uintptr_t)b+m && (uintptr_t)b<(uintptr_t)a+n;
}
static int validate_buffers(const int8_t *input, uint32_t count,
        const int8_t *tables, uint32_t entries, int8_t *output, uint32_t out,
        unsigned bits) {
    if ((bits!=4 && bits!=6) || !valid_range(input,count) ||
        !valid_range(tables,entries) || !valid_range(output,out) ||
        overlaps(input,count,output,out) || overlaps(tables,entries,output,out))
        return CK_INVALID;
    int lo=-(1<<(bits-1)), hi=(1<<(bits-1))-1;
    for (uint32_t i=0;i<count;i++)
        if (input[i]<lo || input[i]>hi) return CK_QUANTIZATION;
    for (uint32_t i=0;i<entries;i++)
        if (tables[i]<-32 || tables[i]>31) return CK_QUANTIZATION;
    return CK_OK;
}
static void begin(ck_scheduler *s, unsigned batch, unsigned terms, unsigned bits) {
    wr(s,CK_BATCH,batch); wr(s,CK_TERMS,terms); wr(s,CK_INPUT_BITS,bits);
    wr(s,CK_COMMAND,CK_BEGIN);
}
static void load_function(ck_scheduler *s, const int8_t *table, unsigned depth) {
    wr(s,CK_COMMAND,CK_LUT_CLEAR); wr(s,CK_LUT_ADDR,0);
    for (unsigned i=0;i<depth;i++) ck_write(CK_LUT_DATA,(uint8_t)table[i]&63u);
    s->stats.mmio_writes+=depth; s->stats.lut_entries+=depth;
}
static int finalize(ck_scheduler *s, int pool) {
    wr(s,CK_COMMAND,CK_FINALIZE); int rc=wait_idle(s); if (rc) return rc;
    if (pool) { wr(s,CK_COMMAND,CK_POOL); rc=wait_idle(s); if (rc) return rc; }
    s->stats.compute_cycles+=rd(s,CK_COMPUTE_CYCLES);
    s->stats.context_cycles+=rd(s,CK_ELAPSED_CYCLES);
    s->stats.jobs++; return CK_OK;
}
int ck_convolution_pool(ck_scheduler *s, const ck_conv_pool_descriptor *d) {
    if (!s || !s->poll_limit || !d || d->width<4 || d->height<4 ||
        d->width>32 || d->height>32 || !d->input_channels || d->input_channels>4 ||
        !d->output_channels || d->output_channels>32 ||
        (d->input_bits!=4 && d->input_bits!=6)) return CK_INVALID;
    unsigned w=d->width, h=d->height, cin=d->input_channels;
    unsigned pw=(w-2)/2, ph=(h-2)/2, plane=pw*ph, terms=cin*9;
    unsigned depth=1u<<d->input_bits, input_size=w*h*cin;
    unsigned table_size=d->output_channels*terms*depth, output_size=plane*d->output_channels;
    if (d->input_count<input_size || d->table_count<table_size ||
        d->output_capacity<output_size) return CK_INVALID;
    int rc=validate_buffers(d->input,input_size,d->tables,table_size,d->output,output_size,d->input_bits);
    if (rc) return rc;
    rc=device_available(s); if (rc) return rc;
    unsigned mask=depth-1;
    for (unsigned oc=0;oc<d->output_channels;oc++) {
        for (unsigned first=0;first<plane;first+=2) {
            unsigned windows=plane-first>=2 ? 2 : 1, lanes=windows*4;
            unsigned anchors[8];
            for (unsigned g=0;g<windows;g++) {
                unsigned q=first+g, y=(q/pw)*2, x=(q%pw)*2;
                unsigned a=y*w+x;
                anchors[g*4]=a; anchors[g*4+1]=a+1;
                anchors[g*4+2]=a+w; anchors[g*4+3]=a+w+1;
            }
            begin(s,lanes,terms,d->input_bits);
            const int8_t *table=d->tables+oc*terms*depth;
            for (unsigned ic=0;ic<cin;ic++)
                for (unsigned ky=0;ky<3;ky++)
                    for (unsigned kx=0;kx<3;kx++,table+=depth) {
                        load_function(s,table,depth);
                        unsigned offset=ic*w*h+ky*w+kx;
                        for (unsigned lane=0;lane<lanes;lane++)
                            ck_write(CK_INPUT+lane*4,(uint8_t)d->input[anchors[lane]+offset]&mask);
                        s->stats.mmio_writes+=lanes; s->stats.input_values+=lanes;
                        wr(s,CK_COMMAND,CK_ADD); rc=wait_idle(s);
                        if (rc) return stop_failed_job(s,rc);
                    }
            rc=finalize(s,1); if (rc) return stop_failed_job(s,rc);
            for (unsigned g=0;g<windows;g++)
                d->output[oc*plane+first+g]=(int8_t)rd(s,CK_POOL_RESULT+g*4);
            s->stats.output_values+=windows;
        }
    }
    return CK_OK;
}
int ck_dense(ck_scheduler *s, const ck_dense_descriptor *d) {
    if (!s || !s->poll_limit || !d || !d->features || d->features>64 ||
        !d->outputs || d->outputs>32 || (d->input_bits!=4 && d->input_bits!=6))
        return CK_INVALID;
    unsigned depth=1u<<d->input_bits, entries=d->features*d->outputs*depth;
    if (d->input_count<d->features || d->table_count<entries || d->output_capacity<d->outputs)
        return CK_INVALID;
    int rc=validate_buffers(d->input,d->features,d->tables,entries,d->output,d->outputs,d->input_bits);
    if (rc) return rc;
    rc=device_available(s); if (rc) return rc;
    const int8_t *table=d->tables;
    for (unsigned oc=0;oc<d->outputs;oc++) {
        begin(s,1,d->features,d->input_bits);
        for (unsigned f=0;f<d->features;f++,table+=depth) {
            load_function(s,table,depth);
            wr(s,CK_INPUT,(uint8_t)d->input[f]&(depth-1)); s->stats.input_values++;
            wr(s,CK_COMMAND,CK_ADD); rc=wait_idle(s);
            if (rc) return stop_failed_job(s,rc);
        }
        rc=finalize(s,0); if (rc) return stop_failed_job(s,rc);
        d->output[oc]=(int8_t)rd(s,CK_RESULT); s->stats.output_values++;
    }
    return CK_OK;
}
unsigned ck_argmax(const int8_t *scores, unsigned count) {
    unsigned best=0;
    for (unsigned i=1;i<count;i++) if (scores[i]>scores[best]) best=i;
    return best;
}
