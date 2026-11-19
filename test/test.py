"""Pin-only CPU firmware test, reusable against RTL and powered gate netlists."""
import random
import cocotb
from cocotb.triggers import Timer

class Program:
    def __init__(self): self.words=[]; self.labels={}; self.fixups=[]
    def emit(self,w): self.words.append(w & 0xffffffff)
    def label(self,n): self.labels[n]=4*len(self.words)
    def li(self,r,v):
        v &= 0xffffffff
        hi=((v+0x800)>>12)&0xfffff
        self.emit((hi<<12)|(r<<7)|0x37)
        self.addi(r,r,v-(hi<<12))
    def addi(self,d,s,v): self.emit(((v&4095)<<20)|(s<<15)|(d<<7)|0x13)
    def andi(self,d,s,v): self.emit(((v&4095)<<20)|(s<<15)|(7<<12)|(d<<7)|0x13)
    def store(self,r,base,off=0,byte=False):
        self.emit((((off&4095)>>5)<<25)|(r<<20)|(base<<15)|((0 if byte else 2)<<12)|((off&31)<<7)|0x23)
    def load(self,d,base,off=0): self.emit(((off&4095)<<20)|(base<<15)|(2<<12)|(d<<7)|3)
    def bne(self,a,b,label): self.fixups.append((len(self.words),a,b,label)); self.emit(0)
    def finish(self):
        for idx,a,b,label in self.fixups:
            v=self.labels[label]-4*idx
            assert -4096<=v<4096 and v%2==0
            self.words[idx]=(((v>>12)&1)<<31)|(((v>>5)&63)<<25)|(b<<20)|(a<<15)|(1<<12)|(((v>>1)&15)<<8)|(((v>>11)&1)<<7)|0x63
        return self.words

def firmware():
    p=Program(); p.li(1,0x20000000); p.li(10,0x1000)
    def check(reg,value): p.li(6,value); p.bne(reg,6,'fail')
    def clear(): p.li(2,2); p.store(2,1,8)
    serial=[0]
    def mac(a,b):
        p.li(2,a); p.store(2,1,0); p.li(2,b); p.store(2,1,4)
        p.li(2,1); p.store(2,1,8); poll()
    def poll():
        name='poll'+str(serial[0]); serial[0]+=1; p.label(name)
        p.load(3,1,12); p.andi(4,3,3); p.li(5,2); p.bne(4,5,name)
        p.andi(4,3,31); check(4,6) # busy=0, done=valid=1, error=0
    clear(); p.load(3,1,16); check(3,0)
    mac(3,-4); p.load(3,1,16); check(3,-12)
    mac(100,100); p.load(3,1,16); check(3,9988)
    mac(-128,127); p.load(3,1,16); check(3,-6268)
    # Upper byte stores must not change the low-byte operand register.
    p.li(2,7); p.store(2,1,0); p.li(2,99); p.store(2,1,1,byte=True)
    p.load(3,1,0); check(3,7)
    clear(); p.load(3,1,16); check(3,0)
    # Wrap the signed 24-bit accumulator through its positive limit.
    p.li(2,127); p.store(2,1,0); p.store(2,1,4); p.li(7,521)
    p.label('wrap_loop'); p.li(2,1); p.store(2,1,8); poll()
    p.addi(7,7,-1); p.bne(7,0,'wrap_loop')
    p.load(3,1,16); expected=((521*127*127+(1<<23))%(1<<24))-(1<<23); check(3,expected)
    # Reserved/unmapped regions complete and read zero in this baseline.
    for base in [0x10000000,0x30000000,0x40000000]:
        p.li(8,base); p.load(3,8); check(3,0)
    # Exercise host memory writes, reads and byte enables.
    p.li(2,0x12345678); p.store(2,10,4); p.load(3,10,4); check(3,0x12345678)
    p.li(2,0xab); p.store(2,10,5,byte=True); p.load(3,10,4); check(3,0x1234ab78)
    p.li(2,0x600d600d); p.store(2,10); p.emit(0x0000006f)
    p.label('fail'); p.li(2,0xbad00bad); p.store(2,10); p.emit(0x0000006f)
    words=p.finish()
    assert all(((w>>7)&31)<16 for w in words if (w&127) in [0x13,0x37,3])
    return words

async def tick(d,ctrl=0,data=0):
    d.clk.value=0; d.ui_in.value=ctrl; d.uio_in.value=data
    await Timer(25,unit='ns'); d.clk.value=1; await Timer(25,unit='ns')
    assert int(d.uio_oe.value)==0, 'Host input pins must never be driven'

async def peek(d,ctrl):
    d.clk.value=0; d.ui_in.value=ctrl; await Timer(5,unit='ns')
    return int(d.uo_out.value)

async def host_word(d,write_data=False):
    result=0
    for lane in range(4): result |= (await peek(d,lane|(16 if write_data else 0)))<<(8*lane)
    return result

async def execute(d,seed,disable_reset=False,negative_control=False):
    rng=random.Random(seed); d.ena.value=0 if disable_reset else 1; d.rst_n.value=1 if disable_reset else 0
    for _ in range(5): await tick(d)
    d.ena.value=1; d.rst_n.value=1
    words=firmware()
    if negative_control:
        assert words[9] == 0x00030313 # first expected value: addi x6,x6,0
        words[9] |= 1 << 20 # deliberately expect 1 after accumulator clear
    memory={i*4:w for i,w in enumerate(words)}; transactions=0
    for _ in range(150000):
        status=await peek(d,32)
        assert not status&128, 'CPU trapped'
        if status&0x60 != 0x60:
            await tick(d); continue
        address=await host_word(d); writing=bool(status&16); lanes=status&15
        for _ in range(rng.randrange(4)): await tick(d)
        if writing:
            value=await host_word(d,True); old=memory.get(address&~3,0)
            for lane in range(4):
                if lanes&(1<<lane): old=(old&~(255<<(8*lane)))|(value&(255<<(8*lane)))
            memory[address&~3]=old
        else:
            assert address&~3 in memory, f'Unexpected read at {address:#x}'
            value=memory[address&~3]
            for lane in range(4): await tick(d,4|lane,(value>>(8*lane))&255)
        await tick(d,8); await tick(d)
        transactions+=1
        if writing and address==0x1000:
            expected=0xbad00bad if negative_control else 0x600d600d
            assert memory[0x1000]==expected, f'Firmware signature: {memory[0x1000]:08x}, expected {expected:08x}'
            if negative_control:
                d._log.info('Firmware NEGATIVE_CONTROL_PASS wrong expected value rejected')
                return
            assert memory[0x1004]==0x1234ab78
            d._log.info('Firmware PASS seed=%d transactions=%d reset=%s',seed,transactions,'ena' if disable_reset else 'rst_n')
            return
    assert False, 'CPU/host transaction timeout'

@cocotb.test()
async def cpu_mac_firmware(d):
    await execute(d,19)
    await execute(d,20,disable_reset=True)
    await execute(d,21,negative_control=True)
