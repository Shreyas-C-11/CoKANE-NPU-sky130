/* Straightforward CPU-only baseline: identical quantized operations/data,
 * including range scans. No CoKANE MMIO and no precomputed expected tensors. */
#include "cokane_scheduler.h"
static int validate(const int8_t *input, unsigned n, unsigned bits,
                    const int8_t *tables, unsigned entries) {
    int lo=-(1<<(bits-1)),hi=(1<<(bits-1))-1;
    for (unsigned i=0;i<n;i++) if(input[i]<lo || input[i]>hi) return -1;
    for (unsigned i=0;i<entries;i++) if(tables[i]<-32 || tables[i]>31) return -1;
    return 0;
}
static int clip(int sum) { return sum>31 ? 31 : sum < -32 ? -32 : sum; }
int ck_reference_conv_pool(const ck_conv_pool_descriptor *d) {
    unsigned w=d->width,h=d->height,cin=d->input_channels;
    unsigned pw=(w-2)/2,ph=(h-2)/2,depth=1u<<d->input_bits;
    if(validate(d->input,w*h*cin,d->input_bits,d->tables,cin*d->output_channels*9*depth)) return -1;
    for(unsigned oc=0;oc<d->output_channels;oc++)
        for(unsigned py=0;py<ph;py++)
            for(unsigned px=0;px<pw;px++) {
                int maximum=-32;
                for(unsigned dy=0;dy<2;dy++)
                    for(unsigned dx=0;dx<2;dx++) {
                        int sum=0;
                        for(unsigned ic=0;ic<cin;ic++)
                            for(unsigned ky=0;ky<3;ky++)
                                for(unsigned kx=0;kx<3;kx++) {
                                    unsigned address=(ic*h+py*2+dy+ky)*w+px*2+dx+kx;
                                    unsigned function=(oc*cin+ic)*9+ky*3+kx;
                                    unsigned code=(uint8_t)d->input[address]&(depth-1);
                                    sum+=d->tables[function*depth+code];
                                }
                        sum=clip(sum); if(sum>maximum) maximum=sum;
                    }
                d->output[(oc*ph+py)*pw+px]=(int8_t)maximum;
            }
    return 0;
}
int ck_reference_dense(const ck_dense_descriptor *d) {
    unsigned depth=1u<<d->input_bits;
    if(validate(d->input,d->features,d->input_bits,d->tables,d->features*d->outputs*depth)) return -1;
    for(unsigned oc=0;oc<d->outputs;oc++) {
        int sum=0;
        for(unsigned i=0;i<d->features;i++) {
            unsigned code=(uint8_t)d->input[i]&(depth-1);
            sum+=d->tables[(oc*d->features+i)*depth+code];
        }
        d->output[oc]=(int8_t)clip(sum);
    }
    return 0;
}


