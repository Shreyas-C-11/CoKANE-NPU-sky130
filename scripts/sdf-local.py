#!/usr/bin/env python3
"""Execute pin firmware on the powered netlist with CVC SDF timing checks enabled."""
import argparse,hashlib,importlib.util,json,os,pathlib,subprocess,sys,re
root=pathlib.Path(__file__).resolve().parent.parent
p=argparse.ArgumentParser();p.add_argument('run');p.add_argument('corner');p.add_argument('--fast',action='store_true');p.add_argument('--attempt',default='1');a=p.parse_args()
run=root/'runs'/a.run
work=root/'verification/timing'/a.run/(a.corner+('-negative-fast' if a.fast else '')+'-attempt'+a.attempt)
work.mkdir(parents=True,exist_ok=False)
spec=importlib.util.spec_from_file_location('firmware_tests',root/'test/test.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
program=work/'firmware.hex';program.write_text(''.join(f'{x:08x}\n' for x in m.firmware()))
config=json.loads((run/'resolved.json').read_text());pdk=pathlib.Path(config['PDK_ROOT'])/'sky130A/libs.ref/sky130_fd_sc_hd/verilog'
cvc=next((root/'verification/tools').glob('open-src-cvc-*/build64/cvc64'))
sdf=next((run/'final/sdf'/a.corner).glob('*.sdf'));netlist=run/'final/pnl/tt_um_cokane_soc.pnl.v'
original=(pdk/'primitives.v').read_text(); compatible=re.sub(r'\(([01xX?])([01xX?])\)',r'(\1 \2)',original)
assert re.sub(r'\s','',original)==re.sub(r'\s','',compatible)
primitives=work/'primitives-cvc.v';primitives.write_text(compatible)
cmd=[str(cvc),'+interp','+define+USE_POWER_PINS','+typdelays','+sdf_annotate',str(sdf)+'+tb_sdf.user_project','+sdf_log_file',str(work/'annotation.log'),str(primitives),'-v',str(pdk/'sky130_fd_sc_hd.v'),str(netlist),str(root/'test/tb_sdf.v'),'+PROGRAM='+str(program)]
if a.fast:cmd.append('+FAST')
with (work/'simulation.log').open('w') as out:r=subprocess.run(cmd,cwd=work,stdout=out,stderr=subprocess.STDOUT)
text=(work/'simulation.log').read_text(errors='replace');annotation=(work/'annotation.log').read_text(errors='replace') if (work/'annotation.log').exists() else ''
result={'run':a.run,'corner':a.corner,'negative_fast_clock':a.fast,'process_exit':r.returncode,'firmware_pass_marker':'SDF_FIRMWARE_PASS' in text,'netlist_sha256':hashlib.sha256(netlist.read_bytes()).hexdigest(),'sdf_sha256':hashlib.sha256(sdf.read_bytes()).hexdigest(),'simulator_source':json.loads((root/'verification/tools/cvc-source.json').read_text()),'command':cmd,'simulation_log':str(work/'simulation.log'),'annotation_log':str(work/'annotation.log'),'status':'needs_log_review','udp_whitespace_only_compatibility':True,'attempt':a.attempt}
report=root/'evidence'/f'sdf-{a.run}-{a.corner}{"-negative-fast" if a.fast else ""}.json';report.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
raise SystemExit(0 if result['firmware_pass_marker'] and r.returncode==0 else 1)
