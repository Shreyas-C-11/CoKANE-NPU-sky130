# Baseline execution record

Prepared 19 November 2026. Original 3x2 run stopped; original run and sources preserved.

- Configuration: 3x4, 50 ns, 55% placement target density.
- Pin-only firmware RTL: PASS, two boots, seeds 19 and 20, 7,959 memory transactions per boot.
- Cases: signed MAC, wrapping overflow, reset/deselection restart, low-byte write qualification, reserved-address responses, external-memory word/byte operations, randomized host stalls.
- RTL logs: local `rtl-test.log`; portable JUnit record: `rtl-results.xml`.
- Physical flow: running at source commit ec2406afc6e2d72002086148cd85816489f60def. Initial placement utilization 32.2645%; clock-tree synthesis reached. Final results pending.
- Gate-level / SDF / precheck: pending.
- No GitHub remote, authentication changes or uploads.

## Physical result and notification handler

The 3x4 flow completed. Final routing DRC, Magic DRC, LVS and antenna counts are zero. Setup/hold WNS is zero (no negative slack) across nine reported corners. Slew, fanout and capacitance violations remain; KLayout DRC was skipped. This is completed_with_findings, not full sign-off. See build-notification.json for exact counts. Gate-level simulation, SDF verification and shuttle precheck remain pending.

A local start/finish handler records status and changed events; it does not send external notifications.
