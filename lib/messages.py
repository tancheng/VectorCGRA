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

#=========================================================================
# Generic data message
#=========================================================================

def mk_data( payload_nbits=16, predicate_nbits=1, bypass_nbits=1,
             prefix="CGRAData" ):

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

def mk_ctrl(num_fu_in = 2, num_inports = 5, num_outports = 5,
            prefix = "CGRAConfig"):

  ctrl_nbits = 6
  CtrlType = mk_bits(ctrl_nbits)
  InportsType = mk_bits(clog2(num_inports + 1))
  OutportsType = mk_bits(clog2(num_outports + 1))
  FuInType = mk_bits(clog2(num_fu_in + 1))
  predicate_nbits = 1
  PredicateType = mk_bits(predicate_nbits)
  vector_factor_power_nbits = 3
  VectorFactorPowerType = mk_bits(vector_factor_power_nbits)

  new_name = f"{prefix}_{ctrl_nbits}_{num_fu_in}_{num_inports}_" \
             f"{num_outports}_{predicate_nbits}_" \
             f"{vector_factor_power_nbits}"

  def str_func(s):
    out_str = '(in)'

    for i in range(num_fu_in):
      if i != 0:
        out_str += '-'
      out_str += str(int(s.fu_in[i]))

    out_str += '|(p)'
    out_str += str(int(s.predicate))

    out_str += '|(out)'
    for i in range(num_outports):
      if i != 0:
        out_str += '-'
      out_str += str(int(s.outport[i]))

    out_str += '|(p_in)'
    for i in range(num_inports):
      if i != 0:
        out_str += '-'
      out_str += str(int(s.predicate_in[i]))

    out_str += '|(vector_factor_power)'
    out_str += str(int(s.vector_factor_power))

    out_str += '|(is_last_ctrl)'
    out_str += str(int(s.is_last_ctrl))

    return f"(opt){s.ctrl}|{out_str}"

  field_dict = {}
  field_dict['ctrl'] = CtrlType
  # The 'predicate' indicates whether the current operation is based on
  # the partial predication or not. Note that 'predicate' is different
  # from the following 'predicate_in', which contributes to the
  # 'predicate' at the next cycle.
  field_dict['predicate'] = PredicateType
  # The fu_in indicates the input register ID (i.e., operands) for the
  # operation.
  field_dict['fu_in'] = [FuInType for _ in range(num_fu_in)]

  field_dict['outport'] = [InportsType for _ in range(num_outports)]
  # I assume one tile supports single predicate during the entire
  # execution time, as it is hard to distinguish predication for
  # different operations (we automatically update, i.e., 'or', the
  # predicate stored in the predicate register). This should be
  # guaranteed by the compiler.
  field_dict['predicate_in'] = [PredicateType for _ in range(
      num_inports)] 

  field_dict['vector_factor_power'] = VectorFactorPowerType

  field_dict['is_last_ctrl'] = b1

  # TODO: to support multiple predicate
  # field_dict[ 'predicate_in0' ] = ...
  # field_dict[ 'predicate_in1' ] = ...

  return mk_bitstruct(new_name, field_dict,
    namespace = {'__str__': str_func}
  )


def mk_separate_ctrl(num_operations = 7,
                     num_fu_inports = 4,
                     num_fu_outports = 2,
                     num_tile_inports = 5,
                     num_tile_outports = 5,
                     prefix = "CGRAConfig"):
  operation_nbits = clog2(num_operations)
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

    # out_str = '|(fu_out)'
    # for i in range(num_fu_out):
    #   if i != 0:
    #     out_str += '-'
    #   out_str += str(int(s.fu_out[i]))

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

    return f"(opt){s.ctrl}|{out_str}"

  field_dict = {}
  field_dict['ctrl'] = OperationType
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

  # TODO: to support multiple predicate
  # field_dict[ 'predicate_in0' ] = ...
  # field_dict[ 'predicate_in1' ] = ...

  return mk_bitstruct( new_name, field_dict,
    namespace = { '__str__': str_func }
  )


#=========================================================================
# Cmd message
#=========================================================================

def mk_cmd(cmd_nbits = 6,
           prefix="CommandMessage"):

  CmdType = mk_bits(clog2(cmd_nbits))

  new_name = f"{cmd}"

  def str_func(s):
    return f"{s.cmd}"

  return mk_bitstruct(new_name, {
      'cmd': CmdType,
    },
    namespace = {'__str__': str_func}
  )

#=========================================================================
# Ring multi-CGRA data/config/cmd packet
#=========================================================================

def mk_ring_multi_cgra_pkt(nrouters = 4, opaque_nbits = 8, vc = 2,
                           cmd_nbits = 6, addr_nbits = 16,
                           data_nbits = 16, predicate_nbits = 1,
                           prefix="RingMultiCGRAPacket"):

  IdType = mk_bits(clog2(nrouters))
  OpqType = mk_bits(opaque_nbits)
  CmdType = mk_bits(cmd_nbits)
  AddrType = mk_bits(addr_nbits)
  DataType = mk_bits(data_nbits)
  PredicateType = mk_bits(predicate_nbits)

  new_name = f"{prefix}_{nrouters}_{vc}_{opaque_nbits}_{cmd_nbits}_" \
             f"{addr_nbits}_{data_nbits}_{predicate_nbits}"

  if vc > 1:
    VcIdType = mk_bits(clog2(vc))

    def str_func(s):
      return f"{s.src}>{s.dst}:{s.opaque}:{s.vc_id}:{s.cmd}." \
             f"{s.addr}.{s.data}.{s.predicate}"

    return mk_bitstruct(new_name, {
        'src': IdType,
        'dst': IdType,
        'opaque': OpqType,
        'vc_id': VcIdType,
        'cmd': CmdType,
        'addr': AddrType,
        'data': DataType,
        'predicate': PredicateType,
      },
      namespace = {'__str__': str_func}
    )

  else:
    def str_func(s):
      return f"{s.src}>{s.dst}:{s.opaque}:{s.cmd}.{s.addr}.{s.data}." \
             f"{s.predicate}"

    return mk_bitstruct(new_name, {
        'src': IdType,
        'dst': IdType,
        'opaque': OpqType,
        'cmd': CmdType,
        'addr': AddrType,
        'data': DataType,
        'predicate': PredicateType,
      },
      namespace = {'__str__': str_func}
    )

#=========================================================================
# Mesh multi-CGRA data/config/cmd packet
#=========================================================================

def mk_multi_cgra_noc_pkt(ncols = 2, nrows = 2, opaque_nbits = 8, vc = 2,
                          cmd_nbits = 6, addr_nbits = 16,
                          data_nbits = 16, predicate_nbits = 1,
                          prefix="MeshMultiCGRAPacket"):

  IdType = mk_bits(max(clog2(ncols * nrows), 1))
  XType = mk_bits(max(clog2(ncols), 1))
  YType = mk_bits(max(clog2(nrows), 1))
  OpqType = mk_bits(opaque_nbits)
  CmdType = mk_bits(cmd_nbits)
  AddrType = mk_bits(addr_nbits)
  DataType = mk_bits(data_nbits)
  PredicateType = mk_bits(predicate_nbits)
  PayloadType = mk_bits(1)

  new_name = f"{prefix}_{ncols*nrows}_{ncols}x{nrows}_{vc}_{opaque_nbits}_" \
             f"{cmd_nbits}_{addr_nbits}_{data_nbits}_{predicate_nbits}_1"

  if vc > 1:
    VcIdType = mk_bits(clog2(vc))

    def str_func(s):
      return f"{s.src}>{s.dst}&{s.src_x},{s.src_y}>{s.dst_x},{s.dst_y}:" \
             f"{s.opaque}:{s.vc_id}:{s.cmd}.{s.addr}.{s.data}.{s.predicate}." \
             f"{s.payload}"

    return mk_bitstruct(new_name, {
        'src': IdType,
        'dst': IdType,
        'src_x': XType,
        'src_y': YType,
        'dst_x': XType,
        'dst_y': YType,
        'opaque': OpqType,
        'vc_id': VcIdType,
        'cmd': CmdType,
        'addr': AddrType,
        'data': DataType,
        'predicate': PredicateType,
        'payload': PayloadType,
      },
      namespace = {'__str__': str_func}
    )

  else:
    def str_func(s):
      return f"{s.src}>{s.dst}&{s.src_x},{s.src_y}>{s.dst_x},{s.dst_y}:" \
             f"{s.opaque}:{s.cmd}.{s.addr}.{s.data}.{s.predicate}.{s.payload}"

    return mk_bitstruct(new_name, {
        'src': IdType,
        'dst': IdType,
        'src_x': XType,
        'src_y': YType,
        'dst_x': XType,
        'dst_y': YType,
        'opaque': OpqType,
        'cmd': CmdType,
        'addr': AddrType,
        'data': DataType,
        'predicate': PredicateType,
        'payload': PayloadType,
      },
      namespace = {'__str__': str_func}
    )

#=========================================================================
# Ring for delivering ctrl signals and commands across tiles
#=========================================================================

def mk_ring_across_tiles_pkt(nrouters = 4,
                             ctrl_actions = 8,
                             ctrl_mem_size = 4,
                             ctrl_operations = 7,
                             ctrl_fu_inports = 4,
                             ctrl_fu_outports = 4,
                             ctrl_tile_inports = 5,
                             ctrl_tile_outports = 5,
                             prefix="RingAcrossTilesPacket"):

  IdType = mk_bits(clog2(nrouters))
  opaque_nbits = 1
  OpqType = mk_bits(opaque_nbits)
  CtrlActionType = mk_bits(clog2(ctrl_actions))
  CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
  CtrlOperationType = mk_bits(clog2(ctrl_operations))
  CtrlTileInType = mk_bits(clog2(ctrl_tile_inports  + 1))
  CtrlTileOutType = mk_bits(clog2(ctrl_tile_outports + 1))
  num_routing_outports = ctrl_tile_outports + ctrl_fu_inports
  CtrlRoutingOutType = mk_bits(clog2(num_routing_outports + 1))
  CtrlFuInType = mk_bits(clog2(ctrl_fu_inports + 1))
  CtrlFuOutType = mk_bits(clog2(ctrl_fu_outports + 1))
  CtrlPredicateType = mk_bits(1)
  VcIdType = mk_bits(1)

  new_name = f"{prefix}_{nrouters}_{opaque_nbits}_{ctrl_actions}_" \
             f"{ctrl_mem_size}_{ctrl_operations}_{ctrl_fu_inports}_"\
             f"{ctrl_fu_outports}_{ctrl_tile_inports}_{ctrl_tile_outports}"

  def str_func(s):
    out_str = '(ctrl_operation)' + str(s.ctrl_operation)
    out_str += '|(ctrl_fu_in)'
    for i in range(ctrl_fu_inports):
      if i != 0:
        out_str += '-'
      out_str += str(int(s.ctrl_fu_in[i]))

    out_str += '|(ctrl_predicate)'
    out_str += str(int(s.ctrl_predicate))

    out_str += '|(ctrl_routing_xbar_out)'
    for i in range(num_routing_outports):
      if i != 0:
        out_str += '-'
      out_str += str(int(s.ctrl_routing_xbar_outport[i]))

    out_str += '|(ctrl_fu_xbar_out)'
    for i in range(num_routing_outports):
      if i != 0:
        out_str += '-'
      out_str += str(int(s.ctrl_fu_xbar_outport[i]))

    out_str += '|(ctrl_predicate_in)'
    for i in range(ctrl_tile_inports):
      if i != 0:
        out_str += '-'
      out_str += str(int(s.ctrl_routing_predicate_in[i]))

    return f"{s.src}>{s.dst}:{s.opaque}:{s.ctrl_action}.{s.ctrl_addr}." \
           f"{out_str}"

  field_dict = {}
  field_dict['src'] = IdType
  field_dict['dst'] = IdType
  field_dict['opaque'] = OpqType
  field_dict['vc_id'] = VcIdType
  field_dict['ctrl_action'] = CtrlActionType
  field_dict['ctrl_addr'] = CtrlAddrType
  field_dict['ctrl_operation'] = CtrlOperationType
  # TODO: need fix to pair `predicate` with specific operation.
  # The 'predicate' indicates whether the current operation is based on
  # the partial predication or not. Note that 'predicate' is different
  # from the following 'predicate_in', which contributes to the 'predicate'
  # at the next cycle.
  field_dict['ctrl_predicate'] = CtrlPredicateType
  # The fu_in indicates the input register ID (i.e., operands) for the
  # operation.
  field_dict['ctrl_fu_in'] = [CtrlFuInType for _ in range(ctrl_fu_inports)]

  field_dict['ctrl_routing_xbar_outport'] = [CtrlTileInType for _ in range(
      num_routing_outports)]
  field_dict['ctrl_fu_xbar_outport'] = [CtrlFuOutType for _ in range(
      num_routing_outports)]
  # I assume one tile supports single predicate during the entire execution
  # time, as it is hard to distinguish predication for different operations
  # (we automatically update, i.e., 'or', the predicate stored in the
  # predicate register). This should be guaranteed by the compiler.
  field_dict['ctrl_routing_predicate_in'] = [CtrlPredicateType for _ in range(
      ctrl_tile_inports)]

  return mk_bitstruct(new_name, field_dict,
    namespace = {'__str__': str_func}
  )

#=========================================================================
# Crossbar (tiles <-> SRAM) packet
#=========================================================================

def mk_tile_sram_xbar_pkt(number_src = 5, number_dst = 5,
                          mem_size_global = 64,
                          prefix="TileSramXbarPacket"):

  SrcType = mk_bits(clog2(number_src))
  DstType = mk_bits(clog2(number_dst))
  AddrType = mk_bits(clog2(mem_size_global))

  new_name = f"{prefix}_{number_src}_{number_dst}_{mem_size_global}"

  def str_func(s):
    return f"{s.src}>{s.dst}:{s.addr}"

  return mk_bitstruct(new_name, {
      'src': SrcType,
      'dst': DstType,
      'addr': AddrType,
    },
    namespace = {'__str__': str_func}
  )


#=========================================================================
# Ring for delivering ctrl and data signals and commands across CGRAs
#=========================================================================

def mk_intra_cgra_pkt(nrouters = 4,
                      cmd_nbits = 4,
                      cgraId_nbits = 4,
                      ctrl_actions = 8,
                      ctrl_mem_size = 16,
                      ctrl_operations = 64,
                      ctrl_fu_inports = 2,
                      ctrl_fu_outports = 2,
                      ctrl_tile_inports = 4,
                      ctrl_tile_outports = 4,
                      addr_nbits = 16,
                      data_nbits = 16,
                      predicate_nbits = 1,
                      prefix="IntraCgraPacket"):

  CgraIdType = mk_bits(cgraId_nbits)
  TileIdType = mk_bits(clog2(nrouters))
  opaque_nbits = 8
  OpqType = mk_bits(opaque_nbits)
  CtrlActionType = mk_bits(clog2(ctrl_actions))
  CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
  CtrlOperationType = mk_bits(clog2(ctrl_operations))
  CtrlTileInType = mk_bits(clog2(ctrl_tile_inports + 1))
  CtrlTileOutType = mk_bits(clog2(ctrl_tile_outports + 1))
  num_routing_outports = ctrl_tile_outports + ctrl_fu_inports
  CtrlRoutingOutType = mk_bits(clog2(num_routing_outports + 1))
  CtrlFuInType = mk_bits(clog2(ctrl_fu_inports + 1))
  CtrlFuOutType = mk_bits(clog2(ctrl_fu_outports + 1))
  CtrlPredicateType = mk_bits(predicate_nbits)
  VcIdType = mk_bits(1)
  CmdType = mk_bits(cmd_nbits)
  AddrType = mk_bits(addr_nbits)
  DataType = mk_bits(data_nbits)
  DataPredicateType = mk_bits(predicate_nbits)


  new_name = f"{prefix}_{nrouters}_{opaque_nbits}_{ctrl_actions}_" \
             f"{ctrl_mem_size}_{ctrl_operations}_{ctrl_fu_inports}_"\
             f"{ctrl_fu_outports}_{ctrl_tile_inports}_{ctrl_tile_outports}"

  def str_func(s):
    out_str = '(ctrl_operation)' + str(s.ctrl_operation)
    out_str += '|(ctrl_fu_in)'
    for i in range(ctrl_fu_inports):
      if i != 0:
        out_str += '-'
      out_str += str(int(s.ctrl_fu_in[i]))

    out_str += '|(ctrl_predicate)'
    out_str += str(int(s.ctrl_predicate))

    out_str += '|(ctrl_routing_xbar_out)'
    for i in range(num_routing_outports):
      if i != 0:
        out_str += '-'
      out_str += str(int(s.ctrl_routing_xbar_outport[i]))

    out_str += '|(ctrl_fu_xbar_out)'
    for i in range(num_routing_outports):
      if i != 0:
        out_str += '-'
      out_str += str(int(s.ctrl_fu_xbar_outport[i]))

    out_str += '|(ctrl_predicate_in)'
    for i in range(ctrl_tile_inports):
      if i != 0:
        out_str += '-'
      out_str += str(int(s.ctrl_routing_predicate_in[i]))

    return f"{s.srcTile}>{s.dstTile}:{s.opaque}:{s.ctrl_action}.{s.ctrl_addr}." \
           f"{out_str}"

  field_dict = {}
  field_dict['cgraId'] = CgraIdType
  field_dict['srcTile'] = TileIdType
  field_dict['dstTile'] = TileIdType
  field_dict['opaque'] = OpqType
  field_dict['vc_id'] = VcIdType
  field_dict['ctrl_action'] = CtrlActionType
  field_dict['ctrl_addr'] = CtrlAddrType
  field_dict['ctrl_operation'] = CtrlOperationType
  # TODO: need fix to pair `predicate` with specific operation.
  # The 'predicate' indicates whether the current operation is based on
  # the partial predication or not. Note that 'predicate' is different
  # from the following 'predicate_in', which contributes to the 'predicate'
  # at the next cycle.
  field_dict['ctrl_predicate'] = CtrlPredicateType
  # The fu_in indicates the input register ID (i.e., operands) for the
  # operation.
  field_dict['ctrl_fu_in'] = [CtrlFuInType for _ in range(ctrl_fu_inports)]

  field_dict['ctrl_routing_xbar_outport'] = [CtrlTileInType for _ in range(
      num_routing_outports)]
  field_dict['ctrl_fu_xbar_outport'] = [CtrlFuOutType for _ in range(
      num_routing_outports)]
  # I assume one tile supports single predicate during the entire execution
  # time, as it is hard to distinguish predication for different operations
  # (we automatically update, i.e., 'or', the predicate stored in the
  # predicate register). This should be guaranteed by the compiler.
  field_dict['ctrl_routing_predicate_in'] = [CtrlPredicateType for _ in range(
      ctrl_tile_inports)]
  field_dict['cmd'] = CmdType
  field_dict['addr'] = AddrType
  field_dict['data'] = DataType
  field_dict['data_predicate'] = DataPredicateType

  return mk_bitstruct(new_name, field_dict,
    namespace = {'__str__': str_func}
  )