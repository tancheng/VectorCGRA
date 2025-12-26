`timescale 1ps/1ps

`include "header.sv"

// vcs -sverilog -full64 -timescale=1ns/1ps ../MeshMultiCgraRTL__explicit__pickled.v MeshMultiCgraRTL_2x2_fir_scalar_tb.v -debug_access+all

module cgra_test
(
);

  logic [0:0] clk;
  logic [0:0] reset;

  IntraCgraPacket_4_2x2_16_8_2_CgraPayload__432fde8bfb7da0ed recv_from_cpu_pkt__msg;
  logic [0:0] recv_from_cpu_pkt__rdy;
  logic [0:0] recv_from_cpu_pkt__val;

  IntraCgraPacket_4_2x2_16_8_2_CgraPayload__432fde8bfb7da0ed send_to_cpu_pkt__msg;
  logic [0:0] send_to_cpu_pkt__rdy;
  logic [0:0] send_to_cpu_pkt__val;

  MeshMultiCgraRTL__explicit MultiCGRA (.*);

  int PASS = 'd0;

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
} IntraCgraPacket_4_2x2_16_8_2_CgraPayload__432fde8bfb7da0ed;
*/
/*
typedef struct packed {
  logic [4:0] cmd;
  CgraData_32_1_1_1__payload_32__predicate_1__bypass_1__delay_1 data;
  logic [6:0] data_addr;
  CGRAConfig_7_4_2_4_4_3__49d22cda396bec88 ctrl;
  logic [3:0] ctrl_addr;
} MultiCgraPayload_Cmd_Data_DataAddr_Ctrl_CtrlAddr__d9140faa89010e06;
*/
/*
typedef struct packed {
  logic [31:0] payload;
  logic [0:0] predicate;
  logic [0:0] bypass;
  logic [0:0] delay;
} CgraData_32_1_1_1__payload_32__predicate_1__bypass_1__delay_1;
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

    // Preload data.
    #10 // CMD_STORE_REQUEST/
    recv_from_cpu_pkt__msg = make_intra_cgra_pkt(0, 0, 12, 10, 1, 0, 0);
    recv_from_cpu_pkt__val = 1'b1;
    #10
    recv_from_cpu_pkt__msg = make_intra_cgra_pkt(0, 0, 12, 11, 1, 1, 0);
    #10
    recv_from_cpu_pkt__msg = make_intra_cgra_pkt(0, 0, 12, 12, 1, 2, 0);
    #10
    recv_from_cpu_pkt__msg = make_intra_cgra_pkt(0, 0, 12, 13, 1, 3, 0);
    #10
    recv_from_cpu_pkt__msg = make_intra_cgra_pkt(0, 0, 12, 14, 1, 4, 0);
    #10
    recv_from_cpu_pkt__msg = make_intra_cgra_pkt(0, 0, 12, 15, 1, 5, 0);
    #10
    recv_from_cpu_pkt__msg = make_intra_cgra_pkt(0, 0, 12, 16, 1, 6, 0);
    #10
    recv_from_cpu_pkt__msg = make_intra_cgra_pkt(0, 0, 12, 17, 1, 7, 0);
    #10
    recv_from_cpu_pkt__msg = make_intra_cgra_pkt(0, 0, 12, 18, 1, 8, 0);
    #10
    recv_from_cpu_pkt__msg = make_intra_cgra_pkt(0, 0, 12, 19, 1, 9, 0);
    #10
    recv_from_cpu_pkt__msg = make_intra_cgra_pkt(0, 0, 12, 20, 1, 10, 0);
    #10
    recv_from_cpu_pkt__msg = make_intra_cgra_pkt(0, 0, 12, 21, 1, 11, 0);
    #10
    recv_from_cpu_pkt__msg = make_intra_cgra_pkt(0, 0, 12, 22, 1, 12, 0);
    #10
    recv_from_cpu_pkt__msg = make_intra_cgra_pkt(0, 0, 12, 23, 1, 13, 0);
    #10
    recv_from_cpu_pkt__msg = make_intra_cgra_pkt(0, 0, 12, 24, 1, 14, 0);
    #10
    recv_from_cpu_pkt__msg = make_intra_cgra_pkt(0, 0, 12, 25, 1, 15, 0);

    // Tile 0. 
    #10 // CMD_CONST.
    recv_from_cpu_pkt__msg = make_intra_cgra_pkt(0, 0, 13, 3, 1, 0, 0);
    #10 // CMD_CONFIG_COUNT_PER_ITER.
    recv_from_cpu_pkt__msg = make_intra_cgra_pkt(0, 0,  8, 4, 1, 0, 0);
    #10 // CMD_CONFIG_TOTAL_CTRL_COUNT
    recv_from_cpu_pkt__msg = make_intra_cgra_pkt(0, 0,  7, 'd42, 1, 0, 0);
    #10 // CMD_CONFIG - OPT_ADD.
    recv_from_cpu_pkt__msg = make_intra_cgra_config_pkt(0, 0, 3, 2,
      '{3'd4, 3'd3, 3'd2, 3'd1},
      '{3'd0, 3'd0, 3'd0, 3'd1, 3'd0, 3'd0, 3'd0, 3'd0},
      '{2'd0, 2'd0, 2'd0, 2'd1, 2'd1, 2'd0, 2'd0, 2'd0},
      '{2'd0, 2'd0, 2'd0, 2'd2},
      '{1'd0, 1'd0, 1'd1, 1'd0},
      '{4'd0, 4'd0, 4'd0, 4'd0},
      '{4'd0, 4'd0, 4'd0, 4'd0},
      0);
    #10 // CMD_CONFIG - OPT_PHI_CONST.
    recv_from_cpu_pkt__msg = make_intra_cgra_config_pkt(0, 0, 3, 32,
      '{3'd4, 3'd3, 3'd2, 3'd1},
      '{3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0}, // routing_xbar_outport (TileInType list)
      '{2'd0, 2'd0, 2'd1, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0}, // fu_xbar_outport (FuOutType list)
      '{2'd0, 2'd0, 2'd2, 2'd0},  // write_reg_from (b2(0), b2(2), ...)
      '{1'd0, 1'd0, 1'd0, 1'd1},           // read_reg_from
      '{ default: 4'd0 },           // write_reg_idx (not specified, zeroed)
      '{ default: 4'd0 },           // read_reg_idx  (not specified, zeroed)
      1);                         // ctrl_addr = 1
    #10 // CMD_CONFIG - OPT_NAH.
    recv_from_cpu_pkt__msg = make_intra_cgra_config_pkt(0, 0, 3, 1,
      '{3'd4, 3'd3, 3'd2, 3'd1},
      '{3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0},
      '{2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0},
      '{2'd0, 2'd0, 2'd0, 2'd0},
      '{1'd0, 1'd0, 1'd0, 1'd0},
      '{ default: 4'd0 },
      '{ default: 4'd0 },
      2);
    #10 // CMD_CONFIG - OPT_NAH.
    recv_from_cpu_pkt__msg = make_intra_cgra_config_pkt(0, 0, 3, 1,
      '{3'd4, 3'd3, 3'd2, 3'd1},
      '{3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0},
      '{2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0},
      '{2'd0, 2'd0, 2'd0, 2'd0},
      '{1'd0, 1'd0, 1'd0, 1'd0},
      '{ default: 4'd0 },
      '{ default: 4'd0 },
      3);
    #10 // CMD_CONFIG_PROLOGUE_FU.
    recv_from_cpu_pkt__msg = make_intra_cgra_config_pkt_w_data(0, 0, 4, 0,
      '{3'd0, 3'd0, 3'd0, 3'd0},
      '{3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0},
      '{2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0},
      '{2'd0, 2'd0, 2'd0, 2'd0},
      '{1'd0, 1'd0, 1'd0, 1'd0},
      '{ default: 4'd0 },
      '{ default: 4'd0 },
      0,
      1,
      1,
      0);
    //#10 // CMD_CONFIG_PROLOGUE_FU.
    //recv_from_cpu_pkt__msg = make_intra_cgra_config_pkt_w_data(0, 0, 4, 0,
    //  '{3'd0, 3'd0, 3'd0, 3'd0},
    //  '{3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0},
    //  '{2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0},
    //  '{2'd0, 2'd0, 2'd0, 2'd0},
    //  '{1'd0, 1'd0, 1'd0, 1'd0},
    //  '{ default: 4'd0 },
    //  '{ default: 4'd0 },
    //  1,
    //  1,
    //  1,
    //  0);
    #10 // CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR.
    recv_from_cpu_pkt__msg = make_intra_cgra_config_pkt_w_data(0, 0, 6, 0,
      '{3'd0, 3'd0, 3'd0, 3'd0},
      '{3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0},
      '{2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0},
      '{2'd0, 2'd0, 2'd0, 2'd0},
      '{1'd0, 1'd0, 1'd0, 1'd0},
      '{ default: 4'd0 },
      '{ default: 4'd0 },
      0,
      1,
      1,
      0);
    #10 // CMD_CONFIG_PROLOGUE_FU_CROSSBAR.
    recv_from_cpu_pkt__msg = make_intra_cgra_config_pkt_w_data(0, 0, 5, 0,
      '{3'd0, 3'd0, 3'd0, 3'd0},
      '{3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0},
      '{2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0},
      '{2'd0, 2'd0, 2'd0, 2'd0},
      '{1'd0, 1'd0, 1'd0, 1'd0},
      '{ default: 4'd0 },
      '{ default: 4'd0 },
      0,
      1,
      1,
      0);
    //#10 // CMD_CONFIG_PROLOGUE_FU_CROSSBAR.
    //recv_from_cpu_pkt__msg = make_intra_cgra_config_pkt_w_data(0, 0, 5, 0,
    //  '{3'd0, 3'd0, 3'd0, 3'd0},
    //  '{3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0},
    //  '{2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0},
    //  '{2'd0, 2'd0, 2'd0, 2'd0},
    //  '{1'd0, 1'd0, 1'd0, 1'd0},
    //  '{ default: 4'd0 },
    //  '{ default: 4'd0 },
    //  1,
    //  1,
    //  1,
    //  0);
    #10 // CMD_LAUNCH.
    recv_from_cpu_pkt__msg = make_intra_cgra_config_pkt_w_data(0, 0, 0, 0,
      '{3'd0, 3'd0, 3'd0, 3'd0},
      '{3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0},
      '{2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0},
      '{2'd0, 2'd0, 2'd0, 2'd0},
      '{1'd0, 1'd0, 1'd0, 1'd0},
      '{ default: 4'd0 },
      '{ default: 4'd0 },
      0,
      0,
      0,
      0);

    // Tile 1.
    #10 //CMD_CONFIG_COUNT_PER_ITER
    recv_from_cpu_pkt__msg = make_intra_cgra_config_pkt_w_data(
      .src(5'd0),
      .dst(5'd1),
      .cmd(5'd8),                 // CMD_CONFIG_COUNT_PER_ITER = 8
      .operation(7'd0),
      .fu_in_code('{default:3'd0}),
      .routing_xbar_outport('{default:3'd0}),
      .fu_xbar_outport('{default:2'd0}),
      .write_reg_from('{default:2'd0}),
      .read_reg_from('{default:1'd0}),
      .write_reg_idx('{default:4'd0}),
      .read_reg_idx('{default:4'd0}),
      .ctrl_addr(4'd0),
      .data(32'd4),               // kCtrlCountPerIter = 4
      .pred(1'd1),                // predicate = 1
      .data_addr(7'd0)
    );
    #10
    recv_from_cpu_pkt__msg = make_intra_cgra_config_pkt_w_data(
          .src(5'd0),
          .dst(5'd1),
          .cmd(5'd7),             // CMD_CONFIG_TOTAL_CTRL_COUNT = 7
          .operation(7'd0),
          .fu_in_code('{default:3'd0}),
          .routing_xbar_outport('{default:3'd0}),
          .fu_xbar_outport('{default:2'd0}),
          .write_reg_from('{default:2'd0}),
          .read_reg_from('{default:1'd0}),
          .write_reg_idx('{default:4'd0}),
          .read_reg_idx('{default:4'd0}),
          .ctrl_addr(4'd0),
          .data(32'd42),         // kTotalCtrlSteps = 42
          .pred(1'd1),
          .data_addr(7'd0)
    );
    #10
    recv_from_cpu_pkt__msg = make_intra_cgra_config_pkt_w_data(
          .src(5'd0),
          .dst(5'd1),
          .cmd(5'd3),             // CMD_CONFIG = 3
          .operation(7'd1),       // OPT_NAH 1
          .fu_in_code('{3'd4, 3'd3, 3'd2, 3'd1}),
          .routing_xbar_outport('{default:3'd0}),
          .fu_xbar_outport('{default:2'd0}),
          .write_reg_from('{default:2'd0}),
          .read_reg_from('{default:1'd0}),
          .write_reg_idx('{default:4'd0}),
          .read_reg_idx('{default:4'd0}),
          .ctrl_addr(4'd0),
          .data(32'd0),
          .pred(1'd0),
          .data_addr(7'd0)
    );
    #10
    recv_from_cpu_pkt__msg = make_intra_cgra_config_pkt_w_data(
          .src(5'd0),
          .dst(5'd1),
          .cmd(5'd3),
          .operation(7'd16),       // OPT_GRT_PRED = 16
          .fu_in_code('{3'd4, 3'd3, 3'd2, 3'd1}),
          .routing_xbar_outport('{3'd0, 3'd0, 3'd1, 3'd3, 3'd0, 3'd0, 3'd0, 3'd0}),
          .fu_xbar_outport('{2'd0, 2'd0, 2'd0, 2'd1, 2'd0, 2'd0, 2'd0, 2'd0}),
          .write_reg_from('{2'd0, 2'd0, 2'd0, 2'd2}),
          .read_reg_from('{default:1'd0}),
          .write_reg_idx('{default:4'd0}),
          .read_reg_idx('{default:4'd0}),
          .ctrl_addr(4'd1),
          .data(32'd0),
          .pred(1'd0),
          .data_addr(7'd0)
      );
    #10
    // OPT_RET (OPT_RET = 35)
    recv_from_cpu_pkt__msg = make_intra_cgra_config_pkt_w_data(
          .src(5'd0),
          .dst(5'd1),
          .cmd(5'd3),
          .operation(7'd35),
          .fu_in_code('{3'd4, 3'd3, 3'd2, 3'd1}),
          .routing_xbar_outport('{3'd0,3'd0,3'd0,3'd0,3'd0,3'd0,3'd0,3'd0}),
          .fu_xbar_outport('{2'd0,2'd0,2'd0,2'd0,2'd0,2'd0,2'd0,2'd0}),
          .write_reg_from('{2'd0,2'd0,2'd0,2'd0}),
          .read_reg_from('{1'b0, 1'b0, 1'b0, 1'b1}),
          .write_reg_idx('{4'd0,4'd0,4'd0,4'd0}),
          .read_reg_idx('{4'd0,4'd0,4'd0,4'd0}),
          .ctrl_addr(4'd2),
          .data(32'd0),
          .pred(1'd0),
          .data_addr(7'd0)
      );
    #10
    // NAH again (OPT_NAH = 1)
    recv_from_cpu_pkt__msg = make_intra_cgra_config_pkt_w_data(
          .src(5'd0),
          .dst(5'd1),
          .cmd(5'd3),
          .operation(7'd1),
          .fu_in_code('{3'd4, 3'd3, 3'd2, 3'd1}),
          .routing_xbar_outport('{3'd0,3'd0,3'd0,3'd0,3'd0,3'd0,3'd0,3'd0}),
          .fu_xbar_outport('{2'd0,2'd0,2'd0,2'd0,2'd0,2'd0,2'd0,2'd0}),
          .write_reg_from('{2'd0,2'd0,2'd0,2'd0}),
          .read_reg_from('{1'd0,1'd0,1'd0,1'd0}),
          .write_reg_idx('{4'd0,4'd0,4'd0,4'd0}),
          .read_reg_idx('{4'd0,4'd0,4'd0,4'd0}),
          .ctrl_addr(4'd3),
          .data(32'd0),
          .pred(1'd0),
          .data_addr(7'd0)
      );
    #10
    // CONFIG_PROLOGUE_FU (ctrl_addr = 1)
    recv_from_cpu_pkt__msg = make_intra_cgra_config_pkt_w_data(
          .src(5'd0),
          .dst(5'd1),
          .cmd(5'd4),
          .operation(7'd0),
          .fu_in_code('{default:3'd0}),
          .routing_xbar_outport('{default:3'd0}),
          .fu_xbar_outport('{default:2'd0}),
          .write_reg_from('{default:2'd0}),
          .read_reg_from('{default:1'd0}),
          .write_reg_idx('{default:4'd0}),
          .read_reg_idx('{default:4'd0}),
          .ctrl_addr(4'd1),
          .data(32'd1),
          .pred(1'd1),
          .data_addr(7'd0)
      );
    #10
    // CONFIG_PROLOGUE_FU (ctrl_addr = 2)
    recv_from_cpu_pkt__msg = make_intra_cgra_config_pkt_w_data(
          .src(5'd0),
          .dst(5'd1),
          .cmd(5'd4),
          .operation(7'd0),
          .fu_in_code('{default:3'd0}),
          .routing_xbar_outport('{default:3'd0}),
          .fu_xbar_outport('{default:2'd0}),
          .write_reg_from('{default:2'd0}),
          .read_reg_from('{default:1'd0}),
          .write_reg_idx('{default:4'd0}),
          .read_reg_idx('{default:4'd0}),
          .ctrl_addr(4'd2),
          .data(32'd1),
          .pred(1'd1),
          .data_addr(7'd0)
      );
    #10
    // CONFIG_PROLOGUE_ROUTING_CROSSBAR (all 0)
    recv_from_cpu_pkt__msg = make_intra_cgra_config_pkt_w_data(
          .src(5'd0),
          .dst(5'd1),
          .cmd(5'd6),
          .operation(7'd0),
          .fu_in_code('{default:3'd0}),
          .routing_xbar_outport('{3'd0,3'd0,3'd0,3'd0,3'd0,3'd0,3'd0,3'd0}),
          .fu_xbar_outport('{default:2'd0}),
          .write_reg_from('{default:2'd0}),
          .read_reg_from('{default:1'd0}),
          .write_reg_idx('{default:4'd0}),
          .read_reg_idx('{default:4'd0}),
          .ctrl_addr(4'd1),
          .data(32'd1),
          .pred(1'd1),
          .data_addr(7'd0)
      );
    #10
    // CONFIG_PROLOGUE_ROUTING_CROSSBAR (first routing = 2)
    recv_from_cpu_pkt__msg = make_intra_cgra_config_pkt_w_data(
          .src(5'd0),
          .dst(5'd1),
          .cmd(5'd6),
          .operation(7'd0),
          .fu_in_code('{default:3'd0}),
          .routing_xbar_outport('{3'd0,3'd0,3'd0,3'd0,3'd0,3'd0,3'd0,3'd2}),
          .fu_xbar_outport('{default:2'd0}),
          .write_reg_from('{default:2'd0}),
          .read_reg_from('{default:1'd0}),
          .write_reg_idx('{default:4'd0}),
          .read_reg_idx('{default:4'd0}),
          .ctrl_addr(4'd1),
          .data(32'd1),
          .pred(1'd1),
          .data_addr(7'd0)
      );
    #10
    // CONFIG_PROLOGUE_FU_CROSSBAR (ctrl_addr = 1)
    recv_from_cpu_pkt__msg = make_intra_cgra_config_pkt_w_data(
          .src(5'd0),
          .dst(5'd1),
          .cmd(5'd5),
          .operation(7'd0),
          .fu_in_code('{default:3'd0}),
          .routing_xbar_outport('{default:3'd0}),
          .fu_xbar_outport('{2'd0,2'd0,2'd0,2'd0,2'd0,2'd0,2'd0,2'd0}),
          .write_reg_from('{default:2'd0}),
          .read_reg_from('{default:1'd0}),
          .write_reg_idx('{default:4'd0}),
          .read_reg_idx('{default:4'd0}),
          .ctrl_addr(4'd1),
          .data(32'd1),
          .pred(1'd1),
          .data_addr(7'd0)
      );
    #10
    // CMD_LAUNCH
    recv_from_cpu_pkt__msg = make_intra_cgra_config_pkt_w_data(
          .src(5'd0),
          .dst(5'd1),
          .cmd(5'd0),
          .operation(7'd0),
          .fu_in_code('{default:3'd0}),
          .routing_xbar_outport('{default:3'd0}),
          .fu_xbar_outport('{default:2'd0}),
          .write_reg_from('{default:2'd0}),
          .read_reg_from('{default:1'd0}),
          .write_reg_idx('{default:4'd0}),
          .read_reg_idx('{default:4'd0}),
          .ctrl_addr(4'd0),
          .data(32'd0),
          .pred(1'd0),
          .data_addr(7'd0)
      );
    ////////////
    // Tile 4 //
    ////////////
    #10
    recv_from_cpu_pkt__msg =
      make_intra_cgra_config_pkt_w_data(
        .src(5'd0),
        .dst(5'd4),
        .cmd(5'd13), // CMD_CONST
        .operation(7'd0),
        .fu_in_code('{3'd0, 3'd0, 3'd0, 3'd0}),
        .routing_xbar_outport('{3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0}),
        .fu_xbar_outport('{2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0}),
        .write_reg_from('{2'd0, 2'd0, 2'd0, 2'd0}), // write_reg_from_code (do not reverse)
        .read_reg_from('{1'd0, 1'd0, 1'd0, 1'd0}),  // read_reg_from_code (do not reverse)
        .write_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .read_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .ctrl_addr(4'd0),
        .data(32'd2),
        .pred(1'd1),
        .data_addr(7'd0)
      );
    #10
    // CMD_CONFIG_COUNT_PER_ITER
    recv_from_cpu_pkt__msg =
      make_intra_cgra_config_pkt_w_data(
        .src(5'd0),
        .dst(5'd4),
        .cmd(5'd8), // CMD_CONFIG_COUNT_PER_ITER
        .operation(7'd0),
        .fu_in_code('{3'd0, 3'd0, 3'd0, 3'd0}),
        .routing_xbar_outport('{3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0}),
        .fu_xbar_outport('{2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0}),
        .write_reg_from('{2'd0, 2'd0, 2'd0, 2'd0}),
        .read_reg_from('{1'd0, 1'd0, 1'd0, 1'd0}),
        .write_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .read_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .ctrl_addr(4'd0),
        .data(32'd4),
        .pred(1'd1),
        .data_addr(7'd0)
      );
    #10
    // CMD_CONFIG_TOTAL_CTRL_COUNT
    recv_from_cpu_pkt__msg =
      make_intra_cgra_config_pkt_w_data(
        .src(5'd0),
        .dst(5'd4),
        .cmd(5'd7), // CMD_CONFIG_TOTAL_CTRL_COUNT
        .operation(7'd0),
        .fu_in_code('{3'd0, 3'd0, 3'd0, 3'd0}),
        .routing_xbar_outport('{3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0}),
        .fu_xbar_outport('{2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0}),
        .write_reg_from('{2'd0, 2'd0, 2'd0, 2'd0}),
        .read_reg_from('{1'd0, 1'd0, 1'd0, 1'd0}),
        .write_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .read_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .ctrl_addr(4'd0),
        .data(32'd42),
        .pred(1'd1),
        .data_addr(7'd0)
      );
    #10
    // CMD_CONFIG @ ctrl_addr=0, OPT_NAH
    recv_from_cpu_pkt__msg =
      make_intra_cgra_config_pkt_w_data(
        .src(5'd0),
        .dst(5'd4),
        .cmd(5'd3), // CMD_CONFIG
        .operation(7'd1), // OPT_NAH
        .fu_in_code('{3'd4, 3'd3, 3'd2, 3'd1}),
        // reverse of [0,0,0,0,0,0,0,0] is itself
        .routing_xbar_outport('{3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0}),
        // reverse of [0,0,0,0,0,0,0,0] is itself
        .fu_xbar_outport('{2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0}),
        .write_reg_from('{2'd0, 2'd0, 2'd0, 2'd0}), // keep provided code
        .read_reg_from('{1'd0, 1'd0, 1'd0, 1'd0}),  // keep provided code
        .write_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .read_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .ctrl_addr(4'd0),
        .data(32'd0),
        .pred(1'd0),
        .data_addr(7'd0)
      );
    #10
    // CMD_CONFIG @ ctrl_addr=1, OPT_ADD_CONST
    // routing: reverse of [0,0,0,0,1,0,0,0] -> [0,0,0,1,0,0,0,0]
    // fu_xbar : reverse of [0,0,0,0,1,0,0,0] -> [0,0,0,1,0,0,0,0]
    recv_from_cpu_pkt__msg =
      make_intra_cgra_config_pkt_w_data(
        .src(5'd0),
        .dst(5'd4),
        .cmd(5'd3), // CMD_CONFIG
        .operation(7'd25), // OPT_ADD_CONST
        .fu_in_code('{3'd4, 3'd3, 3'd2, 3'd1}),
        .routing_xbar_outport('{3'd0, 3'd0, 3'd0, 3'd1, 3'd0, 3'd0, 3'd0, 3'd0}),
        .fu_xbar_outport('{2'd0, 2'd0, 2'd0, 2'd1, 2'd0, 2'd0, 2'd0, 2'd0}),
        .write_reg_from('{2'd0, 2'd0, 2'd0, 2'd2}), // write_reg_from_code (keep order)
        .read_reg_from('{1'd0, 1'd0, 1'd0, 1'd0}),  // read_reg_from_code
        .write_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .read_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .ctrl_addr(4'd1),
        .data(32'd0),
        .pred(1'd0),
        .data_addr(7'd0)
      );
    #10
    // CMD_CONFIG @ ctrl_addr=2, OPT_LD
    // fu_xbar : reverse of [0,0,0,0,0,1,0,0] -> [0,0,1,0,0,0,0,0]
    // write_reg_from inline [0,2,0,0] -> reverse -> [0,0,2,0]
    recv_from_cpu_pkt__msg =
      make_intra_cgra_config_pkt_w_data(
        .src(5'd0),
        .dst(5'd4),
        .cmd(5'd3), // CMD_CONFIG
        .operation(7'd12), // OPT_LD
        .fu_in_code('{3'd4, 3'd3, 3'd2, 3'd1}),
        .routing_xbar_outport('{3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0}),
        .fu_xbar_outport('{2'd0, 2'd0, 2'd1, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0}),
        .write_reg_from('{2'd0, 2'd0, 2'd2, 2'd0}),
        .read_reg_from('{1'd0, 1'd0, 1'd0, 1'd1}), // read_reg_from_code
        .write_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .read_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .ctrl_addr(4'd2),
        .data(32'd0),
        .pred(1'd0),
        .data_addr(7'd0)
      );
    #10
    // CMD_CONFIG @ ctrl_addr=3, OPT_MUL
    // routing: reverse of [0,0,0,0,1,0,0,0] -> [0,0,0,1,0,0,0,0]
    // fu_xbar : reverse of [0,1,0,0,0,0,0,0] -> [0,0,0,0,0,0,1,0]
    // read_reg_from inline [0,1,0,0] -> reverse -> [0,0,1,0]
    recv_from_cpu_pkt__msg =
      make_intra_cgra_config_pkt_w_data(
        .src(5'd0),
        .dst(5'd4),
        .cmd(5'd3), // CMD_CONFIG
        .operation(7'd7), // OPT_MUL
        .fu_in_code('{3'd4, 3'd3, 3'd2, 3'd1}),
        .routing_xbar_outport('{3'd0, 3'd0, 3'd0, 3'd1, 3'd0, 3'd0, 3'd0, 3'd0}),
        .fu_xbar_outport('{2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd1, 2'd0}),
        .write_reg_from('{2'd0, 2'd0, 2'd0, 2'd0}),
        .read_reg_from('{1'd0, 1'd0, 1'd1, 1'd0}),
        .write_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .read_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .ctrl_addr(4'd3),
        .data(32'd0),
        .pred(1'd0),
        .data_addr(7'd0)
      );
    #10
    // CMD_LAUNCH
    recv_from_cpu_pkt__msg =
      make_intra_cgra_config_pkt_w_data(
        .src(5'd0),
        .dst(5'd4),
        .cmd(5'd0), // CMD_LAUNCH
        .operation(7'd0),
        .fu_in_code('{3'd0, 3'd0, 3'd0, 3'd0}),
        .routing_xbar_outport('{3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0}),
        .fu_xbar_outport('{2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0}),
        .write_reg_from('{2'd0, 2'd0, 2'd0, 2'd0}),
        .read_reg_from('{1'd0, 1'd0, 1'd0, 1'd0}),
        .write_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .read_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .ctrl_addr(4'd0),
        .data(32'd0),
        .pred(1'd0),
        .data_addr(7'd0)
      );
    ////////////
    // Tile 5 //
    ////////////
    #10
    // CMD_CONST (kLoopUpperBound, pred=1)
    recv_from_cpu_pkt__msg =
      make_intra_cgra_config_pkt_w_data(
        .src(5'd0),
        .dst(5'd5),
        .cmd(5'd13),
        .operation(7'd0),
        .fu_in_code('{3'd0, 3'd0, 3'd0, 3'd0}),
        .routing_xbar_outport('{3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0}),
        .fu_xbar_outport('{2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0}),
        .write_reg_from('{2'd0, 2'd0, 2'd0, 2'd0}),
        .read_reg_from('{1'd0, 1'd0, 1'd0, 1'd0}),
        .write_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .read_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .ctrl_addr(4'd0),
        .data(32'd10),
        .pred(1'd1),
        .data_addr(7'd0)
      );
    #10
    // CMD_CONFIG_COUNT_PER_ITER (kCtrlCountPerIter, pred=1)
    recv_from_cpu_pkt__msg =
      make_intra_cgra_config_pkt_w_data(
        .src(5'd0),
        .dst(5'd5),
        .cmd(5'd8),
        .operation(7'd0),
        .fu_in_code('{3'd0, 3'd0, 3'd0, 3'd0}),
        .routing_xbar_outport('{3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0}),
        .fu_xbar_outport('{2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0}),
        .write_reg_from('{2'd0, 2'd0, 2'd0, 2'd0}),
        .read_reg_from('{1'd0, 1'd0, 1'd0, 1'd0}),
        .write_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .read_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .ctrl_addr(4'd0),
        .data(32'd4),
        .pred(1'd1),
        .data_addr(7'd0)
      );
    #10
    // CMD_CONFIG_TOTAL_CTRL_COUNT (kTotalCtrlSteps, pred=1)
    recv_from_cpu_pkt__msg =
      make_intra_cgra_config_pkt_w_data(
        .src(5'd0),
        .dst(5'd5),
        .cmd(5'd7),
        .operation(7'd0),
        .fu_in_code('{3'd0, 3'd0, 3'd0, 3'd0}),
        .routing_xbar_outport('{3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0}),
        .fu_xbar_outport('{2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0}),
        .write_reg_from('{2'd0, 2'd0, 2'd0, 2'd0}),
        .read_reg_from('{1'd0, 1'd0, 1'd0, 1'd0}),
        .write_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .read_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .ctrl_addr(4'd0),
        .data(32'd42),
        .pred(1'd1),
        .data_addr(7'd0)
      );
    #10
    // CMD_CONFIG @ ctrl_addr=0, OPT_NAH
    // (explicit arrays reversed; provided *_code arrays kept as-is)
    recv_from_cpu_pkt__msg =
      make_intra_cgra_config_pkt_w_data(
        .src(5'd0),
        .dst(5'd5),
        .cmd(5'd3),
        .operation(7'd1),
        .fu_in_code('{3'd4, 3'd3, 3'd2, 3'd1}),
        .routing_xbar_outport('{3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0}),
        .fu_xbar_outport('{2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0}),
        .write_reg_from('{2'd0, 2'd0, 2'd0, 2'd0}),
        .read_reg_from('{1'd0, 1'd0, 1'd0, 1'd0}),
        .write_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .read_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .ctrl_addr(4'd0),
        .data(32'd0),
        .pred(1'd0),
        .data_addr(7'd0)
      );
    #10
    // CMD_CONFIG @ ctrl_addr=1, OPT_NAH
    recv_from_cpu_pkt__msg =
      make_intra_cgra_config_pkt_w_data(
        .src(5'd0),
        .dst(5'd5),
        .cmd(5'd3),
        .operation(7'd1),
        .fu_in_code('{3'd4, 3'd3, 3'd2, 3'd1}),
        .routing_xbar_outport('{3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0}),
        .fu_xbar_outport('{2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0}),
        .write_reg_from('{2'd0, 2'd0, 2'd0, 2'd0}),
        .read_reg_from('{1'd0, 1'd0, 1'd0, 1'd0}),
        .write_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .read_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .ctrl_addr(4'd1),
        .data(32'd0),
        .pred(1'd0),
        .data_addr(7'd0)
      );
    #10
    // CMD_CONFIG @ ctrl_addr=2, OPT_NE_CONST (CMP)
    // routing  [0,0,0,0,1,0,0,0] -> reversed -> [0,0,0,1,0,0,0,0]
    // fu_xbar  [1,0,0,0,1,0,0,0] -> reversed -> [0,0,0,0,1,0,0,1]
    recv_from_cpu_pkt__msg =
      make_intra_cgra_config_pkt_w_data(
        .src(5'd0),
        .dst(5'd5),
        .cmd(5'd3),
        .operation(7'd46),
        .fu_in_code('{3'd4, 3'd3, 3'd2, 3'd1}),
        .routing_xbar_outport('{3'd0, 3'd0, 3'd0, 3'd1, 3'd0, 3'd0, 3'd0, 3'd0}),
        .fu_xbar_outport('{2'd0, 2'd0, 2'd0, 2'd1, 2'd0, 2'd0, 2'd0, 2'd1}),
        .write_reg_from('{2'd0, 2'd0, 2'd0, 2'd2}),
        .read_reg_from('{1'd0, 1'd0, 1'd0, 1'd0}),
        .write_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .read_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .ctrl_addr(4'd2),
        .data(32'd0),
        .pred(1'd0),
        .data_addr(7'd0)
      );
    #10
    // CMD_CONFIG @ ctrl_addr=3, OPT_NOT
    // routing  [0,1,0,0,0,0,0,0] -> reversed -> [0,0,0,0,0,0,1,0]
    // fu_xbar  [0,1,0,0,0,0,0,0] -> reversed -> [0,0,0,0,0,0,1,0]
    recv_from_cpu_pkt__msg =
      make_intra_cgra_config_pkt_w_data(
        .src(5'd0),
        .dst(5'd5),
        .cmd(5'd3),
        .operation(7'd11),
        .fu_in_code('{3'd4, 3'd3, 3'd2, 3'd1}),
        .routing_xbar_outport('{3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0}),
        .fu_xbar_outport('{2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd1, 2'd0}),
        .write_reg_from('{2'd0, 2'd0, 2'd0, 2'd0}),
        .read_reg_from('{1'd0, 1'd0, 1'd0, 1'd1}),
        .write_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .read_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .ctrl_addr(4'd3),
        .data(32'd0),
        .pred(1'd0),
        .data_addr(7'd0)
      );
    #10
    // CMD_LAUNCH
    recv_from_cpu_pkt__msg =
      make_intra_cgra_config_pkt_w_data(
        .src(5'd0),
        .dst(5'd5),
        .cmd(5'd0),
        .operation(7'd0),
        .fu_in_code('{3'd0, 3'd0, 3'd0, 3'd0}),
        .routing_xbar_outport('{3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0}),
        .fu_xbar_outport('{2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0}),
        .write_reg_from('{2'd0, 2'd0, 2'd0, 2'd0}),
        .read_reg_from('{1'd0, 1'd0, 1'd0, 1'd0}),
        .write_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .read_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .ctrl_addr(4'd0),
        .data(32'd0),
        .pred(1'd0),
        .data_addr(7'd0)
      );
    ////////////
    // Tile 8 //
    ////////////
    #10
    // CMD_CONST (kLoopLowerBound, pred=1) — for PHI_CONST
    recv_from_cpu_pkt__msg =
      make_intra_cgra_config_pkt_w_data(
        .src(5'd0),
        .dst(5'd8),
        .cmd(5'd13),
        .operation(7'd0),
        .fu_in_code('{3'd0, 3'd0, 3'd0, 3'd0}),
        .routing_xbar_outport('{3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0}),
        .fu_xbar_outport('{2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0}),
        .write_reg_from('{2'd0, 2'd0, 2'd0, 2'd0}),
        .read_reg_from('{1'd0, 1'd0, 1'd0, 1'd0}),
        .write_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .read_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .ctrl_addr(4'd0),
        .data(32'd2),
        .pred(1'd1),
        .data_addr(7'd0)
      );
    #10
    // CMD_CONST (kInputBaseAddress, pred=1) — for ADD_CONST
    recv_from_cpu_pkt__msg =
      make_intra_cgra_config_pkt_w_data(
        .src(5'd0),
        .dst(5'd8),
        .cmd(5'd13),
        .operation(7'd0),
        .fu_in_code('{3'd0, 3'd0, 3'd0, 3'd0}),
        .routing_xbar_outport('{3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0}),
        .fu_xbar_outport('{2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0}),
        .write_reg_from('{2'd0, 2'd0, 2'd0, 2'd0}),
        .read_reg_from('{1'd0, 1'd0, 1'd0, 1'd0}),
        .write_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .read_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .ctrl_addr(4'd0),
        .data(32'd0),
        .pred(1'd1),
        .data_addr(7'd0)
      );
    #10
    // CMD_CONFIG_COUNT_PER_ITER (kCtrlCountPerIter, pred=1)
    recv_from_cpu_pkt__msg =
      make_intra_cgra_config_pkt_w_data(
        .src(5'd0),
        .dst(5'd8),
        .cmd(5'd8),
        .operation(7'd0),
        .fu_in_code('{3'd0, 3'd0, 3'd0, 3'd0}),
        .routing_xbar_outport('{3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0}),
        .fu_xbar_outport('{2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0}),
        .write_reg_from('{2'd0, 2'd0, 2'd0, 2'd0}),
        .read_reg_from('{1'd0, 1'd0, 1'd0, 1'd0}),
        .write_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .read_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .ctrl_addr(4'd0),
        .data(32'd4),
        .pred(1'd1),
        .data_addr(7'd0)
      );
    #10
    // CMD_CONFIG_TOTAL_CTRL_COUNT (kTotalCtrlSteps, pred=1)
    recv_from_cpu_pkt__msg =
      make_intra_cgra_config_pkt_w_data(
        .src(5'd0),
        .dst(5'd8),
        .cmd(5'd7),
        .operation(7'd0),
        .fu_in_code('{3'd0, 3'd0, 3'd0, 3'd0}),
        .routing_xbar_outport('{3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0}),
        .fu_xbar_outport('{2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0}),
        .write_reg_from('{2'd0, 2'd0, 2'd0, 2'd0}),
        .read_reg_from('{1'd0, 1'd0, 1'd0, 1'd0}),
        .write_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .read_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .ctrl_addr(4'd0),
        .data(32'd42),
        .pred(1'd1),
        .data_addr(7'd0)
      );
    #10
    // CMD_CONFIG @ ctrl_addr=0, OPT_PHI_CONST
    // routing  [0,0,0,0,4,0,0,0] -> reversed -> [0,0,0,4,0,0,0,0]
    // fu_xbar  [0,1,0,1,1,0,0,0] -> reversed -> [0,0,0,1,1,0,1,0]
    recv_from_cpu_pkt__msg =
      make_intra_cgra_config_pkt_w_data(
        .src(5'd0),
        .dst(5'd8),
        .cmd(5'd3),
        .operation(7'd32),
        .fu_in_code('{3'd4, 3'd3, 3'd2, 3'd1}),
        .routing_xbar_outport('{3'd0, 3'd0, 3'd0, 3'd4, 3'd0, 3'd0, 3'd0, 3'd0}),
        .fu_xbar_outport('{2'd0, 2'd0, 2'd0, 2'd1, 2'd1, 2'd0, 2'd1, 2'd0}),
        .write_reg_from('{2'd0, 2'd0, 2'd0, 2'd2}),
        .read_reg_from('{1'd0, 1'd0, 1'd0, 1'd0}),
        .write_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .read_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .ctrl_addr(4'd0),
        .data(32'd0),
        .pred(1'd0),
        .data_addr(7'd0)
      );
    #10
    // CMD_CONFIG @ ctrl_addr=1, OPT_ADD_CONST
    // fu_xbar  [0,0,0,0,0,1,0,0] -> reversed -> [0,0,1,0,0,0,0,0]
    // write_reg_from inline [0,2,0,0] -> reversed -> [0,0,2,0]
    recv_from_cpu_pkt__msg =
      make_intra_cgra_config_pkt_w_data(
        .src(5'd0),
        .dst(5'd8),
        .cmd(5'd3),
        .operation(7'd25),
        .fu_in_code('{3'd4, 3'd3, 3'd2, 3'd1}),
        .routing_xbar_outport('{3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0}),
        .fu_xbar_outport('{2'd0, 2'd0, 2'd1, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0}),
        .write_reg_from('{2'd0, 2'd0, 2'd2, 2'd0}),
        .read_reg_from('{1'd0, 1'd0, 1'd0, 1'd1}),
        .write_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .read_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .ctrl_addr(4'd1),
        .data(32'd0),
        .pred(1'd0),
        .data_addr(7'd0)
      );
    #10
    // CMD_CONFIG @ ctrl_addr=2, OPT_LD
    // fu_in_code inline [2,0,0,0] -> reversed -> [0,0,0,2]
    // fu_xbar     [0,1,0,0,0,0,0,0] -> reversed -> [0,0,0,0,0,0,1,0]
    // read_reg_from inline [0,1,0,0] -> reversed -> [0,0,1,0]
    recv_from_cpu_pkt__msg =
      make_intra_cgra_config_pkt_w_data(
        .src(5'd0),
        .dst(5'd8),
        .cmd(5'd3),
        .operation(7'd12),
        .fu_in_code('{3'd0, 3'd0, 3'd0, 3'd2}), // Hand-coded.
        .routing_xbar_outport('{3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0}),
        .fu_xbar_outport('{2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd1, 2'd0}),
        .write_reg_from('{2'd0, 2'd0, 2'd0, 2'd0}),
        .read_reg_from('{1'd0, 1'd0, 1'd1, 1'd0}),
        .write_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .read_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .ctrl_addr(4'd2),
        .data(32'd0),
        .pred(1'd0),
        .data_addr(7'd0)
      );
    #10
    // CMD_CONFIG @ ctrl_addr=3, OPT_NAH
    recv_from_cpu_pkt__msg =
      make_intra_cgra_config_pkt_w_data(
        .src(5'd0),
        .dst(5'd8),
        .cmd(5'd3),
        .operation(7'd1),
        .fu_in_code('{3'd4, 3'd3, 3'd2, 3'd1}),
        .routing_xbar_outport('{3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0}),
        .fu_xbar_outport('{2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0}),
        .write_reg_from('{2'd0, 2'd0, 2'd0, 2'd0}),
        .read_reg_from('{1'd0, 1'd0, 1'd0, 1'd0}),
        .write_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .read_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .ctrl_addr(4'd3),
        .data(32'd0),
        .pred(1'd0),
        .data_addr(7'd0)
      );
    #10
    // CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR @ ctrl_addr=0, data=1 (pred=1)
    // routing [3,0,0,0,0,0,0,0] -> reversed -> [0,0,0,0,0,0,0,3]
    // (unspecified args default to zeros)
    recv_from_cpu_pkt__msg =
      make_intra_cgra_config_pkt_w_data(
        .src(5'd0),
        .dst(5'd8),
        .cmd(5'd6),
        .operation(7'd0),
        .fu_in_code('{3'd0, 3'd0, 3'd0, 3'd0}),
        .routing_xbar_outport('{3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd3}),
        .fu_xbar_outport('{2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0}),
        .write_reg_from('{2'd0, 2'd0, 2'd0, 2'd0}),
        .read_reg_from('{1'd0, 1'd0, 1'd0, 1'd0}),
        .write_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .read_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .ctrl_addr(4'd0),
        .data(32'd1),
        .pred(1'd1),
        .data_addr(7'd0)
      );
    #10
    // CMD_LAUNCH
    recv_from_cpu_pkt__msg =
      make_intra_cgra_config_pkt_w_data(
        .src(5'd0),
        .dst(5'd8),
        .cmd(5'd0),
        .operation(7'd0),
        .fu_in_code('{3'd0, 3'd0, 3'd0, 3'd0}),
        .routing_xbar_outport('{3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0}),
        .fu_xbar_outport('{2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0}),
        .write_reg_from('{2'd0, 2'd0, 2'd0, 2'd0}),
        .read_reg_from('{1'd0, 1'd0, 1'd0, 1'd0}),
        .write_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .read_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .ctrl_addr(4'd0),
        .data(32'd0),
        .pred(1'd0),
        .data_addr(7'd0)
      );
    ////////////
    // Tile 9 //
    ////////////
    #10
    // CMD_CONST (kLoopIncrement, pred=1) — for ADD_CONST
    recv_from_cpu_pkt__msg =
      make_intra_cgra_config_pkt_w_data(
        .src(5'd0),
        .dst(5'd9),
        .cmd(5'd13),
        .operation(7'd0),
        .fu_in_code('{3'd0, 3'd0, 3'd0, 3'd0}),
        .routing_xbar_outport('{3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0}),
        .fu_xbar_outport('{2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0}),
        .write_reg_from('{2'd0, 2'd0, 2'd0, 2'd0}),
        .read_reg_from('{1'd0, 1'd0, 1'd0, 1'd0}),
        .write_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .read_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .ctrl_addr(4'd0),
        .data(32'd1),
        .pred(1'd1),
        .data_addr(7'd0)
      );
    #10
    // CMD_CONFIG_COUNT_PER_ITER (kCtrlCountPerIter, pred=1)
    recv_from_cpu_pkt__msg =
      make_intra_cgra_config_pkt_w_data(
        .src(5'd0),
        .dst(5'd9),
        .cmd(5'd8),
        .operation(7'd0),
        .fu_in_code('{3'd0, 3'd0, 3'd0, 3'd0}),
        .routing_xbar_outport('{3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0}),
        .fu_xbar_outport('{2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0}),
        .write_reg_from('{2'd0, 2'd0, 2'd0, 2'd0}),
        .read_reg_from('{1'd0, 1'd0, 1'd0, 1'd0}),
        .write_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .read_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .ctrl_addr(4'd0),
        .data(32'd4),
        .pred(1'd1),
        .data_addr(7'd0)
      );
    #10
    // CMD_CONFIG_TOTAL_CTRL_COUNT (kTotalCtrlSteps, pred=1)
    recv_from_cpu_pkt__msg =
      make_intra_cgra_config_pkt_w_data(
        .src(5'd0),
        .dst(5'd9),
        .cmd(5'd7),
        .operation(7'd0),
        .fu_in_code('{3'd0, 3'd0, 3'd0, 3'd0}),
        .routing_xbar_outport('{3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0}),
        .fu_xbar_outport('{2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0}),
        .write_reg_from('{2'd0, 2'd0, 2'd0, 2'd0}),
        .read_reg_from('{1'd0, 1'd0, 1'd0, 1'd0}),
        .write_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .read_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .ctrl_addr(4'd0),
        .data(32'd42),
        .pred(1'd1),
        .data_addr(7'd0)
      );
    #10
    // CMD_CONFIG @ ctrl_addr=0, OPT_NAH
    // routing  [0,0,0,0,0,0,0,0] -> reversed -> same
    // fu_xbar  [0,0,0,0,0,0,0,0] -> reversed -> same
    recv_from_cpu_pkt__msg =
      make_intra_cgra_config_pkt_w_data(
        .src(5'd0),
        .dst(5'd9),
        .cmd(5'd3),
        .operation(7'd1),
        .fu_in_code('{3'd4, 3'd3, 3'd2, 3'd1}),
        .routing_xbar_outport('{3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0}),
        .fu_xbar_outport('{2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0}),
        .write_reg_from('{2'd0, 2'd0, 2'd0, 2'd0}),
        .read_reg_from('{1'd0, 1'd0, 1'd0, 1'd0}),
        .write_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .read_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .ctrl_addr(4'd0),
        .data(32'd0),
        .pred(1'd0),
        .data_addr(7'd0)
      );
    #10
    // CMD_CONFIG @ ctrl_addr=1, OPT_ADD_CONST
    // routing  [0,0,0,0,3,0,0,0] -> reversed -> [0,0,0,3,0,0,0,0]
    // fu_xbar  [0,1,0,0,0,1,0,0] -> reversed -> [0,0,1,0,0,0,1,0]
    // write_reg_from inline [0,2,0,0] -> reversed -> [0,0,2,0]
    recv_from_cpu_pkt__msg =
      make_intra_cgra_config_pkt_w_data(
        .src(5'd0),
        .dst(5'd9),
        .cmd(5'd3),
        .operation(7'd25),
        .fu_in_code('{3'd4, 3'd3, 3'd2, 3'd1}),
        .routing_xbar_outport('{3'd0, 3'd0, 3'd0, 3'd3, 3'd0, 3'd0, 3'd0, 3'd0}),
        .fu_xbar_outport('{2'd0, 2'd0, 2'd1, 2'd0, 2'd0, 2'd0, 2'd1, 2'd0}),
        .write_reg_from('{2'd0, 2'd0, 2'd2, 2'd0}),
        .read_reg_from('{1'd0, 1'd0, 1'd0, 1'd0}),
        .write_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .read_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .ctrl_addr(4'd1),
        .data(32'd0),
        .pred(1'd0),
        .data_addr(7'd0)
      );
    #10
    // CMD_CONFIG @ ctrl_addr=2, OPT_NAH
    recv_from_cpu_pkt__msg =
      make_intra_cgra_config_pkt_w_data(
        .src(5'd0),
        .dst(5'd9),
        .cmd(5'd3),
        .operation(7'd1),
        .fu_in_code('{3'd4, 3'd3, 3'd2, 3'd1}),
        .routing_xbar_outport('{3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0}),
        .fu_xbar_outport('{2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0}),
        .write_reg_from('{2'd0, 2'd0, 2'd0, 2'd0}),
        .read_reg_from('{1'd0, 1'd0, 1'd0, 1'd0}),
        .write_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .read_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .ctrl_addr(4'd2),
        .data(32'd0),
        .pred(1'd0),
        .data_addr(7'd0)
      );
    #10
    // CMD_CONFIG @ ctrl_addr=3, OPT_GRT_PRED
    // fu_in    [2,1,0,0]         . -> reversed -> [0,0,1,2]
    // routing  [0,0,0,0,2,0,0,0]   -> reversed -> [0,0,0,2,0,0,0,0]
    // fu_xbar  [0,0,1,0,0,0,0,0]   -> reversed -> [0,0,0,0,0,1,0,0]
    // read_reg_from [0,1,0,0]      -> reversed -> [0,0,1,0]
    recv_from_cpu_pkt__msg =
      make_intra_cgra_config_pkt_w_data(
        .src(5'd0),
        .dst(5'd9),
        .cmd(5'd3),
        .operation(7'd16),
        .fu_in_code('{3'd0, 3'd0, 3'd1, 3'd2}),
        .routing_xbar_outport('{3'd0, 3'd0, 3'd0, 3'd2, 3'd0, 3'd0, 3'd0, 3'd0}),
        .fu_xbar_outport('{2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd1, 2'd0, 2'd0}),
        .write_reg_from('{2'd0, 2'd0, 2'd0, 2'd0}),
        .read_reg_from('{1'd0, 1'd0, 1'd1, 1'd0}),
        .write_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .read_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .ctrl_addr(4'd3),
        .data(32'd0),
        .pred(1'd0),
        .data_addr(7'd0)
      );
    #10
    // CMD_LAUNCH
    recv_from_cpu_pkt__msg =
      make_intra_cgra_config_pkt_w_data(
        .src(5'd0),
        .dst(5'd9),
        .cmd(5'd0),
        .operation(7'd0),
        .fu_in_code('{3'd0, 3'd0, 3'd0, 3'd0}),
        .routing_xbar_outport('{3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0, 3'd0}),
        .fu_xbar_outport('{2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0, 2'd0}),
        .write_reg_from('{2'd0, 2'd0, 2'd0, 2'd0}),
        .read_reg_from('{1'd0, 1'd0, 1'd0, 1'd0}),
        .write_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .read_reg_idx('{4'd0, 4'd0, 4'd0, 4'd0}),
        .ctrl_addr(4'd0),
        .data(32'd0),
        .pred(1'd0),
        .data_addr(7'd0)
      );


    #10
    recv_from_cpu_pkt__val = 0;

    #3000

    if ('d1 == PASS) $display("TEST PASSED.");
    else $display("TEST FAILED.");

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

    if ( send_to_cpu_pkt__val && ('d2215 == send_to_cpu_pkt__msg.payload.data.payload) )
    begin
      PASS = 1;
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

