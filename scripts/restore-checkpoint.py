#!/usr/bin/env python3
"""Resolve an archived checkpoint's relative paths after verifying its files."""
import argparse,hashlib,json,pathlib
p=argparse.ArgumentParser(description=__doc__);p.add_argument('checkpoint');p.add_argument('output');a=p.parse_args()
base=pathlib.Path(a.checkpoint).resolve();manifest=json.loads((base/'manifest.json').read_text())
for rel,digest in manifest['files'].items():
 path=(base/rel).resolve();path.relative_to(base)
 assert hashlib.sha256(path.read_bytes()).hexdigest()==digest, 'Checkpoint hash mismatch: '+rel
state=json.loads((base/'state-portable.json').read_text())
def resolve(v):
 if isinstance(v,dict): return {k:resolve(x) for k,x in v.items()}
 if isinstance(v,list): return [resolve(x) for x in v]
 if isinstance(v,str):
  path=(base/v).resolve();path.relative_to(base);assert path.is_file();return str(path)
 return v
metrics=state.pop('metrics',None);state=resolve(state)
if metrics is not None:state['metrics']=metrics
out=pathlib.Path(a.output);assert not out.exists(),'Refusing to overwrite output';out.write_text(json.dumps(state,indent=2)+'\n');print(out.resolve())
