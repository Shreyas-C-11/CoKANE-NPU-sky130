#!/usr/bin/env python3
"""Bind the submission to qualified physical artifacts; never run hardening."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument('--materialize-dir', type=Path)
args = p.parse_args()
subprocess.run([sys.executable, str(root/'scripts/check-frozen-prototype.py')], check=True)
manifest = json.loads((root/'layout/manifest.json').read_text())
qualification = json.loads((root/manifest['qualification_record']).read_text())
assert qualification['result'] == 'PASS' and not qualification['problems']
assert manifest['pdk'] == 'sky130A' and manifest['tiles'] == '5x4'
assert manifest['qualified_commit'] == qualification['source']['commit']
assert len(manifest['files']) == 3
if args.materialize_dir:
    args.materialize_dir.mkdir(parents=True, exist_ok=True)
for rel, item in manifest['files'].items():
    path = (root/rel).resolve()
    path.relative_to(root)
    data = path.read_bytes()
    assert hashlib.sha256(data).hexdigest() == item['sha256'], rel+' stored hash'
    if item['compressed']:
        data = gzip.decompress(data)
    digest = hashlib.sha256(data).hexdigest()
    assert digest == item['qualified_sha256'], rel+' qualified hash'
    matches = [v for k, v in qualification['artifacts_sha256'].items()
               if k.endswith('/'+path.name.removesuffix('.gz'))]
    assert matches == [digest], rel+' qualification binding'
    if args.materialize_dir:
        target = args.materialize_dir/path.name.removesuffix('.gz')
        if target.exists():
            assert hashlib.sha256(target.read_bytes()).hexdigest() == digest, str(target)
        else:
            target.write_bytes(data)
    print('QUALIFIED_LAYOUT_MATCH', path.name, digest)
images = json.loads((root/'host/images.json').read_text())
for name, digest in images['sha256'].items():
    assert hashlib.sha256((root/'host'/name).read_bytes()).hexdigest() == digest, name
build = json.loads((root/'evidence/cokane/inference-build.json').read_text())
assert images['sha256']['inference.hex'] == build['artifacts_sha256']['firmware.hex']
print('SUBMISSION_ARTIFACTS_VERIFIED', manifest['qualified_tag'])
