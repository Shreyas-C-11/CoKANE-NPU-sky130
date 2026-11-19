# Baseline execution record

Prepared 19 November 2026. Original 3x2 run stopped; original run and sources preserved.

- Configuration: 3x4, 50 ns, 55% placement target density.
- Pin-only firmware RTL: PASS, two boots, seeds 19 and 20, 7,959 memory transactions per boot.
- Cases: signed MAC, wrapping overflow, reset/deselection restart, low-byte write qualification, reserved-address responses, external-memory word/byte operations, randomized host stalls.
- RTL logs: local `rtl-test.log`; portable JUnit record: `rtl-results.xml`.
- Physical flow: running at source commit ec2406afc6e2d72002086148cd85816489f60def. Initial placement utilization 32.2645%; clock-tree synthesis reached. Final results pending.
- Gate-level / SDF / precheck: pending.
- No GitHub remote, authentication changes or uploads.
