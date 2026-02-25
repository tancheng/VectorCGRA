`timescale 1ps/1ps

`include "header_fir_vector_global_reduce.sv"

// vcs -sverilog -full64 -timescale=1ns/1ps ../../MeshMultiCgraRTL__explicit_vector_global_reduce__pickled.v ../MeshMultiCgraRTL_2x2_fir_vector_global_reduce_tb.v -debug_access+all +incdir+..
// vcs -sverilog -full64 -timescale=1ns/1ps ../../../../../coredec_acc_soc/accelerator_soc/MeshMultiCgraRTL__explicit_vector_global_reduce__pickled.v ../MeshMultiCgraRTL_2x2_fir_vector_global_reduce_tb.v -debug_access+all +incdir+..

module cgra_test
(
);

  logic [0:0] clk;
  logic [0:0] reset;

  IntraCgraPacket_4_2x2_16_8_2_CgraPayload__176d07e92dff4e44 recv_from_cpu_pkt__msg;
  logic [0:0] recv_from_cpu_pkt__rdy;
  logic [0:0] recv_from_cpu_pkt__val;

  IntraCgraPacket_4_2x2_16_8_2_CgraPayload__176d07e92dff4e44 send_to_cpu_pkt__msg;
  logic [0:0] send_to_cpu_pkt__rdy;
  logic [0:0] send_to_cpu_pkt__val;

  MeshMultiCgraRTL__explicit_vector_global_reduce MultiCGRA (.*);

  int  PASS         = 'd0;
  time pass_time_of = 'd0;

  initial
  begin
    $display("\nTEST begin\n");

    clk = 1'b0;
    recv_from_cpu_pkt__val = 1'b0;
    send_to_cpu_pkt__rdy   = 1'b1;

    reset = 1'b0;
    #7
    reset = 1'b1;
    #50
    reset = 1'b0;
    #10
/*
typedef struct packed {
  logic [4:0] src;
  logic [4:0] dst;
  logic [1:0] src_cgra_id;
  logic [1:0] dst_cgra_id;
  logic [0:0] src_cgra_x;
  logic [0:0] src_cgra_y;
  logic [0:0] dst_cgra_x;
  logic [0:0] dst_cgra_y;
  logic [7:0] opaque;
  logic [0:0] vc_id;
  MultiCgraPayload_Cmd_Data_DataAddr_Ctrl_CtrlAddr__d9140faa89010e06 payload;
} IntraCgraPacket_4_2x2_16_8_2_CgraPayload__377cfca417046add;
*/
/*
typedef struct packed {
  logic [5:0] cmd;
  CgraData_32_1_1_1__payload_32__predicate_1__bypass_1__delay_1 data;
  logic [6:0] data_addr;
  CGRAConfig_7_4_2_4_4_3__49d22cda396bec88 ctrl;
  logic [3:0] ctrl_addr;
} MultiCgraPayload_Cmd_Data_DataAddr_Ctrl_CtrlAddr__d9140faa89010e06;
*/
/*
typedef struct packed {
  logic [63:0] payload;
  logic [0:0] predicate;
  logic [0:0] bypass;
  logic [0:0] delay;
} CgraData_64_1_1_1__payload_64__predicate_1__bypass_1__delay_1;
*/
/*
typedef struct packed {
  logic [6:0] operation;
  logic [3:0][2:0] fu_in;
  logic [7:0][2:0] routing_xbar_outport;
  logic [7:0][1:0] fu_xbar_outport;
  logic [2:0] vector_factor_power;
  logic [0:0] is_last_ctrl;
  logic [3:0][1:0] write_reg_from;
  logic [3:0][3:0] write_reg_idx;
  logic [3:0][0:0] read_reg_from;
  logic [3:0][3:0] read_reg_idx;
} CGRAConfig_7_4_2_4_4_3__49d22cda396bec88;
*/

    #10
    recv_from_cpu_pkt__val = 1'b1;
    recv_from_cpu_pkt__msg = unpack_pkt('h0000000180002000200020003000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0000000180002000200020003008000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h000000018001e001c001a0019010000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0000000180026002400220021018000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h00000001800220020001e001d020000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h000000018002a002800260025028000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0000000180002000200020003030000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h00000001a0000000000000007000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0000000100000000000000009000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h00000000e000000000000004d000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0000000060000000000000000004e8d100100001400020000200000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h000000006000000000000000000208d100000004000080000100001);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h000000006000000000000000000018d100000000000000000000002);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h000000006000000000000000000018d100000000000000000000003);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0000000220000000000000005000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0000000080000000000000003000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h00000000c0000000000000003000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h00000000a0000000000000003000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0000000000000000000000000000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0008000100000000000000009000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h00080000e000000000000004d000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h000800006000000000000000000018d100000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h000800006000000000000000000108d100b00001000020000000001);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h000800006000000000000000000238d100000000000000000100002);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h000800006000000000000000000018d100000000000000000000003);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0008000080000000000000003000000000000000000000000000001);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0008000080000000000000003000000000000000000000000000002);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h00080000c0000000000000003000000000000000000000000000001);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h00080000c0000000000000003000000000000200000000000000001);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h00080000a0000000000000003000000000000000000000000000001);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0008000000000000000000000000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h00200001a0000000000000005000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0020000100000000000000009000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h00200000e000000000000004d000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h002000006000000000000000000018d100000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h002000006000000000000000000198d100100001000020000000001);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0020000060000000000000000000c8d100000004000080000100002);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h002000006000000000000000000378d100100000040000000200003);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0020000000000000000000000000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h00280001a0000000000000009000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0028000100000000000000009000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h00280000e000000000000004d000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h002800006000000000000000000018d100000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h002800006000000000000000000018d100000000000000000000001);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0028000060000000000000000002e8d100100001010020000000002);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0028000060000000000000000000b8d100000000040000000100003);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0028000000000000000000000000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h00400001a0000000000000005000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h00400001a0000000000000001000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0040000100000000000000009000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h00400000e000000000000004d000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h004000006000000000000000000208d100400001440020000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h004000006000000000000000000198d100000004000080000100001);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0040000060000000000000000000c00200000000040000000200002);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h004000006000000000000000000018d100000000000000000000003);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h00400000c0000000000000003000000000000300000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0040000000000000000000000000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h00480001a0000000000000003000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0048000100000000000000009000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h00480000e000000000000004d000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h004800006000000000000000000018d100000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h004800006000000000000000000198d100300004040080000000001);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h004800006000000000000000000018d100000000000000000000002);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0048000060000000000000000001000a00200000100000000200003);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0048000000000000000000000000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h00009001a0000000000000007000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0000900100000000000000009000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h00009000e000000000000004d000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0000900060000000000000000004e8d100100001400020000200000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h000090006000000000000000000208d100000004000080000100001);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h000090006000000000000000000018d100000000000000000000002);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h000090006000000000000000000018d100000000000000000000003);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0000900080000000000000003000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h00009000c0000000000000003000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h00009000a0000000000000003000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0000900000000000000000000000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0008900100000000000000009000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h00089000e000000000000004d000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h000890006000000000000000000018d100000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h000890006000000000000000000108d100b00001000020000000001);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h000890006000000000000000000238d100000000000000000100002);
    #10 // Might need to send this twice if CGRA is really not rdy.
    recv_from_cpu_pkt__msg = unpack_pkt('h000890006000000000000000000018d100000000000000000000003);
    #10 // Second send.
    recv_from_cpu_pkt__msg = unpack_pkt('h000890006000000000000000000018d100000000000000000000003, 0);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0008900080000000000000003000000000000000000000000000001);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0008900080000000000000003000000000000000000000000000002);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h00089000c0000000000000003000000000000000000000000000001);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h00089000c0000000000000003000000000000200000000000000001);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h00089000a0000000000000003000000000000000000000000000001);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0008900000000000000000000000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h00209001a0000000000000005000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0020900100000000000000009000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h00209000e000000000000004d000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h002090006000000000000000000018d100000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h002090006000000000000000000198d100100001000020000000001);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0020900060000000000000000000c8d100000004000080000100002);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h002090006000000000000000000378d100100000040000000200003);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0020900000000000000000000000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h00289001a0000000000000009000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0028900100000000000000009000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h00289000e000000000000004d000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h002890006000000000000000000018d100000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h002890006000000000000000000018d100000000000000000000001);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0028900060000000000000000002e8d100100001010020000000002);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0028900060000000000000000000b8d100000000040000000100003);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0028900000000000000000000000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h00409001a0000000000000005000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h00409001a0000000000000001000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0040900100000000000000009000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h00409000e000000000000004d000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h004090006000000000000000000208d100400001440020000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h004090006000000000000000000198d100000004000080000100001);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0040900060000000000000000000c00200000000040000000200002);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h004090006000000000000000000018d100000000000000000000003);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h00409000c0000000000000003000000000000300000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0040900000000000000000000000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h00489001a0000000000000003000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0048900100000000000000009000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h00489000e000000000000004d000000000000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h004890006000000000000000000018d100000000000000000000000);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h004890006000000000000000000198d100300004040080000000001);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h004890006000000000000000000018d100000000000000000000002);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0048900060000000000000000001000a00200000100000000200003);
    #10
    recv_from_cpu_pkt__msg = unpack_pkt('h0048900000000000000000000000000000000000000000000000000);

    #10
    recv_from_cpu_pkt__val = 0;

    #10000

    if ('d1 == PASS) $display("TEST PASSED at %0t.", pass_time_of);
    else             $display("TEST FAILED at %0t.", $time);

    $display("%d", unpack_pkt('h01800001c000000000000229700238d100000000000000000100000, 0).payload.data.payload);

    $display("#########cgra 0 tile 0 cnst mem#################");
    for (int i = 0; i < 512; i++)
    begin
      if ( !$isunknown(MultiCGRA.cgra__0.tile__0.const_mem.reg_file.regs[i]) )
        $display("cgra0tile0cnst %d %d %d (%d)", i, MultiCGRA.cgra__0.tile__0.const_mem.reg_file.regs[i].payload, MultiCGRA.cgra__0.tile__0.const_mem.reg_file.regs[i].predicate, MultiCGRA.cgra__0.tile__0.const_mem.reg_file.regs[i]);
    end
    $display("##########################");
    for (int i = 0; i < 512; i++)
    begin
      if ( !$isunknown(MultiCGRA.cgra__0.tile__1.const_mem.reg_file.regs[i]) )
        $display("cgra0tile1cnst %d %d", i, MultiCGRA.cgra__0.tile__1.const_mem.reg_file.regs[i]);
    end
    $display("##########################");
    for (int i = 0; i < 512; i++)
    begin
      if ( !$isunknown(MultiCGRA.cgra__0.tile__4.const_mem.reg_file.regs[i]) )
        $display("cgra0tile4cnst %d %d", i, MultiCGRA.cgra__0.tile__4.const_mem.reg_file.regs[i]);
    end
    $display("##########################");
    for (int i = 0; i < 512; i++)
    begin
      if ( !$isunknown(MultiCGRA.cgra__0.tile__5.const_mem.reg_file.regs[i]) )
        $display("cgra0tile5cnst %d %d", i, MultiCGRA.cgra__0.tile__5.const_mem.reg_file.regs[i]);
    end
    $display("##########################");
    for (int i = 0; i < 512; i++)
    begin
      if ( !$isunknown(MultiCGRA.cgra__0.tile__8.const_mem.reg_file.regs[i]) )
        $display("cgra0tile8cnst %d %d", i, MultiCGRA.cgra__0.tile__8.const_mem.reg_file.regs[i]);
    end
    $display("##########################");
    for (int i = 0; i < 512; i++)
    begin
      if ( !$isunknown(MultiCGRA.cgra__0.tile__9.const_mem.reg_file.regs[i]) )
        $display("cgra0tile9cnst %d %d", i, MultiCGRA.cgra__0.tile__9.const_mem.reg_file.regs[i]);
    end

    $display("********cgra 0 ctrl mem******************");
    for (int i = 0; i < 512; i++)
    begin
      if ( !$isunknown(MultiCGRA.cgra__0.tile__0.ctrl_mem.reg_file.regs[i]) )
        $display("cgra0tile0ctrl %d %d", i, MultiCGRA.cgra__0.tile__0.ctrl_mem.reg_file.regs[i]);
    end
    $display("##########################");
    for (int i = 0; i < 512; i++)
    begin
      if ( !$isunknown(MultiCGRA.cgra__0.tile__1.ctrl_mem.reg_file.regs[i]) )
        $display("cgra0tile1ctrl %d %d", i, MultiCGRA.cgra__0.tile__1.ctrl_mem.reg_file.regs[i]);
    end
    $display("##########################");
    for (int i = 0; i < 512; i++)
    begin
      if ( !$isunknown(MultiCGRA.cgra__0.tile__4.ctrl_mem.reg_file.regs[i]) )
        $display("cgra0tile4ctrl %d %d", i, MultiCGRA.cgra__0.tile__4.ctrl_mem.reg_file.regs[i]);
    end
    $display("##########################");
    for (int i = 0; i < 512; i++)
    begin
      if ( !$isunknown(MultiCGRA.cgra__0.tile__5.ctrl_mem.reg_file.regs[i]) )
        $display("cgra0tile5ctrl %d %d", i, MultiCGRA.cgra__0.tile__5.ctrl_mem.reg_file.regs[i]);
    end
    $display("##########################");
    for (int i = 0; i < 512; i++)
    begin
      if ( !$isunknown(MultiCGRA.cgra__0.tile__8.ctrl_mem.reg_file.regs[i]) )
        $display("cgra0tile8ctrl %d %d", i, MultiCGRA.cgra__0.tile__8.ctrl_mem.reg_file.regs[i]);
    end
    $display("##########################");
    for (int i = 0; i < 512; i++)
    begin
      if ( !$isunknown(MultiCGRA.cgra__0.tile__9.ctrl_mem.reg_file.regs[i]) )
        $display("cgra0tile9ctrl %d %d", i, MultiCGRA.cgra__0.tile__9.ctrl_mem.reg_file.regs[i]);
    end

    $display("*************cgra0 data mem 0*************");
    for (int i = 0; i < 16; i++)
    begin
      if ( !$isunknown(MultiCGRA.cgra__0.data_mem.memory_wrapper__0.memory.regs[i]) )
        $display("cgra0regfile0 (addr 0 init) %d %d (%d)", i, MultiCGRA.cgra__0.data_mem.memory_wrapper__0.memory.regs[i].payload, MultiCGRA.cgra__0.data_mem.memory_wrapper__0.memory.regs[i]);
    end
    $display("#############cgra0 data mem 1#############");
    for (int i = 0; i < 16; i++)
    begin
      if ( !$isunknown(MultiCGRA.cgra__0.data_mem.memory_wrapper__1.memory.regs[i]) )
        $display("cgra0regfile1 (addr 0 init) %d %d", i, MultiCGRA.cgra__0.data_mem.memory_wrapper__1.memory.regs[i]);
    end

    $finish();
  end

  initial
    forever
    begin
      #5
      clk = ~clk;
    end

  always @ (posedge clk or negedge clk)
  begin
    #1

    if ( send_to_cpu_pkt__val && ( ('d2212 * 'd2 + 'd3) == send_to_cpu_pkt__msg.payload.data.payload ) )
    begin
      PASS         = 'd1;
      pass_time_of = $time;
    end
  end

  /*initial
  begin
    $dumpfile("./output.vcd");
    $dumpvars (0, cgra_test);
  end*/
  // The Verilator test fails on these $fsdb* functions; if pragmas do not work, add --bbox-sys to Verilator cmd.
`ifndef VERILATOR
  initial
  begin
    $fsdbDumpfile("./output.fsdb");
    $fsdbDumpvars ("+all", "cgra_test");
    $fsdbDumpMDA;
    $fsdbDumpSVA;
  end
`endif


endmodule

