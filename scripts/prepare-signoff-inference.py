"""Keep the frozen executable; optionally replace only its read-only LUT data."""
import hashlib,json,pathlib,subprocess,sys
root=pathlib.Path(__file__).resolve().parents[1];out=pathlib.Path(sys.argv[1]);model=sys.argv[2]
assert model in ['synthetic','zero']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
build=json.loads(subprocess.check_output(['git','show','cokane-working-prototype-v0.2:evidence/cokane/inference-build.json'],cwd=root))
original=root/'verification/inference'
for name in ['firmware.elf','firmware.hex','fixture.json']:
    assert sha(original/name)==build['artifacts_sha256'][name],name
image=bytearray().join(int(w,16).to_bytes(4,'little') for w in (original/'firmware.hex').read_text().splitlines())
fixture=json.loads((original/'fixture.json').read_text());ranges=[]
if model=='zero':
    nm=root.parent/'tools/xpack-riscv-none-elf-gcc-15.2.0-1/bin/riscv-none-elf-nm'
    symbols=subprocess.check_output([str(nm),'-S',str(original/'firmware.elf')],text=True)
    targets={f'fixture_{name}':len(fixture[name]) for name in ['conv1','conv2','dense']}
    for line in symbols.splitlines():
        fields=line.split()
        if len(fields)==4 and fields[3] in targets:
            address,size=int(fields[0],16),int(fields[1],16)
            assert fields[2] in ['r','R'] and size==targets.pop(fields[3])
            image[address:address+size]=bytes(size);ranges.append([fields[3],address,size])
    assert not targets and len(ranges)==3
    for name in ['conv1','conv2','dense']:fixture[name]=[0]*len(fixture[name])
    for name in ['expected_a','expected_b','expected_scores']:fixture[name]=[0]*len(fixture[name])
    fixture['prediction']=0
out.mkdir(parents=True,exist_ok=False)
(out/'firmware.hex').write_text(''.join(f'{int.from_bytes(image[i:i+4],"little"):08x}\n' for i in range(0,len(image),4)))
(out/'fixture.json').write_text(json.dumps(fixture,separators=(',',':'))+'\n')
(out/'model-identity.json').write_text(json.dumps({'model':model,'frozen_commit':'db530b7fe46207c3720513d0c4b0d0d69ce45dee','original_firmware_sha256':sha(original/'firmware.hex'),'firmware_sha256':sha(out/'firmware.hex'),'fixture_sha256':sha(out/'fixture.json'),'modified_readonly_lut_ranges':ranges,'executable_instructions_modified':False},indent=2)+'\n')
