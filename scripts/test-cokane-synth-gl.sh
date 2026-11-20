#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate
mkdir -p verification/cokane-synth-gl evidence/cokane
revision=$(python -c 'import json; print(json.load(open("evidence/pdk-version.json"))["version"])')
models="$PWD/../pdk/ciel/sky130/versions/$revision/sky130A/libs.ref/sky130_fd_sc_hd/verilog"
make -C test_cokane ICARUS_BIN_DIR="$PWD/scripts" SIM_BUILD="$PWD/verification/cokane-synth-gl/sim_build" COCOTB_RESULTS_FILE="$PWD/verification/cokane-synth-gl/results.xml" COCOTB_TEST_FILTER=arithmetic_and_protocol COMPILE_ARGS="-g2012 -DFUNCTIONAL" VERILOG_SOURCES="$models/primitives.v $models/sky130_fd_sc_hd.v $PWD/verification/cokane-synth/engine.v $PWD/test_cokane/tb.v" > evidence/cokane/engine-synth-gl.log 2>&1
python - <<'PY'
import pathlib,json,hashlib,xml.etree.ElementTree as ET
p=pathlib.Path('verification/cokane-synth-gl/results.xml');r=ET.parse(p).getroot()
assert len(r.findall('.//testcase'))==1 and not any(r.findall('.//'+x) for x in ['failure','error','skipped'])
assert 'COKANE_PROTOCOL_PASS' in pathlib.Path('evidence/cokane/engine-synth-gl.log').read_text()
sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
d={'result':'PASS','scope':'Standalone mapped engine arithmetic/protocol functional simulation; no SDF or timing qualification','netlist_sha256':sha('verification/cokane-synth/engine.v'),'test_sha256':sha('test_cokane/test_cokane.py'),'cases':1}
pathlib.Path('evidence/cokane/engine-synth-gl-validation.json').write_text(json.dumps(d,indent=2)+'\n')
pathlib.Path('evidence/cokane/engine-synth-gl-results.xml').write_bytes(p.read_bytes());print('MAPPED_ENGINE_FUNCTIONAL_PASS')
PY
