# Repair only excessive routed signal fanout; retain final limit 10.
source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
read_current_odb
set_propagated_clock [all_clocks]
set modified 0
set inst [$::block findInst _06773_]
if {$inst=="NULL"} {error "Expected mux hotspot instance not found"}
set current [[$inst getMaster] getName]
if {$current=="sky130_fd_sc_hd__mux2_1"} {
 replace_cell _06773_ sky130_fd_sc_hd__mux2_2
 set modified 1
 puts "Transition ECO: _06773_ mux2_1 -> mux2_2"
} elseif {$current!="sky130_fd_sc_hd__mux2_2" && $current!="sky130_fd_sc_hd__mux2_4"} {
 error "Unexpected cell at transition hotspot: $current"
}
if {$modified>0} {
 # Rip up signal wires only; power special-wires and all cells are preserved.
 foreach net [$::block getNets] {
  if {[$net getSigType] == "POWER" || [$net getSigType] == "GROUND"} {continue}
  set wire [$net getWire]
  if {$wire != "NULL"} {odb::dbWire_destroy $wire}
 }
 source $::env(SCRIPTS_DIR)/openroad/common/dpl.tcl
 source $::env(SCRIPTS_DIR)/openroad/common/set_rc.tcl
 source $::env(SCRIPTS_DIR)/openroad/common/grt.tcl
 estimate_parasitics -global_routing
}
write_metric_int "design__postroute_transition_repairs" $modified
puts "Post-route cells strengthened: $modified"
write_views
