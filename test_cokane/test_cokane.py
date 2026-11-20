"""External Wishbone tests; expected sums/tensors use independent Python integers."""
import random
import cocotb
from cocotb.triggers import Timer

CMD, STATUS = 8, 4
BEGIN, ADD, FINAL, ABORT, CLEAR, POOL, LUT_CLEAR = range(1, 8)

def signed(v, bits=32):
    return v-(1 << bits) if v & (1 << (bits-1)) else v

def sat(v):
    return max(-32, min(31, v))

class Bus:
    def __init__(self, d): self.d=d; self.transfers=0
    async def tick(self):
        self.d.clk.value=0
        await Timer(25, unit='ns')
        self.d.clk.value=1
        await Timer(25, unit='ns')
    async def reset(self):
        d=self.d; d.cyc.value=0; d.stb.value=0; d.we.value=0; d.sel.value=0; d.rst.value=1
        for _ in range(3): await self.tick()
        d.rst.value=0; await self.tick()
    async def access(self, off, value=None, sel=15):
        d=self.d
        d.adr.value=0x10000000+off; d.dat_i.value=(value or 0)&0xffffffff
        d.sel.value=sel; d.we.value=int(value is not None); d.cyc.value=1; d.stb.value=1
        for _ in range(8):
            await self.tick()
            if int(d.ack.value): break
        else: raise AssertionError('Wishbone timeout')
        result=int(d.dat_o.value)
        d.cyc.value=0; d.stb.value=0; d.we.value=0
        await self.tick(); assert not int(d.ack.value)
        self.transfers+=1
        return result
    async def write(self, off, value, sel=15): return await self.access(off, value, sel)
    async def read(self, off): return await self.access(off)
    async def command(self, cmd): await self.write(CMD,cmd)
    async def idle(self):
        for _ in range(80):
            if not (await self.read(STATUS))&1: return
        raise AssertionError('Engine stuck busy')
    async def no_error(self):
        s=await self.read(STATUS); assert not s&8, f'error status {s:08x}'
    async def error(self, code):
        s=await self.read(STATUS); assert s&8 and (s>>8)&255==code, f'{s:08x} != error {code}'
        await self.command(CLEAR); await self.no_error()
    async def begin(self, lanes, terms, bits=6):
        await self.command(ABORT)
        await self.write(12,lanes); await self.write(16,terms); await self.write(36,bits)
        await self.command(BEGIN)
    async def table(self, values):
        await self.command(LUT_CLEAR); await self.write(32,0)
        for value in values: await self.write(40,value&63)
    async def inputs(self, values):
        for i,value in enumerate(values): await self.write(64+4*i,value)
    async def add(self, values):
        await self.inputs(values); await self.command(ADD); await self.idle(); await self.no_error()
    async def partials(self, count): return [signed(await self.read(128+4*i)) for i in range(count)]
    async def results(self, count): return [signed(await self.read(192+4*i)) for i in range(count)]

@cocotb.test()
async def arithmetic_and_protocol(d):
    b=Bus(d); await b.reset(); rng=random.Random(20261120)
    assert await b.read(0)==0x434b0100
    assert await b.read(192)==0 and await b.read(224)==0 and await b.read(40)==0
    # Narrow writes in other byte lanes must have no side effects.
    await b.write(12,0,sel=14); assert await b.read(12)==8
    for off,value in [(12,0),(12,9),(16,0),(16,65),(36,8),(32,64)]:
        await b.write(off,value); await b.error(3)
    await b.command(99); await b.error(6)
    await b.write(0x60,1); await b.error(5)
    await b.write(0x100,1); await b.error(5)
    await b.write(0x41,1); await b.error(5)
    assert await b.read(0x100)==0
    await b.command(ADD); await b.error(2)
    await b.command(FINAL); await b.error(2)
    # Missing LUT and input validation is atomic, including a missing last lane.
    await b.begin(8,1); await b.command(ADD); await b.error(4)
    await b.table([7]*64); await b.inputs([0]*7)
    await b.command(ADD); await b.error(4); assert await b.partials(8)==[0]*8
    await b.write(92,0); await b.command(ADD); await b.idle(); await b.no_error()
    assert await b.partials(8)==[7]*8
    await b.command(ADD); await b.error(2) # Too many terms.
    await b.command(FINAL); await b.idle(); assert await b.results(8)==[7]*8
    # LUT reload preserves wide sums; no early per-channel clipping.
    await b.begin(8,3)
    for value,expected in [(31,31),(31,62),(-32,30)]:
        await b.table([value]*64); assert await b.partials(8)==([0]*8 if expected==31 else ([31]*8 if expected==62 else [62]*8))
        await b.add([0]*8); assert await b.partials(8)==[expected]*8
    await b.command(FINAL); await b.idle(); assert await b.results(8)==[30]*8
    assert await b.read(24)==8*(2*3+1)
    assert await b.read(28)>await b.read(24)
    # Independent address-dependent functions, all batch lengths and bounds.
    for lanes in range(1,9):
        terms=[1,9,18,50,64,9,18,50][lanes-1]
        bits=4 if lanes%2 else 6; depth=1<<bits
        await b.begin(lanes,terms,bits); expected=[0]*lanes
        for term in range(terms):
            table=[rng.randrange(-32,32) for _ in range(depth)]
            codes=[rng.randrange(depth) for _ in range(lanes)]
            await b.table(table); await b.add(codes)
            expected=[a+table[x] for a,x in zip(expected,codes)]
            assert await b.partials(lanes)==expected
        await b.command(FINAL); await b.idle(); await b.no_error()
        assert await b.results(lanes)==list(map(sat,expected))
        assert await b.read(44)==lanes
        assert await b.read(24)==lanes*(2*terms+1)
        for _ in range(4): await b.tick()
        assert await b.results(lanes)==list(map(sat,expected))
    # Both full-width accumulator extremes and both saturation rails.
    for value in [-32,31]:
        await b.begin(1,64); await b.table([value]*64)
        for _ in range(64): await b.add([0])
        assert await b.partials(1)==[value*64]
        await b.command(FINAL); await b.idle(); assert await b.results(1)==[value]
    # Four-bit raw code ordering, stale/unwritten entries and consumed inputs.
    await b.begin(1,2,4); await b.table(list(range(16)))
    await b.write(64,63); await b.error(7)
    await b.add([15]); assert await b.partials(1)==[15]
    await b.command(ADD); await b.error(4)
    await b.command(LUT_CLEAR); await b.inputs([0]); await b.command(ADD); await b.error(4)
    assert await b.partials(1)==[15]
    await b.write(32,0); await b.write(40,1); await b.command(ADD); await b.idle()
    await b.command(FINAL); await b.idle(); assert await b.results(1)==[16]
    # Signed pooling, including all-negative inputs and independent groups.
    for values in [[-32,-10,-31,-20],[-32,-10,-31,-20,1,31,0,-1]]:
        await b.begin(len(values),1); await b.table(values+[0]*(64-len(values)))
        await b.add(list(range(len(values)))); await b.command(FINAL); await b.idle()
        await b.command(POOL); await b.idle(); await b.no_error()
        assert await b.read(48)==len(values)//4
        assert [signed(await b.read(224+4*i)) for i in range(len(values)//4)]==[max(values[i:i+4]) for i in range(0,len(values),4)]
    # Immutable context configuration and early finalization rejection.
    await b.begin(8,2); await b.write(12,1); await b.error(3); assert await b.read(12)==8
    await b.command(FINAL); await b.error(2)
    # Attempt LUT mutation while busy: rejected, current operation completes.
    await b.table([3]*64); await b.inputs([0]*8); await b.command(ADD)
    await b.write(40,31); await b.idle(); await b.error(1)
    assert await b.partials(8)==[3]*8
    # Abort invalidates the in-flight context and all results, but keeps the LUT.
    await b.inputs([0]*8); await b.command(ADD); await b.command(ABORT)
    await b.idle(); assert await b.read(STATUS)==0; assert await b.partials(8)==[0]*8
    await b.write(32,0); assert signed(await b.read(40))==3
    # Reset must invalidate a previously initialized table.
    await b.reset(); await b.begin(1,1); await b.inputs([0]); await b.command(ADD); await b.error(4)
    d._log.info('COKANE_PROTOCOL_PASS transfers=%d',b.transfers)

@cocotb.test()
async def independent_convolution_pool_dense(d):
    """Two differently shaped layers + dense head, nonconstant signed LUTs.

    Oracle traverses each output/tap directly. Driver schedules the same problem
    function-major in pooled batches, exercising layout and channel identity.
    """
    b=Bus(d); await b.reset(); rng=random.Random(731)
    image=[[[rng.randrange(16) for _ in range(10)] for _ in range(10)]]
    async def layer(image,cout,bits):
        cin=len(image); h=len(image[0]); w=len(image[0][0]); oh=h-2; ow=w-2
        funcs=[[[rng.randrange(-4,5) for _ in range(1<<bits)] for _ in range(cin*9)] for _ in range(cout)]
        expected=[]
        for oc in range(cout):
            conv=[]
            for y in range(oh):
                row=[]
                for x in range(ow):
                    total=0
                    for ic in range(cin):
                        for ky in range(3):
                            for kx in range(3):
                                code=image[ic][y+ky][x+kx]&((1<<bits)-1)
                                total+=funcs[oc][ic*9+ky*3+kx][code]
                    row.append(sat(total))
                conv.append(row)
            expected.append([[max(conv[y+dy][x+dx] for dy in range(2) for dx in range(2)) for x in range(0,ow-1,2)] for y in range(0,oh-1,2)])
        got=[[[None for _ in range(ow//2)] for _ in range(oh//2)] for _ in range(cout)]
        for oc in range(cout):
            windows=[(y,x) for y in range(0,oh-1,2) for x in range(0,ow-1,2)]
            for start in range(0,len(windows),2):
                wins=windows[start:start+2]
                positions=[(y+dy,x+dx) for y,x in wins for dy in range(2) for dx in range(2)]
                await b.begin(len(positions),cin*9,bits)
                for f,table in enumerate(funcs[oc]):
                    ic=f//9; ky=(f%9)//3; kx=f%3
                    await b.table(table)
                    await b.add([image[ic][y+ky][x+kx]&((1<<bits)-1) for y,x in positions])
                await b.command(FINAL); await b.idle(); await b.command(POOL); await b.idle(); await b.no_error()
                for i,(y,x) in enumerate(wins): got[oc][y//2][x//2]=signed(await b.read(224+4*i))
        assert got==expected
        return got
    l1=await layer(image,2,4); l2=await layer(l1,2,6)
    features=[v for channel in l2 for row in channel for v in row]
    scores=[]; expected=[]
    for cls in range(3):
        tables=[[rng.randrange(-32,32) for _ in range(64)] for _ in features]
        expected.append(sat(sum(t[x&63] for t,x in zip(tables,features))))
        await b.begin(1,len(features))
        for table,x in zip(tables,features): await b.table(table); await b.add([x&63])
        await b.command(FINAL); await b.idle(); scores.extend(await b.results(1))
    assert scores==expected
    # Negative control verifies that a changed expectation is actually rejected.
    assert scores!=[expected[0]+1]+expected[1:]
    d._log.info('COKANE_TENSOR_PASS layers=2 dense_classes=3 transfers=%d',b.transfers)
