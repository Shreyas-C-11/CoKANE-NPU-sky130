"""Bind CPU inference observations, firmware and RTL to the same verified build."""
import hashlib,json,pathlib,xml.etree.ElementTree as ET
root=pathlib.Path(__file__).resolve().parents[1];p=root/'evidence/cokane'
load=lambda f:json.loads(f.read_text())
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
build=load(p/'inference-build.json');result=load(p/'inference-validation.json');host=load(p/'scheduler-host-validation.json')
assert all(d['result']=='PASS' for d in [build,result,host])
for name,digest in build['inputs_sha256'].items():assert sha(root/name)==digest,name
for name,digest in build['artifacts_sha256'].items():assert sha(root/'verification/inference'/name)==digest,name
r=ET.parse(p/'inference-results.xml').getroot()
assert len(r.findall('.//testcase'))==1 and not any(r.findall('.//'+x) for x in ['failure','error','skipped'])
assert 'COMPILED_CPU_INFERENCE_PASS' in (p/'inference-rtl.log').read_text()
files=[f for f in (root/'src').iterdir() if f.suffix in ['.v','.sv','.vh']]
files += [root/'test_inference'/f for f in ['tb.v','Makefile','test_inference.py','host_backend.c']]
files += [root/'scripts'/f for f in ['test_scheduler_host.py','test-inference.sh','collect-inference.py']]
result['rtl_and_harness_sha256']={str(f.relative_to(root)):sha(f) for f in files}
result['firmware_build_record_sha256']=sha(p/'inference-build.json')
result['host_scheduler_record_sha256']=sha(p/'scheduler-host-validation.json')
result['physical_qualification']=False
(p/'inference-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print('INFERENCE_MILESTONE_PASS')
print(json.dumps({k:result[k] for k in ['scores','prediction','cpu_cycles','simulation_inference_ms','accelerator_busy_ms','statistics']},indent=2))
