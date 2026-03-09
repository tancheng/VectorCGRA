"""
==========================================================================
messages.py
==========================================================================
Collection of messages definition.

Convention: The fields/constructor arguments should appear in the order
            of [ payload_nbits, predicate_nbits ]

Author : Cheng Tan
  Date : Dec 3, 2019
"""
from pymtl3 import *
from .cmd_type import *
from .opt_type import *
from ..lib.util.common import *

#=========================================================================
# Generic data message
#=========================================================================

def mk_data(payload_nbits=16, predicate_nbits=1, bypass_nbits=1,
            prefix="CgraData"):

  PayloadType   = mk_bits( payload_nbits   )
  PredicateType = mk_bits( predicate_nbits )
  BypassType    = mk_bits( bypass_nbits )
  DelayType     = mk_bits( 1 )

  new_name = f"{prefix}_{payload_nbits}_{predicate_nbits}_{bypass_nbits}_1"

  def str_func( s ):
    return f"{s.payload}.{s.predicate}.{s.bypass}.{s.delay}"

  return mk_bitstruct( new_name, {
      'payload'  : PayloadType,
      'predicate': PredicateType,
      'bypass'   : BypassType,
      'delay'    : DelayType,
    },
    namespace = { '__str__': str_func }
  )

#=========================================================================
# Predicate signal
#=========================================================================

def mk_predicate( payload_nbits=1, predicate_nbits=1, prefix="CGRAData" ):

  PayloadType   = mk_bits( payload_nbits   )
  PredicateType = mk_bits( predicate_nbits )

  new_name = f"{prefix}_{payload_nbits}_{predicate_nbits}"

  def str_func( s ):
    return f"{s.payload}.{s.predicate}"

  return mk_bitstruct( new_name, {
      'payload'  : PayloadType,
      'predicate': PredicateType,
    },
    namespace = { '__str__': str_func }
  )

#=========================================================================
# Generic config message
#=========================================================================

def mk_ctrl(num_fu_inports = 4,
            num_fu_outports = 2,
            num_tile_inports = 5,
            num_tile_outports = 5,
            num_registers_per_reg_bank = 16,
            prefix = "CGRAConfig"):
  operation_nbits = clog2(NUM_OPTS)
  OperationType = mk_bits(operation_nbits)
  TileInportsType = mk_bits(clog2(num_tile_inports  + 1))
  TileOutportsType = mk_bits(clog2(num_tile_outports + 1))
  num_routing_outports = num_tile_outports + num_fu_inports
  RoutingOutportsType = mk_bits(clog2(num_routing_outports + 1))
  FuInType = mk_bits(clog2(num_fu_inports + 1))
  FuOutType = mk_bits(clog2(num_fu_outports + 1))
  predicate_nbits = 1
  PredicateType = mk_bits(predicate_nbits)
  vector_factor_power_nbits = 3
  VectorFactorPowerType = mk_bits(vector_factor_power_nbits)
  # 3 inports of register file bank.
  RegFromType = mk_bits(2)
  RegIdxType = mk_bits(clog2(num_registers_per_reg_bank))

  new_name = f"{prefix}_{operation_nbits}_{num_fu_inports}_" \
             f"{num_fu_outports}_{num_tile_inports}_" \
             f"{num_tile_outports}_{predicate_nbits}_" \
             f"{vector_factor_power_nbits}"

  def str_func(s):
    out_str = '(fu_in)'
    for i in range(num_fu_inports):
      if i != 0:
        out_str += '-'
      out_str += str(int(s.fu_in[i]))

    out_str += '|(predicate)'
    out_str += str(int(s.predicate))

    out_str += '|(routing_xbar_out)'
    for i in range(num_routing_outports):
      if i != 0:
        out_str += '-'
      out_str += str(int(s.routing_xbar_outport[i]))

    out_str += '|(fu_xbar_out)'
    for i in range(num_routing_outports):
      if i != 0:
        out_str += '-'
      out_str += str(int(s.fu_xbar_outport[i]))

    out_str += '|(predicate_in)'
    for i in range(num_tile_inports):
      if i != 0:
        out_str += '-'
      out_str += str(int(s.routing_predicate_in[i]))

    out_str += '|(vector_factor_power)'
    out_str += str(int(s.vector_factor_power))

    out_str += '|(is_last_ctrl)'
    out_str += str(int(s.is_last_ctrl))

    out_str += '|(read_reg_from)'
    for i in range(num_fu_inports):
      if i != 0:
        out_str += '-'
      out_str += str(int(s.read_reg_from[i]))

    out_str += '|(write_reg_from)'
    for i in range(num_fu_inports):
      if i != 0:
        out_str += '-'
      out_str += str(int(s.write_reg_from[i]))

    out_str += '|(write_reg_idx)'
    for i in range(num_fu_inports):
      if i != 0:
        out_str += '-'
      out_str += str(int(s.write_reg_idx[i]))

    out_str += '|(read_reg_idx)'
    for i in range(num_fu_inports):
      if i != 0:
        out_str += '-'
      out_str += str(int(s.read_reg_idx[i]))

    return f"(opt){s.operation}|{out_str}"

  field_dict = {}
  field_dict['operation'] = OperationType
  # TODO: need fix to pair `predicate` with specific operation.
  # The 'predicate' indicates whether the current operation is based on
  # the partial predication or not. Note that 'predicate' is different
  # from the following 'predicate_in', which contributes to the 'predicate'
  # at the next cycle.
  field_dict['predicate'] = PredicateType
  # The fu_in indicates the input register ID (i.e., operands) for the
  # operation.
  field_dict['fu_in'] = [FuInType for _ in range(num_fu_inports)]

  field_dict['routing_xbar_outport'] = [TileInportsType for _ in range(
      num_routing_outports)]
  field_dict['fu_xbar_outport'] = [FuOutType for _ in range(
      num_routing_outports)]
  # I assume one tile supports single predicate during the entire execution
  # time, as it is hard to distinguish predication for different operations
  # (we automatically update, i.e., 'or', the predicate stored in the
  # predicate register). This should be guaranteed by the compiler.
  field_dict['routing_predicate_in'] = [PredicateType for _ in range(
      num_tile_inports)]

  field_dict['vector_factor_power'] = VectorFactorPowerType

  field_dict['is_last_ctrl'] = b1

  # Register file related signals.
  # Indicates whether to write data into the register bank, and the
  # corresponding inport.
  field_dict['write_reg_from'] = [RegFromType for _ in range(num_fu_inports)]
  field_dict['write_reg_idx'] = [RegIdxType for _ in range(num_fu_inports)]
  # Indicates whether to read data from the register bank.
  field_dict['read_reg_from'] = [b1 for _ in range(num_fu_inports)]
  field_dict['read_reg_idx'] = [RegIdxType for _ in range(num_fu_inports)]

  # TODO: to support multiple predicate
  # field_dict[ 'predicate_in0' ] = ...
  # field_dict[ 'predicate_in1' ] = ...

  return mk_bitstruct( new_name, field_dict,
    namespace = { '__str__': str_func }
  )

#=========================================================================
# Cmd message
#=========================================================================

def mk_cmd(num_commands = 12,
           prefix="CgraCommand"):

  CmdType = mk_bits(clog2(num_commands))

  new_name = f"{num_commands}"

  def str_func(s):
    return f"{s.cmd}"

  return mk_bitstruct(new_name, {
      'cmd': CmdType,
    },
    namespace = {'__str__': str_func}
  )

#=========================================================================
# Multi-cgra oriented inter-/intra-cgra data/config/cmd packet payload
#=========================================================================

def mk_cgra_payload(DataType,
                    DataAddrType,
                    CtrlType,
                    CtrlAddrType,
                    prefix="MultiCgraPayload"):

  new_name = f"{prefix}_Cmd_Data_DataAddr_Ctrl_CtrlAddr"

  field_dict = {}
  field_dict['cmd'] = mk_bits(clog2(NUM_CMDS))
  field_dict['data'] = DataType
  field_dict['data_addr'] = DataAddrType
  field_dict['ctrl'] = CtrlType
  field_dict['ctrl_addr'] = CtrlAddrType

  def str_func(s):
      return f"MultiCgraNocPayload: cmd:{s.cmd}|data:{s.data}|data_addr:{s.data_addr}|" \
             f"ctrl:{s.ctrl}|ctrl_addr:{s.ctrl_addr}\n"

  return mk_bitstruct(new_name, field_dict,
    namespace = {'__str__': str_func}
  )

#=========================================================================
# For both ring- and mesh-based multi-cgra NoC packet.
#=========================================================================

def mk_inter_cgra_pkt(num_cgra_columns,
                      num_cgra_rows,
                      num_tiles,
                      CgraPayloadType,
                      prefix="InterCgraPacket"):

  CgraIdType = mk_bits(max(clog2(num_cgra_columns * num_cgra_rows), 1))
  CgraXType = mk_bits(max(clog2(num_cgra_columns), 1))
  CgraYType = mk_bits(max(clog2(num_cgra_rows), 1))
  # An additional router for controller to receive CMD_COMPLETE signal from Ring to CPU.
  TileIdType = mk_bits(clog2(num_tiles + 1))
  opaque_nbits = 8
  OpqType = mk_bits(opaque_nbits)
  num_vcs = 4
  VcIdType = mk_bits(clog2(num_vcs))

  new_name = f"{prefix}_{num_cgra_columns*num_cgra_rows}_" \
             f"{num_cgra_columns}x{num_cgra_rows}_{num_tiles}_" \
             f"{opaque_nbits}_{num_vcs}_CgraPayload"

  field_dict = {}
  field_dict['src'] = CgraIdType
  field_dict['dst'] = CgraIdType
  field_dict['src_x'] = CgraXType
  field_dict['src_y'] = CgraYType
  field_dict['dst_x'] = CgraXType
  field_dict['dst_y'] = CgraYType
  field_dict['src_tile_id'] = TileIdType
  field_dict['dst_tile_id'] = TileIdType
  field_dict['opaque'] = OpqType
  field_dict['vc_id'] = VcIdType
  field_dict['payload'] = CgraPayloadType

  def str_func(s):
    return f"InterCgraPkt: {s.src}->{s.dst} || " \
           f"({s.src_x},{s.src_y})->({s.dst_x},{s.dst_y}) || " \
           f"tileid:{s.src_tile_id}->{s.dst_tile_id} || " \
           f"{s.opaque}:{s.vc_id} || " \
           f"payload:{s.payload}\n"

  return mk_bitstruct(new_name, field_dict,
    namespace = {'__str__': str_func}
  )

#=========================================================================
# For intra-cgra (i.e., inter-tile) packet, mainly used for delivering
# ctrl signal related messages.
#=========================================================================

def mk_intra_cgra_pkt(num_cgra_columns,
                      num_cgra_rows,
                      num_tiles,
                      CgraPayloadType,
                      prefix="IntraCgraPacket"):

  CgraIdType = mk_bits(max(clog2(num_cgra_columns * num_cgra_rows), 1))
  CgraXType = mk_bits(max(clog2(num_cgra_columns), 1))
  CgraYType = mk_bits(max(clog2(num_cgra_rows), 1))
  # An additional router for controller to receive CMD_COMPLETE signal from Ring to CPU.
  TileIdType = mk_bits(clog2(num_tiles + 1))
  opaque_nbits = 8
  OpqType = mk_bits(opaque_nbits)
  num_vcs = 2
  VcIdType = mk_bits(clog2(num_vcs))

  new_name = f"{prefix}_{num_cgra_columns*num_cgra_rows}_" \
             f"{num_cgra_columns}x{num_cgra_rows}_{num_tiles}_" \
             f"{opaque_nbits}_{num_vcs}_CgraPayload"

  def str_func(s):
    return f"IntraCgraPkt: {s.src}->{s.dst} || " \
           f"cgra_id:{s.src_cgra_id}({s.src_cgra_x}, {s.src_cgra_y})->{s.dst_cgra_id}({s.dst_cgra_x}, {s.dst_cgra_y}) || " \
           f"{s.opaque}:{s.vc_id} || " \
           f"payload:{s.payload}\n"

  field_dict = {}
  field_dict['src'] = TileIdType
  field_dict['dst'] = TileIdType
  field_dict['src_cgra_id'] = CgraIdType
  field_dict['dst_cgra_id'] = CgraIdType
  field_dict['src_cgra_x'] = CgraXType
  field_dict['src_cgra_y'] = CgraYType
  field_dict['dst_cgra_x'] = CgraXType
  field_dict['dst_cgra_y'] = CgraYType
  field_dict['opaque'] = OpqType
  field_dict['vc_id'] = VcIdType
  field_dict['payload'] = CgraPayloadType

  return mk_bitstruct(new_name, field_dict,
    namespace = {'__str__': str_func}
  )

#=========================================================================
# STEP Specific
#=========================================================================

def mk_cpu_pkt(CfgPayloadType,
                prefix="CpuPkt"):

    CmdType = mk_bits(max(1, NUM_CMDS))

    new_name = f"{prefix}_n_tiles"

    def str_func(s):
        return f"CpuPkt: bitstream:{s.cmd}\n"

    field_dict = {}
    field_dict['cmd'] = CmdType
    field_dict['cfg'] = CfgPayloadType
    

    return mk_bitstruct(new_name, field_dict,
        namespace = {'__str__': str_func}
)

def mk_cfg_pkt(BitstreamType,
                CfgMetadataType,
                prefix="CfgPkt"):

    new_name = f"{prefix}"

    def str_func(s):
        return f"CfgPkt: string output\n"

    field_dict = {}
    field_dict['bitstream'] = BitstreamType
    field_dict['metadata'] = CfgMetadataType

    return mk_bitstruct(new_name, field_dict,
        namespace = {'__str__': str_func}
)


def mk_cfg_metadata_pkt(
                        num_tiles,
                        num_consts,
                        num_rd_ports,
                        num_wr_ports,
                        num_ld_ports,
                        num_st_ports,
                        DataType,
                        RegAddrType,
                        PredAddrType,
                        CfgTokenizerType,
                        prefix="CfgMetadataPkt"):
    
    ThreadCountType = mk_bits(clog2(MAX_THREAD_COUNT))
    CfgIdType = mk_bits(clog2(MAX_BITSTREAM_COUNT))
    CmdType = mk_bits(max(1, NUM_CMDS))

    new_name = f"{prefix}_{num_rd_ports}_{num_wr_ports}"

    def str_func(s):
        return f"CfgMetadataPkt: cfg_id [{s.cfg_id}, br_id: {s.br_id}, thread_count: {s.thread_count}, start_cfg: {s.start_cfg}, end_cfg: {s.end_cfg}]\n"

    field_dict = {}
    # TODO @darrenl pred_tile_valid is whether the immediate rf predicate is 0 or 1. should be address instead
    field_dict['cmd'] = CmdType
    field_dict['tile_load_count'] = mk_bits(clog2(num_tiles+1))
    field_dict['pred_tile_valid'] = [Bits1 for _ in range(num_tiles)]
    field_dict['ld_enable'] = [Bits1 for _ in range(num_ld_ports)]
    field_dict['st_enable'] = [Bits1 for _ in range(num_st_ports)]
    field_dict['ld_reg_addr'] = [RegAddrType for _ in range(num_ld_ports)]
    field_dict['in_regs'] = [RegAddrType for _ in range(num_rd_ports)]
    field_dict['in_regs_val'] = [Bits1 for _ in range(num_rd_ports)]
    field_dict['in_tid_enable'] = [Bits1 for _ in range(num_rd_ports)]
    field_dict['out_regs'] = [RegAddrType for _ in range(num_wr_ports)]
    field_dict['out_regs_val'] = [Bits1 for _ in range(num_wr_ports)]
    field_dict['out_pred_regs'] = [PredAddrType for _ in range(num_wr_ports)]
    field_dict['out_pred_regs_val'] = [Bits1 for _ in range(num_wr_ports)]
    field_dict['tokenizer_cfg'] = CfgTokenizerType
    field_dict['cfg_id'] = CfgIdType
    field_dict['br_id'] = CfgIdType
    field_dict['thread_count'] = ThreadCountType
    field_dict['start_cfg'] = Bits1
    field_dict['end_cfg'] = Bits1
    # Branching / predication control
    field_dict['branch_en'] = Bits1
    field_dict['branch_has_else'] = Bits1
    field_dict['branch_backedge_sel'] = mk_bits(2)
    field_dict['pred_reg_id'] = PredAddrType
    field_dict['branch_true_cfg_id'] = CfgIdType
    field_dict['branch_false_cfg_id'] = CfgIdType
    field_dict['reconverge_cfg_id'] = CfgIdType
    # Loop control
    field_dict['loop_en'] = Bits1
    field_dict['loop_start_cfg_id'] = CfgIdType
    field_dict['loop_exit_cfg_id'] = CfgIdType
    field_dict['loop_max'] = ThreadCountType

    return mk_bitstruct(new_name, field_dict,
        namespace = {'__str__': str_func}
)

def mk_cfg_tokenizer_pkt(num_taker_ports,
                        num_returner_ports,
                        max_delay,
                        PortRouteType,
                        PortDelayType,
                        prefix="TokenizerCfgPkt"
                        ):
    new_name = f"{prefix}"

    # Additional for 0th index = Unused Port
    # PortRouteType Convention => [rf_wr_port_0, rf_wr_port_1, ld_port0, ld_port1, st_port_0, st_port_1]

    def str_func(s):
        return f"TokenizerCfgPkt: \n"

    field_dict = {}
    field_dict['token_route_sink_enable'] = [PortRouteType for _ in range(num_taker_ports)]
    field_dict['token_route_delay_to_sink'] = [PortDelayType for _ in range(num_returner_ports)]

    return mk_bitstruct(new_name, field_dict,
        namespace = {'__str__': str_func}
)

def mk_pred_math_pkt(PredAddrType,
                        DataType,
                        OperationType,
                        prefix="PredMathPkt"
                        ):
    new_name = f"{prefix}"

    def str_func(s):
        return f"PredMathPkt: wr_addr: {s.wr_addr} | lhs: {s.lhs} | rhs: {s.rhs} | opt_type: {s.opt_type}\n"

    field_dict = {}
    field_dict['wr_addr'] = PredAddrType
    field_dict['lhs'] = DataType
    field_dict['rhs'] = DataType
    field_dict['opt_type'] = OperationType

    return mk_bitstruct(new_name, field_dict,
        namespace = {'__str__': str_func}
)

def mk_bitstream_pkt(num_tiles,
                    TileBitstreamType,
                    prefix="BitstreamPkt"):

    new_name = f"{prefix}_n_tiles_{num_tiles}"

    def str_func(s):
        return f"BitstreamPkt: bitstream\n"

    field_dict = {}
    field_dict['bitstream'] = [TileBitstreamType for _ in range(num_tiles)]

    return mk_bitstruct(new_name, field_dict,
        namespace = {'__str__': str_func}
)

def mk_ld_req_pkt(prefix="LdReqPkt"):

    new_name = f"{prefix}_n_tiles"

    def str_func(s):
        return f"LdReqPkt: bitstream:\n"

    AddrType = mk_bits( AXI_ADDR_BITWIDTH )
    IdType = mk_bits( clog2(MAX_THREAD_COUNT) )

    field_dict = {}
    field_dict['addr'] = AddrType
    field_dict['id'] = IdType

    return mk_bitstruct(new_name, field_dict,
        namespace = {'__str__': str_func}
)

def mk_ld_resp_pkt(DataType, prefix="LdRespPkt"):

    new_name = f"{prefix}_n_tiles"

    def str_func(s):
        return f"LdRespPkt: bitstream:\n"

    IdType = mk_bits( clog2(MAX_THREAD_COUNT) )

    field_dict = {}
    field_dict['data'] = DataType
    field_dict['id'] = IdType

    return mk_bitstruct(new_name, field_dict,
        namespace = {'__str__': str_func}
)

def mk_st_req_pkt(DataType,
                    prefix="StReqPkt"):

    new_name = f"{prefix}_n_tiles"

    def str_func(s):
        return f"StReqPkt: bitstream:\n"

    AddrType = mk_bits( AXI_ADDR_BITWIDTH )
    IdType = mk_bits( clog2(MAX_THREAD_COUNT) )

    field_dict = {}
    field_dict['addr'] = AddrType
    field_dict['data'] = DataType
    field_dict['id']   = IdType

    return mk_bitstruct(new_name, field_dict,
        namespace = {'__str__': str_func}
)

def mk_tile_bitstream_pkt(
                            num_tile_inports,
                            num_tile_outports,
                            num_fu_inports,
                            num_fu_outports,
                            TileIdType,
                            OperationType,
                            DataType,
                            RegAddrType,
                            PredRegAddrType,
                            prefix="TileBitstreamPkt"):
    new_name = f"{prefix}_{num_fu_inports}_{num_fu_outports}"

    def str_func(s):
        return f"TileBitstreamPkt: fu_in:{s.tile_in_route}|fu_out:{s.tile_out_route}|operation:{s.opt_type}\n"

    TilePortType = mk_bits( clog2(num_tile_inports + 1) )
    TileOutType = mk_bits( num_tile_outports )
    ShiftAmountType = mk_bits( clog2(SHIFT_REGISTER_SIZE) )

    # Tile routing:
    # 4 i/os, [No op, N, S, W, E]
    # 3 Fu inport and 1 Fu Outport
    # Ex: FMA with E * N + W & send W
    # field_dict['tile_in_route'] = [TilePortType(4), TilePortType(1), TilePortType(3)]
    # field_dict['tile_out_route'] = [TilePortType(3)]
    #
    # Ex: Mul with S * N & send N
    # field_dict['tile_in_route'] = [TilePortType(2), TilePortType(1), TilePortType(0)]
    # field_dict['tile_out_route'] = [TilePortType(1)]
    
    field_dict = {}
    field_dict['tile_id'] = TileIdType
    field_dict['tile_in_route'] = [TilePortType for _ in range(num_fu_inports)]
    field_dict['tile_out_route'] = TileOutType
    field_dict['tile_pred_route'] = TileOutType
    field_dict['tile_out_shift_amounts'] = [ShiftAmountType for _ in range(num_tile_outports)]
    field_dict['tile_fwd_route'] = [TileOutType for _ in range(num_tile_inports)]
    field_dict['const_val'] = DataType
    field_dict['pred_fwd_route'] = TilePortType
    field_dict['pred_gen'] = Bits1
    field_dict['opt_type'] = OperationType

    return mk_bitstruct(new_name, field_dict,
        namespace = {'__str__': str_func}
)

#=========================================================================
# Crossbar (tiles <-> SRAM) packet
#=========================================================================

# def mk_tile_sram_xbar_pkt(number_inports,
#                           number_outports,
#                           PyloadType,
#                           prefix="TileSramXbarPacket"):
#
#   SrcType = mk_bits(clog2(number_inports))
#   DstType = mk_bits(clog2(number_outports))
#
#   new_name = f"{prefix}_{number_inports}_{number_outports}_PayloadType"
#
#   def str_func(s):
#     return f"{s.src}>{s.dst}:(payload){s.payload}"
#
#   return mk_bitstruct(new_name, {
#       'src': SrcType,
#       'dst': DstType,
#       'payload': PayloadType,
#     },
#     namespace = {'__str__': str_func}
#   )

def mk_tile_sram_xbar_pkt(number_src = 5,
                          number_dst = 5,
                          mem_size_global = 64,
                          num_cgras = 4,
                          num_tiles = 17,
                          prefix="TileSramXbarPacket"):

  SrcType = mk_bits(clog2(number_src))
  DstType = mk_bits(clog2(number_dst))
  AddrType = mk_bits(clog2(mem_size_global))
  CgraIdType = mk_bits(max(1, clog2(num_cgras)))
  TileIdType = mk_bits(clog2(num_tiles + 1))

  new_name = f"{prefix}_{number_src}_{number_dst}_{mem_size_global}"

  def str_func(s):
    return f"{s.src}>{s.dst}:(addr){s.addr}.(src_cgra){s.src_cgra}.(src_tile){s.src_tile}"

  return mk_bitstruct(new_name, {
      'src': SrcType,
      'dst': DstType,
      'addr': AddrType,
      'src_cgra': CgraIdType,
      'src_tile': TileIdType,
    },
    namespace = {'__str__': str_func}
  )

#=========================================================================
# Crossbar (controller <-> NoC) packet
#=========================================================================

def mk_controller_noc_xbar_pkt(InterCgraPktType,
                               prefix="ControllerNocXbarPacket"):

  DstType = mk_bits(1) # clog2(number_outports))

  new_name = f"{prefix}_InterCgraPktType"

  def str_func(s):
    return f"->{s.dst}:(inter_cgra_pkt){s.inter_cgra_pkt}"

  return mk_bitstruct(new_name, {
      'dst': DstType,
      'inter_cgra_pkt': InterCgraPktType,
    },
    namespace = {'__str__': str_func}
  )
