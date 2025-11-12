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
from .util.data_struct_attr import *

#=========================================================================
# Generic data message
#=========================================================================

def mk_data(payload_nbits=16, predicate_nbits=1, bypass_nbits=1,
            prefix="CgraData"):
  """
  Build a CGRA data bitstruct with payload, predicate, bypass, and delay fields.

  Args:
    payload_nbits   (int): Width of the arithmetic payload.
    predicate_nbits (int): Width of the predicate/valid flag.
    bypass_nbits    (int): Width of the bypass metadata.
    prefix         (str):  Prefix used in the generated type name.

  Returns:
    type: PyMTL bitstruct class (e.g., ``<class 'CgraData_32_1_1_1'>``).

  Example:
    >>> DataType = mk_data(32, 1)
    >>> print(DataType)
    <class 'types.CgraData_32_1_1_1'>
    >>> sample = DataType(payload=5, predicate=1, bypass=0, delay=0)
    >>> print(sample)
    00000005.1.0.0
  """

  PayloadType   = mk_bits( payload_nbits   )
  PredicateType = mk_bits( predicate_nbits )
  BypassType    = mk_bits( bypass_nbits )
  DelayType     = mk_bits( 1 )

  new_name = f"{prefix}_{payload_nbits}_{predicate_nbits}_{bypass_nbits}_1"

  def str_func( s ):
    return f"{s.payload}.{s.predicate}.{s.bypass}.{s.delay}"

  return mk_bitstruct( new_name, {
      kAttrPayload  : PayloadType,
      kAttrPredicate: PredicateType,
      kAttrBypass   : BypassType,
      kAttrDelay    : DelayType,
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
      kAttrPayload  : PayloadType,
      kAttrPredicate: PredicateType,
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
  """
  Build a CGRA control bitstruct that describes FU routing/config information.

  Args:
    num_fu_inports (int): Number of FU input ports per tile.
    num_fu_outports (int): Number of FU output ports per tile.
    num_tile_inports (int): Number of tile-to-tile input ports.
    num_tile_outports (int): Number of tile-to-tile output ports.
    num_registers_per_reg_bank (int): Register count per bank.
    prefix (str): Prefix used in the generated type name.

  Returns:
    type: PyMTL bitstruct class encoding a CGRA control word.

  Example:
    >>> CtrlType = mk_ctrl(num_fu_inports=2, num_fu_outports=2)
    >>> print(CtrlType)
    <class 'types.CGRAConfig_7_2_2_5_5_3'>
    >>> ctrl = CtrlType(operation=0, fu_in=[0, 1], fu_xbar_outport=[0]*4,
    ...                 routing_xbar_outport=[0]*4, vector_factor_power=0,
    ...                 is_last_ctrl=0, write_reg_from=[0, 0], write_reg_idx=[0, 0],
    ...                 read_reg_from=[0, 0], read_reg_idx=[0, 0])
    >>> print(ctrl.operation)
    00
  """

  operation_nbits = clog2(NUM_OPTS)
  OperationType = mk_bits(operation_nbits)
  TileInportsType = mk_bits(clog2(num_tile_inports  + 1))
  TileOutportsType = mk_bits(clog2(num_tile_outports + 1))
  num_routing_outports = num_tile_outports + num_fu_inports
  RoutingOutportsType = mk_bits(clog2(num_routing_outports + 1))
  FuInType = mk_bits(clog2(num_fu_inports + 1))
  FuOutType = mk_bits(clog2(num_fu_outports + 1))
  vector_factor_power_nbits = 3
  VectorFactorPowerType = mk_bits(vector_factor_power_nbits)
  # 3 inports of register file bank.
  RegFromType = mk_bits(2)
  RegIdxType = mk_bits(clog2(num_registers_per_reg_bank))

  new_name = f"{prefix}_{operation_nbits}_{num_fu_inports}_" \
             f"{num_fu_outports}_{num_tile_inports}_" \
             f"{num_tile_outports}_{vector_factor_power_nbits}"

  def str_func(s):
    out_str = '(fu_in)'
    for i in range(num_fu_inports):
      if i != 0:
        out_str += '-'
      out_str += str(int(s.fu_in[i]))

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
  field_dict[kAttrOperation] = OperationType
  # The fu_in indicates the input register ID (i.e., operands) for the
  # operation.
  field_dict[kAttrFuIn] = [FuInType for _ in range(num_fu_inports)]

  field_dict[kAttrRoutingXbarOutport] = [TileInportsType for _ in range(
      num_routing_outports)]
  field_dict[kAttrFuXbarOutport] = [FuOutType for _ in range(
      num_routing_outports)]

  field_dict[kAttrVectorFactorPower] = VectorFactorPowerType

  field_dict[kAttrIsLastCtrl] = b1

  # Register file related signals.
  # Indicates whether to write data into the register bank, and the
  # corresponding inport.
  field_dict[kAttrWriteRegFrom] = [RegFromType for _ in range(num_fu_inports)]
  field_dict[kAttrWriteRegIdx] = [RegIdxType for _ in range(num_fu_inports)]
  # Indicates whether to read data from the register bank.
  field_dict[kAttrReadRegFrom] = [b1 for _ in range(num_fu_inports)]
  field_dict[kAttrReadRegIdx] = [RegIdxType for _ in range(num_fu_inports)]

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
  """
  Build the payload bitstruct used inside inter/intra-CGRA network packets.

  Args:
    DataType: Bitstruct type representing the data value.
    DataAddrType: Bit type for global/local data addresses.
    CtrlType: Bitstruct type for CGRA control/config commands.
    CtrlAddrType: Bit width for control memory addresses.
    prefix (str): Prefix used in the generated type name.

  Returns:
    type: PyMTL bitstruct class containing cmd/data/addr/ctrl fields.

  Example:
    >>> DataType = mk_data(32, 1)
    >>> DataAddrType = mk_bits(8)
    >>> CtrlType = mk_ctrl()
    >>> CtrlAddrType = mk_bits(4)
    >>> PayloadType = mk_cgra_payload(DataType, DataAddrType, CtrlType, CtrlAddrType)
    >>> print(PayloadType)
    <class 'types.MultiCgraPayload_Cmd_Data_DataAddr_Ctrl_CtrlAddr'>
    >>> payload = PayloadType(cmd=0, data=DataType(), data_addr=0, ctrl=CtrlType(), ctrl_addr=0)
    >>> print(payload)
    MultiCgraNocPayload: cmd:00|data:00000000.0.0.0|data_addr:00|ctrl:(opt)00|(fu_in)0-0-0-0|(routing_xbar_out)0-0-0-0-0-0-0-0-0|(fu_xbar_out)0-0-0-0-0-0-0-0-0|(vector_factor_power)0|(is_last_ctrl)0|(read_reg_from)0-0-0-0|(write_reg_from)0-0-0-0|(write_reg_idx)0-0-0-0|(read_reg_idx)0-0-0-0|ctrl_addr:0
  """

  new_name = f"{prefix}_Cmd_Data_DataAddr_Ctrl_CtrlAddr"

  field_dict = {}
  field_dict[kAttrCmd] = mk_bits(clog2(NUM_CMDS))
  field_dict[kAttrData] = DataType
  field_dict[kAttrDataAddr] = DataAddrType
  field_dict[kAttrCtrl] = CtrlType
  field_dict[kAttrCtrlAddr] = CtrlAddrType

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
                      num_rd_tiles,
                      CgraPayloadType,
                      prefix="InterCgraPacket"):
  """
  Build the inter-CGRA network packet bitstruct that wraps a payload.

  Args:
    num_cgra_columns (int): Number of CGRA columns in the mesh/ring.
    num_cgra_rows (int): Number of CGRA rows.
    num_tiles (int): Number of tiles per CGRA (plus CPU marker).
    num_rd_tiles (int): Number of tiles able to issue remote loads.
    CgraPayloadType: Payload bitstruct type (from mk_cgra_payload).
    prefix (str): Prefix for the generated packet type.

  Returns:
    type: PyMTL bitstruct class for inter-CGRA packets carrying the payload.

  Example:
    >>> DataType = mk_data(32, 1)
    >>> CtrlType = mk_ctrl()
    >>> PayloadType = mk_cgra_payload(DataType, mk_bits(8), CtrlType, mk_bits(4))
    >>> PktType = mk_inter_cgra_pkt(2, 1, 4, 3, PayloadType)
    >>> print(PktType)
    <class 'types.InterCgraPacket_2_2x1_4_8_4_CgraPayload'>
    >>> pkt = PktType(0, 1, 0, 0, 1, 0, 0, 0, 0, 0, payload=PayloadType())
    >>> print(pkt)
    InterCgraPkt: 0->1 || (0,0)->(1,0) || tileid:0->0 || remote_src_port:0 || 00:0 || payload:MultiCgraNocPayload: cmd:00|data:00000000.0.0.0|data_addr:00|ctrl:(opt)00|(fu_in)0-0-0-0|(routing_xbar_out)0-0-0-0-0-0-0-0-0|(fu_xbar_out)0-0-0-0-0-0-0-0-0|(vector_factor_power)0|(is_last_ctrl)0|(read_reg_from)0-0-0-0|(write_reg_from)0-0-0-0|(write_reg_idx)0-0-0-0|(read_reg_idx)0-0-0-0|ctrl_addr:0
  """

  CgraIdType = mk_bits(max(clog2(num_cgra_columns * num_cgra_rows), 1))
  CgraXType = mk_bits(max(clog2(num_cgra_columns), 1))
  CgraYType = mk_bits(max(clog2(num_cgra_rows), 1))
  # An additional router for controller to receive CMD_COMPLETE signal from Ring to CPU.
  TileIdType = mk_bits(clog2(num_tiles + 1))
  RemoteSrcPortType = mk_bits(clog2(num_rd_tiles + 1))
  opaque_nbits = 8
  OpqType = mk_bits(opaque_nbits)
  num_vcs = 4
  VcIdType = mk_bits(clog2(num_vcs))

  new_name = f"{prefix}_{num_cgra_columns*num_cgra_rows}_" \
             f"{num_cgra_columns}x{num_cgra_rows}_{num_tiles}_" \
             f"{opaque_nbits}_{num_vcs}_CgraPayload"

  field_dict = {}
  field_dict[kAttrSrc] = CgraIdType # src CGRA id
  field_dict[kAttrDst] = CgraIdType # dst CGRA id
  field_dict[kAttrSrcX] = CgraXType # CGRA 2d coordinates
  field_dict[kAttrSrcY] = CgraYType
  field_dict[kAttrDstX] = CgraXType
  field_dict[kAttrDstY] = CgraYType
  field_dict[kAttrSrcTileId] = TileIdType
  field_dict[kAttrDstTileId] = TileIdType
  field_dict[kAttrRemoteSrcPort] = RemoteSrcPortType
  field_dict[kAttrOpaque] = OpqType
  field_dict[kAttrVcId] = VcIdType
  field_dict[kAttrPayload] = CgraPayloadType

  def str_func(s):
    return f"InterCgraPkt: {s.src}->{s.dst} || " \
           f"({s.src_x},{s.src_y})->({s.dst_x},{s.dst_y}) || " \
           f"tileid:{s.src_tile_id}->{s.dst_tile_id} || " \
           f"remote_src_port:{s.remote_src_port} || " \
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
  field_dict[kAttrSrc] = TileIdType
  field_dict[kAttrDst] = TileIdType
  field_dict[kAttrSrcCgraId] = CgraIdType
  field_dict[kAttrDstCgraId] = CgraIdType
  field_dict[kAttrSrcCgraX] = CgraXType
  field_dict[kAttrSrcCgraY] = CgraYType
  field_dict[kAttrDstCgraX] = CgraXType
  field_dict[kAttrDstCgraY] = CgraYType
  field_dict[kAttrOpaque] = OpqType
  field_dict[kAttrVcId] = VcIdType
  field_dict[kAttrPayload] = CgraPayloadType

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
      kAttrSrc: SrcType,
      kAttrDst: DstType,
      kAttrAddr: AddrType,
      kAttrSrcCgra: CgraIdType,
      kAttrSrcTile: TileIdType,
    },
    namespace = {'__str__': str_func}
  )

def mk_mem_access_pkt(DataType,
                      number_src = 5,
                      number_dst = 5,
                      mem_size_global = 64,
                      num_cgras = 4,
                      num_tiles = 17,
                      num_rd_tiles = 4,
                      prefix="MemAccessPacket"):

  SrcType = mk_bits(clog2(number_src))
  DstType = mk_bits(clog2(number_dst))
  AddrType = mk_bits(clog2(mem_size_global))
  CgraIdType = mk_bits(max(1, clog2(num_cgras)))
  TileIdType = mk_bits(clog2(num_tiles + 1))
  RemoteSrcPortType = mk_bits(clog2(num_rd_tiles + 1))

  new_name = f"{prefix}_{number_src}_{number_dst}_{mem_size_global}"

  def str_func(s):
    return f"{s.src}>{s.dst}:(addr){s.addr}.(data){s.data}.(src_cgra){s.src_cgra}.(src_tile){s.src_tile}.(remote_src_port){s.remote_src_port}"

  return mk_bitstruct(new_name, {
      kAttrSrc: SrcType,
      kAttrDst: DstType,
      kAttrAddr: AddrType,
      kAttrData: DataType,
      kAttrSrcCgra: CgraIdType,
      kAttrSrcTile: TileIdType,
      kAttrRemoteSrcPort: RemoteSrcPortType,
    },
    namespace = {'__str__': str_func}
  )

#=========================================================================
# Crossbar (controller <-> NoC) packet
#=========================================================================

def mk_controller_noc_xbar_pkt(InterCgraPktType,
                               prefix="ControllerNocXbarPacket"):
  """
  Build the packet wrapper used by the controller crossbar before sending to NoC.

  Args:
    InterCgraPktType: Bitstruct class for the underlying inter-CGRA packet.
    prefix (str): Prefix for the generated crossbar packet type.

  Returns:
    type: PyMTL bitstruct class tagging a destination outport plus the packet.

  Example:
    >>> DataType = mk_data(16, 1)
    >>> CtrlType = mk_ctrl()
    >>> PayloadType = mk_cgra_payload(DataType, mk_bits(8), CtrlType, mk_bits(4))
    >>> PktType = mk_inter_cgra_pkt(2, 1, 4, 3, PayloadType)
    >>> XbarPktType = mk_controller_noc_xbar_pkt(PktType)
    >>> print(XbarPktType)
    <class 'types.ControllerNocXbarPacket_InterCgraPktType'>
    >>> xbar_pkt = XbarPktType(dst=0, inter_cgra_pkt=PktType())
    >>> print(xbar_pkt)
    ->0:(inter_cgra_pkt)InterCgraPkt: 0->0 || (0,0)->(0,0) || tileid:0->0 || remote_src_port:0 || 00:0 || payload:MultiCgraNocPayload: cmd:00|data:0000.0.0.0|data_addr:00|ctrl:(opt)00|(fu_in)0-0-0-0|(routing_xbar_out)0-0-0-0-0-0-0-0-0|(fu_xbar_out)0-0-0-0-0-0-0-0-0|(vector_factor_power)0|(is_last_ctrl)0|(read_reg_from)0-0-0-0|(write_reg_from)0-0-0-0|(write_reg_idx)0-0-0-0|(read_reg_idx)0-0-0-0|ctrl_addr:0
  """

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

#=========================================================================
# CGRA ID type
#=========================================================================

def mk_cgra_id_type(num_cgra_columns,
                    num_cgra_rows,
                    prefix="CgraId"):

  num_cgras = num_cgra_columns * num_cgra_rows
  return mk_bits(max(1, clog2(num_cgras)))
