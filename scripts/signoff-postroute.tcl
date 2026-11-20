# Extracted r2 closure: cell substitution only; preserve the frozen logic.
source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
read_current_odb
set_propagated_clock [all_clocks]
set before [dict create]
foreach inst [$::block getInsts] {
 dict set before [$inst getName] [list [$inst getLocation] [$inst getOrient] [[$inst getMaster] getName]]
}
set affected [dict create]
proc mark_inst_nets {inst} {
 global affected
 foreach pin [$inst getITerms] {
  set net [$pin getNet]
  if {$net!="NULL" && [$net getSigType]!="POWER" && [$net getSigType]!="GROUND"} {dict set affected [$net getName] 1}
 }
}
set modified 0
foreach {name old new} {
 clkbuf_0_clk sky130_fd_sc_hd__clkbuf_16 sky130_fd_sc_hd__clkbuf_8
 hold5664 sky130_fd_sc_hd__dlygate4sd3_1 sky130_fd_sc_hd__clkdlybuf4s25_2
} {
 set inst [$::block findInst $name]
 if {$inst=="NULL"} {error "Missing ECO instance $name"}
 set master [[$inst getMaster] getName]
 if {$master==$old || ($name=="hold5664" && $master=="sky130_fd_sc_hd__clkdlybuf4s50_2")} {
  mark_inst_nets $inst
  replace_cell $name $new
  mark_inst_nets $inst
  incr modified
  puts "Extracted closure: $name $old -> $new"
 } elseif {$master!=$new} {error "Unexpected master $name $master"}
}
if {$modified>0} {
 source $::env(SCRIPTS_DIR)/openroad/common/dpl.tcl
 foreach inst [$::block getInsts] {
  set name [$inst getName]
  set after [list [$inst getLocation] [$inst getOrient] [[$inst getMaster] getName]]
  if {![dict exists $before $name] || [dict get $before $name]!=$after} {mark_inst_nets $inst}
 }
 dict for {name flag} $affected {
  set net [$::block findNet $name]
  set wire [$net getWire]
  if {$wire!="NULL"} {odb::dbWire_destroy $wire}
 }
 puts "Affected signal nets rerouted: [dict size $affected]"
 source $::env(SCRIPTS_DIR)/openroad/common/set_rc.tcl
 source $::env(SCRIPTS_DIR)/openroad/common/grt.tcl
 estimate_parasitics -global_routing
}
write_metric_int "design__signoff_postroute_repairs" $modified
write_views
