# CPU + mac-sentry + CoKANE

This programmable inference chip combines a PicoRV32 CPU, a six-bit CoKANE lookup-and-add engine, and [mac-sentry](NPU_Specs.md#independent-protected-mac), a separate signed 8×8 multiply–accumulate peripheral. MAC Sentry protects its accumulator with SECDED and checks arithmetic results with a modulo-7 predictor and bounded retry. The frozen integrated design passed its declared SKY130 digital block qualification at **20 MHz in 5×4 Tiny Tapeout tiles**. Final macro area: **0.4379900672 mm²**.

The CPU schedules layers and transfers model tables and feature maps through external host-backed memory. CoKANE reuses one 64×6-bit LUT, a shared adder and eight 12-bit partial sums, with a single final saturation point. Synthetic and zero-model inference are verified; trained accuracy and physical board operation remain unmeasured.


## Documentation

- **[Complete chip specification](NPU_Specs.md)** — CPU, mac-sentry, CoKANE, block diagram, registers, memory, pins, timing, qualification and submission procedure.
- [Tiny Tapeout datasheet](docs/info.md) — project pinout, boot and testing summary.
- [External-memory host guide](host/README.md) — board setup and stepped-clock bring-up.
- [Qualification evidence](evidence/qualification-ck-signoff-r4.json) and [qualified layout manifest](layout/manifest.json).

## Repository

`src/` contains RTL; `firmware/` contains CPU software; `host/` contains the external memory service. Tests and `scripts/` reproduce validation. `layout/` contains the qualified physical files; `evidence/` binds results to their inputs. `licenses/` and the upstream `tt/` submodule retain third-party notices and support tools.

```sh
python3 scripts/verify-submission.py
```

This checks frozen functional sources, host images and qualified physical hashes. See the specification for CAD environment requirements and additional test commands. CI imports the exact qualified GDS using Tiny Tapeout's custom-GDS workflow.

Prototype: `cokane-working-prototype-v0.2` (`db530b7`). Qualified release: `cokane-20mhz-5x4-v0.2` (`0fa8227`). Performance work is preserved separately.
