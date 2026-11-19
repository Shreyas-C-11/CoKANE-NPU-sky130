# Copyright 2020-2023 Efabless Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
source $::env(SCRIPTS_DIR)/openroad/common/resizer.tcl

read_current_odb

# Electrical repair must use the slow corner explicitly, not Tcl corner order.
lln::set_sta_cmd_corner max_ss_100C_1v60
puts "Electrical repair command corner: max_ss_100C_1v60"

set_propagated_clock [all_clocks]

set_dont_touch_objects

# set rc values
source $::env(SCRIPTS_DIR)/openroad/common/set_rc.tcl

# (Re-)GRT and Estimate Parasitics
# Temporarily always enabled: https://github.com/The-OpenROAD-Project/OpenROAD/issues/5590
#if { $::env(GRT_DESIGN_REPAIR_RUN_GRT) } {
source $::env(SCRIPTS_DIR)/openroad/common/grt.tcl
#}
estimate_parasitics -global_routing

# Repair Design
# Leave two loads of headroom for antenna diodes added later.
# The declared design limit remains MAX_FANOUT_CONSTRAINT (10).
set_max_fanout $::env(MAX_FANOUT_CONSTRAINT) [current_design]
set arg_list [list]
lappend arg_list -verbose
lappend arg_list -max_wire_length $::env(GRT_DESIGN_REPAIR_MAX_WIRE_LENGTH)
lappend arg_list -slew_margin $::env(GRT_DESIGN_REPAIR_MAX_SLEW_PCT)
lappend arg_list -cap_margin $::env(GRT_DESIGN_REPAIR_MAX_CAP_PCT)
if { [info exists ::env(GRT_DESIGN_REPAIR_MAX_UTILIZATION)] } {
    lappend arg_list -max_utilization $::env(GRT_DESIGN_REPAIR_MAX_UTILIZATION)
}
if { [info exists ::env(GRT_DESIGN_REPAIR_BUFFER_GAIN)] } {
    lappend arg_list -buffer_gain $::env(GRT_DESIGN_REPAIR_BUFFER_GAIN)
}
log_cmd repair_design {*}$arg_list
set_max_fanout $::env(MAX_FANOUT_CONSTRAINT) [current_design]

# Re-DPL and GRT
source $::env(SCRIPTS_DIR)/openroad/common/dpl.tcl
unset_dont_touch_objects
if { $::env(GRT_DESIGN_REPAIR_RUN_GRT) } {
    source $::env(SCRIPTS_DIR)/openroad/common/grt.tcl
}


# Use the newly routed parasitics and repeat only while electrical checks fail.
estimate_parasitics -global_routing
for {set pass 0} {$pass < 3} {incr pass} {
 lln::set_sta_cmd_corner max_ss_100C_1v60
 set remaining [expr {[sta::max_slew_violation_count]+[sta::max_capacitance_violation_count]+[sta::max_fanout_violation_count]}]
 puts "Final electrical pass $pass: $remaining violations"
 if {$remaining==0} {break}
 log_cmd repair_design {*}$arg_list
 source $::env(SCRIPTS_DIR)/openroad/common/dpl.tcl
 source $::env(SCRIPTS_DIR)/openroad/common/grt.tcl
 estimate_parasitics -global_routing
}
puts "Post-repair slow-corner electrical report"
report_check_types -max_slew -max_capacitance -max_fanout -violators -corner max_ss_100C_1v60
write_metric_int "design__max_slew_violation__count" [sta::max_slew_violation_count]
write_metric_int "design__max_cap_violation__count" [sta::max_capacitance_violation_count]
write_metric_int "design__max_fanout_violation__count" [sta::max_fanout_violation_count]
write_views
