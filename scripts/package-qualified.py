#!/usr/bin/env python3
"""Archive a qualified run, its Git history and a portable replay checkpoint."""
import hashlib,json,pathlib,shutil,subprocess,sys,tarfile
root=pathlib.Path(__file__).resolve().parent.parent;run_name=sys.argv[1];release=sys.argv[2]
q=json.loads((root/f'evidence/qualification-{run_name}.json').read_text());assert q['result']=='PASS'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as stream:
  for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
for name,digest in q['artifacts_sha256'].items():assert sha(root/name)==digest,'Qualified artifact changed: '+name
stage=root/'verification'/('release-'+release);stage.mkdir(parents=True,exist_ok=False)
subprocess.run(['git','bundle','create',str(stage/'source.bundle'),'--all'],cwd=root,check=True)
inputs=json.loads((root/f'evidence/run-{run_name}-inputs.json').read_text());parent=pathlib.Path(inputs['parent_checkpoint']);resume_step=inputs.get('resume_step','OpenROAD.FinalElectricalRepair')
state=json.loads(parent.read_text());metrics=state.pop('metrics',None);files={};counter=[0]
checkpoint=stage/'checkpoint';checkpoint.mkdir()
def portable(v):
 if isinstance(v,dict):return {k:portable(x) for k,x in v.items()}
 if isinstance(v,list):return [portable(x) for x in v]
 if isinstance(v,str):
  source=pathlib.Path(v);assert source.is_file(),source
  counter[0]+=1;rel=f'views/{counter[0]:03d}-{source.name}';target=checkpoint/rel;target.parent.mkdir(exist_ok=True);shutil.copy2(source,target);files[rel]=sha(target);return rel
 return v
state=portable(state)
if metrics is not None:state['metrics']=metrics
(checkpoint/'state-portable.json').write_text(json.dumps(state,indent=2)+'\n')
(checkpoint/'manifest.json').write_text(json.dumps({'original_checkpoint':str(parent),'original_checkpoint_sha256':sha(parent),'resume_step':resume_step,'files':files},indent=2)+'\n')
(stage/'README.txt').write_text(f'''CPU + hybrid MAC baseline: {release}
Qualified run: {run_name}
Scope: 20 MHz, 3x4 tiles; RTL, functional gate tests, nine-corner STA, electrical checks, physical checks and Tiny Tapeout prechecks.
SDF timing simulation, silicon/radiation qualification and full-chip power/IR signoff are excluded.

Clone the included history with: git clone source.bundle cpu-mac-baseline
The local release tag is included. See the source README and evidence/qualification-{run_name}.json.

The portable checkpoint reproduces the incremental closure entry point. After installing the pinned tool/PDK environment, create a fresh materialized state with:
python3 cpu-mac-baseline/scripts/restore-checkpoint.py checkpoint state-local.json
Then, from the cloned source directory, set QUALIFY_FROM_STATE to that absolute state-local.json path and QUALIFY_FROM_STEP={resume_step} before running scripts/harden-local.sh with a fresh run name. Re-run qualification for any rebuilt result.

SHA256SUMS covers the archive members. Tool binaries and PDK installations are not included.
''')
entries={str(p.relative_to(stage)):p for p in stage.rglob('*') if p.is_file()}
final=root/'runs'/run_name/'final'
for p in final.rglob('*'):
 if p.is_file():entries['final/'+str(p.relative_to(final))]=p
entries['resolved.json']=root/'runs'/run_name/'resolved.json'
entries['source-README.md']=root/'README.md'
for p in (root/'evidence').glob('*'):
 if p.is_file() and (run_name in p.name or p.name in ['validation-policy.json','rtl-current-validation.json','rtl-current-results.xml','rtl-current-input-sha256.json','source-provenance.json','pdk-version.json','tool-versions.txt']):entries['evidence/'+p.name]=p
sta_dirs=list((root/'runs'/run_name).glob('*-openroad-stapostpnr'))
for directory in sta_dirs:
 for p in directory.rglob('*.rpt'):entries['timing/'+str(p.relative_to(directory))]=p
# Waveforms are optional debug outputs and are not release evidence.
(stage/'SHA256SUMS').write_text(''.join(f'{sha(p)}  {name}\n' for name,p in sorted(entries.items())))
entries['SHA256SUMS']=stage/'SHA256SUMS'
out_dir=root/'releases';out_dir.mkdir(exist_ok=True);archive=out_dir/(release+'.tar.gz')
with tarfile.open(archive,'x:gz',dereference=True) as tar:
 for name,p in sorted(entries.items()):tar.add(p,arcname=release+'/'+name,recursive=False)
(archive.with_suffix(archive.suffix+'.sha256')).write_text(sha(archive)+'  '+archive.name+'\n')
print(archive);print('SIZE_BYTES',archive.stat().st_size);print('SHA256',sha(archive))
