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
  # 11 bits from above

  field_dict = {}
  field_dict['cmd'] = mk_bits(clog2(NUM_CMDS)) #4
  field_dict['data'] = DataType #35
  field_dict['data_addr'] = DataAddrType #7
  field_dict['ctrl'] = CtrlType #111
  field_dict['ctrl_addr'] = CtrlAddrType #3

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
  field_dict['src'] = CgraIdType # src CGRA id
  field_dict['dst'] = CgraIdType # dst CGRA id
  field_dict['src_x'] = CgraXType # CGRA 2d coordinates
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

  CgraIdType = mk_bits(max(clog2(num_cgra_columns * num_cgra_rows), 1)) #1
  CgraXType = mk_bits(max(clog2(num_cgra_columns), 1)) #1
  CgraYType = mk_bits(max(clog2(num_cgra_rows), 1)) #1
  # An additional router for controller to receive CMD_COMPLETE signal from Ring to CPU.
  TileIdType = mk_bits(clog2(num_tiles + 1)) # 3
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
  field_dict['src'] = TileIdType #3
  field_dict['dst'] = TileIdType #3
  field_dict['src_cgra_id'] = CgraIdType #1
  field_dict['dst_cgra_id'] = CgraIdType #1
  field_dict['src_cgra_x'] = CgraXType #1
  field_dict['src_cgra_y'] = CgraYType #1
  field_dict['dst_cgra_x'] = CgraXType #1
  field_dict['dst_cgra_y'] = CgraYType #1
  field_dict['opaque'] = OpqType #8
  field_dict['vc_id'] = VcIdType #1
  # 21 bits above
  field_dict['payload'] = CgraPayloadType

  return mk_bitstruct(new_name, field_dict,
    namespace = {'__str__': str_func}
  )

#=========================================================================
# STEP Specific
#=========================================================================

def mk_cpu_pkt(num_tiles,
                num_consts,
                num_rd_regs,
                num_wr_regs,
                ConstDataType,
                RegAddrType,
                CfgIdType,
                CfgPayloadType,
                prefix="CpuPkt"):

    CmdType = mkbits(max(1, NUM_CMDS))

    new_name = f"{prefix}_n_tiles[{num_tiles}]"

    def str_func(s):
        return f"CpuPkt: bitstream:{s.cfgs}\n"

    field_dict = {}
    field_dict['cmd'] = CmdType
    field_dict['cfg'] = CfgPayloadType
    

    return mk_bitstruct(new_name, field_dict,
        namespace = {'__str__': str_func}
)

def mk_cfg_pkt(BitstreamType,
                     CfgMetadataPkt,
                     prefix="CfgPkt"):

    new_name = f"{prefix}"

    def str_func(s):
        return f"CfgPkt: string output\n"

    field_dict = {}
    field_dict['bitstream'] = BitstreamType
    field_dict['metadata'] = CfgMetadataPkt
    

    return mk_bitstruct(new_name, field_dict,
        namespace = {'__str__': str_func}
)


def mk_cfg_metadata_pkt(num_tiles,
                        num_consts,
                        num_rd_regs,
                        num_wr_regs,
                        ConstDataType,
                        RegAddrType,
                        BitstreamType,
                        prefix="CfgMetadataPkt"):
    
    ThreadCountType = mkbits(clog2(MAX_THREAD_COUNT))
    CfgIdType = mkbits(clog2(MAX_BITSTREAM_SIZE))

    new_name = f"{prefix}_{num_rd_regs}_{num_wr_regs}"

    def str_func(s):
        return f"CfgMetadataPkt: cfg_id [{s.cfg_id}, br_id: {s.br_id}, thread_count: {s.thread_count}, start_cfg: {s.start_cfg}, end_cfg: {s.end_cfg}]\n"

    field_dict = {}
    field_dict['const'] = [ConstDataType for _ in range(num_consts)]
    field_dict['in_regs'] = [RegAddrType for _ in range(num_rd_regs)]
    field_dict['out_regs'] = [RegAddrType for _ in range(num_wr_regs)]
    field_dict['cfg_id'] = CfgIdType
    field_dict['br_id'] = CfgIdType
    field_dict['thread_count'] = ThreadCountType
    field_dict['start_cfg'] = b(1)
    field_dict['end_cfg'] = b(1)

    return mk_bitstruct(new_name, field_dict,
        namespace = {'__str__': str_func}
)

def mk_bitstream_pkt(num_tiles,
                    TileBitstreamType,
                    prefix="BitstreamPkt"):

    new_name = f"{prefix}_n_tiles[{num_tiles}]_BitstreamPayload"

    def str_func(s):
        return f"BitstreamPkt: bitstream:{s.bitstream}\n"

    field_dict = {}
    field_dict['bitstream'] = [TileBitstreamType for _ in range(num_tiles)]

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

