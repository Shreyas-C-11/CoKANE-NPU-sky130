# CPU + MAC + programmable CoKANE

Development branch for a SKY130 5x4-tile integration at a 20 MHz target. See [NPU_Specs.md](NPU_Specs.md) for architecture, numerical bounds, memory budget, block diagram and the register ABI.

The implementation adds one 64x6-bit writable LUT bank, eight signed 12-bit partial sums, a shared lookup/adder datapath, final six-bit saturation and signed pooling. The CPU gathers windows and moves tables/feature maps through the existing host-backed memory service. There is no DMA or full-model on-chip memory.

This frozen integrated design **passed the declared digital block qualification** in `ck-signoff-r4` (5x4, 20 MHz). See SIGNOFF.md and its artifact-bound report. The inherited `cpu-mac-20mhz-3x4-v1` tag and historical evidence describe the CPU+MAC baseline only. The new qualification flow uses independent placement/routing and artifact-bound verification; historical baseline ECO scripts are unused.

Current implementation and test results are recorded under `evidence/cokane/`. The original supplied FPGA sources remain in the sibling `CKAN/` folder.

## First verified milestone

The RTL prototype passes three standalone test groups, two CPU firmware boots, an intentional saturation-bug mutation test and standalone mapped-engine functional simulation. A synthetic integer 28x28 two-convolution/pooling network and 50->10 dense head match an independent oracle. This does not establish trained-model accuracy.

Preliminary filtered SKY130 cell areas: CoKANE alone 0.047658 mm2; CPU+MAC+CoKANE 0.174172 mm2. Integrated mapping uses ABC fast mapping for a footprint estimate. Timing, placement, routing and physical qualification remain pending. See `evidence/cokane/prototype-validation.json` and section 9 of the specification for measured scope and reproducible commands.

## Compiled inference firmware

`bash scripts/test-inference.sh` builds RV32E/ILP32E C and runs a synthetic 28x28, two-convolution/pooling, 50->10 KAN network on the actual CPU/NPU RTL, alongside a CPU-only reference. Both intermediate maps, all scores and argmax match an independent integer oracle. Thirty native C cases cover descriptors, numerical ranges, aliases and runtime failure handling.

Selective six-bit LUT loading reduces entry writes from 86,432 to 27,976 without changing the hardware. The measured scheduler improves from 751.1 ms to 700.5 ms, but remains slower than the CPU-only reference at 462.9 ms (nominal 20 MHz, specified simulation RAM waits, instrumented firmware). This proves correctness, not acceleration, trained accuracy or physical timing closure. Performance and trained accuracy are deferred while the frozen functional architecture undergoes physical qualification. Specification section 10 and `evidence/cokane/inference-validation.json` record the comparison and exact scope.

## Preserved prototype and qualification

The working prototype is preserved at `cokane-working-prototype-v0.2` (`db530b7`). The separate `feature/cokane-performance` worktree retains it for later performance and trained-model work. The `signoff/cokane-v0.2` branch qualifies the same RTL and firmware in 5x4 tiles at 20 MHz. Physical cell sizing and routing may change; the frozen functional sources may not. See [SIGNOFF.md](SIGNOFF.md) for the required gates and scope. Qualification passed for the scope in `evidence/qualification-ck-signoff-r4.json`; see SIGNOFF.md for exclusions.
