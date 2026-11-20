# Frozen CoKANE qualification

The preserved working prototype is commit `db530b7fe46207c3720513d0c4b0d0d69ce45dee`, tagged `cokane-working-prototype-v0.2`. Its RTL, firmware and synthetic fixture generator are protected by `evidence/frozen-prototype.json` and `scripts/check-frozen-prototype.py`.

`signoff/cokane-v0.2` qualifies that architecture. `feature/cokane-performance`, checked out separately in `../cokane-performance` on the server and `../CoKANE-performance` locally, retains the same prototype for later work. Performance changes and trained-model accuracy are deferred. Physical cell sizing, buffering, routing and verification changes belong on the qualification branch.

## Qualification sequence

1. Preserve the tag, independent Git bundle, full prototype archive and SHA-256 manifests.
2. Check the frozen arithmetic, protocol, reset, abort, error and scheduler regressions. Retain the saturation mutation test and compiled CPU tensor comparisons.
3. Place and route the combined CPU, MAC and CoKANE in the supported SKY130 **5x4** footprint, at **20 MHz / 50 ns**, without relaxing declared electrical limits.
4. Close extracted setup and hold timing, transition, capacitance and fanout at all nine declared RC/PVT corners. Require zero route, Magic and KLayout DRC, LVS and antenna violations.
5. Run the actual final gate netlist against the pin-level host: basic CPU/reset tests, full frozen synthetic inference, and a deliberately degenerate all-zero model. Compare both intermediate tensors, every score and argmax to the independent oracle.
6. Pass all 15 Tiny Tapeout prechecks on the same GDS, LEF and netlist. Bind every result to artifact hashes with `scripts/qualify.py RUN_TAG`.
7. Package the passing digital block, reports, source history, pinned environment identifiers and a portable physical checkpoint. Verify every packaged file and preserve a release tag.

The frozen block **passed the declared digital qualification** in `ck-signoff-r4`. Flow completion alone does not mean qualification. The authoritative result will be `evidence/qualification-RUN_TAG.json`, including its exact exclusions and artifact hashes.

## Accuracy and execution

A valid model with poor classification accuracy still performs its integer operations and returns scores. All-zero tables are a useful execution test: they should complete with zero features/scores and first-index tie-breaking. This cannot establish useful recognition accuracy. The software checks supported dimensions, buffer sizes and quantized ranges; errors and timeouts during owned work trigger cleanup. A stalled external bus has no hardware acknowledgment timeout, so continued host memory service remains an integration requirement.

This qualification covers the declared digital block. Trained-model accuracy, speedup, SDF timing simulation (by prior agreement), silicon/radiation qualification and full-chip power/IR/EM or foundry release are outside this milestone.

## Qualified milestone: ck-signoff-r4

The 5x4 / 20 MHz candidate passed nine-corner extracted STA with worst setup slack +0.419117 ns and worst hold slack +0.129389 ns. Transition, fanout, capacitance, route/Magic/KLayout DRC, LVS and routed antenna counts are zero. All 15 prechecks passed. Basic four-state gate firmware passed both resets and its negative control. Full compiled gate inference matched all 338 + 50 intermediate values and ten scores for both the frozen synthetic fixture and all-zero tables.

`evidence/qualification-ck-signoff-r4.json` binds the exact artifacts and reports. The local release tag is `cokane-20mhz-5x4-v0.2`. Physical changes were cell sizing/buffering/routing; frozen RTL and firmware hashes still match the prototype. Performance improvement and trained accuracy remain deferred.
