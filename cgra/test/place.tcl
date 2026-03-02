# ─────────────────────────────────────────────
# Project Creation
# ─────────────────────────────────────────────
create_project cgra_proj ./cgra_proj -part xczu9eg-ffvb1156-2-e -force

# Read CGRA RTL source
add_files -norecurse STEP_CgraRTL__04893b29c6460e2a__pickled.v
set_property file_type SystemVerilog [get_files *.v]

# ─────────────────────────────────────────────
# Create & open Block Design
# ─────────────────────────────────────────────
create_bd_design "cgra_system"
open_bd_design   "cgra_system"

# ─────────────────────────────────────────────
# Instantiate IPs  (use real IP version numbers)
# ─────────────────────────────────────────────

# AXI DMA  (MM2S = memory→stream, S2MM = stream→memory)
create_ip -name axi_dma \
          -vendor xilinx.com -library ip -version 7.1 \
          -module_name dma_mm2s_s2mm

set_property -dict {
    CONFIG.c_include_mm2s          1
    CONFIG.c_include_s2mm          1
    CONFIG.c_m_axi_mm2s_data_width 64
    CONFIG.c_m_axis_mm2s_tdata_width 64
    CONFIG.c_s_axis_s2mm_tdata_width 64
    CONFIG.c_m_axi_s2mm_data_width 64
} [get_ips dma_mm2s_s2mm]

# ── Input width converter  (DMA 64-bit → CGRA 256-bit) ─────────────────────
#    Correct IP: axis_dwidth_converter, NOT axis_data_fifo
create_ip -name axis_dwidth_converter \
          -vendor xilinx.com -library ip -version 1.1 \
          -module_name axis_dwidth_in

set_property -dict {
    CONFIG.S_TDATA_NUM_BYTES  8
    CONFIG.M_TDATA_NUM_BYTES 32
} [get_ips axis_dwidth_in]

# ── Output width converter (CGRA 256-bit → DMA 64-bit) ─────────────────────
create_ip -name axis_dwidth_converter \
          -vendor xilinx.com -library ip -version 1.1 \
          -module_name axis_dwidth_out

set_property -dict {
    CONFIG.S_TDATA_NUM_BYTES 32
    CONFIG.M_TDATA_NUM_BYTES  8
} [get_ips axis_dwidth_out]

# ─────────────────────────────────────────────
# Add IP instances to block design
# ─────────────────────────────────────────────
create_bd_cell -type ip -vlnv xilinx.com:ip:axi_dma:7.1            dma_mm2s_s2mm
create_bd_cell -type ip -vlnv xilinx.com:ip:axis_dwidth_converter:1.1 axis_dwidth_in
create_bd_cell -type ip -vlnv xilinx.com:ip:axis_dwidth_converter:1.1 axis_dwidth_out

# Add CGRA RTL module as a block design cell
create_bd_cell -type module -reference STEP_CgraRTL__04893b29c6460e2a cgra_0

# ─────────────────────────────────────────────
# Clock & Reset ports on the block design
# ─────────────────────────────────────────────
create_bd_port -dir I -type clk  clk
create_bd_port -dir I -type rst  resetn   ;# active-low for AXI IPs
create_bd_port -dir I -type rst  reset    ;# active-high for CGRA

# ─────────────────────────────────────────────
# AXI-Stream connections  (single, canonical set)
# ─────────────────────────────────────────────

# Input path:  DMA MM2S → width-up converter → CGRA receive port
connect_bd_intf_net \
    [get_bd_intf_pins dma_mm2s_s2mm/M_AXIS_MM2S] \
    [get_bd_intf_pins axis_dwidth_in/S_AXIS]

connect_bd_intf_net \
    [get_bd_intf_pins axis_dwidth_in/M_AXIS] \
    [get_bd_intf_pins cgra_0/recv_from_cpu_bitstream_pkt]

# Output path: CGRA send port → width-down converter → DMA S2MM
connect_bd_intf_net \
    [get_bd_intf_pins cgra_0/send_to_cpu_metadata_pkt] \
    [get_bd_intf_pins axis_dwidth_out/S_AXIS]

connect_bd_intf_net \
    [get_bd_intf_pins axis_dwidth_out/M_AXIS] \
    [get_bd_intf_pins dma_mm2s_s2mm/S_AXIS_S2MM]

# ─────────────────────────────────────────────
# Clock connections  (one canonical set)
# ─────────────────────────────────────────────
connect_bd_net [get_bd_ports clk] [get_bd_pins dma_mm2s_s2mm/m_axi_mm2s_aclk]
connect_bd_net [get_bd_ports clk] [get_bd_pins dma_mm2s_s2mm/m_axi_s2mm_aclk]
connect_bd_net [get_bd_ports clk] [get_bd_pins dma_mm2s_s2mm/s_axi_lite_aclk]
connect_bd_net [get_bd_ports clk] [get_bd_pins axis_dwidth_in/aclk]
connect_bd_net [get_bd_ports clk] [get_bd_pins axis_dwidth_out/aclk]
connect_bd_net [get_bd_ports clk] [get_bd_pins cgra_0/clk]

# ─────────────────────────────────────────────
# Reset connections
# ─────────────────────────────────────────────
# AXI/AXIS IPs expect active-low synchronous reset
connect_bd_net [get_bd_ports resetn] [get_bd_pins dma_mm2s_s2mm/axi_resetn]
connect_bd_net [get_bd_ports resetn] [get_bd_pins axis_dwidth_in/aresetn]
connect_bd_net [get_bd_ports resetn] [get_bd_pins axis_dwidth_out/aresetn]
# CGRA expects active-high reset
connect_bd_net [get_bd_ports reset]  [get_bd_pins cgra_0/reset]

# ─────────────────────────────────────────────
# Validate, generate, and save block design
# ─────────────────────────────────────────────
validate_bd_design
generate_target all [get_bd_designs cgra_system]
save_bd_design

# ─────────────────────────────────────────────
# Generate IP output products
# ─────────────────────────────────────────────
generate_target all [get_ips *]

# ─────────────────────────────────────────────
# Synthesis → Implementation → Bitstream
# ─────────────────────────────────────────────
launch_runs synth_1 -jobs 8
wait_on_run synth_1

launch_runs impl_1 -to_step write_bitstream -jobs 8
wait_on_run impl_1

report_utilization    -file util_report.rpt
report_timing_summary -file timing_report.rpt

exit


#### Original Below
#read_verilog -sv STEP_CgraRTL__04893b29c6460e2a__pickled.v
#read_xdc constraints.xdc

#synth_design -top STEP_CgraRTL__04893b29c6460e2a -part xczu9eg-ffvb1156-2-e

#opt_design
#place_design

#report_utilization -file util_place.rpt
#report_timing_summary -file timing_place.rpt

#exit