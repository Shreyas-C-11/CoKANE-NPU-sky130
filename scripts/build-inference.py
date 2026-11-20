"""Build actual RV32E/ILP32E firmware and a separately computed tensor fixture."""
import hashlib,json,os,pathlib,subprocess
from inference_fixture import write
root=pathlib.Path(__file__).resolve().parents[1]
out=root/'verification/inference';out.mkdir(parents=True,exist_ok=True)
write(out)
prefix=pathlib.Path(os.environ.get('RISCV_TOOLCHAIN',str(root.parent/'tools/xpack-riscv-none-elf-gcc-15.2.0-1')))/'bin/riscv-none-elf-'
tool=lambda name:str(prefix)+name
sources=['firmware/inference_start.S','firmware/inference_main.c','firmware/cokane_scheduler.c','firmware/inference_runtime.c','firmware/inference_reference.c']
cmd=[tool('gcc'),'-march=rv32e','-mabi=ilp32e','-mno-relax','-msmall-data-limit=0','-Os','-g',
     '-std=c11','-Wall','-Wextra','-Werror','-ffreestanding','-fno-builtin','-fno-pic','-fno-pie',
     '-fno-unwind-tables','-fno-asynchronous-unwind-tables','-ffunction-sections','-fdata-sections',
     '-nostdlib','-static','-Wl,--no-relax,--gc-sections','-Wl,-Map,'+str(out/'firmware.map'),
     '-T',str(root/'firmware/inference.ld'),'-I'+str(root/'firmware'),'-I'+str(out),
     *[str(root/p) for p in sources],'-lgcc','-o',str(out/'firmware.elf')]
subprocess.run(cmd,check=True,cwd=root)
subprocess.run([tool('objcopy'),'-O','binary',str(out/'firmware.elf'),str(out/'firmware.bin')],check=True)
binary=(out/'firmware.bin').read_bytes();assert len(binary)<0x2e000
data=binary+bytes(0x40000-len(binary))
(out/'firmware.hex').write_text(''.join(f'{int.from_bytes(data[i:i+4],"little"):08x}\n' for i in range(0,len(data),4)))
with (out/'firmware-disassembly.txt').open('w') as f:
    subprocess.run([tool('objdump'),'-d',str(out/'firmware.elf')],stdout=f,check=True)
attributes=subprocess.check_output([tool('readelf'),'-h','-A',str(out/'firmware.elf')],text=True)
(out/'firmware-attributes.txt').write_text(attributes)
assert 'RVE' in attributes
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inputs=sources+['firmware/cokane.h','firmware/cokane_scheduler.h','firmware/inference.ld','scripts/build-inference.py','scripts/inference_fixture.py']
record={'result':'PASS','compiler':subprocess.check_output([tool('gcc'),'--version'],text=True).splitlines()[0],
        'compiler_sha256':sha(pathlib.Path(tool('gcc'))),'architecture':'rv32e','abi':'ilp32e','command':cmd,
        'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
        'inputs_sha256':{p:sha(root/p) for p in inputs},'binary_bytes':len(binary),
        'artifacts_sha256':{name:sha(out/name) for name in ['firmware.elf','firmware.bin','firmware.hex','fixture.json','inference_fixture.h']}}
(root/'evidence/cokane/inference-build.json').write_text(json.dumps(record,indent=2)+'\n')
print('RV32E_FIRMWARE_BUILD_PASS bytes=',len(binary))
