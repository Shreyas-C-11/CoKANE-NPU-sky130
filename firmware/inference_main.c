/* Synthetic data comes from a reproducible fixture, not a trained classifier. */
#include "cokane_scheduler.h"
#include "inference_fixture.h"

static int8_t feature_a[338], feature_b[50], scores[10];
static ck_scheduler scheduler;
static int8_t cpu_a[338], cpu_b[50], cpu_scores[10];
int ck_reference_conv_pool(const ck_conv_pool_descriptor *d);
int ck_reference_dense(const ck_dense_descriptor *d);
typedef struct {
    uint32_t magic, stage;
    int32_t error;
    uint32_t prediction, feature_a, count_a, feature_b, count_b, scores, count_scores;
    ck_statistics stats;
    uint32_t cpu_a, cpu_b, cpu_scores, cpu_prediction;
} inference_report;
static volatile inference_report *const report=(volatile inference_report *)0x30000;

int main(void) {
    report->magic=0; report->stage=1; report->error=0;
    ck_scheduler_init(&scheduler,1024);
    if (ck_read(CK_ID)!=0x434b0100u) { report->error=-99; goto fail; }
    ck_conv_pool_descriptor first={fixture_image,fixture_conv1,feature_a,
        784,sizeof(fixture_conv1),sizeof(feature_a),28,28,1,2,4};
    ck_conv_pool_descriptor second={feature_a,fixture_conv2,feature_b,
        sizeof(feature_a),sizeof(fixture_conv2),sizeof(feature_b),13,13,2,2,6};
    ck_dense_descriptor head={feature_b,fixture_dense,scores,
        sizeof(feature_b),sizeof(fixture_dense),sizeof(scores),50,10,6};
    int rc=ck_convolution_pool(&scheduler,&first);
    if (rc) { report->error=rc; goto fail; }
    report->stage=2;
    rc=ck_convolution_pool(&scheduler,&second);
    if (rc) { report->error=rc; goto fail; }
    report->stage=3;
    rc=ck_dense(&scheduler,&head);
    if (rc) { report->error=rc; goto fail; }
    report->prediction=ck_argmax(scores,10);
    report->feature_a=(uintptr_t)feature_a; report->count_a=sizeof(feature_a);
    report->feature_b=(uintptr_t)feature_b; report->count_b=sizeof(feature_b);
    report->scores=(uintptr_t)scores; report->count_scores=sizeof(scores);
    report->stats=scheduler.stats;
    report->stage=4;
    first.output=cpu_a; second.input=cpu_a; second.output=cpu_b;
    head.input=cpu_b; head.output=cpu_scores;
    if (ck_reference_conv_pool(&first) || ck_reference_conv_pool(&second) || ck_reference_dense(&head)) {
        report->error=-100; goto fail;
    }
    report->stage=5;
    report->cpu_a=(uintptr_t)cpu_a; report->cpu_b=(uintptr_t)cpu_b;
    report->cpu_scores=(uintptr_t)cpu_scores; report->cpu_prediction=ck_argmax(cpu_scores,10);
    __asm__ volatile ("" ::: "memory");
    report->magic=0x600d600d;
    for (;;) { }
fail:
    report->magic=0xbad00bad;
    for (;;) { }
}
