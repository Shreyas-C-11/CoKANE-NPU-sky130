# CPU + hybrid MAC baseline

PicoRV32 RV32E-sized CPU (16 registers, uncompressed instructions, no hardware multiply/divide, counters or interrupts), Wishbone decoder and MAC Sentry hybrid 8-bit signed / 24-bit wrapping MAC. Target: SKY130, 3x4 Tiny Tapeout tiles, 20 MHz (50 ns).

This is an independently verified CPU+MAC development baseline. CoKANE, QSPI and UART are excluded. Program/data memory is supplied by a synchronous external host through the pins. Reserved CoKANE/peripheral reads acknowledge with zero. The module retains its imported name `tt_um_cokane_soc` for flow compatibility.

## Validation status

Pin-only RTL firmware regression passes with random host wait states, both external reset and deselection reset, signed arithmetic, 521-operation accumulator overflow, MAC status polling, byte-enable handling, and external-memory read/write checks. Each boot completes 7,959 host transactions. Physical implementation, gate-level simulation and prechecks remain pending until reports demonstrate completion. Passing RTL is not tapeout sign-off.

## Run locally on the development server

Create `.venv` using Python 3.11 and install `test/requirements.txt`. Then run `scripts/test-local.sh`. The simulator wrappers use the sibling `../tools/oss-cad-suite` installation and avoid its Python environment override. On an ordinary Icarus installation: activate the Python environment and run `make -C test`.

Run `scripts/harden-local.sh` for the existing server LibreLane/PDK setup. This uses sibling `../ttvenv`, `../pyextra`, `../pdk` and `../tools/librelane-devshell`. Build outputs are ignored. `src/config.json` is the authoritative hand-edited flow configuration; generated user/merged configurations are ignored. `tt/` is a bundled support-tool snapshot; provenance is in `evidence/source-provenance.json`.

## Host protocol

All host inputs must meet setup/hold relative to `clk`; there is no asynchronous clock crossing. Use a host-controlled clock for bring-up. Reset with `rst_n=0` or `ena=0` for several rising edges. Keep `ena=1` while executing.

- `ui[1:0]`: byte lane (little endian).
- `ui[2]`: at a rising edge, capture `uio_in` into that byte of the 32-bit memory read-data register.
- `ui[3]`: acknowledge the pending external-memory request. Assert only after all read bytes are loaded. Do not capture a byte on the same edge as acknowledging it. Pulse for one clock, then deassert.
- `ui[4]`: output CPU write data instead of address.
- `ui[5]`: output status, overriding address/data selection.
- `ui[7:6]`: reserved, drive zero.
- `uo[7:0]`: selected address/data byte; in status mode `{trap,cyc,stb,we,sel[3:0]}`.
- All `uio` pins are host inputs; output enables are always zero.

Wait for status `cyc=stb=1`; inspect address, write direction and byte enables. For reads, load four bytes, then acknowledge. For writes, read four data bytes and apply the selected byte enables to host memory before acknowledging. Inputs and address/data selections can change between clock edges while the CPU waits.

## MAC registers

Base `0x20000000`: A `+0x00`, B `+0x04`, CTRL `+0x08` (bit0 start, bit1 clear), STATUS `+0x0c`, signed ACC `+0x10`. A/B/CTRL only accept writes with byte enable 0. Poll busy low before issuing start/clear. Completion and fault status are retained for firmware readback. STATUS: busy bit0, done bit1, valid bit2, error bits4:3, corrected bit5, detected bit6, retried bit7, retry count bits9:8. This integration does not independently protect the bus or CPU.

The hybrid core combines SECDED accumulator storage, modulo-7 candidate checking and at most two extra attempts. It has documented shared-dependency and residue-collision limitations; it is not comprehensive fault protection. Upstream licenses and provenance are retained.

## Acceptance gates

Require functional RTL tests, completed physical flow, required DRC/LVS/antenna checks, setup/hold across required corners at 50 ns, pin-level gate tests, SDF timing validation where supported, and Tiny Tapeout prechecks. Retain source identities and reports. Until these pass, do not label this design confirmed for tapeout.
