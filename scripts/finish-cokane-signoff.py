#!/usr/bin/env python3
"""Finish an already running qualification; record local events, never publish."""
import datetime,hashlib,json,os,pathlib,subprocess,sys,tarfile,time,traceback
root=pathlib.Path(__file__).resolve().parents[1];os.chdir(root)
tag=sys.argv[1];pids=[int(x) for x in sys.argv[2:]]
assert tag=='ck-signoff-r4' and pids
release='cokane-20mhz-5x4-v0.2'
status=root/f'evidence/signoff-handler-{tag}.json'
def save(state,**kw):
 d={'status':state,'run':tag,'updated_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'release':release,**kw}
 tmp=status.with_suffix('.tmp');tmp.write_text(json.dumps(d,indent=2)+'\n');tmp.replace(status)
def cmd(*args):subprocess.run(args,check=True,cwd=root)
def git(*args):cmd('git','-c','user.name=Shreyas Chaudhari','-c','user.email=shreyaschaudhari11@gmail.com',*args)
def active(pid):
 try:return f'scripts/run-signoff-inference.sh {tag} '.encode() in pathlib.Path(f'/proc/{pid}/cmdline').read_bytes().replace(b'\0',b' ')
 except FileNotFoundError:return False
try:
 save('WAITING_FOR_FINAL_GATE_INFERENCE',simulation_pids=pids)
 deadline=time.monotonic()+24*3600
 while any(active(p) for p in pids):
  if time.monotonic()>deadline:raise RuntimeError('Gate test wait exceeded 24 hours; inspect logs')
  time.sleep(15)
 assert subprocess.check_output(['git','branch','--show-current'],text=True).strip()=='signoff/cokane-v0.2'
 for model in ['synthetic','zero']:
  d=json.loads((root/f'evidence/signoff-{tag}-{model}-inference.json').read_text())
  assert d['result']=='PASS' and d['model_identity']['model']==model
 save('CHECKING_ALL_EVIDENCE')
 cmd(sys.executable,'scripts/qualify.py',tag)
 policy=root/'evidence/validation-policy.json';d=json.loads(policy.read_text());d['status']='QUALIFIED_FOR_DECLARED_SCOPE';policy.write_text(json.dumps(d,indent=2)+'\n')
 p=root/f'evidence/physical-review-{tag}.json';d=json.loads(p.read_text());d['scope']='Physical review; final gate inference and prechecks also passed';p.write_text(json.dumps(d,indent=2)+'\n')
 # Canonical documentation is maintained in NPU_Specs.md from bound evidence.
 cmd(sys.executable,'scripts/qualify.py',tag)
 cmd(sys.executable,'scripts/notify-build.py','--run-dir',str(root/'runs'/tag),'--exit-code','0')
 files=['evidence/validation-policy.json','evidence/build-notification.json',f'evidence/physical-review-{tag}.json',f'evidence/qualification-{tag}.json',f'evidence/gl-{tag}-validation.json',f'evidence/gl-{tag}-results.xml',f'evidence/gl-{tag}-exit-code.txt',f'evidence/precheck-{tag}.json',f'evidence/precheck-{tag}-results.xml']
 for model in ['synthetic','zero']:
  files += [f'evidence/signoff-{tag}-{model}-inference.json',f'evidence/signoff-{tag}-{model}-inference-results.xml']
 git('add','--',*files)
 git('commit','-m','Qualify frozen CPU MAC CoKANE block at 20 MHz in 5x4 tiles')
 git('tag','-a',release,'-m','Frozen CPU + MAC + CoKANE digital block qualification; trained accuracy and performance work deferred')
 save('PACKAGING_QUALIFIED_BLOCK')
 cmd(sys.executable,'scripts/package-qualified.py',tag,release)
 archive=root/'releases'/(release+'.tar.gz')
 with tarfile.open(archive,'r:gz') as tar:
  manifest=tar.extractfile(release+'/SHA256SUMS').read().decode()
  expected={}
  for line in manifest.splitlines():
   digest,name=line.split('  ',1);expected[release+'/'+name]=digest
  assert {m.name for m in tar.getmembers()}==set(expected)|{release+'/SHA256SUMS'}
  for name,digest in expected.items():
   h=hashlib.sha256()
   with tar.extractfile(name) as stream:
    for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
   assert h.hexdigest()==digest,name
 stage=root/'verification'/('release-'+release)
 cmd(sys.executable,'scripts/restore-checkpoint.py',str(stage/'checkpoint'),str(stage/'restored-state.json'))
 cmd('git','bundle','verify',str(stage/'source.bundle'))
 h=hashlib.sha256()
 with archive.open('rb') as stream:
  for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
 digest=h.hexdigest()
 assert archive.with_suffix('.gz.sha256').read_text().split()[0]==digest
 proof={'result':'PASS','archive':str(archive),'archive_sha256':digest,'archive_members_verified':len(expected),'portable_checkpoint_restored':True,'source_bundle_verified':True}
 (root/f'evidence/package-check-{tag}.json').write_text(json.dumps(proof,indent=2)+'\n')
 save('COMPLETE_FOR_DECLARED_SCOPE',**proof)
 print('COKANE_DECLARED_SCOPE_COMPLETE',digest,flush=True)
except Exception as error:
 save('FAILED_REQUIRES_REVIEW',error=str(error))
 traceback.print_exc();raise
