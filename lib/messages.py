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

  operation_nbits = clog2(NUM_OPTS)
  OperationType = mk_bits(operation_nbits)
  # routing_xbar_outport must be wide enough to index both tile inports AND
  # the new register-bank inports (num_tile_inports + num_fu_inports entries).
  tile_in_type_nbits = clog2(num_tile_inports + num_fu_inports + 1)
  TileInportsType = mk_bits(tile_in_type_nbits)
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

  # Includes tile_in_type_nbits in the name so the wider type gets a unique
  # cache key and doesn't collide with the old Bits3 version.
  new_name = f"{prefix}_{operation_nbits}_{num_fu_inports}_" \
             f"{num_fu_outports}_{num_tile_inports}_" \
             f"{num_tile_outports}_{vector_factor_power_nbits}_{tile_in_type_nbits}"

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

    out_str += '|(read_reg_towards)'
    for i in range(num_fu_inports):
      if i != 0:
        out_str += '-'
      out_str += str(int(s.read_reg_towards[i]))

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

  field_dict[kAttrIsLastCtrl] = mk_bits(1)

  # Register file related signals.
  # Indicates whether to write data into the register bank, and the
  # corresponding inport.
  field_dict[kAttrWriteRegFrom] = [RegFromType for _ in range(num_fu_inports)]
  field_dict[kAttrWriteRegIdx] = [RegIdxType for _ in range(num_fu_inports)]
  # Indicates where to route data read from the register bank:
  # 0: towards nothing (no read)
  # 1: towards FU (reg data consumed by operation)
  # 2: towards routing_xbar (reg data routed out to outport)
  # 3: towards both FU and routing_xbar
  field_dict[kAttrReadRegTowards] = [RegFromType for _ in range(num_fu_inports)]
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
# DMA messages
#=========================================================================

def mk_dma_cmd(dram_addr_nbits = 64,
               spm_addr_nbits = 32,
               bytes_nbits = 32,
               tag_nbits = 8,
               prefix = "DmaCmd"):

  OpcodeType   = mk_bits(3)
  DramAddrType = mk_bits(dram_addr_nbits)
  SpmAddrType  = mk_bits(spm_addr_nbits)
  BytesType    = mk_bits(bytes_nbits)
  TagType      = mk_bits(tag_nbits)

  new_name = f"{prefix}_{dram_addr_nbits}_{spm_addr_nbits}_{bytes_nbits}_{tag_nbits}"

  def str_func(s):
    return f"dma_cmd(op={s.opcode},dram={s.dram_addr},spm={s.spm_addr},bytes={s.nbytes},tag={s.dma_tag})"

  return mk_bitstruct(new_name, {
      'opcode'   : OpcodeType,
      'dram_addr': DramAddrType,
      'spm_addr' : SpmAddrType,
      # NOTE nbytes is the number of bytes to transfer.
      # Currently, only nbytes that are multiples of 4 are supported.
      'nbytes'   : BytesType,
      # This dma_tag isn't used now. We may use it to distinguish different DMA commands.
      'dma_tag'  : TagType,
    },
    namespace = {'__str__': str_func}
  )

# A data structure to represent the data to be transferred by DMA.
#
# === Mask Design ===
# Data transfer granularity between DRAM and SPM is 1 word (4 bytes)
# The `dram_mask` and `spm_mask` fields define the bitwidth of byte
# masks for DRAM and SPM data respectively.
#
# Actual mask *values* are generated independently by the DMA engine
# FSM (see DmaEngineRTL), NOT carried in this struct:
#
# - dram_mask (16-bit, one bit per byte of 128-bit(16 bytes) DRAM beat):
#   Dynamically computed during MVOUT (SPM -> DRAM) based on the
#   number of valid words in the last beat. Values range from 0x000f
#   (1 word) to 0xffff (full beat). For example, if DMA move 1 word from SPM to DRAM, the mask is 0x000f.
#   If DMA move 2 words from SPM to DRAM, the mask is 0x00ff.
#   If DMA move 3 words from SPM to DRAM, the mask is 0x0fff.
#   If DMA move 4 words from SPM to DRAM, the mask is 0xffff.
#
# - spm_mask (4-bit, one bit per byte of 32-bit SPM word):
#   SPM writes always write full words, so the mask is
#   hardcoded to 0xf. This field is reserved for
#   future byte-granular SPM write support.
def mk_dma_data(dram_data_nbits = 128,
                dram_mask_nbits = 16,
                spm_data_nbits = 32,
                spm_mask_nbits = 4,
                prefix = "DmaData"):
  DramDataType = mk_bits(dram_data_nbits)
  DramMaskType = mk_bits(dram_mask_nbits)
  SpmDataType = mk_bits(spm_data_nbits)
  SpmMaskType = mk_bits(spm_mask_nbits)
  new_name = f"{prefix}_{dram_data_nbits}_{dram_mask_nbits}_{spm_data_nbits}"

  def str_func(s):
    return f"dma_data(dram_data={s.dram_data},dram_mask={s.dram_mask},spm_data={s.spm_data})"
  
  return mk_bitstruct(new_name, {
    'dram_data': DramDataType,
    # 16-bit byte mask for 16-bytes DRAM beat.
    'dram_mask': DramMaskType,
    'spm_data': SpmDataType,
    # 4-bit byte mask for 4-bytes SPM word.
    # Always 0xf in current implementation (full-word writes only).
    'spm_mask': SpmMaskType,
  },
  namespace = {'__str__': str_func}
  )

def mk_dma_done(tag_nbits = 8,
                prefix = "DmaDone"):

  TagType = mk_bits(tag_nbits)

  new_name = f"{prefix}_{tag_nbits}"

  def str_func(s):
    return f"dma_done(dma_tag={s.dma_tag})"

  return mk_bitstruct(new_name, {
      'dma_tag': TagType,
    },
    namespace = {'__str__': str_func}
  )

#=========================================================================
# The type of write request signal from DMA to DRAM
#=========================================================================
def mk_dma_dram_wr_req(addr_nbits = 64,
                       data_nbits = 128,
                       mask_nbits = 16,
                       prefix = "DmaDramWrReq"):

  AddrType = mk_bits(addr_nbits)
  DataType = mk_bits(data_nbits)
  MaskType = mk_bits(mask_nbits)

  new_name = f"{prefix}_{addr_nbits}_{data_nbits}_{mask_nbits}"

  def str_func(s):
    return f"dma_dram_wr(addr={s.addr},data={s.data},mask={s.mask})"

  return mk_bitstruct(new_name, {
      'addr': AddrType,
      'data': DataType,
      'mask': MaskType,
    },
    namespace = {'__str__': str_func}
  )

# The type of write request signal from DMA to SPM
def mk_dma_spm_write_req(addr_nbits = 32,
                         data_nbits = 32,
                         prefix = "DmaSpmWriteReq"):

  AddrType = mk_bits(addr_nbits)
  DataType = mk_bits(data_nbits)
  MaskType = mk_bits(max(1, data_nbits // 8))

  new_name = f"{prefix}_{addr_nbits}_{data_nbits}"

  def str_func(s):
    return f"dma_spm_wr(addr={s.addr},data={s.data},mask={s.mask})"

  return mk_bitstruct(new_name, {
      'addr': AddrType,
      'data': DataType,
      'mask': MaskType,
    },
    namespace = {'__str__': str_func}
  )

# The type of read request signal from DMA to SPM
def mk_dma_spm_read_req(addr_nbits = 32,
                        prefix = "DmaSpmReadReq"):

  AddrType = mk_bits(addr_nbits)

  new_name = f"{prefix}_{addr_nbits}"

  def str_func(s):
    return f"dma_spm_rd(addr={s.addr})"

  return mk_bitstruct(new_name, {
      'addr': AddrType,
    },
    namespace = {'__str__': str_func}
  )

# The type of read response signal from SPM to DMA
def mk_dma_spm_read_resp(data_nbits = 32,
                         prefix = "DmaSpmReadResp"):

  DataType = mk_bits(data_nbits)

  new_name = f"{prefix}_{data_nbits}"

  def str_func(s):
    return f"dma_spm_rd_resp(data={s.data})"

  return mk_bitstruct(new_name, {
      'data': DataType,
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
