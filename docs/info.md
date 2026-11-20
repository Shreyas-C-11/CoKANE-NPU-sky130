# CPU + MAC + programmable CoKANE

Development branch for a SKY130 5x4-tile integration at a 20 MHz target. See [NPU_Specs.md](NPU_Specs.md) for architecture, numerical bounds, memory budget, block diagram and the register ABI.

The implementation adds one 64x6-bit writable LUT bank, eight signed 12-bit partial sums, a shared lookup/adder datapath, final six-bit saturation and signed pooling. The CPU gathers windows and moves tables/feature maps through the existing host-backed memory service. There is no DMA or full-model on-chip memory.

This integrated design is **not physically qualified**. The inherited `cpu-mac-20mhz-3x4-v1` tag and historical evidence describe the CPU+MAC baseline only. Instance-specific baseline post-route ECO scripts must not be used to qualify the changed netlist.

Current implementation and test results are recorded under `evidence/cokane/`. The original supplied FPGA sources remain in the sibling `CKAN/` folder.

## First verified milestone

The RTL prototype passes three standalone test groups, two CPU firmware boots, an intentional saturation-bug mutation test and standalone mapped-engine functional simulation. A synthetic integer 28x28 two-convolution/pooling network and 50->10 dense head match an independent oracle. This does not establish trained-model accuracy.

Preliminary filtered SKY130 cell areas: CoKANE alone 0.047658 mm2; CPU+MAC+CoKANE 0.174172 mm2. Integrated mapping uses ABC fast mapping for a footprint estimate. Timing, placement, routing and physical qualification remain pending. See `evidence/cokane/prototype-validation.json` and section 9 of the specification for measured scope and reproducible commands.
