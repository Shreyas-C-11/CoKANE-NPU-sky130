#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p evidence/cokane
WAVES=0 bash scripts/test-local.sh > evidence/cokane/cpu-rtl.log 2>&1
source .venv/bin/activate
python - <<'PY'
import pathlib,json,hashlib,re,subprocess,xml.etree.ElementTree as ET
r=ET.parse('test/results.xml').getroot()
assert r.findall('.//testcase') and not any(r.findall('.//'+x) for x in ['failure','error','skipped'])
p=pathlib.Path('evidence/cokane');log=(p/'cpu-rtl.log').read_text()
assert len(re.findall(r'Firmware PASS seed=',log))==2 and 'Firmware NEGATIVE_CONTROL_PASS' in log
files=[f for f in pathlib.Path('src').iterdir() if f.suffix in ['.v','.sv','.vh']]+[pathlib.Path('test/test.py')]
d={'result':'PASS','source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'positive_boots':2,'wrong_expectation_rejected':True,'scope':'Pin-only CPU+MAC+CoKANE firmware, external reset and ena reset, random host stalls','input_sha256':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}}
(p/'cpu-validation.json').write_text(json.dumps(d,indent=2)+'\n');(p/'cpu-results.xml').write_bytes(pathlib.Path('test/results.xml').read_bytes());print('CPU_INTEGRATION_PASS')
PY
