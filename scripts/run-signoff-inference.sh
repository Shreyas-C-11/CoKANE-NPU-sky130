#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
cd "$project"
tag=${1:?unique verification tag}; model=${2:-synthetic}; netlist=${3:-}
[[ "$tag" =~ ^[A-Za-z0-9_-]+$ ]] || exit 2
python3 scripts/check-frozen-prototype.py
work="$project/verification/signoff-$tag-$model"
python3 scripts/prepare-signoff-inference.py "$work" "$model"
export SIGNOFF_MODEL="$model" SIGNOFF_FIRMWARE="$work/firmware.hex" SIGNOFF_FIXTURE="$work/fixture.json"
export SIGNOFF_RESULT="$project/evidence/signoff-$tag-$model-inference.json"
export SIGNOFF_NETLIST="$netlist"
if [[ -n "$netlist" ]]; then
 test -f "$netlist"
 gates=yes
else
 gates=no
fi
revision=$(python3 -c 'import json;print(json.load(open("evidence/pdk-version.json"))["version"])')
models="$project/../pdk/ciel/sky130/versions/$revision/sky130A/libs.ref/sky130_fd_sc_hd/verilog"
unset VERILATOR_ROOT YOSYS_DATDIR PYTHONHOME PYTHONEXECUTABLE LD_LIBRARY_PATH
export PATH=/usr/local/bin:/usr/bin:/bin
cd ../tools/librelane-devshell
./AppRun bash -c 'set -eu; cd "$1"; source .venv/bin/activate; make -C test_signoff SIM=verilator SIM_BUILD="$2/sim" COCOTB_RESULTS_FILE="$2/results.xml" GATES="$3" NETLIST="$4" PDK_MODELS="$5" FIRMWARE="$SIGNOFF_FIRMWARE" WAVES=0; python -m cocotb_tools.check_results "$2/results.xml"' bash "$project" "$work" "$gates" "$netlist" "$models" > "$project/evidence/signoff-$tag-$model-inference.log" 2>&1
cp "$work/results.xml" "$project/evidence/signoff-$tag-$model-inference-results.xml"
python3 - "$project" "$tag" "$model" "$work" <<'PY'
import pathlib,sys,json,hashlib
root=pathlib.Path(sys.argv[1]);tag,model=sys.argv[2:4];work=pathlib.Path(sys.argv[4])
p=root/f'evidence/signoff-{tag}-{model}-inference.json';d=json.loads(p.read_text())
assert d['result']=='PASS'
d['model_identity']=json.loads((work/'model-identity.json').read_text())
d['harness_sha256']={str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [root/'test_signoff/host_tb.v',root/'test_signoff/Makefile',root/'test_signoff/test_host_inference.py']}
p.write_text(json.dumps(d,indent=2)+'\n');print('PIN_INFERENCE_VERIFIED',model)
PY
