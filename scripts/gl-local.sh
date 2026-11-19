#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
tag=${1:?usage: gl-local.sh RUN_TAG}
[[ "$tag" =~ ^[A-Za-z0-9_-]+$ ]] || exit 2
export PDK_ROOT=$(python3 -c 'import json,sys; print(json.load(open("runs/"+sys.argv[1]+"/resolved.json"))["PDK_ROOT"])' "$tag")
netlist=${2:-"$PWD/runs/$tag/final/pnl/tt_um_cokane_soc.pnl.v"}
cp "$netlist" test/gate_level_netlist.v
rm -f "evidence/gl-$tag-exit-code.txt"
result=0
./scripts/test-local.sh GATES=yes > "evidence/gl-$tag.log" 2>&1 || result=$?
printf '%s\n' "$result" > "evidence/gl-$tag-exit-code.txt"
if [ -f test/results.xml ]; then cp test/results.xml "evidence/gl-$tag-results.xml"; fi
.venv/bin/python scripts/collect-gl.py "$tag" "$netlist"
exit "$result"
