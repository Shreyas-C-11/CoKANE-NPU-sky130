"""Map both standalone and integrated designs to the pinned SKY130 TT library."""
import hashlib,json,pathlib,subprocess
root=pathlib.Path(__file__).resolve().parent.parent
pdk=json.loads((root/'evidence/pdk-version.json').read_text())
revision=pdk.get('revision') or pdk.get('version')
if not revision:
    # Evidence identifies the pinned root directly in the inherited run config.
    cfg=json.loads((root.parent/'cpu-mac-baseline/runs/r16-orienteco/resolved.json').read_text())
    pdkroot=pathlib.Path(cfg['PDK_ROOT'])
else:
    pdkroot=root.parent/'pdk/ciel/sky130/versions'/revision
lib=pdkroot/'sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib'
assert lib.is_file(),lib
out=root/'verification/cokane-synth';out.mkdir(parents=True,exist_ok=True)
sources=['tt_um_cokane_soc.v','soc_core.v','wb_decoder.v','mac_wb.v','cokane_wb.v','picorv32.v','mac_hybrid.sv','mac_residue7_check.sv','signed_residue7.sv','secded_decoder.sv','secded_encoder.sv']
inputs={str((root/'src'/f).relative_to(root)):hashlib.sha256((root/'src'/f).read_bytes()).hexdigest() for f in sources}
results={}
for name,top,files in [('engine','cokane_wb',['cokane_wb.v']),('integrated','tt_um_cokane_soc',sources)]:
    script=f'''read_liberty -lib {lib}
read_verilog -sv -DSYNTHESIS -I{root/'src'} {' '.join(str(root/'src'/f) for f in files)}
hierarchy -check -top {top}
synth -top {top} -flatten -noabc
select -assert-none t:$dlatch t:$adlatch
dfflibmap -liberty {lib}
abc -liberty {lib}
clean
check -assert
tee -o {out/(name+'-stat.json')} stat -json -liberty {lib}
write_verilog -noattr {out/(name+'.v')}
'''
    ys=out/(name+'.ys');ys.write_text(script)
    log=root/'evidence/cokane'/(name+'-synthesis.log')
    with log.open('w') as stream:subprocess.run(['yosys','-s',str(ys)],stdout=stream,stderr=subprocess.STDOUT,check=True,cwd=root)
    record=json.loads((out/(name+'-stat.json')).read_text())
    (root/'evidence/cokane'/(name+'-stat.json')).write_text(json.dumps(record,indent=2)+'\n')
    results[name]=record
result={'result':'PASS','scope':'standard-cell synthesis feasibility only; no timing or physical qualification','library':str(lib),'library_sha256':hashlib.sha256(lib.read_bytes()).hexdigest(),'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True,cwd=root).strip(),'inputs_sha256':inputs,'statistics':results}
(root/'evidence/cokane/synthesis-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print('SYNTHESIS_FEASIBILITY_PASS')
for name,result in results.items():print(name,json.dumps(result.get('design',result)))
