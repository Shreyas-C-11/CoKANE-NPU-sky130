#!/usr/bin/env python3
"""Require artifact-bound functional and physical evidence for the declared scope."""
from datetime import datetime,timezone
import hashlib,json,pathlib,sys,subprocess,xml.etree.ElementTree as ET
root=pathlib.Path(__file__).resolve().parent.parent;tag=sys.argv[1];run=root/'runs'/tag
load=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
metrics=load(run/'final/metrics.json');config=load(run/'resolved.json');policy=load(root/'evidence/validation-policy.json')
gl=load(root/f'evidence/gl-{tag}-validation.json');pre=load(root/f'evidence/precheck-{tag}.json')
required=['design__lint_error__count','design__inferred_latch__count','synthesis__check_error__count','route__drc_errors','magic__drc_error__count','klayout__drc_error__count','design__lvs_error__count','route__antenna_violation__count','design__max_slew_violation__count','design__max_fanout_violation__count','design__max_cap_violation__count']
checks={k:metrics.get(k) for k in required};problems=[]
rtl=load(root/'evidence/rtl-current-validation.json')
r=ET.parse(root/'evidence/rtl-current-results.xml').getroot()
if rtl.get('result')!='PASS' or not r.findall('.//testcase') or any(r.findall('.//'+x) for x in ['error','failure','skipped']) or (root/'evidence/rtl-current-exit-code.txt').read_text().strip()!='0':problems.append('RTL regression evidence does not pass')
for k,v in checks.items():
 if v is None or v!=0:problems.append(f'{k}={v}')
assert len(config['STA_CORNERS'])==9,'Expected nine STA corners'
for corner in config['STA_CORNERS']:
 for category in ['setup','hold']:
  k=f'timing__{category}__wns__corner:{corner}';v=metrics.get(k);checks[k]=v
  if v is None or float(v)<0:problems.append(f'{k}={v}')
 for category in ['slew','fanout','cap']:
  k=f'design__max_{category}_violation__count__corner:{corner}';v=metrics.get(k);checks[k]=v
  if v is None or float(v)>0:problems.append(f'{k}={v}')
if config['CLOCK_PERIOD']!=50:problems.append('Clock period is not 50 ns')
if gl['result']!='PASS' or gl['netlist_sha256']!=sha(run/'final/pnl/tt_um_cokane_soc.pnl.v'):problems.append('Gate result absent or netlist mismatch')
if pre['result']!='PASS' or pre['sha256']['tt_um_cokane_soc.gds']!=sha(run/'final/gds/tt_um_cokane_soc.gds'):problems.append('Precheck absent or GDS mismatch')
for pre_name,final_name in [('tt_um_cokane_soc.lef','lef/tt_um_cokane_soc.lef'),('tt_um_cokane_soc.v','pnl/tt_um_cokane_soc.pnl.v')]:
 if pre['sha256'].get(pre_name)!=sha(run/'final'/final_name):problems.append('Precheck artifact mismatch: '+pre_name)
initial=load(root/'evidence/rtl-current-input-sha256.json');rtl_files={}
for name,digest in initial.items():
 if pathlib.Path(name).suffix in ['.v','.sv','.vh'] or name=='test/test.py':
  current=sha(root/name);rtl_files[name]=current
  if current!=digest:problems.append('RTL regression input changed: '+name)
if policy['sdf_required']:problems.append('SDF qualification not implemented by this collector')
source=load(run/'final/commit_id.json')
physical_sources=[str(p.relative_to(root)) for p in (root/'src').glob('*') if p.suffix in ['.v','.sv','.vh']]+['src/config.json','info.yaml','scripts/qualified-flow.py','scripts/clock-fanout.tcl','scripts/repair-slowcorner.tcl','scripts/final-electrical.tcl','scripts/post-fanout.tcl','scripts/post-transition.tcl']
for name in physical_sources:
 recorded=subprocess.check_output(['git','show',source['commit']+':'+name],cwd=root)
 if hashlib.sha256(recorded).hexdigest()!=sha(root/name):problems.append('Physical build source changed: '+name)
files=[run/'final/gds/tt_um_cokane_soc.gds',run/'final/pnl/tt_um_cokane_soc.pnl.v',run/'final/lef/tt_um_cokane_soc.lef',run/'final/metrics.json',run/'resolved.json',run/'final/commit_id.json']
result={'run':tag,'result':'PASS' if not problems else 'FAIL','created_at_utc':datetime.now(timezone.utc).isoformat(),'scope':policy,'source':load(run/'final/commit_id.json'),'checks':checks,'rtl_result':rtl,'functional_gate_result':gl,'precheck_result':pre,'rtl_inputs_match_passing_regression':not any('RTL regression input' in p for p in problems),'rtl_sha256':rtl_files,'artifacts_sha256':{str(p.relative_to(root)):sha(p) for p in files},'problems':problems}
(root/f'evidence/qualification-{tag}.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));raise SystemExit(0 if not problems else 1)
