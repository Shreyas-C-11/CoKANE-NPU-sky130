# Split an over-fanout CTS root into groups of four using identical clock buffers.
# Electrical limits remain unchanged; downstream STA and LVS must verify the result.
source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
read_current_odb
set_propagated_clock [all_clocks]
set root [$::block findInst clkbuf_0_clk]
if {$root == "NULL"} {error "Expected CTS clock root not found"}
set root_pin [$root findITerm X]
set root_net [$root_pin getNet]
set loads {}
foreach pin [$root_net getITerms] {
 if {[$pin getIoType] == "INPUT"} {
  lappend loads "[[$pin getInst] getName]/[[$pin getMTerm] getName]"
 }
}
set loads [lsort $loads]
puts "Clock root load count before repair: [llength $loads]"
if {[llength $loads] > 10} {
 set idx 0
 for {set start 0} {$start < [llength $loads]} {incr start 4} {
  set group [lrange $loads $start [expr {$start+3}]]
  set sx 0.0; set sy 0.0
  foreach name $group {
   lassign [split $name /] inst_name term_name
   set iterm [[$::block findInst $inst_name] findITerm $term_name]
   set xy [$iterm getAvgXY]
   set sx [expr {$sx+[lindex $xy end-1]}]
   set sy [expr {$sy+[lindex $xy end]}]
  }
  set denom [expr {[llength $group]*[$::block getDbUnitsPerMicron]}]
  set location [list [expr {$sx/$denom}] [expr {$sy/$denom}]]
  insert_buffer -buffer_cell sky130_fd_sc_hd__clkbuf_8 -load_pins [get_pins $group] -location $location -buffer_name cts_fanout_split_$idx -net_name cts_fanout_split_net_$idx
  incr idx
 }
 source $::env(SCRIPTS_DIR)/openroad/common/dpl.tcl
}
set count 0
foreach pin [$root_net getITerms] {if {[$pin getIoType] == "INPUT"} {incr count}}
puts "Clock root load count after repair: $count"
if {$count>10} {error "Clock root fanout remains above 10"}
source $::env(SCRIPTS_DIR)/openroad/common/set_rc.tcl
estimate_parasitics -placement
write_views
