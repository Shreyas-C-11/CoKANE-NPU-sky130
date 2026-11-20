#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate
mkdir -p verification/cokane-mutant evidence/cokane
python - <<'PY'
from pathlib import Path
import hashlib,json
r=Path('verification/cokane-mutant');p=Path('src/cokane_wb.v');s=p.read_text()
needle='psum[lane[2:0]]<=updated_sum;';assert s.count(needle)==1
s=s.replace(needle,"if (updated_sum > 12'sd31) psum[lane[2:0]]<=12'sd31; else if (updated_sum < -12'sd32) psum[lane[2:0]]<=-12'sd32; else psum[lane[2:0]]<=updated_sum;")
(r/'mutant.v').write_text(s)
(r/'inputs.json').write_text(json.dumps({'original_source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'mutant_sha256':hashlib.sha256(s.encode()).hexdigest(),'test_sha256':hashlib.sha256(Path('test_cokane/test_cokane.py').read_bytes()).hexdigest(),'mutation':'Incorrect six-bit saturation after every contribution'},indent=2)+'\n')
PY
if make -C test_cokane ICARUS_BIN_DIR="$PWD/scripts" SIM_BUILD="$PWD/verification/cokane-mutant/sim_build" COCOTB_RESULTS_FILE="$PWD/verification/cokane-mutant/results.xml" COCOTB_TEST_FILTER=arithmetic_and_protocol VERILOG_SOURCES="$PWD/verification/cokane-mutant/mutant.v $PWD/test_cokane/tb.v" > evidence/cokane/negative-control.log 2>&1; then
 echo 'ERROR: broken saturation mutant passed'; exit 1
fi
python - <<'PY'
import pathlib,json,xml.etree.ElementTree as ET
p=pathlib.Path('verification/cokane-mutant');r=ET.parse(p/'results.xml').getroot()
f=r.findall('.//failure');assert len(r.findall('.//testcase'))==1 and len(f)==1
assert '[31' in f[0].get('message','') and '([62] * 8)' in f[0].get('message','')
d=json.load(open(p/'inputs.json'));d.update(result='PASS',meaning='Early-saturation mutant rejected by unchanged regression',observed_test_failures=1)
pathlib.Path('evidence/cokane/negative-control.json').write_text(json.dumps(d,indent=2)+'\n');print('NEGATIVE_CONTROL_PASS')
PY
