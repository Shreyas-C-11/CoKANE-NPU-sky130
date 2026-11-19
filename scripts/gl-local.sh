#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PDK_ROOT=$(python3 -c 'import json; print(json.load(open("runs/wokwi/resolved.json"))["PDK_ROOT"])')
cp runs/wokwi/final/pnl/tt_um_cokane_soc.pnl.v test/gate_level_netlist.v
rm -f evidence/gl-exit-code.txt
result=0
./scripts/test-local.sh GATES=yes > evidence/gl-test.log 2>&1 || result=$?
printf '%s\n' "$result" > evidence/gl-exit-code.txt
if [ -f test/results.xml ]; then cp test/results.xml evidence/gl-results.xml; fi
exit "$result"
