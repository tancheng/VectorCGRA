function automatic IntraCgraPacket_4_2x2_16_8_2_CgraPayload__432fde8bfb7da0ed make_intra_cgra_pkt
(
  input logic [4:0] src,
  input logic [4:0] dst,
  input logic [4:0] cmd,
  input logic [31:0] data_payload,
  input logic       data_predicate,
  input logic [6:0] data_addr,
  input logic [6:0] ctrl_operation
);

  IntraCgraPacket_4_2x2_16_8_2_CgraPayload__432fde8bfb7da0ed pkt;

  pkt.src         = src;
  pkt.dst         = dst;
  pkt.src_cgra_id = 2'd0;
  pkt.dst_cgra_id = 2'd0;
  pkt.src_cgra_x  = 1'b0;
  pkt.src_cgra_y  = 1'b0;
  pkt.dst_cgra_x  = 1'b0;
  pkt.dst_cgra_y  = 1'b0;
  pkt.opaque      = 8'd0;
  pkt.vc_id       = 1'b0;


  pkt.payload.cmd              = cmd;
  pkt.payload.data_addr        = data_addr;
  pkt.payload.ctrl_addr                = 4'd0;

  pkt.payload.data.payload     = data_payload;
  pkt.payload.data.predicate   = data_predicate;
  pkt.payload.data.bypass      = 1'b0;
  pkt.payload.data.delay       = 1'b0;


  pkt.payload.ctrl.operation   = ctrl_operation;
  pkt.payload.ctrl.fu_in               = '{default: 3'd0};
  pkt.payload.ctrl.routing_xbar_outport = '{default: 3'd0};
  pkt.payload.ctrl.fu_xbar_outport     = '{default: 2'd0};
  pkt.payload.ctrl.vector_factor_power = 3'd0;
  pkt.payload.ctrl.is_last_ctrl        = 1'b0;
  pkt.payload.ctrl.write_reg_from      = '{default: 2'd0};
  pkt.payload.ctrl.write_reg_idx       = '{default: 4'd0};
  pkt.payload.ctrl.read_reg_from       = '{default: 1'd0};
  pkt.payload.ctrl.read_reg_idx        = '{default: 4'd0};

  return pkt;
endfunction

function automatic IntraCgraPacket_4_2x2_16_8_2_CgraPayload__432fde8bfb7da0ed make_intra_cgra_config_pkt
(
  input logic [4:0] src,
  input logic [4:0] dst,
  input logic [4:0] cmd,
  input logic [6:0] operation,
  input logic [3:0][2:0] fu_in_code,
  input logic [7:0][2:0] routing_xbar_outport,
  input logic [7:0][1:0] fu_xbar_outport,
  input logic [3:0][1:0] write_reg_from,
  input logic [3:0][0:0] read_reg_from,
  input logic [3:0][3:0] write_reg_idx,
  input logic [3:0][3:0] read_reg_idx,
  input logic [3:0] ctrl_addr
);

  IntraCgraPacket_4_2x2_16_8_2_CgraPayload__432fde8bfb7da0ed pkt;

  pkt.src         = src;
  pkt.dst         = dst;
  pkt.src_cgra_id = 2'd0;
  pkt.dst_cgra_id = 2'd0;
  pkt.src_cgra_x  = 1'b0;
  pkt.src_cgra_y  = 1'b0;
  pkt.dst_cgra_x  = 1'b0;
  pkt.dst_cgra_y  = 1'b0;
  pkt.opaque      = 8'd0;
  pkt.vc_id       = 1'b0;

  pkt.payload.cmd = cmd; // CMD_CONFIG
  pkt.payload.data = '0; // Not used for config packets
  pkt.payload.data_addr = 7'd0;
  pkt.payload.ctrl_addr = ctrl_addr;

  pkt.payload.ctrl.operation           = operation;
  pkt.payload.ctrl.fu_in               = fu_in_code;
  pkt.payload.ctrl.routing_xbar_outport = routing_xbar_outport;
  pkt.payload.ctrl.fu_xbar_outport     = fu_xbar_outport;
  pkt.payload.ctrl.vector_factor_power = 3'd0;
  pkt.payload.ctrl.is_last_ctrl        = 1'b0;
  pkt.payload.ctrl.write_reg_from      = write_reg_from;
  pkt.payload.ctrl.write_reg_idx       = write_reg_idx;
  pkt.payload.ctrl.read_reg_from       = read_reg_from;
  pkt.payload.ctrl.read_reg_idx        = read_reg_idx;

  return pkt;
endfunction

function automatic IntraCgraPacket_4_2x2_16_8_2_CgraPayload__432fde8bfb7da0ed make_intra_cgra_config_pkt_w_data
(
  input logic [4:0] src,
  input logic [4:0] dst,
  input logic [4:0] cmd,
  input logic [6:0] operation,
  input logic [3:0][2:0] fu_in_code,
  input logic [7:0][2:0] routing_xbar_outport,
  input logic [7:0][1:0] fu_xbar_outport,
  input logic [3:0][1:0] write_reg_from,
  input logic [3:0][0:0] read_reg_from,
  input logic [3:0][3:0] write_reg_idx,
  input logic [3:0][3:0] read_reg_idx,
  input logic [3:0] ctrl_addr,
  input logic [31:0] data,
  input logic [0:0] pred,
  input logic [6:0] data_addr
);

  IntraCgraPacket_4_2x2_16_8_2_CgraPayload__432fde8bfb7da0ed pkt;

  pkt.src         = src;
  pkt.dst         = dst;
  pkt.src_cgra_id = 2'd0;
  pkt.dst_cgra_id = 2'd0;
  pkt.src_cgra_x  = 1'b0;
  pkt.src_cgra_y  = 1'b0;
  pkt.dst_cgra_x  = 1'b0;
  pkt.dst_cgra_y  = 1'b0;
  pkt.opaque      = 8'd0;
  pkt.vc_id       = 1'b0;

  pkt.payload.cmd = cmd;
  pkt.payload.data_addr = data_addr;
  pkt.payload.ctrl_addr = ctrl_addr;

  pkt.payload.ctrl.operation           = operation;
  pkt.payload.ctrl.fu_in               = fu_in_code;
  pkt.payload.ctrl.routing_xbar_outport = routing_xbar_outport;
  pkt.payload.ctrl.fu_xbar_outport     = fu_xbar_outport;
  pkt.payload.ctrl.vector_factor_power = 3'd0;
  pkt.payload.ctrl.is_last_ctrl        = 1'b0;
  pkt.payload.ctrl.write_reg_from      = write_reg_from;
  pkt.payload.ctrl.write_reg_idx       = write_reg_idx;
  pkt.payload.ctrl.read_reg_from       = read_reg_from;
  pkt.payload.ctrl.read_reg_idx        = read_reg_idx;

  pkt.payload.data.payload   = data;
  pkt.payload.data.predicate = pred;
  pkt.payload.data.bypass    = 1'b0;
  pkt.payload.data.delay     = 1'b0;

  return pkt;
endfunction

