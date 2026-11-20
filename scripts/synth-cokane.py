"""Map both standalone and integrated designs to the pinned SKY130 TT library."""
import hashlib,json,pathlib,subprocess
from librelane.common.toolbox import Toolbox
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
original_lib=lib
excluded_files=[pdkroot/'sky130A/libs.tech/openlane/sky130_fd_sc_hd'/name for name in ['no_synth.cells','drc_exclude.cells']]
excluded=frozenset(line.strip() for f in excluded_files for line in f.read_text().splitlines() if line.strip() and not line.lstrip().startswith('#'))
lib=pathlib.Path(Toolbox(str(out/'filtered-lib')).remove_cells_from_lib(frozenset([str(lib)]),excluded)[0])
sources=['tt_um_cokane_soc.v','soc_core.v','wb_decoder.v','mac_wb.v','cokane_wb.v','picorv32.v','mac_hybrid.sv','mac_residue7_check.sv','signed_residue7.sv','secded_decoder.sv','secded_encoder.sv']
inputs={str((root/'src'/f).relative_to(root)):hashlib.sha256((root/'src'/f).read_bytes()).hexdigest() for f in sources+sorted(p.name for p in (root/'src').glob('*.vh'))}
results={}
for name,top,files in [('engine','cokane_wb',['cokane_wb.v']),('integrated','tt_um_cokane_soc',sources)]:
    script=f'''read_liberty -lib {lib}
read_verilog -sv -DSYNTHESIS -I{root/'src'} {' '.join(str(root/'src'/f) for f in files)}
hierarchy -check -top {top}
synth -top {top} -flatten -noabc
select -assert-none t:$dlatch t:$adlatch t:$_DLATCH_* t:$_DLATCHSR_*
dffunmap
dfflibmap -liberty {lib}
abc {'-fast' if name=='integrated' else ''} -liberty {lib}
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
result={'result':'PASS','scope':'standard-cell synthesis feasibility only; no timing or physical qualification','library':str(original_lib),'mapping_library':str(lib),'excluded_cell_files_sha256':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in excluded_files},'library_sha256':hashlib.sha256(original_lib.read_bytes()).hexdigest(),'mapping_library_sha256':hashlib.sha256(lib.read_bytes()).hexdigest(),'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True,cwd=root).strip(),'inputs_sha256':inputs,'mapping_strategy':{'engine':'ABC default mapping','integrated':'ABC fast mapping for preliminary footprint estimation'},'statistics':results}
(root/'evidence/cokane/synthesis-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print('SYNTHESIS_FEASIBILITY_PASS')
for name,result in results.items():print(name,{k:result['design'][k] for k in ['num_cells','area','sequential_area']})
