"""Exercise compiled C scheduling with a protocol model and independent oracle.

The real CPU+RTL test is separate. This fast test covers descriptor/error paths
and dimensions that would otherwise take much longer in CPU simulation.
"""
import ctypes as C
import hashlib,json,pathlib,random,sys
from inference_fixture import convolution_pool,dense,create

ROOT=pathlib.Path(__file__).resolve().parents[1]
class Stats(C.Structure):
    _fields_=[(k,C.c_uint32) for k in ['jobs','lut_entries','input_values','output_values','mmio_reads','mmio_writes','compute_cycles','context_cycles']]
class Scheduler(C.Structure): _fields_=[('poll_limit',C.c_uint32),('stats',Stats)]
Ptr=C.POINTER(C.c_int8)
common=[('input',Ptr),('tables',Ptr),('output',Ptr),('input_count',C.c_uint32),('table_count',C.c_uint32),('output_capacity',C.c_uint32)]
class Conv(C.Structure): _fields_=common+[('width',C.c_uint16),('height',C.c_uint16),('input_channels',C.c_uint8),('output_channels',C.c_uint8),('input_bits',C.c_uint8)]
class Dense(C.Structure): _fields_=common+[('features',C.c_uint16),('outputs',C.c_uint16),('input_bits',C.c_uint8)]
def array(x):return (C.c_int8*len(x))(*x)

class Device:
    def __init__(self):
        self.batch=8;self.terms=1;self.bits=6;self.active=False;self.error=False
        self.table=[0]*64;self.valid=set();self.inputs={};self.sums=[0]*8;self.result=[];self.pooled=[]
        self.addr=0;self.count=0;self.compute=0;self.elapsed=0;self.reads=0;self.writes=0;self.aborts=0
        self.stuck=False;self.fail_add=False;self.inject_failure=False
    def read(self,off):
        self.reads+=1;self.elapsed+=int(self.active)
        if off==4:return int(self.active)<<1 | int(self.error)<<3 | int(self.stuck)
        if off==24:return self.compute
        if off==28:return self.elapsed
        if 192<=off<224:return self.result[(off-192)//4]&0xffffffff
        if 224<=off<232:return self.pooled[(off-224)//4]&0xffffffff
        raise AssertionError(f'unexpected read {off:#x}')
    def write(self,off,value):
        self.writes+=1;self.elapsed+=int(self.active)
        if off==12:self.batch=value
        elif off==16:self.terms=value
        elif off==36:self.bits=value
        elif off==32:self.addr=value
        elif off==40:
            self.table[self.addr]=(value&63)-64 if value&32 else value&63
            self.valid.add(self.addr);self.addr=(self.addr+1)&63
        elif 64<=off<96:self.inputs[(off-64)//4]=value
        elif off==8:
            if value==1:
                assert not self.active and not self.error
                self.sums=[0]*8;self.inputs={};self.count=0;self.compute=0;self.elapsed=0;self.active=True
            elif value==2:
                assert self.active and self.count<self.terms
                assert all(i in self.inputs and self.inputs[i] in self.valid for i in range(self.batch))
                if self.inject_failure:self.error=True;return
                if self.fail_add:self.stuck=True;return
                for i in range(self.batch):self.sums[i]+=self.table[self.inputs[i]]
                self.inputs={};self.count+=1;self.compute+=2*self.batch
            elif value==3:
                assert self.active and self.count==self.terms
                self.result=[max(-32,min(31,x)) for x in self.sums[:self.batch]]
                self.compute+=self.batch;self.active=False
            elif value==4:
                self.active=False;self.stuck=False;self.error=False;self.aborts+=1
            elif value==6:
                assert len(self.result) in [4,8]
                self.pooled=[max(self.result[i:i+4]) for i in range(0,len(self.result),4)]
                self.compute+=len(self.pooled)
            elif value==7:self.valid=set()
            else:raise AssertionError(f'unexpected command {value}')
        else:raise AssertionError(f'unexpected write {off:#x}')

def main():
    lib=C.CDLL(sys.argv[1]);read_t=C.CFUNCTYPE(C.c_uint32,C.c_uint);write_t=C.CFUNCTYPE(None,C.c_uint,C.c_uint32)
    lib.ck_bind.argtypes=[read_t,write_t]
    lib.ck_scheduler_init.argtypes=[C.POINTER(Scheduler),C.c_uint32]
    lib.ck_convolution_pool.argtypes=[C.POINTER(Scheduler),C.POINTER(Conv)]
    lib.ck_dense.argtypes=[C.POINTER(Scheduler),C.POINTER(Dense)]
    lib.ck_argmax.argtypes=[Ptr,C.c_uint];lib.ck_argmax.restype=C.c_uint
    lib.ck_reference_conv_pool.argtypes=[C.POINTER(Conv)]
    lib.ck_reference_dense.argtypes=[C.POINTER(Dense)]
    assert lib.ck_conv_size()==C.sizeof(Conv) and lib.ck_dense_size()==C.sizeof(Dense)
    callbacks=[]
    def bind(device):
        # Callback exceptions are fatal: collect them rather than allowing ctypes
        # to print and ignore an invalid operation.
        failures=[]
        def read(off):
            try:return device.read(off)
            except Exception as e:failures.append(e);return 8
        def write(off,value):
            try:device.write(off,value)
            except Exception as e:failures.append(e)
        rr,ww=read_t(read),write_t(write);callbacks[:]=[rr,ww];lib.ck_bind(rr,ww)
        return failures
    rng=random.Random(418);cases=0
    for w,h,cin,cout,bits in [(4,4,1,1,4),(5,9,2,3,6),(8,8,4,3,6),(11,9,2,2,4),(32,4,1,1,6)]:
        values=[rng.randrange(-(1<<(bits-1)),1<<(bits-1)) for _ in range(w*h*cin)]
        tables=[rng.randrange(-4,5) for _ in range(cout*cin*9*(1<<bits))]
        expected=convolution_pool(values,w,h,cin,cout,bits,tables)
        a,t,o=array(values),array(tables),array([99]*(len(expected)+2))
        d=Conv(a,t,o,len(a),len(t),len(o),w,h,cin,cout,bits)
        model=Device();errors=bind(model);s=Scheduler();lib.ck_scheduler_init(C.byref(s),16)
        assert lib.ck_convolution_pool(C.byref(s),C.byref(d))==0
        assert list(o)[:len(expected)]==expected and list(o)[-2:]==[99,99]
        assert not errors and s.stats.mmio_reads==model.reads and s.stats.mmio_writes==model.writes
        cases+=1
    # Full descriptor sequence also runs natively against the direct oracle.
    f=create();model=Device();errors=bind(model);s=Scheduler();lib.ck_scheduler_init(C.byref(s),16)
    a,t1,t2,td=array(f['image']),array(f['conv1']),array(f['conv2']),array(f['dense'])
    o1,o2,score=array([0]*338),array([0]*50),array([0]*10)
    d1=Conv(a,t1,o1,784,len(t1),338,28,28,1,2,4)
    d2=Conv(o1,t2,o2,338,len(t2),50,13,13,2,2,6)
    dh=Dense(o2,td,score,50,len(td),10,50,10,6)
    assert lib.ck_convolution_pool(C.byref(s),C.byref(d1))==0
    assert list(o1)==f['expected_a']
    assert lib.ck_convolution_pool(C.byref(s),C.byref(d2))==0
    assert list(o2)==f['expected_b']
    assert lib.ck_dense(C.byref(s),C.byref(dh))==0 and list(score)==f['expected_scores']
    assert lib.ck_argmax(score,10)==f['prediction'] and not errors
    assert (s.stats.jobs,s.stats.lut_entries,s.stats.compute_cycles)==(206,86432,34486)
    cases+=1
    # Straightforward CPU-only arithmetic is checked against the same oracle.
    ca,cb,cs=array([0]*338),array([0]*50),array([0]*10)
    c1=Conv.from_buffer_copy(d1);c2=Conv.from_buffer_copy(d2);ch=Dense.from_buffer_copy(dh)
    c1.output=ca;c2.input=ca;c2.output=cb;ch.input=cb;ch.output=cs
    before=(model.reads,model.writes)
    assert lib.ck_reference_conv_pool(C.byref(c1))==0 and list(ca)==f['expected_a']
    assert lib.ck_reference_conv_pool(C.byref(c2))==0 and list(cb)==f['expected_b']
    assert lib.ck_reference_dense(C.byref(ch))==0 and list(cs)==f['expected_scores']
    assert (model.reads,model.writes)==before
    cases+=1
    # Invalid descriptors/quantization/aliases cause zero device traffic.
    model=Device();errors=bind(model);s=Scheduler();lib.ck_scheduler_init(C.byref(s),3)
    def invalid(desc,expected=-1):
        before=(model.reads,model.writes)
        assert lib.ck_convolution_pool(C.byref(s),C.byref(desc))==expected
        assert (model.reads,model.writes)==before
    for field,value in [('width',0),('width',33),('height',3),('input_channels',5),('input_channels',0),('output_channels',0),('input_bits',8),('input_count',783),('table_count',1),('output_capacity',337)]:
        bad=Conv.from_buffer_copy(d1);setattr(bad,field,value);invalid(bad);cases+=1
    bad=Conv.from_buffer_copy(d1);bad.output=bad.input;invalid(bad);cases+=1
    old=a[0];a[0]=8;invalid(d1,-5);a[0]=old;cases+=1
    old=t1[0];t1[0]=32;invalid(d1,-5);t1[0]=old;cases+=1
    for field,value in [('features',65),('features',0),('outputs',33),('input_bits',8),('table_count',0),('output_capacity',9)]:
        bad=Dense.from_buffer_copy(dh);setattr(bad,field,value)
        before=(model.reads,model.writes);assert lib.ck_dense(C.byref(s),C.byref(bad))==-1
        assert (model.reads,model.writes)==before;cases+=1
    # Existing context belongs to its caller: the scheduler must not abort it.
    model.active=True
    assert lib.ck_dense(C.byref(s),C.byref(dh))==-2 and model.aborts==0 and model.writes==0
    model.active=False;model.error=True
    assert lib.ck_dense(C.byref(s),C.byref(dh))==-3 and model.aborts==0
    cases+=2
    # Runtime engine error and timeout cancel owned work and preserve sentinels.
    for timeout in [False,True]:
        model=Device();model.fail_add=timeout;model.inject_failure=not timeout
        errors=bind(model);s=Scheduler();lib.ck_scheduler_init(C.byref(s),3)
        for i in range(10):score[i]=99
        assert lib.ck_dense(C.byref(s),C.byref(dh))==(-4 if timeout else -3)
        assert model.aborts==1 and not model.active and list(score)==[99]*10 and not errors
        cases+=1
    assert lib.ck_argmax(array([-4,-2,-2,-8]),4)==1
    result={'result':'PASS','cases':cases,'scope':'Compiled C scheduler against a behavioral protocol model and independent tensor oracle; separate CPU RTL execution required','full_synthetic_profile':True,'invalid_descriptor_zero_device_writes':True,'timeout_and_hardware_error_abort':True}
    (ROOT/'evidence/cokane/scheduler-host-validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print('SCHEDULER_HOST_PASS',cases)

if __name__=='__main__':main()
