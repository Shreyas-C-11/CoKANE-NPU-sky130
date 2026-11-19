#!/usr/bin/env python3
import os,pathlib,sys,json
from librelane.flows.classic import Classic
from librelane.steps.openroad import CTS,OpenROADStep
from librelane.steps import Step

@Step.factory.register()
class ClockFanoutRepair(OpenROADStep):
    id='OpenROAD.ClockFanoutRepair'
    name='Clock Root Fanout Repair'
    config_vars=CTS.config_vars
    def get_script_path(self):
        return str(pathlib.Path(__file__).with_name('clock-fanout.tcl'))

class QualifiedCPUFlow(Classic):
    Steps=Classic.Steps.copy()
    Steps.insert(Steps.index(CTS)+1,ClockFanoutRepair)

root=pathlib.Path(__file__).resolve().parent.parent
pdk_root=pathlib.Path(os.environ['PDK_ROOT'])
if not (pdk_root/'sky130A').is_dir():
    version=json.loads((root/'evidence/pdk-version.json').read_text())['version']
    pdk_root=pdk_root/'ciel/sky130/versions'/version
assert (pdk_root/'sky130A').is_dir(), 'Pinned SKY130 revision missing'
flow=QualifiedCPUFlow(sys.argv[1],pdk_root=str(pdk_root),pdk='sky130A')
flow.start(tag=sys.argv[2],_force_run_dir=sys.argv[3])
