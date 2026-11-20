#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p evidence/cokane
source .venv/bin/activate
python - <<'PY'
import hashlib,json,pathlib,subprocess
files=['src/cokane_wb.v','test_cokane/tb.v','test_cokane/test_cokane.py','test_cokane/Makefile']
pathlib.Path('evidence/cokane/unit-inputs.json').write_text(json.dumps({'commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'sha256':{p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest() for p in files}},indent=2)+'\n')
PY
make -C test_cokane ICARUS_BIN_DIR="$PWD/scripts" > evidence/cokane/unit.log 2>&1
python -m cocotb_tools.check_results test_cokane/results.xml
cp test_cokane/results.xml evidence/cokane/unit-results.xml
python - <<'PY'
import json,pathlib,xml.etree.ElementTree as ET
p=pathlib.Path('evidence/cokane');r=ET.parse(p/'unit-results.xml').getroot()
cases=r.findall('.//testcase');assert len(cases)==3
assert not any(r.findall('.//'+x) for x in ['failure','error','skipped'])
text=(p/'unit.log').read_text()
for marker in ['COKANE_PROTOCOL_PASS','COKANE_TENSOR_PASS image=28x28 layers=2 features=50 dense_classes=10','COKANE_BOUNDARIES_PASS']:assert marker in text,marker
record={'result':'PASS','cases':len(cases),'input_manifest':'unit-inputs.json','scope':['Wishbone arithmetic/protocol','synthetic integer 28x28 two-convolution/pooling layers + 50->10 KAN','reset, abort and bus boundary checks'],'trained_model_accuracy_verified':False}
(p/'unit-validation.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
PY
