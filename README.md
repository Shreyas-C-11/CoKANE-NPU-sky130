# CPU + hybrid MAC baseline

PicoRV32 RV32E-sized CPU (16 registers, uncompressed instructions, no hardware multiply/divide, counters or interrupts), Wishbone decoder and MAC Sentry hybrid 8-bit signed / 24-bit wrapping MAC. Target: SKY130, 3x4 Tiny Tapeout tiles, 20 MHz (50 ns).

This is an independently verified CPU+MAC development baseline. CoKANE, QSPI and UART are excluded. Program/data memory is supplied by a synchronous external host through the pins. Reserved CoKANE/peripheral reads acknowledge with zero. The module retains its imported name `tt_um_cokane_soc` for flow compatibility.

## Validation status

The accepted qualification scope is in `evidence/validation-policy.json`: RTL, functional gate simulation, nine-corner STA, electrical limits, physical checks and shuttle prechecks. SDF timing qualification is excluded by user agreement because the available simulators do not implement the unmodified SKY130 timing models correctly.

Use the artifact-bound `evidence/qualification-<run>.json` result to identify a qualified run. A LibreLane "Flow complete" message alone is insufficient: electrical findings may be warnings. A run must have a PASS qualification record before it is tagged as a baseline.

The regression boots through the physical pins with randomized host stalls, checks signed MAC arithmetic and accumulator overflow, exercises byte writes and memory responses, and restarts using reset and deselection. A negative control deliberately changes an expected value and must reach the firmware failure signature. The test host paces the clock while serving memory; 20 MHz timing closure is established separately by STA.

## Run locally on the development server

Create `.venv` using Python 3.11 and install `test/requirements.txt`. Then run `scripts/test-local.sh`. The simulator wrappers use the sibling `../tools/oss-cad-suite` installation and avoid its Python environment override. On an ordinary Icarus installation: activate the Python environment and run `make -C test`.

Run `scripts/harden-local.sh UNIQUE_RUN_TAG` for the existing server LibreLane/PDK setup. Each run uses a fresh directory and refuses to overwrite previous results. This uses sibling `../ttvenv`, `../pyextra`, `../pdk` and `../tools/librelane-devshell`. Build outputs are ignored. `src/config.json` is the authoritative hand-edited flow configuration; generated user/merged configurations are ignored. `tt/` is a bundled support-tool snapshot; provenance is in `evidence/source-provenance.json`.

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

## Local build notifications

`scripts/harden-local.sh` invokes `scripts/notify-build.py` at start and finish, including failed exits. The handler writes `evidence/build-notification.json` and appends changed states to ignored `evidence/build-events.jsonl`. Run `python3 scripts/notify-build.py` to refresh status for an existing run. Reports distinguish flow completion, tool failure and outstanding physical violations; they never assert full sign-off. The handler records local events only. It has no mail, webhook or Codex background-message integration.

## Physical closure recipe

The custom flow in `scripts/qualified-flow.py` adds two integration repairs to the vendored Classic flow. Clock-root fanout is split into four branches. Electrical repair loads the slow library explicitly, reserves fanout headroom for later antenna diodes, and runs again after timing optimization using updated global-route parasitics. Transition and hold repair margins are stricter than the final declared limits. The final limits remain 50 ns clock period, 0.75 ns maximum transition, fanout 10 and 0.2 pF design maximum capacitance, with stricter library pin limits also checked.

The exact PDK revision is recorded in `evidence/pdk-version.json`; imported IP/support revisions are in `evidence/source-provenance.json`. Full setup/hold and electrical results must pass all nine configured corners after extraction.

## Verify a completed run

```sh
./scripts/gl-local.sh RUN_TAG
./scripts/precheck-local.sh RUN_TAG
python3 scripts/collect-precheck.py RUN_TAG
.venv/bin/python scripts/qualify.py RUN_TAG
```

Precheck uses its own `.precheck-venv`, installed from `tt/precheck/requirements.txt`. Gate simulation uses `.venv`, installed from `test/requirements.txt`. Verification records bind their result to the netlist/GDS SHA-256. The qualifier also verifies the hardware/flow sources against the build's recorded Git commit and the RTL inputs against the passing regression.

The exploratory CVC/SDF helper and its failure record are retained for diagnosis; they are not part of the accepted qualification evidence. Radiation/silicon qualification and full-chip power/IR signoff are outside this baseline's scope.
