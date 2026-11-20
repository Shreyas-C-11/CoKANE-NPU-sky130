#!/usr/bin/env python3
"""Reject functional changes on the physical qualification branch."""
import hashlib,json,pathlib
root=pathlib.Path(__file__).resolve().parents[1]
d=json.loads((root/'evidence/frozen-prototype.json').read_text())
for name,digest in d['immutable_files_sha256'].items():
    assert hashlib.sha256((root/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==digest,name
assert 'tiles: "5x4"' in (root/'info.yaml').read_text()
assert json.loads((root/'src/config.json').read_text())['CLOCK_PERIOD']==50
print('FROZEN_PROTOTYPE_INPUTS_MATCH',d['frozen_commit'])
