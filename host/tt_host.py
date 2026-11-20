"""Tiny Tapeout SDK v3 / MicroPython stepped-clock memory server.

No board pin numbers are hardcoded. A 20 us half period is conservative
bring-up timing, not a verified 20 MHz external-host implementation.
"""
import time
from host.memory import Memory
from host.protocol import reset_sequence, serve, check_inference

def _delay(us):
    if hasattr(time, 'sleep_us'):
        time.sleep_us(us)
    else:
        time.sleep(us/1000000)

class BoardLink:
    def __init__(self, tt, half_period_us=20):
        if half_period_us < 20:
            raise ValueError('Initial bring-up requires at least 20 us half periods')
        self.tt, self.delay = tt, half_period_us

    def execute(self, operation):
        name = operation[0]
        if name == 'reset':
            self.tt.clk(0)
            self.tt.reset_project(operation[1])
            _delay(self.delay)
            return None
        self.tt.clk(0)
        self.tt.ui_in.value = operation[1]
        if name == 'tick':
            self.tt.uio_in.value = operation[2]
        _delay(self.delay)
        if name == 'sample':
            return int(self.tt.uo_out.value)
        if name != 'tick':
            raise ValueError('Unknown host operation')
        self.tt.clk(1)
        _delay(self.delay)
        self.tt.clk(0)
        _delay(self.delay)
        return None

    def run(self, sequence):
        value = None
        while True:
            try:
                operation = sequence.send(value)
            except StopIteration as complete:
                return complete.args[0] if complete.args else None
            value = self.execute(operation)

def prepare_board(project='tt_um_cokane_soc'):
    from ttboard.demoboard import DemoBoard
    from ttboard.mode import RPMode
    tt = DemoBoard.get()
    design = tt.shuttle.get(project)
    if design is None:
        raise RuntimeError('Project is not present on this shuttle: '+project)
    tt.clock_project_stop()
    tt.uio_oe_pico.value = 0  # Release the bus before selecting this design.
    tt.apply_configs = False  # Do not let config.ini start a free-running clock.
    design.enable()
    tt.mode = RPMode.ASIC_RP_CONTROL
    if tt.manual_project_clock is not None:
        tt.manual_project_clock.monitoring = False
    tt.reset_project(True)
    tt.clock_project_once(msDelay=1)  # Configure the SDK's project-clock output.
    tt.clk(0)
    tt.ui_in.value = 32
    tt.uio_in.value = 0
    tt.uio_oe_pico.value = 255  # All eight uio pins are ASIC inputs in this design.
    return tt

def run(image='host/smoke.hex', inference=False, project='tt_um_cokane_soc'):
    memory = Memory()
    memory.load_hex(image)
    tt = prepare_board(project)
    link = BoardLink(tt)
    try:
        link.run(reset_sequence())
        stats = link.run(serve(memory, 0x30004 if inference else 0x1000,
                               4 if inference else 0x600d600d,
                               40000000 if inference else 200000))
        if inference:
            import json
            with open('host/expected.json') as stream:
                check_inference(memory, json.load(stream))
        elif memory.word(0x1004) != 0x1234ab78:
            raise RuntimeError('Byte-enable smoke-test mismatch')
        print('COKANE_HOST_PASS', stats)
        return memory, stats
    finally:
        # Success, failure and Ctrl-C all leave a stopped clock and asserted reset.
        tt.clk(0)
        tt.reset_project(True)
        tt.uio_oe_pico.value = 0
