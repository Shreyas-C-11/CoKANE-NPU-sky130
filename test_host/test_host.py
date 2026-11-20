"""Exercise the board's exact shared host sequencer against the actual chip RTL."""
import pathlib
import sys
import cocotb
from cocotb.triggers import Timer
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from host.memory import Memory
from host.protocol import reset_sequence, serve

async def drive(dut, sequence):
    value = None
    while True:
        try:
            operation = sequence.send(value)
        except StopIteration as complete:
            return complete.args[0] if complete.args else None
        dut.clk.value = 0
        if operation[0] == 'reset':
            dut.rst_n.value = int(not operation[1])
            await Timer(100, unit='ns')
            value = None
            continue
        dut.ui_in.value = operation[1]
        if operation[0] == 'tick':
            dut.uio_in.value = operation[2]
        await Timer(100, unit='ns')
        assert int(dut.uio_oe.value) == 0 and int(dut.uio_out.value) == 0
        if operation[0] == 'sample':
            value = int(dut.uo_out.value)
        else:
            dut.clk.value = 1
            await Timer(100, unit='ns')
            dut.clk.value = 0
            await Timer(100, unit='ns')
            value = None

@cocotb.test()
async def board_host_cpu_mac_cokane(dut):
    dut.ena.value = 1
    dut.rst_n.value = 0
    dut.clk.value = 0
    dut.ui_in.value = 32
    dut.uio_in.value = 0
    memory = Memory()
    memory.load_hex(str(ROOT/'host/smoke.hex'))
    await drive(dut, reset_sequence())
    result = await drive(dut, serve(memory))
    assert memory.word(0x1000) == 0x600d600d
    assert memory.word(0x1004) == 0x1234ab78
    dut._log.info('REAL_HOST_SEQUENCER_PASS %s', result)
