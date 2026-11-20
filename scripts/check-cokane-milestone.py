#!/usr/bin/env python3
"""Validate the RTL prototype evidence. Does not confer physical qualification."""
import hashlib,json,pathlib,subprocess
from datetime import datetime,timezone
root=pathlib.Path(__file__).resolve().parent.parent
p=root/'evidence/cokane'
load=lambda f:json.loads(f.read_text())
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
u=load(p/'unit-validation.json');cpu=load(p/'cpu-validation.json')
s=load(p/'synthesis-validation.json');g=load(p/'engine-synth-gl-validation.json')
n=load(p/'negative-control.json');h=load(p/'firmware-header-validation.json')
for record in [u,cpu,s,g,n,h]:assert record['result']=='PASS'
for name,digest in load(p/'unit-inputs.json')['sha256'].items():assert sha(root/name)==digest,name
for name,digest in cpu['input_sha256'].items():assert sha(root/name)==digest,name
for name,digest in s['inputs_sha256'].items():assert sha(root/name)==digest,name
assert g['netlist_sha256']==sha(root/'verification/cokane-synth/engine.v')
assert g['test_sha256']==sha(root/'test_cokane/test_cokane.py')
assert n['original_source_sha256']==sha(root/'src/cokane_wb.v')
assert n['test_sha256']==sha(root/'test_cokane/test_cokane.py')
assert h['sha256']==sha(root/'firmware/cokane.h')
assert s['library_sha256']==sha(pathlib.Path(s['library']))
assert s['mapping_library_sha256']==sha(pathlib.Path(s['mapping_library']))
for name,digest in s['excluded_cell_files_sha256'].items():assert sha(pathlib.Path(name))==digest
assert u['cases']==3 and cpu['positive_boots']==2 and cpu['wrong_expectation_rejected']
reports=['unit-validation.json','unit-inputs.json','unit-results.xml','cpu-validation.json','cpu-results.xml','negative-control.json','engine-synth-gl-validation.json','engine-synth-gl-results.xml','synthesis-validation.json','engine-stat.json','integrated-stat.json','firmware-header-validation.json']
summary={name:{k:r['design'][k] for k in ['num_cells','area','sequential_area']} for name,r in s['statistics'].items()}
d={'result':'PASS','milestone':'RTL prototype and synthesis feasibility','created_at_utc':datetime.now(timezone.utc).isoformat(),'rtl_source_commit':load(p/'unit-inputs.json')['commit'],'physically_qualified':False,'trained_model_accuracy_verified':False,'statistics':summary,'report_sha256':{name:sha(p/name) for name in reports},'pending':['Data movement/performance improvements: measured scheduler remains slower than CPU-only reference','Trained-model exporter and accuracy validation','Fresh 5x4 physical implementation','Integrated post-route functional gate simulation','Nine-corner STA and electrical limits at 50 ns','DRC/LVS/antenna and Tiny Tapeout prechecks']}
if (p/'inference-validation.json').exists():
 inference=load(p/'inference-validation.json');assert inference['result']=='PASS'
 d['compiled_cpu_inference_record_sha256']=sha(p/'inference-validation.json')
(p/'prototype-validation.json').write_text(json.dumps(d,indent=2)+'\n')
notification={'status':'cpu_inference_checks_passed' if (p/'inference-validation.json').exists() else 'prototype_checks_passed','fully_verified':False,'qualified_for_declared_scope':False,'scope':'CPU + MAC + programmable CoKANE RTL prototype','pending_verification':d['pending'],'prototype_record':'evidence/cokane/prototype-validation.json'}
(root/'evidence/build-notification.json').write_text(json.dumps(notification,indent=2)+'\n')
print('COKANE_RTL_PROTOTYPE_PASS')
print(json.dumps(summary,indent=2))
