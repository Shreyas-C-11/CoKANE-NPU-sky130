# Repair clock fanout by topology, not by generated instance identity.
source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
read_current_odb
set_propagated_clock [all_clocks]
set inserted 0
set serial 0
for {set pass 0} {$pass<8} {incr pass} {
 set modified 0
 foreach net [$::block getNets] {
  set name [$net getName]
  if {[$net getSigType]!="CLOCK" && $name!="clk" && ![string match "clknet*" $name] && ![string match "signoff_clock_net*" $name]} {continue}
  set loads {}
  foreach pin [$net getITerms] {
   if {[$pin getIoType]=="INPUT"} {lappend loads "[[$pin getInst] getName]/[[$pin getMTerm] getName]"}
  }
  if {[llength $loads]<=8} {continue}
  puts "Clock split: $name loads=[llength $loads]"
  set loads [lsort $loads]
  for {set start 0} {$start<[llength $loads]} {incr start 4} {
   set group [lrange $loads $start [expr {$start+3}]]
   set sx 0.0;set sy 0.0
   foreach path $group {
    set slash [string last / $path]
    set inst_name [string range $path 0 [expr {$slash-1}]]
    set pin_name [string range $path [expr {$slash+1}] end]
    set pin [[$::block findInst $inst_name] findITerm $pin_name]
    set xy [$pin getAvgXY]
    set sx [expr {$sx+[lindex $xy end-1]}];set sy [expr {$sy+[lindex $xy end]}]
   }
   set denom [expr {[llength $group]*[$::block getDbUnitsPerMicron]}]
   while {[$::block findInst signoff_clock_buf_$serial]!="NULL"} {incr serial}
   insert_buffer -buffer_cell sky130_fd_sc_hd__clkbuf_8 -load_pins [get_pins $group] -location [list [expr {$sx/$denom}] [expr {$sy/$denom}]] -buffer_name signoff_clock_buf_$serial -net_name signoff_clock_net_$serial
   incr serial;incr inserted;incr modified
  }
 }
 if {$modified==0} {break}
}
if {$inserted>0} {source $::env(SCRIPTS_DIR)/openroad/common/dpl.tcl}
source $::env(SCRIPTS_DIR)/openroad/common/set_rc.tcl
estimate_parasitics -placement
write_metric_int "design__signoff_clock_buffers" $inserted
write_views
