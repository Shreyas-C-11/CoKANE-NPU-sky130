# Stepped-clock external-memory host

This is external RP2 software, not hardware inside the ASIC. The same protocol
generator is exercised against the actual CPU/MAC/CoKANE RTL in `test_host/`.
Board execution has **not** been measured: there is no fabricated CoKANE chip or
attached board in this session. RTL co-simulation does not certify PCB timing.

## Hardware and software

Use a Tiny Tapeout ETR demoboard (RP2350) with Tiny Tapeout MicroPython SDK v3,
or a compatible older RP2040 demoboard after checking its SDK API and RAM use.
The design must be selected by its actual shuttle name `tt_um_cokane_soc`.
No numeric project slot is guessed; it will be assigned by the shuttle.
Keep input DIP switches off and disconnect external drivers from the UI/UIO
headers while the RP2 controls the design. Use the demoboard's normal voltage
translation; never connect MCU signals to bare 1.8 V core pins.

The driver uses SDK port names instead of GPIO numbers. All eight UIO pins are
ASIC inputs: `uio_oe=0`. The RP2 enables its own UIO output drivers only after
selecting this design, and releases them on completion, failure or Ctrl-C.

## Install and run

Copy the `host/` directory to the MicroPython filesystem using the board's
normal USB/REPL file-transfer tool. There is no need to modify `boot.py`.
The firmware images are plain text: one 32-bit little-endian word as eight
hexadecimal digits per line, starting at CPU address zero.

At the REPL:

```python
from host.tt_host import run
memory, stats = run()  # host/smoke.hex: CPU, MAC, CoKANE and byte-enable checks
```

Expected output starts with `COKANE_HOST_PASS`. The smoke firmware writes
`0x600d600d` at external address `0x1000` and `0x1234ab78` at `0x1004`.
A trap, failure signature, out-of-range access or cycle limit raises an error
and leaves the clock low and the project in reset.

After the smoke test succeeds, the frozen synthetic network can be run with:

```python
memory, stats = run('host/inference.hex', inference=True)
```

This checks all 338 first-layer features, 50 second-layer features, ten scores
and argmax against `host/expected.json`. It stops when the accelerator phase
writes stage 4; it does not continue the firmware's optional CPU-only benchmark.
This is a synthetic numerical fixture, not trained MNIST accuracy validation.

## Timing and memory

The RP2 supplies every clock edge. There is **no free-running project clock**.
Before an edge it holds control/data stable for at least 20 us; it also holds
the clock high for at least 20 us. Additional low time and Python overhead make
the actual rate lower than 25 kHz. The ASIC's qualified 20 MHz limit is a
separate core timing result; this software makes no 20 MHz host claim.

Sampling output bytes does not advance the clock. This allows arbitrarily
slow memory service without losing a request. Read bytes are captured on four
rising edges, ACK is asserted for one edge, then deasserted for one edge.
Reset is held active for eight clock cycles and released while the clock is low.
The optional demoboard manual-clock button monitor is disabled during service.

RAM addresses span 256 KiB, but pages are allocated on demand so zero regions
do not consume that much MCU RAM. The code, tables, feature maps, high stack and
report area remain addressable. Actual MCU free memory still limits the loaded
workload; use the small smoke image first, particularly on RP2040 boards.
Full inference under Python single-stepping can be very slow.

## Local checks

```sh
python -m unittest host.test_memory -v
make -C test_host
python -m cocotb_tools.check_results test_host/results.xml
```

`test_host` drives the unchanged top-level RTL pins using `host/protocol.py`.
It exercises the same firmware signatures used on the board. On-board SDK
port configuration, voltage levels and physical waveforms still require a
real-board smoke test and logic-analyzer review before claiming hardware host
validation. A future FPGA/PIO host may run faster, but must preserve the same
protocol and meet the external setup/hold requirements.

References:

- [Tiny Tapeout ETR SDK guide](https://tinytapeout.com/guides/get-started-demoboard-etr/)
- [Tiny Tapeout SDK source](https://github.com/TinyTapeout/tt-micropython-firmware)
