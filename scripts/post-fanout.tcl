# Incremental extracted electrical ECO; retain unaffected detailed wires.
source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
read_current_odb
set_propagated_clock [all_clocks]
set modified 0
set dirty_nets [dict create]
set original [dict create]
proc mark_inst_nets {inst} {
 global dirty_nets
 foreach pin [$inst getITerms] {
  set net [$pin getNet]
  if {$net!="NULL" && [$net getSigType]!="POWER" && [$net getSigType]!="GROUND"} {dict set dirty_nets [$net getName] $net}
 }
}
foreach inst [$::block getInsts] {dict set original [$inst getName] [list [$inst getLocation] [$inst getOrient] [[$inst getMaster] getName]]}
foreach {name expected replacement} {
 _11238_ sky130_fd_sc_hd__dfxtp_2 sky130_fd_sc_hd__dfxtp_4
 _08538_ sky130_fd_sc_hd__a21o_2 sky130_fd_sc_hd__a21o_4
 hold2473 sky130_fd_sc_hd__dlygate4sd3_1 sky130_fd_sc_hd__clkdlybuf4s50_2
} {
 set inst [$::block findInst $name]
 if {$inst=="NULL"} {error "Expected electrical hotspot missing: $name"}
 set current [[$inst getMaster] getName]
 if {$current==$expected} {
  mark_inst_nets $inst
  replace_cell $name $replacement
  incr modified
  puts "Incremental electrical ECO: $name $expected -> $replacement"
 } elseif {$current!=$replacement} {error "Unexpected cell at $name: $current"}
}
if {$modified>0} {
 source $::env(SCRIPTS_DIR)/openroad/common/dpl.tcl
 foreach inst [$::block getInsts] {
  set name [$inst getName]
  set current [list [$inst getLocation] [$inst getOrient] [[$inst getMaster] getName]]
  if {![dict exists $original $name] || [dict get $original $name]!=$current} {mark_inst_nets $inst}
 }
 dict for {name net} $dirty_nets {
  set wire [$net getWire]
  if {$wire!="NULL"} {odb::dbWire_destroy $wire}
 }
 puts "Incremental ECO: rerouting [dict size $dirty_nets] changed nets"
 source $::env(SCRIPTS_DIR)/openroad/common/set_rc.tcl
 source $::env(SCRIPTS_DIR)/openroad/common/grt.tcl
 estimate_parasitics -global_routing
}
write_metric_int "design__postroute_fanout_splits" $modified
puts "Post-route electrical cells changed: $modified"
write_views
