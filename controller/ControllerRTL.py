"""
==========================================================================
ControllerRTL.py
==========================================================================
Controller for each CGRA. Mutiple controllers are interconnected in a
multi-cgra system.

Author : Cheng Tan
  Date : Dec 2, 2024
"""

from ..lib.basic.val_rdy.ifcs import RecvIfcRTL
from ..lib.basic.val_rdy.ifcs import SendIfcRTL
from ..lib.basic.val_rdy.queues import NormalQueueRTL
from ..lib.messages import *
from ..lib.opt_type import *
from ..lib.util.common import *
from ..noc.PyOCN.pymtl3_net.channel.ChannelRTL import ChannelRTL
from ..noc.PyOCN.pymtl3_net.xbar.XbarRTL import XbarRTL

from .GlobalReduceUnitRTL import GlobalReduceUnitRTL
from ..lib.util.data_struct_attr import *

class ControllerRTL(Component):

  def construct(s,
                InterCgraPktType,
                multi_cgra_rows,
                multi_cgra_columns,
                num_tiles,
                controller2addr_map,
                idTo2d_map,
                has_dma_ports = False):

    # Derives types from InterCgraPktType.
    CgraPayloadType = InterCgraPktType.get_field_type(kAttrPayload)
    DataType = CgraPayloadType.get_field_type(kAttrData)
    DataPayloadType = DataType.get_field_type(kAttrPayload)
    DataAddrType = CgraPayloadType.get_field_type(kAttrDataAddr)
    
    # Derives CgraIdType from grid dimensions.
    CgraIdType = mk_cgra_id_type(multi_cgra_columns, multi_cgra_rows)
    
    # Reconstructs IntraCgraPktType.
    IntraCgraPktType = mk_intra_cgra_pkt(multi_cgra_columns,
                                         multi_cgra_rows,
                                         num_tiles,
                                         CgraPayloadType)
    
    assert(multi_cgra_columns >= multi_cgra_rows)

    # Used for calculating the x/y position.
    XType = mk_bits(max(clog2(multi_cgra_columns), 1))
    YType = mk_bits(max(clog2(multi_cgra_rows), 1))
    TileIdType = mk_bits(clog2(num_tiles + 1))
    ControllerXbarPktType = mk_controller_noc_xbar_pkt(InterCgraPktType)
    DmaOpcodeType = mk_bits(3)
    DmaDramAddrType = mk_bits(64)
    DmaBytesType = mk_bits(32)
    DmaTagType = mk_bits(8)
    DmaDramAddrPartType = mk_bits(32)
    DmaMaskType = mk_bits(max(1, DataPayloadType.nbits // CHAR_BIT))

    if has_dma_ports:
      assert DataPayloadType.nbits == 32

    # Interface
    s.cgra_id = InPort(CgraIdType)

    # Request from/to other CGRA via NoC.
    s.recv_from_inter_cgra_noc = RecvIfcRTL(InterCgraPktType)
    s.send_to_inter_cgra_noc = SendIfcRTL(InterCgraPktType)

    s.recv_from_cpu_pkt = RecvIfcRTL(IntraCgraPktType)
    s.send_to_ctrl_ring_pkt = SendIfcRTL(IntraCgraPktType)

    s.recv_from_ctrl_ring_pkt = RecvIfcRTL(IntraCgraPktType)
    s.send_to_cpu_pkt = SendIfcRTL(IntraCgraPktType)

    # Request from/to tiles.
    s.recv_from_tile_load_request_pkt = RecvIfcRTL(InterCgraPktType)
    s.recv_from_tile_load_response_pkt = RecvIfcRTL(InterCgraPktType)
    s.recv_from_tile_store_request_pkt = RecvIfcRTL(InterCgraPktType)

    s.send_to_mem_load_request = SendIfcRTL(InterCgraPktType)
    s.send_to_tile_load_response = SendIfcRTL(InterCgraPktType)
    s.send_to_mem_store_request = SendIfcRTL(InterCgraPktType)

    if has_dma_ports:
      # Controller-owned command path from CPU packets to the DMA engine.
      s.dma_cmd_val       = OutPort()
      s.dma_cmd_rdy       = InPort()
      s.dma_cmd_opcode    = OutPort(DmaOpcodeType)
      s.dma_cmd_dram_addr = OutPort(DmaDramAddrType)
      s.dma_cmd_spm_addr  = OutPort(DataAddrType)
      s.dma_cmd_bytes     = OutPort(DmaBytesType)
      s.dma_cmd_tag       = OutPort(DmaTagType)

      s.dma_done_val      = InPort()
      s.dma_done_rdy      = OutPort()
      s.dma_done_tag      = InPort(DmaTagType)

      # DMA engine side of the controller-forwarded SPM access path.
      s.spm_dma_wval  = InPort()
      s.spm_dma_wrdy  = OutPort()
      s.spm_dma_waddr = InPort(DataAddrType)
      s.spm_dma_wdata = InPort(DataPayloadType)
      s.spm_dma_wmask = InPort(DmaMaskType)

      s.spm_dma_rval       = InPort()
      s.spm_dma_rrdy       = OutPort()
      s.spm_dma_raddr      = InPort(DataAddrType)
      s.spm_dma_rresp_val  = OutPort()
      s.spm_dma_rresp_rdy  = InPort()
      s.spm_dma_rresp_data = OutPort(DataPayloadType)

      # Data memory side of the same SPM access path.
      s.send_to_mem_dma_wval  = OutPort()
      s.recv_from_mem_dma_wrdy = InPort()
      s.send_to_mem_dma_waddr = OutPort(DataAddrType)
      s.send_to_mem_dma_wdata = OutPort(DataPayloadType)
      s.send_to_mem_dma_wmask = OutPort(DmaMaskType)

      s.send_to_mem_dma_rval       = OutPort()
      s.recv_from_mem_dma_rrdy     = InPort()
      s.send_to_mem_dma_raddr      = OutPort(DataAddrType)
      s.recv_from_mem_dma_rresp_val  = InPort()
      s.send_to_mem_dma_rresp_rdy    = OutPort()
      s.recv_from_mem_dma_rresp_data = InPort(DataPayloadType)
    else:
      s.dma_cmd_val       = Wire()
      s.dma_cmd_rdy       = Wire()
      s.dma_cmd_opcode    = Wire(DmaOpcodeType)
      s.dma_cmd_dram_addr = Wire(DmaDramAddrType)
      s.dma_cmd_spm_addr  = Wire(DataAddrType)
      s.dma_cmd_bytes     = Wire(DmaBytesType)
      s.dma_cmd_tag       = Wire(DmaTagType)

      s.dma_done_val      = Wire()
      s.dma_done_rdy      = Wire()
      s.dma_done_tag      = Wire(DmaTagType)

      s.spm_dma_wval  = Wire()
      s.spm_dma_wrdy  = Wire()
      s.spm_dma_waddr = Wire(DataAddrType)
      s.spm_dma_wdata = Wire(DataPayloadType)
      s.spm_dma_wmask = Wire(DmaMaskType)

      s.spm_dma_rval       = Wire()
      s.spm_dma_rrdy       = Wire()
      s.spm_dma_raddr      = Wire(DataAddrType)
      s.spm_dma_rresp_val  = Wire()
      s.spm_dma_rresp_rdy  = Wire()
      s.spm_dma_rresp_data = Wire(DataPayloadType)

      s.send_to_mem_dma_wval    = Wire()
      s.recv_from_mem_dma_wrdy  = Wire()
      s.send_to_mem_dma_waddr   = Wire(DataAddrType)
      s.send_to_mem_dma_wdata   = Wire(DataPayloadType)
      s.send_to_mem_dma_wmask   = Wire(DmaMaskType)

      s.send_to_mem_dma_rval           = Wire()
      s.recv_from_mem_dma_rrdy         = Wire()
      s.send_to_mem_dma_raddr          = Wire(DataAddrType)
      s.recv_from_mem_dma_rresp_val    = Wire()
      s.send_to_mem_dma_rresp_rdy      = Wire()
      s.recv_from_mem_dma_rresp_data   = Wire(DataPayloadType)

    # Component
    s.recv_from_tile_load_request_pkt_queue = ChannelRTL(InterCgraPktType, latency = 1)
    s.recv_from_tile_load_response_pkt_queue = ChannelRTL(InterCgraPktType, latency = 1)
    s.recv_from_tile_store_request_pkt_queue = ChannelRTL(InterCgraPktType, latency = 1)

    s.send_to_mem_load_request_queue = ChannelRTL(InterCgraPktType, latency = 1)
    s.send_to_tile_load_response_queue = ChannelRTL(InterCgraPktType, latency = 1)
    s.send_to_mem_store_request_queue = ChannelRTL(InterCgraPktType, latency = 1)

    # Crossbar with 4 inports (load and store requests towards remote
    # memory, load response from local memory, ctrl&data packet from cpu,
    # and command signal from inter-tile, i.e., intra-cgra, ring) and 1 
    # outport (only allow one request be sent out per cycle).
    s.crossbar = XbarRTL(ControllerXbarPktType, CONTROLLER_CROSSBAR_INPORTS, 1)
    s.recv_from_cpu_pkt_queue = NormalQueueRTL(IntraCgraPktType)
    s.send_to_cpu_pkt_queue = NormalQueueRTL(IntraCgraPktType)

    # Global reduce unit.
    # TODO: We need multiple GlobalReduceUnitRTL to enable more than 1 reduction
    # across the fabric: https://github.com/tancheng/VectorCGRA/issues/184.
    s.global_reduce_unit = GlobalReduceUnitRTL(InterCgraPktType)

    # LUT for global data address mapping.
    addr_offset_nbits = 0
    s.addr2controller_lut = [Wire(CgraIdType) for _ in range(len(controller2addr_map))]
    # Assumes the address range is contiguous within one CGRA's SPMs.
    addr2controller_vector = [-1 for _ in range(len(controller2addr_map))]
    for src_cgra_id, address_range in controller2addr_map.items():
      begin_addr, end_addr = address_range[0], address_range[1]
      address_length = end_addr - begin_addr + 1
      assert (address_length & (address_length - 1)) == 0, f"{address_length} is not a power of 2."
      addr_offset_nbits = clog2(address_length)
      addr_base = begin_addr >> addr_offset_nbits
      assert addr2controller_vector[addr_base] == -1, f"address range [{begin_addr}, {end_addr}] overlaps with others."
      addr2controller_vector[addr_base] = CgraIdType(src_cgra_id)

      s.addr2controller_lut[addr_base] //= CgraIdType(src_cgra_id)

    # Constructs the idTo2d lut.
    s.idTo2d_x_lut= [Wire(XType) for _ in range(multi_cgra_columns * multi_cgra_rows)]
    s.idTo2d_y_lut= [Wire(YType) for _ in range(multi_cgra_columns * multi_cgra_rows)]
    for cgra_id in idTo2d_map:
      xy = idTo2d_map[cgra_id]
      s.idTo2d_x_lut[cgra_id] //= XType(xy[0])
      s.idTo2d_y_lut[cgra_id] //= YType(xy[1])

    s.addr_dst_id = Wire(CgraIdType)

    s.dma_dram_addr_lo = Wire(DmaDramAddrPartType)
    s.dma_dram_addr_hi = Wire(DmaDramAddrPartType)
    s.dma_spm_addr     = Wire(DataAddrType)
    s.dma_bytes        = Wire(DmaBytesType)
    s.dma_tag          = Wire(DmaTagType)

    # Connections.
    # Requests towards others, 1 cycle delay to improve timing.
    s.recv_from_tile_load_request_pkt_queue.recv //= s.recv_from_tile_load_request_pkt
    s.recv_from_tile_load_response_pkt_queue.recv //= s.recv_from_tile_load_response_pkt
    s.recv_from_tile_store_request_pkt_queue.recv //= s.recv_from_tile_store_request_pkt

    # Requests towards local from others, 1 cycle delay to improve timing.
    s.send_to_mem_load_request_queue.send //= s.send_to_mem_load_request
    s.send_to_tile_load_response_queue.send //= s.send_to_tile_load_response
    s.send_to_mem_store_request_queue.send //= s.send_to_mem_store_request

    # For control signals delivery from CPU to tiles.
    s.recv_from_cpu_pkt //= s.recv_from_cpu_pkt_queue.recv
    s.send_to_cpu_pkt //= s.send_to_cpu_pkt_queue.send

    @update_ff
    def update_dma_cmd_regs():
      if s.reset:
        s.dma_dram_addr_lo <<= DmaDramAddrPartType(0)
        s.dma_dram_addr_hi <<= DmaDramAddrPartType(0)
        s.dma_spm_addr     <<= DataAddrType(0)
        s.dma_bytes        <<= DmaBytesType(0)
        s.dma_tag          <<= DmaTagType(0)
      elif has_dma_ports:
        cpu_payload = s.recv_from_cpu_pkt_queue.send.msg.payload
        cpu_cmd = cpu_payload.cmd
        cpu_data = cpu_payload.data.payload
        if s.recv_from_cpu_pkt_queue.send.val & s.recv_from_cpu_pkt_queue.send.rdy:
          if cpu_cmd == CMD_DMA_CONFIG_DRAM_ADDR_LO:
            s.dma_dram_addr_lo <<= DmaDramAddrPartType(cpu_data)
          elif cpu_cmd == CMD_DMA_CONFIG_DRAM_ADDR_HI:
            s.dma_dram_addr_hi <<= DmaDramAddrPartType(cpu_data)
          elif cpu_cmd == CMD_DMA_CONFIG_SPM_ADDR:
            s.dma_spm_addr <<= cpu_payload.data_addr
          elif cpu_cmd == CMD_DMA_CONFIG_BYTES:
            s.dma_bytes <<= DmaBytesType(cpu_data)
          elif cpu_cmd == CMD_DMA_CONFIG_TAG:
            s.dma_tag <<= trunc(cpu_data, DmaTagType)

    @update
    def update_dma_spm_forwarding():
      if has_dma_ports:
        s.send_to_mem_dma_wval  @= s.spm_dma_wval
        s.spm_dma_wrdy          @= s.recv_from_mem_dma_wrdy
        s.send_to_mem_dma_waddr @= s.spm_dma_waddr
        s.send_to_mem_dma_wdata @= s.spm_dma_wdata
        s.send_to_mem_dma_wmask @= s.spm_dma_wmask

        s.send_to_mem_dma_rval        @= s.spm_dma_rval
        s.spm_dma_rrdy                @= s.recv_from_mem_dma_rrdy
        s.send_to_mem_dma_raddr       @= s.spm_dma_raddr
        s.spm_dma_rresp_val           @= s.recv_from_mem_dma_rresp_val
        s.send_to_mem_dma_rresp_rdy   @= s.spm_dma_rresp_rdy
        s.spm_dma_rresp_data          @= s.recv_from_mem_dma_rresp_data

    @update
    def update_received_msg():
      kLoadRequestInportIdx = 0
      kLoadResponseInportIdx = 1
      kStoreRequestInportIdx = 2
      kFromCpuCtrlAndDataIdx = 3
      kFromInterTileRingIdx = 4
      kFromReduceUnitIdx = 5

      s.send_to_cpu_pkt_queue.recv.val @= 0
      s.send_to_cpu_pkt_queue.recv.msg @= IntraCgraPktType(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
      s.recv_from_ctrl_ring_pkt.rdy @= 0

      if has_dma_ports:
        s.dma_cmd_val       @= 0
        s.dma_cmd_opcode    @= DmaOpcodeType(DMA_MVIN)
        s.dma_cmd_dram_addr @= concat(s.dma_dram_addr_hi, s.dma_dram_addr_lo)
        s.dma_cmd_spm_addr  @= s.dma_spm_addr
        s.dma_cmd_bytes     @= s.dma_bytes
        s.dma_cmd_tag       @= s.dma_tag
        s.dma_done_rdy      @= 0

      for i in range(CONTROLLER_CROSSBAR_INPORTS):
        s.crossbar.recv[i].val @= 0
        s.crossbar.recv[i].msg @= ControllerXbarPktType(0, 0)

      # For the command signal from inter-tile/intra-cgra control ring.
      s.crossbar.recv[kFromInterTileRingIdx].val @= s.recv_from_ctrl_ring_pkt.val
      s.recv_from_ctrl_ring_pkt.rdy @= s.crossbar.recv[kFromInterTileRingIdx].rdy
      s.crossbar.recv[kFromInterTileRingIdx].msg @= \
          ControllerXbarPktType(0, # dst (always 0 to align with the single outport of the crossbar, i.e., NoC)
                                InterCgraPktType(s.cgra_id,
                                                 s.recv_from_ctrl_ring_pkt.msg.dst_cgra_id,
                                                 s.idTo2d_x_lut[s.cgra_id], # src_x
                                                 s.idTo2d_y_lut[s.cgra_id], # src_y
                                                 s.recv_from_ctrl_ring_pkt.msg.dst_cgra_x, # dst_x
                                                 s.recv_from_ctrl_ring_pkt.msg.dst_cgra_y, # dst_y
                                                 s.recv_from_ctrl_ring_pkt.msg.src, # src_tile_id
                                                 s.recv_from_ctrl_ring_pkt.msg.dst, # dst_tile_id
                                                 0, # remote_src_port, only used for inter-cgra remote load request/response.
                                                 0, # opaque
                                                 0, # vc_id. No need to specify vc_id for self produce-consume pkt thanks to the additional VC buffer.
                                                 s.recv_from_ctrl_ring_pkt.msg.payload))

      # For the load request from local tiles.
      s.crossbar.recv[kLoadRequestInportIdx].val @= s.recv_from_tile_load_request_pkt_queue.send.val
      s.recv_from_tile_load_request_pkt_queue.send.rdy @= s.crossbar.recv[kLoadRequestInportIdx].rdy
      s.crossbar.recv[kLoadRequestInportIdx].msg @= \
          ControllerXbarPktType(0, # dst (always 0 to align with the single outport of the crossbar, i.e., NoC)
                                s.recv_from_tile_load_request_pkt_queue.send.msg)

      # For the store request from local tiles.
      s.crossbar.recv[kStoreRequestInportIdx].val @= s.recv_from_tile_store_request_pkt_queue.send.val
      s.recv_from_tile_store_request_pkt_queue.send.rdy @= s.crossbar.recv[kStoreRequestInportIdx].rdy
      s.crossbar.recv[kStoreRequestInportIdx].msg @= \
          ControllerXbarPktType(0, # dst (always 0 to align with the single outport of the crossbar, i.e., NoC)
                                s.recv_from_tile_store_request_pkt_queue.send.msg)

      # For the load response (i.e., the data towards other) from local memory.
      s.crossbar.recv[kLoadResponseInportIdx].val @= \
          s.recv_from_tile_load_response_pkt_queue.send.val
      s.recv_from_tile_load_response_pkt_queue.send.rdy @= s.crossbar.recv[kLoadResponseInportIdx].rdy
      s.crossbar.recv[kLoadResponseInportIdx].msg @= \
          ControllerXbarPktType(0, # dst (always 0 to align with the single outport of the crossbar, i.e., NoC)
                                s.recv_from_tile_load_response_pkt_queue.send.msg)

      # For the load response (i.e., the data towards other) from local memory.
      s.crossbar.recv[kFromReduceUnitIdx].val @= \
          s.global_reduce_unit.send.val
      s.global_reduce_unit.send.rdy @= s.crossbar.recv[kFromReduceUnitIdx].rdy
      s.crossbar.recv[kFromReduceUnitIdx].msg @= s.global_reduce_unit.send.msg

      cpu_payload = s.recv_from_cpu_pkt_queue.send.msg.payload
      cpu_cmd = cpu_payload.cmd

      if has_dma_ports & (
          (cpu_cmd == CMD_DMA_CONFIG_DRAM_ADDR_LO) |
          (cpu_cmd == CMD_DMA_CONFIG_DRAM_ADDR_HI) |
          (cpu_cmd == CMD_DMA_CONFIG_SPM_ADDR) |
          (cpu_cmd == CMD_DMA_CONFIG_BYTES) |
          (cpu_cmd == CMD_DMA_CONFIG_TAG)):
        s.recv_from_cpu_pkt_queue.send.rdy @= 1

      elif has_dma_ports & (
          (cpu_cmd == CMD_DMA_MVIN) |
          (cpu_cmd == CMD_DMA_MVOUT)):
        s.dma_cmd_val @= s.recv_from_cpu_pkt_queue.send.val
        if cpu_cmd == CMD_DMA_MVIN:
          s.dma_cmd_opcode @= DmaOpcodeType(DMA_MVIN)
        else:
          s.dma_cmd_opcode @= DmaOpcodeType(DMA_MVOUT)
        s.recv_from_cpu_pkt_queue.send.rdy @= s.dma_cmd_rdy

      else:
        # For the ctrl and data preloading.
        s.crossbar.recv[kFromCpuCtrlAndDataIdx].val @= \
            s.recv_from_cpu_pkt_queue.send.val
        s.recv_from_cpu_pkt_queue.send.rdy @= s.crossbar.recv[kFromCpuCtrlAndDataIdx].rdy
        s.crossbar.recv[kFromCpuCtrlAndDataIdx].msg @= \
            ControllerXbarPktType(0, # dst (always 0 to align with the single outport of the crossbar, i.e., NoC)
                                  InterCgraPktType(s.cgra_id, # src
                                                   s.recv_from_cpu_pkt_queue.send.msg.dst_cgra_id, # dst
                                                   0, # src_x
                                                   0, # src_y
                                                   s.idTo2d_x_lut[s.recv_from_cpu_pkt_queue.send.msg.dst_cgra_id], # dst_x
                                                   s.idTo2d_y_lut[s.recv_from_cpu_pkt_queue.send.msg.dst_cgra_id], # dst_y
                                                   num_tiles, # src_tile_id, num_tiles is used to indicate the request is from CPU, so the LOAD response can come back.
                                                   s.recv_from_cpu_pkt_queue.send.msg.dst, # dst_tile_id
                                                   0, # remote_src_port, only used for inter-cgra remote load request/response.
                                                   0, # opaque
                                                   0, # vc_id
                                                   s.recv_from_cpu_pkt_queue.send.msg.payload))

      # TODO: For the other cmd types.


    # @update
    # def update_received_msg_from_noc():

      # Initiates the signals.
      s.send_to_mem_load_request_queue.recv.val @= 0
      s.send_to_mem_store_request_queue.recv.val @= 0
      s.send_to_tile_load_response_queue.recv.val @= 0

      s.send_to_mem_load_request_queue.recv.msg @= InterCgraPktType(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
      s.send_to_mem_store_request_queue.recv.msg @= InterCgraPktType(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
      s.send_to_tile_load_response_queue.recv.msg @= InterCgraPktType(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

      s.recv_from_inter_cgra_noc.rdy @= 0
      s.send_to_ctrl_ring_pkt.val @= 0
      s.send_to_ctrl_ring_pkt.msg @= IntraCgraPktType(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
      s.global_reduce_unit.recv_count.val @= 0
      s.global_reduce_unit.recv_count.msg @= InterCgraPktType(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
      s.global_reduce_unit.recv_data.val @= 0
      s.global_reduce_unit.recv_data.msg @= InterCgraPktType(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

      # For the load request from NoC.
      received_pkt = s.recv_from_inter_cgra_noc.msg
      if s.recv_from_inter_cgra_noc.val:
        if s.recv_from_inter_cgra_noc.msg.payload.cmd == CMD_LOAD_REQUEST:
          s.send_to_mem_load_request_queue.recv.val @= 1

          if s.send_to_mem_load_request_queue.recv.rdy:
            s.recv_from_inter_cgra_noc.rdy @= 1
            s.send_to_mem_load_request_queue.recv.msg @= received_pkt

        elif s.recv_from_inter_cgra_noc.msg.payload.cmd == CMD_STORE_REQUEST:
          s.send_to_mem_store_request_queue.recv.msg @= received_pkt
          s.send_to_mem_store_request_queue.recv.val @= 1

          if s.send_to_mem_store_request_queue.recv.rdy:
            s.recv_from_inter_cgra_noc.rdy @= 1

        elif s.recv_from_inter_cgra_noc.msg.payload.cmd == CMD_LOAD_RESPONSE:
          # FIXME: This condition needs to check whether this controller is the
          # one connecting to CPU, and with the help from additional field indicating
          # whether the packet is originally from CPU.
          # https://github.com/tancheng/VectorCGRA/issues/116.
          if s.recv_from_inter_cgra_noc.msg.dst_tile_id == num_tiles:
            s.recv_from_inter_cgra_noc.rdy @= s.send_to_cpu_pkt_queue.recv.rdy
            s.send_to_cpu_pkt_queue.recv.val @= 1
            s.send_to_cpu_pkt_queue.recv.msg @= \
                IntraCgraPktType(s.recv_from_inter_cgra_noc.msg.src_tile_id, # src
                                 s.recv_from_inter_cgra_noc.msg.dst_tile_id, # dst
                                 s.recv_from_inter_cgra_noc.msg.src, # src_cgra_id
                                 s.recv_from_inter_cgra_noc.msg.dst, # src_cgra_id
                                 s.recv_from_inter_cgra_noc.msg.src_x, # src_cgra_x
                                 s.recv_from_inter_cgra_noc.msg.src_y, # src_cgra_y
                                 s.recv_from_inter_cgra_noc.msg.dst_x, # dst_cgra_x
                                 s.recv_from_inter_cgra_noc.msg.dst_y, # dst_cgra_y
                                 0, # opaque
                                 0, # vc_id
                                 s.recv_from_inter_cgra_noc.msg.payload)

          else:
            s.recv_from_inter_cgra_noc.rdy @= s.send_to_tile_load_response_queue.recv.rdy
            s.send_to_tile_load_response_queue.recv.msg @= received_pkt
            s.send_to_tile_load_response_queue.recv.val @= 1

        elif s.recv_from_inter_cgra_noc.msg.payload.cmd == CMD_COMPLETE:
          s.recv_from_inter_cgra_noc.rdy @= s.send_to_cpu_pkt_queue.recv.rdy
          s.send_to_cpu_pkt_queue.recv.val @= 1
          s.send_to_cpu_pkt_queue.recv.msg @= \
              IntraCgraPktType(s.recv_from_inter_cgra_noc.msg.src_tile_id, # src
                               s.recv_from_inter_cgra_noc.msg.dst_tile_id, # dst
                               s.recv_from_inter_cgra_noc.msg.src, # src_cgra_id
                               s.recv_from_inter_cgra_noc.msg.dst, # src_cgra_id
                               s.recv_from_inter_cgra_noc.msg.src_x, # src_cgra_x
                               s.recv_from_inter_cgra_noc.msg.src_y, # src_cgra_y
                               s.recv_from_inter_cgra_noc.msg.dst_x, # dst_cgra_x
                               s.recv_from_inter_cgra_noc.msg.dst_y, # dst_cgra_y
                               0, # opaque
                               0, # vc_id
                               s.recv_from_inter_cgra_noc.msg.payload)

        # Consume and discard the leaf counter complete signal (loop termination
        # notification from LoopCounter FU) to avoid blocking the NoC.
        elif s.recv_from_inter_cgra_noc.msg.payload.cmd == CMD_LEAF_COUNTER_COMPLETE:
          s.recv_from_inter_cgra_noc.rdy @= 1

        elif s.recv_from_inter_cgra_noc.msg.payload.cmd == CMD_GLOBAL_REDUCE_ADD:
          s.recv_from_inter_cgra_noc.rdy @= s.global_reduce_unit.recv_data.rdy
          s.global_reduce_unit.recv_data.val @= 1
          s.global_reduce_unit.recv_data.msg @= s.recv_from_inter_cgra_noc.msg

        elif s.recv_from_inter_cgra_noc.msg.payload.cmd == CMD_GLOBAL_REDUCE_COUNT:
          s.recv_from_inter_cgra_noc.rdy @= s.global_reduce_unit.recv_count.rdy
          s.global_reduce_unit.recv_count.val @= 1
          s.global_reduce_unit.recv_count.msg @= s.recv_from_inter_cgra_noc.msg

        elif (s.recv_from_inter_cgra_noc.msg.payload.cmd == CMD_CONFIG) | \
             (s.recv_from_inter_cgra_noc.msg.payload.cmd == CMD_CONFIG_PROLOGUE_FU) | \
             (s.recv_from_inter_cgra_noc.msg.payload.cmd == CMD_CONFIG_PROLOGUE_FU_CROSSBAR) | \
             (s.recv_from_inter_cgra_noc.msg.payload.cmd == CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR) | \
             (s.recv_from_inter_cgra_noc.msg.payload.cmd == CMD_CONFIG_TOTAL_CTRL_COUNT) | \
             (s.recv_from_inter_cgra_noc.msg.payload.cmd == CMD_CONFIG_COUNT_PER_ITER) | \
             (s.recv_from_inter_cgra_noc.msg.payload.cmd == CMD_CONFIG_CTRL_LOWER_BOUND) | \
             (s.recv_from_inter_cgra_noc.msg.payload.cmd == CMD_CONST) | \
             (s.recv_from_inter_cgra_noc.msg.payload.cmd == CMD_GLOBAL_REDUCE_ADD_RESPONSE) | \
             (s.recv_from_inter_cgra_noc.msg.payload.cmd == CMD_GLOBAL_REDUCE_MUL_RESPONSE) | \
             (s.recv_from_inter_cgra_noc.msg.payload.cmd == CMD_CONFIG_STREAMING_LD_START_ADDR) | \
             (s.recv_from_inter_cgra_noc.msg.payload.cmd == CMD_CONFIG_STREAMING_LD_STRIDE) | \
             (s.recv_from_inter_cgra_noc.msg.payload.cmd == CMD_CONFIG_STREAMING_LD_END_ADDR) | \
             (s.recv_from_inter_cgra_noc.msg.payload.cmd == CMD_PAUSE) | \
             (s.recv_from_inter_cgra_noc.msg.payload.cmd == CMD_PRESERVE) | \
             (s.recv_from_inter_cgra_noc.msg.payload.cmd == CMD_RESUME) | \
             (s.recv_from_inter_cgra_noc.msg.payload.cmd == CMD_RECORD_PHI_ADDR) | \
             (s.recv_from_inter_cgra_noc.msg.payload.cmd == CMD_TERMINATE) | \
             (s.recv_from_inter_cgra_noc.msg.payload.cmd == CMD_LAUNCH) | \
             (s.recv_from_inter_cgra_noc.msg.payload.cmd == CMD_CONFIG_LOOP_LOWER) | \
             (s.recv_from_inter_cgra_noc.msg.payload.cmd == CMD_CONFIG_LOOP_UPPER) | \
             (s.recv_from_inter_cgra_noc.msg.payload.cmd == CMD_CONFIG_LOOP_STEP) :
          s.recv_from_inter_cgra_noc.rdy @= s.send_to_ctrl_ring_pkt.rdy
          s.send_to_ctrl_ring_pkt.val @= s.recv_from_inter_cgra_noc.val
          s.send_to_ctrl_ring_pkt.msg @= \
              IntraCgraPktType(s.recv_from_inter_cgra_noc.msg.src_tile_id, # src
                               s.recv_from_inter_cgra_noc.msg.dst_tile_id, # dst
                               s.recv_from_inter_cgra_noc.msg.src, # src_cgra_id
                               s.recv_from_inter_cgra_noc.msg.dst, # src_cgra_id
                               s.recv_from_inter_cgra_noc.msg.src_x, # src_cgra_x
                               s.recv_from_inter_cgra_noc.msg.src_y, # src_cgra_y
                               s.recv_from_inter_cgra_noc.msg.dst_x, # dst_cgra_x
                               s.recv_from_inter_cgra_noc.msg.dst_y, # dst_cgra_y
                               0, # opaque
                               0, # vc_id
                               s.recv_from_inter_cgra_noc.msg.payload)

        # else:
        #   # TODO: Handle other cmd types.
        #   assert(False)

      if has_dma_ports & s.dma_done_val:
        s.dma_done_rdy @= s.send_to_cpu_pkt_queue.recv.rdy
        s.send_to_cpu_pkt_queue.recv.val @= 1
        s.send_to_cpu_pkt_queue.recv.msg @= \
            IntraCgraPktType(num_tiles, # src_tile_id: controller/DMA sideband source
                             num_tiles, # dst_tile_id: CPU-facing controller endpoint
                             s.cgra_id,
                             s.cgra_id,
                             s.idTo2d_x_lut[s.cgra_id],
                             s.idTo2d_y_lut[s.cgra_id],
                             s.idTo2d_x_lut[s.cgra_id],
                             s.idTo2d_y_lut[s.cgra_id],
                             s.dma_done_tag,
                             0,
                             CgraPayloadType(
                               CMD_DMA_DONE,
                               DataType(zext(s.dma_done_tag, DataPayloadType), 1, 0, 0),
                               0, 0, 0))

    @update
    def update_sending_to_noc_msg():
      s.send_to_inter_cgra_noc.val @= s.crossbar.send[0].val
      s.crossbar.send[0].rdy @= s.send_to_inter_cgra_noc.rdy
      s.send_to_inter_cgra_noc.msg @= s.crossbar.send[0].msg.inter_cgra_pkt
      # addr_dst_id = 0
      if (s.crossbar.send[0].msg.inter_cgra_pkt.payload.cmd == CMD_LOAD_REQUEST) | \
         (s.crossbar.send[0].msg.inter_cgra_pkt.payload.cmd == CMD_STORE_REQUEST):
        s.send_to_inter_cgra_noc.msg.dst @= s.addr_dst_id
        s.send_to_inter_cgra_noc.msg.dst_x @= s.idTo2d_x_lut[s.addr_dst_id]
        s.send_to_inter_cgra_noc.msg.dst_y @= s.idTo2d_y_lut[s.addr_dst_id]

    @update
    def capture_addr_dst_id():
      s.addr_dst_id @= s.addr2controller_lut[trunc(s.crossbar.send[0].msg.inter_cgra_pkt.payload.data_addr >> addr_offset_nbits, CgraIdType)]

  def line_trace(s):
    recv_from_cpu_pkt_str = "recv_from_cpu_pkt: " + str(s.recv_from_cpu_pkt.msg)
    recv_from_cpu_pkt_queue_str = "recv_from_cpu_pkt_queue.send: " + str(s.recv_from_cpu_pkt_queue.send.msg)
    crossbar_recv_str = "crossbar_recv.val:" + str(s.crossbar.recv[3].val) + " crossbar_recv.rdy:" + str(s.crossbar.recv[3].rdy) + " crossbar_recv.msg: " + str(s.crossbar.recv[3].msg)
    send_to_ctrl_ring_pkt_str = "send_to_ctrl_ring_pkt.val:" + str(s.send_to_ctrl_ring_pkt.val) + " send_to_ctrl_ring_pkt: " + str(s.send_to_ctrl_ring_pkt.msg) + " send_to_ctrl_ring_pkt.rdy:" + str(s.send_to_ctrl_ring_pkt.rdy)
    recv_from_tile_load_request_pkt_str = "recv_from_tile_load_request_pkt: " + str(s.recv_from_tile_load_request_pkt.msg)
    recv_from_tile_load_response_pkt_str = "recv_from_tile_load_response_pkt: " + str(s.recv_from_tile_load_response_pkt.msg)
    recv_from_tile_store_request_pkt_str = "recv_from_tile_store_request_pkt: " + str(s.recv_from_tile_store_request_pkt.msg)
    crossbar_str = "crossbar: {" + s.crossbar.line_trace() + "}"
    send_to_mem_load_request_str = "send_to_mem_load_request: " + str(s.send_to_mem_load_request.msg)
    send_to_mem_store_request_str = "send_to_mem_store_request: " + str(s.send_to_mem_store_request.msg)
    recv_from_noc_str ="recv_from_noc_pkt.val: " + str(s.recv_from_inter_cgra_noc.val) + " recv_from_noc_pkt.msg: " + str(s.recv_from_inter_cgra_noc.msg) + " recv_from_noc_pkt.rdy: " + str(s.recv_from_inter_cgra_noc.rdy)
    send_to_noc_str = "send_to_noc_pkt: " + str(s.send_to_inter_cgra_noc.msg) + "; rdy: " + str(s.send_to_inter_cgra_noc.rdy) + "; val: " + str(s.send_to_inter_cgra_noc.val)
    return f'{recv_from_cpu_pkt_str} || {recv_from_cpu_pkt_queue_str} || {crossbar_recv_str} ||  {send_to_ctrl_ring_pkt_str} || {recv_from_tile_load_request_pkt_str} || {recv_from_tile_load_response_pkt_str} || {recv_from_tile_store_request_pkt_str} || {crossbar_str} || {send_to_mem_load_request_str} || {send_to_mem_store_request_str} || {recv_from_noc_str} || {send_to_noc_str}\n'
