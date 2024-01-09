# disclaimer: All the values given here are just for illustrative purpose
# Change all the path according to your run directory
# Please go through the file before sourcing it
# Try to run all the command one by one at least for the first time

# Multicore Usage
set_host_options -max_cores 8

# library directory
set search_path [list "/cad/GF/arm/gf/14lppxl/sc9mcpp84_base_rvt_c14/r0p0/db/" ]
set target_library "sc9mcpp84_14lppxl_base_rvt_c14_nn_nominal_max_0p80v_25c.db"
set synthetic_library "/cad/synopsys/syn/O-2018.06-SP4/libraries/syn/dw_foundation.sldb"
set link_library "* $target_library $synthetic_library"

#set search_path [list "/cad/asap7/asap7libs_24/lib/" ]
#set target_library "asap7sc7p5t_24_AO_RVT_TT.db asap7sc7p5t_24_OA_RVT_TT.db asap7sc7p5t_24_SIMPLE_RVT_TT.db asap7sc7p5t_24_INVBUF_RVT_TT.db asap7sc7p5t_24_SEQ_RVT_TT.db"
#set synthetic_library "/cad/synopsys/syn/O-2018.06-SP4/libraries/syn/dw_foundation.sldb"
#set link_library "* $target_library $synthetic_library"



# #################################CHANGE THIS###################################################
# TOP_LEVEL_NAME
set top_level "FPadd_plain"
# PATH TO YOUR VERILOG NETLIST
set netlist_search_path "../"
# NETLIST NAME
set netlist_name "FPadd.sv"
# CLOCK PERIOD
set clk_period 5000
# 290
# ################################################################################################

# Read verilog files
#analyze -format sverilog $netlist_search_path/$netlist_name
analyze {../} -autoread -recursive -format sverilog -top $top_level
#analyze -format verilog $netlist_search_path/counter.sv

elaborate $top_level
list_designs
current_design $top_level

#Create real clock if clock port is found
if {[sizeof_collection [get_ports clk]] > 0} {
  set clk_name "clk"
  set clk_port "clk"
  #If no waveform is specified, 50% duty cycle is assumed
  create_clock -name $clk_name -period $clk_period [get_ports $clk_port] 
  set_drive 0 [get_clocks $clk_name] 
}

set_clock_uncertainty 0.01 [get_clocks $clk_name]
set_clock_transition 0.1 [get_clocks $clk_name]

set_wire_load_mode "segmented" 

set typical_input_delay 30
set typical_output_delay 30
set typical_wire_load 0.010 

# Set maximum fanout of gates
set_max_fanout 16 $top_level 

# Configure the clock network
set_fix_hold [all_clocks] 
set_dont_touch_network $clk_port 

set_driving_cell -lib_cell INV_X3R_A9PP84TR_C14 [all_inputs]
#set_driving_cell -lib_cell INVx3_ASAP7_75t_R [all_inputs]
set_input_delay $typical_input_delay [all_inputs] -clock $clk_name 
remove_input_delay -clock $clk_name [find port $clk_port]
set_output_delay $typical_output_delay [all_outputs] -clock $clk_name 

# Set loading of outputs 
set_load $typical_wire_load [all_outputs] 

# Verify the design
check_design

# Synthesize the design
compile_ultra

optimize_netlist -area

# Rename modules, signals according to the naming rules Used for tool exchange
define_name_rules asu_naming_rules -allowed {a-zA-Z0-9_} -max_length 256 -reserved_words [list "always" "and" "assign" "begin" "buf" "bufif0" "bufif1" "case" "casex" "casez" "cmos" "deassign" "default" "defparam" "disable" "edge" "else" "end" "endcase" "endfunction" "endmodule" "endprimitive" "endspecify" "endtable" "endtask" "event" "for" "force" "forever" "fork" "function" "highz0" "highz1" "if" "initial" "inout" "input" "integer" "join" "large" "macromodule" "medium" "module" "nand" "negedge" "nmos" "nor" "not" "notif0" "notif1" "or" "output" "pmos" "posedge" "primitive" "pull0" "pull1" "pulldown" "pullup" "rcmos" "reg" "release" "repeat" "rnmos" "rpmos" "rtran" "rtranif0" "rtranif1" "scalered" "small" "specify" "specparam" "strong0" "strong1" "supply0" "supply1" "table" "task" "time" "tran" "tranif0" "tranif1" "tri" "tri0" "tri1" "triand" "trior" "vectored" "wait" "wand" "weak0" "weak1" "while" "wire" "wor" "xnor" "xor" "abs" "access" "after" "alias" "all" "and" "architecture" "array" "assert" "attribute" "begin" "block" "body" "buffer" "bus" "case" "component" "configuration" "constant" "disconnect" "downto" "else" "elsif" "end" "entity" "exit" "file" "for" "function" "generate" "generic" "guarded" "if" "in" "inout" "is" "label" "library" "linkage" "loop" "map" "mod" "nand" "new" "next" "nor" "not" "null" "of" "on" "open" "or" "others" "out" "package" "port" "procedure" "process" "range" "record" "register" "rem" "report" "return" "select" "severity" "signal" "subtype" "then" "to" "transport" "type" "units" "until" "use" "variable" "wait" "when" "while" "with" "xor"] -case_insensitive -last_restricted "_" -first_restricted "_" -map {{{"*cell*","U"}, {"*-return","RET"}}} -collapse_name_space -equal_ports_nets -inout_ports_equal_nets
#change_names -rules asu_naming_rules -verbose -hierarchy
change_names -rules asu_naming_rules -hierarchy

# Generate structural verilog netlist
write_file -hierarchy -format verilog -output "./${top_level}.${clk_period}.syn.v"
# Save current design
#TODO write_file -hierarchy -format ddc -output "./${top_level}.ddc"

# Generate Standard Delay Format (SDF) file
#TODO write_sdf -context verilog "./${top_level}.${clk_period}.syn.sdf"

# Generate timing constraints file
write_sdc "./${top_level}.${clk_period}.syn.sdc"

# Generate report file
set maxpaths 5
#set minpaths 100
set rpt_file "./${top_level}.${clk_period}.syn"

#TODO check_design > ${rpt_file}.rpt
report_area -hierarchy -designware > ${rpt_file}_area.rpt
report_power -hier -analysis_effort medium > ${rpt_file}_power.rpt
#TODO report_design > ${rpt_file}.rpt
#TODO report_cell > ${rpt_file}.rpt
#TODO report_port -verbose > ${rpt_file}.rpt
#TODO report_compile_options > ${rpt_file}.rpt
#TODO report_constraint -all_violators -verbose > ${rpt_file}_violaters.rpt
report_timing -path full -delay max -max_paths $maxpaths -nworst 5 > ${rpt_file}_timing.rpt

# Exit dc_shell
quit

