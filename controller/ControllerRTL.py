"""
==========================================================================
ControllerRTL.py
==========================================================================
Simple controller for CGRA.

Author : Cheng Tan
  Date : Dec 2, 2024
"""

from pymtl3 import *
from pymtl3.stdlib.primitive import RegisterFile
from ..lib.basic.val_rdy.ifcs import SendIfcRTL as SendIfcRTL
from ..lib.basic.val_rdy.ifcs import RecvIfcRTL as RecvIfcRTL
from ..lib.basic.val_rdy.queues import NormalQueueRTL
from ..noc.PyOCN.pymtl3_net.xbar.XbarBypassQueueRTL import XbarBypassQueueRTL
from ..noc.PyOCN.pymtl3_net.channel.ChannelRTL import ChannelRTL
from ..lib.cmd_type import *
from ..lib.opt_type import *

class ControllerRTL(Component):

  def construct(s, ControllerIdType, CmdType, FromCpuPktType, NocPktType,
                CGRADataType, CGRAAddrType, multi_cgra_rows,
                multi_cgra_columns, controller_id, controller2addr_map,
                idTo2d_map):

    assert(multi_cgra_columns >= multi_cgra_rows)

    # Used for calculating the x/y position.
    XType = mk_bits(max(clog2(multi_cgra_columns), 1))
    YType = mk_bits(max(clog2(multi_cgra_rows), 1))

    # Interface
    # Request from/to other CGRA via NoC.
    s.recv_from_noc = RecvIfcRTL(NocPktType)
    s.send_to_noc = SendIfcRTL(NocPktType)

    s.recv_from_cpu_pkt = RecvIfcRTL(FromCpuPktType)
    s.send_to_ctrl_ring_ctrl_pkt = SendIfcRTL(FromCpuPktType)

    # Request from/to tiles.
    s.recv_from_tile_load_request_pkt = RecvIfcRTL(NocPktType)
    s.recv_from_tile_load_response_pkt = RecvIfcRTL(NocPktType)
    s.recv_from_tile_store_request_pkt = RecvIfcRTL(NocPktType)

    s.send_to_tile_load_request_addr = SendIfcRTL(CGRAAddrType)
    s.send_to_tile_load_response_data = SendIfcRTL(CGRADataType)
    s.send_to_tile_store_request_addr = SendIfcRTL(CGRAAddrType)
    s.send_to_tile_store_request_data = SendIfcRTL(CGRADataType)

    # Component
    s.recv_from_tile_load_request_pkt_queue = ChannelRTL(NocPktType, latency = 1)
    s.recv_from_tile_load_response_pkt_queue = ChannelRTL(NocPktType, latency = 1)
    s.recv_from_tile_store_request_pkt_queue = ChannelRTL(NocPktType, latency = 1)

    s.send_to_tile_load_request_addr_queue = ChannelRTL(CGRAAddrType, latency = 1)
    s.send_to_tile_load_response_data_queue = ChannelRTL(CGRADataType, latency = 1)
    s.send_to_tile_store_request_addr_queue = ChannelRTL(CGRAAddrType, latency = 1)
    s.send_to_tile_store_request_data_queue = ChannelRTL(CGRADataType, latency = 1)

    # s.recv_from_other_cmd_queue = ChannelRTL(CmdType, latency = 1, num_entries = 2)
    # s.send_to_tile_cmd_queue = ChannelRTL(CmdType, latency = 1, num_entries = 2)
    # s.send_to_other_cmd_queue = ChannelRTL(CmdType, latency = 1, num_entries = 2)

    # Crossbar with 3 inports (load and store requests towards remote
    # memory, and load response from local memory) and 1 outport (only
    # allow one request be sent out per cycle).
    # TODO: Include other cmd requests, e.g., dynamic rescheduling,
    # termination).
    s.crossbar = XbarBypassQueueRTL(NocPktType, 4, 1)

    s.recv_from_cpu_pkt_queue = ChannelRTL(FromCpuPktType, latency = 1)

    # # TODO: below ifcs should be connected through another NoC within
    # # one CGRA, instead of per-tile and performing like a bus.
    # # Configuration signals to be written into and read from per-tile
    # # control memory.
    # s.recv_waddr = [RecvIfcRTL(AddrType) for _ in range(s.num_tiles)]
    # s.recv_wopt = [RecvIfcRTL(CtrlType) for _ in range(s.num_tiles)]

    # s.send_waddr = [SendIfcRTL(AddrType) for _ in range(s.num_tiles)]
    # s.send_wopt = [SendIfcRTL(CtrlType) for _ in range(s.num_tiles)]

    # # Cmd to invoke/terminate tiles execution.
    # s.recv_cmd = [RecvIfcRTL(b2) for _ in range(s.num_tiles)]
    # s.send_cmd = [SendIfcRTL(b2) for _ in range(s.num_tiles)]


    # LUT for global data address mapping.
    addr_offset_nbits = 0
    s.addr2controller_lut = [Wire(ControllerIdType) for _ in range(len(controller2addr_map))]
    # Assumes the address range is contiguous within one CGRA's SPMs.
    addr2controller_vector = [-1 for _ in range(len(controller2addr_map))]
    s.addr_base_items = len(controller2addr_map)
    for src_controller_id, address_range in controller2addr_map.items():
      begin_addr, end_addr = address_range[0], address_range[1]
      address_length = end_addr - begin_addr + 1
      assert (address_length & (address_length - 1)) == 0, f"{address_length} is not a power of 2."
      addr_offset_nbits = clog2(address_length)
      addr_base = begin_addr >> addr_offset_nbits
      assert addr2controller_vector[addr_base] == -1, f"address range [{begin_addr}, {end_addr}] overlaps with others."
      addr2controller_vector[addr_base] = ControllerIdType(src_controller_id)

      s.addr2controller_lut[addr_base] //= ControllerIdType(src_controller_id)

    # Constructs the idTo2d lut.
    s.idTo2d_x_lut= [Wire(XType) for _ in range(multi_cgra_columns * multi_cgra_rows)]
    s.idTo2d_y_lut= [Wire(YType) for _ in range(multi_cgra_columns * multi_cgra_rows)]
    for cgra_id in idTo2d_map:
      xy = idTo2d_map[cgra_id]
      s.idTo2d_x_lut[cgra_id] //= XType(xy[0])
      s.idTo2d_y_lut[cgra_id] //= YType(xy[1])

    # Connections
    # Requests towards others, 1 cycle delay to improve timing.
    s.recv_from_tile_load_request_pkt_queue.recv //= s.recv_from_tile_load_request_pkt
    s.recv_from_tile_load_response_pkt_queue.recv //= s.recv_from_tile_load_response_pkt
    s.recv_from_tile_store_request_pkt_queue.recv //= s.recv_from_tile_store_request_pkt

    # Requests towards local from others, 1 cycle delay to improve timing.
    s.send_to_tile_load_request_addr_queue.send //= s.send_to_tile_load_request_addr
    s.send_to_tile_load_response_data_queue.send //= s.send_to_tile_load_response_data
    s.send_to_tile_store_request_addr_queue.send //= s.send_to_tile_store_request_addr
    s.send_to_tile_store_request_data_queue.send //= s.send_to_tile_store_request_data

    # For control signals delivery from CPU to tiles.
    # TODO: https://github.com/tancheng/VectorCGRA/issues/11 -- The request needs
    # to go through the crossbar for arbitration as well. The packet targeting local
    # tiles can be delivered via the ring within the CGRA; The packet targeting
    # other CGRAs can be delivered via the NoC across CGRAs. Note that the packet
    # format can be in a universal fashion to support both data and config. Later
    # on, the format can be packet-based or flit-based.
#    s.recv_from_cpu_pkt //= s.recv_from_cpu_pkt_queue.recv
    
    @update
    def update_recv_from_cpu_pkt_queue():
      s.recv_from_cpu_pkt_queue.recv.val @= s.recv_from_cpu_pkt.val
      s.recv_from_cpu_pkt_queue.recv.msg @= s.recv_from_cpu_pkt.msg
      # must manually set to 1, otherwise TestSrcRTL in CgraRTL_test.py will stuck
      s.recv_from_cpu_pkt.rdy @= 1

    @update
    def update_received_msg():
      kLoadRequestInportIdx = 0
      kLoadResponseInportIdx = 1
      kStoreRequestInportIdx = 2
      kFromCpuCtrlDataIdx = 3

      # For the load request from local tiles.
      s.crossbar.recv[kLoadRequestInportIdx].val @= s.recv_from_tile_load_request_pkt_queue.send.val
      s.recv_from_tile_load_request_pkt_queue.send.rdy @= s.crossbar.recv[kLoadRequestInportIdx].rdy
      s.crossbar.recv[kLoadRequestInportIdx].msg @= \
          NocPktType(controller_id, # src
                     0, # dst
                     s.idTo2d_x_lut[controller_id], # src_x
                     s.idTo2d_y_lut[controller_id], # src_y
                     0, # dst_x
                     0, # dst_y
                     0, # tile id
                     0,
                     0,
                     CMD_LOAD_REQUEST,
                     s.recv_from_tile_load_request_pkt_queue.send.msg.addr,
                     0,
                     1,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0)



      # For the store request from local tiles.
      s.crossbar.recv[kStoreRequestInportIdx].val @= s.recv_from_tile_store_request_pkt_queue.send.val
      s.recv_from_tile_store_request_pkt_queue.send.rdy @= s.crossbar.recv[kStoreRequestInportIdx].rdy
      s.crossbar.recv[kStoreRequestInportIdx].msg @= \
          NocPktType(controller_id, # src
                     0, # dst 
                     s.idTo2d_x_lut[controller_id], # src_x
                     s.idTo2d_y_lut[controller_id], # src_y
                     0, # dst_x
                     0, # dst_y
                     0, # tile id
                     0,
                     0,
                     CMD_STORE_REQUEST,
                     s.recv_from_tile_store_request_pkt_queue.send.msg.addr,
                     s.recv_from_tile_store_request_pkt_queue.send.msg.data,
                     s.recv_from_tile_store_request_pkt_queue.send.msg.predicate,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0)


      # For the load response (i.e., the data towards other) from local memory.
      s.crossbar.recv[kLoadResponseInportIdx].val @= \
          s.recv_from_tile_load_response_pkt_queue.send.val
      s.recv_from_tile_load_response_pkt_queue.send.rdy @= s.crossbar.recv[kLoadResponseInportIdx].rdy
      s.crossbar.recv[kLoadResponseInportIdx].msg @= \
          NocPktType(controller_id, # src
                     0, # dst 
                     s.idTo2d_x_lut[controller_id], # src_x
                     s.idTo2d_y_lut[controller_id], # src_y
                     0, # dst_x
                     0, # dst_y
                     0, # tile id
                     0,
                     0,
                     CMD_LOAD_RESPONSE,
                     # Retrieves the load (from NoC) address from the message.
                     # The addr information is embedded in the message.
                     s.recv_from_tile_load_response_pkt_queue.send.msg.addr,
                     s.recv_from_tile_load_response_pkt_queue.send.msg.data,
                     s.recv_from_tile_load_response_pkt_queue.send.msg.predicate,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0)


      # For the ctrl preloading.
      s.crossbar.recv[kFromCpuCtrlDataIdx].val @= \
          s.recv_from_cpu_pkt_queue.send.val
      s.recv_from_cpu_pkt_queue.send.rdy @= s.crossbar.recv[kFromCpuCtrlDataIdx].rdy
      s.crossbar.recv[kFromCpuCtrlDataIdx].msg @= \
          NocPktType(s.recv_from_cpu_pkt_queue.send.msg.cgra_id, # src
                     0, # dst 
                     s.idTo2d_x_lut[s.recv_from_cpu_pkt_queue.send.msg.cgra_id], # src_x
                     s.idTo2d_y_lut[s.recv_from_cpu_pkt_queue.send.msg.cgra_id], # src_y
                     0, # dst_x
                     0, # dst_y
                     s.recv_from_cpu_pkt_queue.send.msg.src, # tile id 
                     0,
                     0,
                     CMD_CONFIG,
                     s.recv_from_cpu_pkt_queue.send.msg.addr,
                     s.recv_from_cpu_pkt_queue.send.msg.data,
                     s.recv_from_cpu_pkt_queue.send.msg.data_predicate,
                     0,
                     s.recv_from_cpu_pkt_queue.send.msg.ctrl_action,
                     s.recv_from_cpu_pkt_queue.send.msg.ctrl_addr,
                     s.recv_from_cpu_pkt_queue.send.msg.ctrl_operation,
                     s.recv_from_cpu_pkt_queue.send.msg.ctrl_predicate,
                     s.recv_from_cpu_pkt_queue.send.msg.ctrl_fu_in,
                     s.recv_from_cpu_pkt_queue.send.msg.ctrl_routing_xbar_outport,
                     s.recv_from_cpu_pkt_queue.send.msg.ctrl_fu_xbar_outport,
                     s.recv_from_cpu_pkt_queue.send.msg.ctrl_routing_predicate_in)
        
      # TODO: For the other cmd types.


    # @update
    # def update_received_msg_from_noc():

      # Initiates the signals.
      s.send_to_tile_load_request_addr_queue.recv.val @= 0
      s.send_to_tile_store_request_addr_queue.recv.val @= 0
      s.send_to_tile_store_request_data_queue.recv.val @= 0
      s.send_to_tile_load_response_data_queue.recv.val @= 0
      s.send_to_tile_load_request_addr_queue.recv.msg @= CGRAAddrType()
      s.send_to_tile_store_request_addr_queue.recv.msg @= CGRAAddrType()
      s.send_to_tile_store_request_data_queue.recv.msg @= CGRADataType()
      s.send_to_tile_load_response_data_queue.recv.msg @= CGRADataType()
      s.recv_from_noc.rdy @= 0
      s.send_to_ctrl_ring_ctrl_pkt.val @= 0
      s.send_to_ctrl_ring_ctrl_pkt.msg @= FromCpuPktType()

      # For the load request from NoC.
      received_pkt = s.recv_from_noc.msg
      if s.recv_from_noc.val:
        if s.recv_from_noc.msg.cmd == CMD_LOAD_REQUEST:
          if s.send_to_tile_load_request_addr_queue.recv.rdy:
            s.recv_from_noc.rdy @= 1
            s.send_to_tile_load_request_addr_queue.recv.msg @= \
                CGRAAddrType(received_pkt.addr)
            s.send_to_tile_load_request_addr_queue.recv.val @= 1

        elif s.recv_from_noc.msg.cmd == CMD_STORE_REQUEST:
          if s.send_to_tile_store_request_addr_queue.recv.rdy & \
             s.send_to_tile_store_request_data_queue.recv.rdy:
            s.recv_from_noc.rdy @= 1
            s.send_to_tile_store_request_addr_queue.recv.msg @= \
                CGRAAddrType(received_pkt.addr)
            s.send_to_tile_store_request_data_queue.recv.msg @= \
                CGRADataType(received_pkt.data, received_pkt.predicate, 0, 0)
            s.send_to_tile_store_request_addr_queue.recv.val @= 1
            s.send_to_tile_store_request_data_queue.recv.val @= 1

        elif s.recv_from_noc.msg.cmd == CMD_LOAD_RESPONSE:
          if s.send_to_tile_load_response_data_queue.recv.rdy:
            s.recv_from_noc.rdy @= 1
            s.send_to_tile_load_response_data_queue.recv.msg @= \
                CGRADataType(received_pkt.data, received_pkt.predicate, 0, 0)
            s.send_to_tile_load_response_data_queue.recv.val @= 1

        elif s.recv_from_noc.msg.cmd == CMD_CONFIG:
          if s.send_to_ctrl_ring_ctrl_pkt.rdy:
            s.recv_from_noc.rdy @= 1
            s.send_to_ctrl_ring_ctrl_pkt.val @= 1
            s.send_to_ctrl_ring_ctrl_pkt.msg @= FromCpuPktType(received_pkt.src, # cgra_id
                                                               received_pkt.tile_id, # src
                                                               0, # dst
                                                               received_pkt.opaque, # opaque
                                                               received_pkt.vc_id, # vc_id
                                                               received_pkt.ctrl_action, # ctrl_action
                                                               received_pkt.ctrl_addr, # ctrl_addr
                                                               received_pkt.ctrl_operation, # ctrl_operation
                                                               received_pkt.ctrl_predicate, # ctrl_predicate
                                                               received_pkt.ctrl_fu_in, # ctrl_fu_in
                                                               received_pkt.ctrl_routing_xbar_outport, # ctrl_routing_xbar_outport
                                                               received_pkt.ctrl_fu_xbar_outport, # ctrl_fu_xbar_outport
                                                               received_pkt.ctrl_routing_predicate_in, # ctrl_routing_predicate_in
                                                               received_pkt.cmd, # cmd
                                                               received_pkt.addr, # addr
                                                               received_pkt.data, # data
                                                               received_pkt.predicate)  # data_predicate




        # else:
        #   # TODO: Handle other cmd types.
        #   assert(False)


    @update
    def update_sending_to_noc_msg():
      s.send_to_noc.val @= s.crossbar.send[0].val
      s.crossbar.send[0].rdy @= s.send_to_noc.rdy
      addr_dst_id = s.addr2controller_lut[trunc(s.crossbar.send[0].msg.addr >> addr_offset_nbits, ControllerIdType)]
      s.send_to_noc.msg @= \
          NocPktType(s.crossbar.send[0].msg.src,
                     addr_dst_id,
                     s.crossbar.send[0].msg.src_x,
                     s.crossbar.send[0].msg.src_y,
                     s.idTo2d_x_lut[addr_dst_id],
                     s.idTo2d_y_lut[addr_dst_id],
                     0, 
                     s.crossbar.send[0].msg.opaque,
                     s.crossbar.send[0].msg.vc_id,
                     s.crossbar.send[0].msg.cmd,
                     s.crossbar.send[0].msg.addr,
                     s.crossbar.send[0].msg.data,
                     s.crossbar.send[0].msg.predicate,
                     s.crossbar.send[0].msg.payload,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0)

  def line_trace(s):
    send_to_ctrl_ring_ctrl_pkt_str = "send_to_ctrl_ring_ctrl_pkt: " + str(s.send_to_ctrl_ring_ctrl_pkt.msg)
    recv_from_tile_load_request_pkt_str = "recv_from_tile_load_request_pkt: " + str(s.recv_from_tile_load_request_pkt.msg)
    recv_from_tile_load_response_pkt_str = "recv_from_tile_load_response_pkt: " + str(s.recv_from_tile_load_response_pkt.msg)
    recv_from_tile_store_request_pkt_str = "recv_from_tile_store_request_pkt: " + str(s.recv_from_tile_store_request_pkt.msg)
    crossbar_str = "crossbar: {" + s.crossbar.line_trace() + "}"
    send_to_tile_load_request_addr_str = "send_to_tile_load_request_addr: " + str(s.send_to_tile_load_request_addr.msg)
    send_to_tile_store_request_addr_str = "send_to_tile_store_request_addr: " + str(s.send_to_tile_store_request_addr.msg)
    send_to_tile_store_request_data_str = "send_to_tile_store_request_data: " + str(s.send_to_tile_store_request_data.msg)
    recv_from_noc_str = "recv_from_noc_pkt: " + str(s.recv_from_noc.msg)
    send_to_noc_str = "send_to_noc_pkt: " + str(s.send_to_noc.msg) + "; rdy: " + str(s.send_to_noc.rdy) + "; val: " + str(s.send_to_noc.val)
    return f'{send_to_ctrl_ring_ctrl_pkt_str} || {recv_from_tile_load_request_pkt_str} || {recv_from_tile_load_response_pkt_str} || {recv_from_tile_store_request_pkt_str} || {crossbar_str} || {send_to_tile_load_request_addr_str} || {send_to_tile_store_request_addr_str} || {send_to_tile_store_request_data_str} || {recv_from_noc_str} || {send_to_noc_str}\n'

