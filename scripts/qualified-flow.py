#!/usr/bin/env python3
import os,pathlib,sys
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

flow=QualifiedCPUFlow(sys.argv[1],pdk_root=os.environ['PDK_ROOT'])
flow.start(tag=sys.argv[2],_force_run_dir=sys.argv[3])
