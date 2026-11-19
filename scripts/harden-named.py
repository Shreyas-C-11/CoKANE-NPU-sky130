#!/usr/bin/env python3
"""Run a new LibreLane directory without overwriting any previous result."""
import json,os,re,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent.parent
os.chdir(root)
tag=sys.argv[1]
if not re.fullmatch(r'[A-Za-z0-9_-]+',tag): raise SystemExit('Invalid run tag')
run=root/'runs'/tag
if run.exists(): raise SystemExit(f'Refusing to overwrite {run}')
commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
active={'run_directory':str(run.relative_to(root)),'source_commit':commit}
if os.getenv('QUALIFY_FROM_STATE'):
 active['parent_checkpoint']=os.environ['QUALIFY_FROM_STATE']
 active['parent_checkpoint_sha256']=__import__('hashlib').sha256(Path(os.environ['QUALIFY_FROM_STATE']).read_bytes()).hexdigest()
(root/'evidence/active-run.json').write_text(json.dumps(active,indent=2)+'\n')
(root/f'evidence/run-{tag}-inputs.json').write_text(json.dumps(active,indent=2)+'\n')
subprocess.run([sys.executable,'scripts/notify-build.py','--run-dir',str(run),'--running'],check=True)
subprocess.run([sys.executable,'tt/tt_tool.py','--create-user-config'],check=True)
run.mkdir(parents=True)
rc=subprocess.run([sys.executable,'scripts/qualified-flow.py','src/config_merged.json',tag,str(run)]).returncode
if (run/'final').is_dir():
 (run/'final/commit_id.json').write_text(json.dumps({'commit':commit,'repo':'local-only','app':'vendored Tiny Tapeout tools; LibreLane named run'},indent=2)+'\n')
subprocess.run([sys.executable,'scripts/notify-build.py','--run-dir',str(run),'--exit-code',str(rc)],check=True)
raise SystemExit(rc)
