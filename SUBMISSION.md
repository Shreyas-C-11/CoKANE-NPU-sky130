# SKY130 submission preparation

GitHub owner: **Shreyas-C-11**. Target workflow family: **SKY26d / sky130A**.
The official current tile-size table includes **5x4**, with the same physical
boundary as the qualified GDS. Actual shuttle capacity, order status, price and
acceptance must be checked in the submission portal; a supported template does
not reserve 20 tiles.

## Preserved hardware

- Functional prototype: `cokane-working-prototype-v0.2` / `db530b7`.
- Qualified routed release: `cokane-20mhz-5x4-v0.2` / `0fa8227`.
- Submission changes are confined to packaging, documentation, workflows and
  external host software. `scripts/check-frozen-prototype.py` must still pass.
- Physical build source commit is recorded separately in the qualification
  record; it predates the final verification/documentation commit by design.

| Artifact | SHA-256 of the qualified uncompressed file |
|---|---|
| GDS | `d165be9884d91be828dd27547ccb93793f2321a548b22bcfca44ab19d8b8d769` |
| LEF | `39ca7de3fa7dd34244f89f14b89071960c66ba4f8d4b21ee75dbacf109d4a70f` |
| Powered netlist | `10efb99a1ce91ff7275b61e7382946c9d37c505203e5d66527ca3cbd95ce4665` |

`layout/manifest.json` also binds the compressed GDS file stored in Git. To
verify or materialize the three files locally:

```sh
python scripts/verify-submission.py --materialize-dir .submission-build
```

## GitHub checks required on the exact submission commit

1. `gds / gds`: official custom-GDS import, with hash checks and pinned PDK
   metadata. The artifact must contain one powered `.v` netlist, GDS, OASIS,
   LEF, `commit_id.json`, `pdk.json`, layout manifest and qualification record.
2. `gds / precheck`: official checks on the imported artifact using the current
   shuttle action's rule/PDK environment. These run again even though local
   prechecks already passed in the qualification environment.
3. `gds / gl_test`: CPU/MAC/CoKANE firmware on the imported gate netlist, with
   reset and negative-control checks and the qualified PDK revision's models.
4. `docs / docs`: current project datasheet and pinout render successfully.
5. `test / test`: existing RTL firmware regression passes.
6. `external-memory-host / host`: memory bounds/failure tests and the exact
   board host protocol sequencer pass against the actual RTL.

The viewer deploys GitHub Pages. Enable Pages with **GitHub Actions** as its
source if required by the account/repository. No credentials or tokens belong
in this repository or on the shared CAD server.

## Board bring-up status

`host/tt_host.py` targets the official SDK v3 and supplies slow clock edges
while serving paged external RAM. Use `host/smoke.hex` first. Full inference
uses the frozen firmware/data image `host/inference.hex` and checks the small
oracle file `host/expected.json`. The optional CPU-only benchmark is not needed
for this board bring-up.

Actual board execution, free MCU RAM and logic-analyzer timing still need
measurement with a fabricated chip or compatible FPGA carrier. There is no
claim of 20 MHz RP2 host operation. See `host/README.md` for exact setup and
limitations. This does not change the existing ASIC core timing qualification.

## Portal handoff

After all required jobs pass, create/select the GitHub-backed project in
<https://app.tinytapeout.com/projects/create>, choose the matching SKY130
shuttle and confirm its 5x4 allocation. Submit **the exact tested commit** as a
new revision. Record the revision identifier, Git SHA, shuttle, 20-tile size,
artifact hashes and portal acceptance result. Uploading a repository alone
does not submit a revision for fabrication.

The account owner must review any fabrication price/order, payment or new
legally binding terms before committing to them. No fabrication order is
implied by this local preparation document.

References:

- [Official custom-GDS action](https://github.com/TinyTapeout/tt-gds-action/blob/ttsky26d/custom_gds/action.yml)
- [Current SKY130 tile sizes](https://github.com/TinyTapeout/tt-support-tools/blob/main/tech/sky130A/tile_sizes.yaml)
- [Submission guide](https://www.tinytapeout.com/guides/advanced-workshop/submit-your-design/)
