# Repair extracted electrical hotspots; final fanout limit remains 10.
source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
read_current_odb
set_propagated_clock [all_clocks]
set modified 0
set index 0
foreach net [$::block getNets] {
 if {[$net getSigType] == "POWER" || [$net getSigType] == "GROUND" || [$net getSigType] == "CLOCK"} {continue}
 set name [$net getName]
 if {$name=="clk" || [string match "clknet*" $name] || [string match "cts_fanout*" $name]} {continue}
 set loads {}
 foreach pin [$net getITerms] {
  if {[$pin getIoType] != "OUTPUT"} {lappend loads "[[$pin getInst] getName]/[[$pin getMTerm] getName]"}
 }
 if {[llength $loads] <= 10} {continue}
 set loads [lsort $loads]
 puts "Post-route fanout split: [$net getName] loads=[llength $loads]"
 for {set start 0} {$start<[llength $loads]} {incr start 4} {
  set group [lrange $loads $start [expr {$start+3}]]
  set sx 0.0;set sy 0.0
  foreach name $group {
   lassign [split $name /] inst_name term_name
   set pin [[$::block findInst $inst_name] findITerm $term_name]
   set xy [$pin getAvgXY];set sx [expr {$sx+[lindex $xy end-1]}];set sy [expr {$sy+[lindex $xy end]}]
  }
  set denom [expr {[llength $group]*[$::block getDbUnitsPerMicron]}]
  set location [list [expr {$sx/$denom}] [expr {$sy/$denom}]]
  while {[$::block findInst post_eco_buf_$index] != "NULL"} {incr index}
  insert_buffer -buffer_cell sky130_fd_sc_hd__buf_8 -load_pins [get_pins $group] -location $location -buffer_name post_eco_buf_$index -net_name post_eco_net_$index
  incr index;incr modified
 }
}
# Sizing verified against the parent extracted slow-corner SPEF.
foreach {name expected replacement} {
 _06045_ sky130_fd_sc_hd__mux2_1 sky130_fd_sc_hd__mux2_4
 _06096_ sky130_fd_sc_hd__mux2_1 sky130_fd_sc_hd__mux2_4
 hold2667 sky130_fd_sc_hd__dlygate4sd3_1 sky130_fd_sc_hd__clkdlybuf4s50_2
} {
 set inst [$::block findInst $name]
 if {$inst=="NULL"} {error "Expected electrical hotspot missing: $name"}
 set current [[$inst getMaster] getName]
 if {$current==$expected} {
  replace_cell $name $replacement
  incr modified
  puts "Extracted electrical ECO: $name $expected -> $replacement"
 } elseif {$current!=$replacement} {error "Unexpected cell at $name: $current"}
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
write_metric_int "design__postroute_fanout_splits" $modified
puts "Post-route buffers inserted: $modified"
write_views
