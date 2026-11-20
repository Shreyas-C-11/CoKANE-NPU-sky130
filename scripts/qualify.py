#!/usr/bin/env python3
"""Qualify the frozen CPU + MAC + CoKANE block against bound evidence."""
from datetime import datetime, timezone
import hashlib, json, pathlib, subprocess, sys, xml.etree.ElementTree as ET
root = pathlib.Path(__file__).resolve().parents[1]
tag = sys.argv[1]; run = root/'runs'/tag
load = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
problems, checks, evidence = [], {}, {}
def require(ok, message):
    if not ok: problems.append(message)
def bind(p): evidence[str(p.relative_to(root))] = sha(p)
def passing_json(p):
    d = load(p); bind(p); require(d.get('result') == 'PASS', str(p)+' did not pass'); return d
def passing_xml(p, count=None):
    r = ET.parse(p).getroot(); bind(p); cases = r.findall('.//testcase')
    require(bool(cases) and (count is None or len(cases) == count) and not any(
        r.findall('.//'+x) for x in ['error','failure','skipped']), str(p)+' incomplete or failing')
subprocess.run([sys.executable,str(root/'scripts/check-frozen-prototype.py')],check=True)
frozen = load(root/'evidence/frozen-prototype.json')
policy = load(root/'evidence/validation-policy.json')
require(not policy['sdf_required'], 'SDF evidence required but unavailable')
# Original tests/evidence are retained exactly at the immutable prototype tag.
for p in sorted((root/'evidence/cokane').iterdir()):
    if p.suffix not in ['.json','.xml']: continue
    old = subprocess.check_output(['git','show',frozen['tag']+':'+p.relative_to(root).as_posix()],cwd=root)
    require(hashlib.sha256(old).hexdigest() == sha(p), 'Frozen regression evidence changed: '+p.name)
    bind(p)
for name in ['unit','cpu','engine-synth-gl','inference']:
    passing_json(root/f'evidence/cokane/{name}-validation.json')
    passing_xml(root/f'evidence/cokane/{name}-results.xml')
passing_json(root/'evidence/cokane/scheduler-host-validation.json')
for manifest,key in [('unit-inputs.json','sha256'),('cpu-validation.json','input_sha256'),
                     ('inference-validation.json','rtl_and_harness_sha256')]:
    for name,digest in load(root/'evidence/cokane'/manifest)[key].items():
        require(sha(root/name) == digest, 'Regression input changed: '+name)
metrics = load(run/'final/metrics.json'); config = load(run/'resolved.json')
required = ['design__lint_error__count','design__inferred_latch__count','synthesis__check_error__count',
            'route__drc_errors','magic__drc_error__count','klayout__drc_error__count','design__lvs_error__count',
            'route__antenna_violation__count','design__max_slew_violation__count',
            'design__max_fanout_violation__count','design__max_cap_violation__count']
for k in required:
    checks[k] = metrics.get(k); require(checks[k] == 0, f'{k}={checks[k]}')
expected = {f'{rc}_{pvt}' for rc in ['min','nom','max'] for pvt in ['tt_025C_1v80','ss_100C_1v60','ff_n40C_1v95']}
require(set(config['STA_CORNERS']) == expected, 'Nine expected STA corners required')
for corner in sorted(expected):
    for kind in ['setup','hold']:
        k = f'timing__{kind}__wns__corner:{corner}'; checks[k] = metrics.get(k)
        require(checks[k] is not None and float(checks[k]) >= 0, f'{k}={checks[k]}')
    for kind in ['slew','fanout','cap']:
        k = f'design__max_{kind}_violation__count__corner:{corner}'; checks[k] = metrics.get(k)
        require(checks[k] == 0, f'{k}={checks[k]}')
require(config['CLOCK_PERIOD'] == 50, 'Clock period must remain 50 ns')
netlist = run/'final/pnl/tt_um_cokane_soc.pnl.v'
gl = passing_json(root/f'evidence/gl-{tag}-validation.json')
passing_xml(root/f'evidence/gl-{tag}-results.xml')
require(gl['netlist_sha256'] == sha(netlist), 'Basic gate netlist mismatch')
inference = {}
for model in ['synthetic','zero']:
    prefix = root/f'evidence/signoff-{tag}-{model}-inference'
    d = passing_json(prefix.with_suffix('.json')); passing_xml(pathlib.Path(str(prefix)+'-results.xml'))
    require(d.get('netlist_sha256') == sha(netlist), model+' inference netlist mismatch')
    require(d['tensor_counts'] == [338,50,10], model+' incomplete tensors')
    identity = d['model_identity']
    require(identity['frozen_commit'] == frozen['frozen_commit'], 'Firmware freeze mismatch')
    require(not identity['executable_instructions_modified'], 'Executable code changed')
    require(d['firmware_sha256'] == identity['firmware_sha256'] and d['fixture_sha256'] == identity['fixture_sha256'], 'Model input mismatch')
    for name,digest in d['harness_sha256'].items():
        require(sha(root/name) == digest, 'Inference harness changed: '+name)
    inference[model] = d
pre = passing_json(root/f'evidence/precheck-{tag}.json')
passing_xml(root/f'evidence/precheck-{tag}-results.xml',15)
for name,final in [('tt_um_cokane_soc.gds','gds/tt_um_cokane_soc.gds'),
                   ('tt_um_cokane_soc.lef','lef/tt_um_cokane_soc.lef'),
                   ('tt_um_cokane_soc.v','pnl/tt_um_cokane_soc.pnl.v')]:
    require(pre['sha256'].get(name) == sha(run/'final'/final), 'Precheck mismatch: '+name)
source = load(run/'final/commit_id.json')
physical = [p.relative_to(root).as_posix() for p in (root/'src').iterdir() if p.suffix in ['.v','.sv','.vh']]
physical += ['src/config.json','info.yaml','scripts/qualified-flow.py','scripts/signoff-clock-fanout.tcl',
             'scripts/repair-slowcorner.tcl','scripts/final-electrical.tcl','scripts/signoff-postroute.tcl']
for name in physical:
    old = subprocess.check_output(['git','show',source['commit']+':'+name],cwd=root)
    require(hashlib.sha256(old).hexdigest() == sha(root/name), 'Physical build source changed: '+name)
for p in [netlist,run/'final/gds/tt_um_cokane_soc.gds',run/'final/lef/tt_um_cokane_soc.lef',
          run/'final/metrics.json',run/'resolved.json',run/'final/commit_id.json',
          root/'evidence/frozen-prototype.json',root/'evidence/validation-policy.json']:
    bind(p)
result = {'run':tag,'result':'PASS' if not problems else 'FAIL','created_at_utc':datetime.now(timezone.utc).isoformat(),
          'scope':policy,'frozen_commit':frozen['frozen_commit'],'source':source,'checks':checks,
          'functional_gate_result':gl,'full_firmware_gate_results':inference,'precheck_result':pre,
          'artifacts_sha256':evidence,'problems':problems}
(root/f'evidence/qualification-{tag}.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'result':result['result'],'problems':problems,'bound_artifacts':len(evidence)},indent=2))
raise SystemExit(bool(problems))
