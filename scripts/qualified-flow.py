#!/usr/bin/env python3
"""Fresh CoKANE physical flow; no historical instance-specific ECOs."""
import json,os,pathlib,subprocess,sys
from librelane.state import State
from librelane.flows.classic import Classic
from librelane.steps import Step
from librelane.steps.openroad import CTS,OpenROADStep,RepairDesignPostGRT,ResizerTimingPostGRT
root=pathlib.Path(__file__).resolve().parents[1]
subprocess.run([sys.executable,str(root/'scripts/check-frozen-prototype.py')],check=True)
@Step.factory.register()
class ClockFanoutRepair(OpenROADStep):
    id='OpenROAD.ClockFanoutRepair'
    name='Generic clock fanout repair'
    config_vars=CTS.config_vars
    def get_script_path(self):return str(root/'scripts/signoff-clock-fanout.tcl')
@Step.factory.register()
class SlowCornerRepair(RepairDesignPostGRT):
    id='OpenROAD.SlowCornerRepair'
    name='Slow-corner electrical repair'
    def run(self,state_in,**kwargs):return OpenROADStep.run(self,state_in,corners=['max_ss_100C_1v60'],**kwargs)
    def get_script_path(self):return str(root/'scripts/repair-slowcorner.tcl')
@Step.factory.register()
class FinalElectricalRepair(SlowCornerRepair):
    id='OpenROAD.FinalElectricalRepair'
    name='Final slow-corner electrical repair'
    def get_script_path(self):return str(root/'scripts/final-electrical.tcl')
class CoKANESignoffFlow(Classic):
    Steps=Classic.Steps.copy()
    Steps.insert(Steps.index(CTS)+1,ClockFanoutRepair)
    Steps[Steps.index(RepairDesignPostGRT)]=SlowCornerRepair
    Steps.insert(Steps.index(ResizerTimingPostGRT)+1,FinalElectricalRepair)
pdk=pathlib.Path(os.environ['PDK_ROOT'])
if not (pdk/'sky130A').is_dir():pdk=pdk/'ciel/sky130/versions'/json.loads((root/'evidence/pdk-version.json').read_text())['version']
flow=CoKANESignoffFlow(sys.argv[1],pdk_root=str(pdk),pdk='sky130A')
options={}
if os.getenv('QUALIFY_FROM_STATE'):
    options['with_initial_state']=State.loads(pathlib.Path(os.environ['QUALIFY_FROM_STATE']).read_text())
    options['frm']=os.environ['QUALIFY_FROM_STEP']
if os.getenv('QUALIFY_TO'):options['to']=os.environ['QUALIFY_TO']
flow.start(tag=sys.argv[2],_force_run_dir=sys.argv[3],**options)
