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
  integer file_handle;

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

/*
111103b7 lui x7
00138393 ADDI x7
01039393 slli x7, x7, 16
01039393 slli x7, x7, 16
addi x31 x0 0
lui 31
addi 31
OR 7 7 31
0070b023 sd x7, 0(x1)

22220437 lui x8
addi x8
01041413 slli x8, x8, 16
01041413 slli x8, x8, 16
addi x31 x0 0
lui 31
addi 31
OR 8 8 31
0080b423 sd x8, 8(x1)

33330537 lui x10
ADDI x10
01051513 slli x10, x10, 16
01051513 slli x10, x10, 16
addi x31 x0 0
lui 31
addi 31
OR 10 10 31
00a0b823 sd x10, 16(x1)

01808093 Advance x1 += 24 (h1018)
*/

  file_handle = $fopen("output.txt", "a");
  //$fdisplay( file_handle, "%h", logic_pkt(pkt)[63:0] );
  $fdisplay( file_handle, "%h3b7",   (logic_pkt(pkt)[63:44] + logic_pkt(pkt)[43]) );
  $fdisplay( file_handle, "%h38393",  logic_pkt(pkt)[43:32] );
  $fdisplay( file_handle, "01039393" );
  $fdisplay( file_handle, "01039393" );
  $fdisplay( file_handle, "00000f93" );
  $fdisplay( file_handle, "%hfb7",   (logic_pkt(pkt)[31:12] + logic_pkt(pkt)[11]) );
  $fdisplay( file_handle, "%hf8f93",  logic_pkt(pkt)[11:0] );
  $fdisplay( file_handle, "01f3e3b3" );
  $fdisplay( file_handle, "0070b023" );
  //$fdisplay( file_handle, "%h", logic_pkt(pkt)[127:64] );
  $fdisplay( file_handle, "%h437",   (logic_pkt(pkt)[127:108] + logic_pkt(pkt)[107]) );
  $fdisplay( file_handle, "%h40413",  logic_pkt(pkt)[107:96] );
  $fdisplay( file_handle, "01041413" );
  $fdisplay( file_handle, "01041413" );
  $fdisplay( file_handle, "00000f93" );
  $fdisplay( file_handle, "%hfb7",   (logic_pkt(pkt)[95:76] + logic_pkt(pkt)[75]) );
  $fdisplay( file_handle, "%hf8f93",  logic_pkt(pkt)[75:64] );
  $fdisplay( file_handle, "01f46433" );
  $fdisplay( file_handle, "0080b423" );
  //$fdisplay( file_handle, "%h", logic_pkt(pkt)[184:128] );
  $fdisplay( file_handle, "%h537",   ({ {7{1'b0}}, logic_pkt(pkt)[184:172] } + logic_pkt(pkt)[171])  );
  $fdisplay( file_handle, "%h50513",               logic_pkt(pkt)[171:160] );
  $fdisplay( file_handle, "01051513" );
  $fdisplay( file_handle, "01051513" );
  $fdisplay( file_handle, "00000f93" );
  $fdisplay( file_handle, "%hfb7",   (logic_pkt(pkt)[159:140] + logic_pkt(pkt)[139]) );
  $fdisplay( file_handle, "%hf8f93",  logic_pkt(pkt)[139:128] );
  $fdisplay( file_handle, "01f56533" );
  $fdisplay( file_handle, "00a0b823" );
  // Advance x1 += 24 (h1018)
  $fdisplay( file_handle, "01808093" );
  $fclose(file_handle);

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
  integer file_handle;

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

  file_handle = $fopen("output.txt", "a");
  //$fdisplay( file_handle, "%h", logic_pkt(pkt)[63:0] );
  $fdisplay( file_handle, "%h3b7",   (logic_pkt(pkt)[63:44] + logic_pkt(pkt)[43]) );
  $fdisplay( file_handle, "%h38393",  logic_pkt(pkt)[43:32] );
  $fdisplay( file_handle, "01039393" );
  $fdisplay( file_handle, "01039393" );
  $fdisplay( file_handle, "00000f93" );
  $fdisplay( file_handle, "%hfb7",   (logic_pkt(pkt)[31:12] + logic_pkt(pkt)[11]) );
  $fdisplay( file_handle, "%hf8f93",  logic_pkt(pkt)[11:0] );
  $fdisplay( file_handle, "01f3e3b3" );
  $fdisplay( file_handle, "0070b023" );
  //$fdisplay( file_handle, "%h", logic_pkt(pkt)[127:64] );
  $fdisplay( file_handle, "%h437",   (logic_pkt(pkt)[127:108] + logic_pkt(pkt)[107]) );
  $fdisplay( file_handle, "%h40413",  logic_pkt(pkt)[107:96] );
  $fdisplay( file_handle, "01041413" );
  $fdisplay( file_handle, "01041413" );
  $fdisplay( file_handle, "00000f93" );
  $fdisplay( file_handle, "%hfb7",   (logic_pkt(pkt)[95:76] + logic_pkt(pkt)[75]) );
  $fdisplay( file_handle, "%hf8f93",  logic_pkt(pkt)[75:64] );
  $fdisplay( file_handle, "01f46433" );
  $fdisplay( file_handle, "0080b423" );
  //$fdisplay( file_handle, "%h", logic_pkt(pkt)[184:128] );
  $fdisplay( file_handle, "%h537",   ({ {7{1'b0}}, logic_pkt(pkt)[184:172] } + logic_pkt(pkt)[171])  );
  $fdisplay( file_handle, "%h50513",               logic_pkt(pkt)[171:160] );
  $fdisplay( file_handle, "01051513" );
  $fdisplay( file_handle, "01051513" );
  $fdisplay( file_handle, "00000f93" );
  $fdisplay( file_handle, "%hfb7",   (logic_pkt(pkt)[159:140] + logic_pkt(pkt)[139]) );
  $fdisplay( file_handle, "%hf8f93",  logic_pkt(pkt)[139:128] );
  $fdisplay( file_handle, "01f56533" );
  $fdisplay( file_handle, "00a0b823" );
  // Advance x1 += 24 (h1018)
  $fdisplay( file_handle, "01808093" );
  $fclose(file_handle);

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
  integer file_handle;

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

  file_handle = $fopen("output.txt", "a");
  //$fdisplay( file_handle, "%h", logic_pkt(pkt)[63:0] );
  $fdisplay( file_handle, "%h3b7",   (logic_pkt(pkt)[63:44] + logic_pkt(pkt)[43]) );
  $fdisplay( file_handle, "%h38393",  logic_pkt(pkt)[43:32] );
  $fdisplay( file_handle, "01039393" );
  $fdisplay( file_handle, "01039393" );
  $fdisplay( file_handle, "00000f93" );
  $fdisplay( file_handle, "%hfb7",   (logic_pkt(pkt)[31:12] + logic_pkt(pkt)[11]) );
  $fdisplay( file_handle, "%hf8f93",  logic_pkt(pkt)[11:0] );
  $fdisplay( file_handle, "01f3e3b3" );
  $fdisplay( file_handle, "0070b023" );
  //$fdisplay( file_handle, "%h", logic_pkt(pkt)[127:64] );
  $fdisplay( file_handle, "%h437",   (logic_pkt(pkt)[127:108] + logic_pkt(pkt)[107]) );
  $fdisplay( file_handle, "%h40413",  logic_pkt(pkt)[107:96] );
  $fdisplay( file_handle, "01041413" );
  $fdisplay( file_handle, "01041413" );
  $fdisplay( file_handle, "00000f93" );
  $fdisplay( file_handle, "%hfb7",   (logic_pkt(pkt)[95:76] + logic_pkt(pkt)[75]) );
  $fdisplay( file_handle, "%hf8f93",  logic_pkt(pkt)[75:64] );
  $fdisplay( file_handle, "01f46433" );
  $fdisplay( file_handle, "0080b423" );
  //$fdisplay( file_handle, "%h", logic_pkt(pkt)[184:128] );
  $fdisplay( file_handle, "%h537",   ({ {7{1'b0}}, logic_pkt(pkt)[184:172] } + logic_pkt(pkt)[171])  );
  $fdisplay( file_handle, "%h50513",               logic_pkt(pkt)[171:160] );
  $fdisplay( file_handle, "01051513" );
  $fdisplay( file_handle, "01051513" );
  $fdisplay( file_handle, "00000f93" );
  $fdisplay( file_handle, "%hfb7",   (logic_pkt(pkt)[159:140] + logic_pkt(pkt)[139]) );
  $fdisplay( file_handle, "%hf8f93",  logic_pkt(pkt)[139:128] );
  $fdisplay( file_handle, "01f56533" );
  $fdisplay( file_handle, "00a0b823" );
  // Advance x1 += 24 (h1018)
  $fdisplay( file_handle, "01808093" );
  $fclose(file_handle);

  return pkt;
endfunction

function automatic logic [185-1:0] logic_pkt (IntraCgraPacket_4_2x2_16_8_2_CgraPayload__432fde8bfb7da0ed p);
logic_pkt = {
// Header (MSB->LSB order)
p.src,
p.dst,
p.src_cgra_id,
p.dst_cgra_id,
p.src_cgra_x,
p.src_cgra_y,
p.dst_cgra_x,
p.dst_cgra_y,
p.opaque,
p.vc_id,
// Payload
p.payload.cmd,
p.payload.data.payload,
p.payload.data.predicate,
p.payload.data.bypass,
p.payload.data.delay,
p.payload.data_addr,
p.payload.ctrl.operation,
p.payload.ctrl.fu_in,
p.payload.ctrl.routing_xbar_outport,
p.payload.ctrl.fu_xbar_outport,
p.payload.ctrl.vector_factor_power,
p.payload.ctrl.is_last_ctrl,
p.payload.ctrl.write_reg_from,
p.payload.ctrl.write_reg_idx,
p.payload.ctrl.read_reg_from,
p.payload.ctrl.read_reg_idx,
p.payload.ctrl_addr
};
endfunction

