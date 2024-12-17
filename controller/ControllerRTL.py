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
from ..lib.basic.en_rdy.ifcs import SendIfcRTL, RecvIfcRTL
from ..lib.basic.val_rdy.ifcs import SendIfcRTL as ValRdySendIfcRTL
from ..lib.basic.val_rdy.ifcs import RecvIfcRTL as ValRdyRecvIfcRTL
from ..noc.ChannelNormalRTL import ChannelNormalRTL
from ..noc.PyOCN.pymtl3_net.xbar.XbarBypassQueueRTL import XbarBypassQueueRTL
from ..lib.cmd_type import *
from ..lib.opt_type import *


class ControllerRTL(Component):

  def construct(s, ControllerIdType, CmdType, NocPktType,
                CGRADataType, CGRAAddrType, controller_id,
                controller2addr_map):

    # Interface
    # Request from/to other CGRA via NoC.
    s.recv_from_noc = ValRdyRecvIfcRTL(NocPktType)
    s.send_to_noc = ValRdySendIfcRTL(NocPktType)

    # Request from/to master.
    s.recv_from_master_load_request_pkt = RecvIfcRTL(NocPktType)
    s.recv_from_master_load_response_pkt = RecvIfcRTL(NocPktType)
    s.recv_from_master_store_request_pkt = RecvIfcRTL(NocPktType)

    s.send_to_master_load_request_addr = SendIfcRTL(CGRAAddrType)
    s.send_to_master_load_response_data = SendIfcRTL(CGRADataType)
    s.send_to_master_store_request_addr = SendIfcRTL(CGRAAddrType)
    s.send_to_master_store_request_data = SendIfcRTL(CGRADataType)

    # Component
    s.recv_from_master_load_request_pkt_queue = ChannelNormalRTL(NocPktType, latency = 1, num_entries = 2)
    s.recv_from_master_load_response_pkt_queue = ChannelNormalRTL(NocPktType, latency = 1, num_entries = 2)
    s.recv_from_master_store_request_pkt_queue = ChannelNormalRTL(NocPktType, latency = 1, num_entries = 2)

    s.send_to_master_load_request_addr_queue = ChannelNormalRTL(CGRAAddrType, latency = 1, num_entries = 2)
    s.send_to_master_load_response_data_queue = ChannelNormalRTL(CGRADataType, latency = 1, num_entries = 2)
    s.send_to_master_store_request_addr_queue = ChannelNormalRTL(CGRAAddrType, latency = 1, num_entries = 2)
    s.send_to_master_store_request_data_queue = ChannelNormalRTL(CGRADataType, latency = 1, num_entries = 2)

    # s.recv_from_other_cmd_queue = ChannelNormalRTL(CmdType, latency = 1, num_entries = 2)
    # s.send_to_master_cmd_queue = ChannelNormalRTL(CmdType, latency = 1, num_entries = 2)
    # s.send_to_other_cmd_queue = ChannelNormalRTL(CmdType, latency = 1, num_entries = 2)

    # Crossbar with 3 inports (load and store requests towards remote
    # memory, and load response from master) and 1 outport (only
    # allow one request be sent out per cycle).
    # TODO: Include other cmd requests, e.g., dynamic rescheduling,
    # termination).
    s.crossbar = XbarBypassQueueRTL(NocPktType, 3, 1)

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


    # Connections
    # Requests towards others, 1 cycle delay to improve timing.
    s.recv_from_master_load_request_pkt_queue.recv //= s.recv_from_master_load_request_pkt
    s.recv_from_master_load_response_pkt_queue.recv //= s.recv_from_master_load_response_pkt
    s.recv_from_master_store_request_pkt_queue.recv //= s.recv_from_master_store_request_pkt

    # Reqeusts towards local from others, 1 cycle delay to improve timing.
    s.send_to_master_load_request_addr_queue.send //= s.send_to_master_load_request_addr
    s.send_to_master_load_response_data_queue.send //= s.send_to_master_load_response_data
    s.send_to_master_store_request_addr_queue.send //= s.send_to_master_store_request_addr
    s.send_to_master_store_request_data_queue.send //= s.send_to_master_store_request_data


    # FIXME: Probably not translatable.
    def getDstId(target_address):
      for src_controller_id, address_range in controller2addr_map.items():
        if target_address >= address_range[0] and target_address <= address_range[1]:
          return src_controller_id
      assert(False)


    @update
    def update_received_msg():

      kLoadRequestInportIdx = 0
      kLoadResponseInportIdx = 1
      kStoreRequestInportIdx = 2

      # For the load request from master.
      s.crossbar.recv[kLoadRequestInportIdx].val @= s.recv_from_master_load_request_pkt_queue.send.en
      s.recv_from_master_load_request_pkt_queue.send.rdy @= s.crossbar.recv[kLoadRequestInportIdx].rdy
      s.crossbar.recv[kLoadRequestInportIdx].msg @= \
          NocPktType(controller_id,
                     0,
                     0,
                     0,
                     CMD_LOAD_REQUEST,
                     s.recv_from_master_load_request_pkt_queue.send.msg.addr,
                     0,
                     1)

      # For the store request from master.
      s.crossbar.recv[kStoreRequestInportIdx].val @= s.recv_from_master_store_request_pkt_queue.send.en
      s.recv_from_master_store_request_pkt_queue.send.rdy @= s.crossbar.recv[kStoreRequestInportIdx].rdy
      s.crossbar.recv[kStoreRequestInportIdx].msg @= \
          NocPktType(controller_id,
                     0,
                     0,
                     0,
                     CMD_STORE_REQUEST,
                     s.recv_from_master_store_request_pkt_queue.send.msg.addr,
                     s.recv_from_master_store_request_pkt_queue.send.msg.data,
                     s.recv_from_master_store_request_pkt_queue.send.msg.predicate)

      # For the load response (i.e., the data towards other) from master.
      s.crossbar.recv[kLoadResponseInportIdx].val @= \
          s.recv_from_master_load_response_pkt_queue.send.en
      s.recv_from_master_load_response_pkt_queue.send.rdy @= s.crossbar.recv[kLoadResponseInportIdx].rdy
      s.crossbar.recv[kLoadResponseInportIdx].msg @= \
          NocPktType(controller_id,
                     0,
                     0,
                     0,
                     CMD_LOAD_RESPONSE,
                     # Retrieves the load (from NoC) address from the message.
                     # The addr information is embedded in the message.
                     s.recv_from_master_load_response_pkt_queue.send.msg.addr,
                     s.recv_from_master_load_response_pkt_queue.send.msg.data,
                     s.recv_from_master_load_response_pkt_queue.send.msg.predicate)
      # TODO: For the other cmd types.


    # @update
    # def update_received_msg_from_noc():

      # Initiates the signals.
      s.send_to_master_load_request_addr_queue.recv.en @= 0
      s.send_to_master_store_request_addr_queue.recv.en @= 0
      s.send_to_master_store_request_data_queue.recv.en @= 0
      s.send_to_master_load_response_data_queue.recv.en @= 0
      s.send_to_master_load_request_addr_queue.recv.msg @= CGRAAddrType()
      s.send_to_master_store_request_addr_queue.recv.msg @= CGRAAddrType()
      s.send_to_master_store_request_data_queue.recv.msg @= CGRADataType()
      s.send_to_master_load_response_data_queue.recv.msg @= CGRADataType()
      s.recv_from_noc.rdy @= 0

      # For the load request from NoC.
      received_pkt = s.recv_from_noc.msg
      if s.recv_from_noc.val:
        if s.recv_from_noc.msg.cmd == CMD_LOAD_REQUEST:
          if s.send_to_master_load_request_addr_queue.recv.rdy:
            s.recv_from_noc.rdy @= 1
            s.send_to_master_load_request_addr_queue.recv.msg @= \
                CGRAAddrType(received_pkt.addr)
            s.send_to_master_load_request_addr_queue.recv.en @= 1

        elif s.recv_from_noc.msg.cmd == CMD_STORE_REQUEST:
          if s.send_to_master_store_request_addr_queue.recv.rdy & \
             s.send_to_master_store_request_data_queue.recv.rdy:
            s.recv_from_noc.rdy @= 1
            s.send_to_master_store_request_addr_queue.recv.msg @= \
                CGRAAddrType(received_pkt.addr)
            s.send_to_master_store_request_data_queue.recv.msg @= \
                CGRADataType(received_pkt.data, received_pkt.predicate)
            s.send_to_master_store_request_addr_queue.recv.en @= 1
            s.send_to_master_store_request_data_queue.recv.en @= 1

        elif s.recv_from_noc.msg.cmd == CMD_LOAD_RESPONSE:
          if s.send_to_master_load_response_data_queue.recv.rdy:
            s.recv_from_noc.rdy @= 1
            s.send_to_master_load_response_data_queue.recv.msg @= \
                CGRADataType(received_pkt.data, received_pkt.predicate)
            s.send_to_master_load_response_data_queue.recv.en @= 1

        else:
          # TODO: Handle other cmd types.
          assert(False)


    @update
    def update_sending_to_noc_msg():
      s.send_to_noc.val @= s.crossbar.send[0].val
      s.crossbar.send[0].rdy @= s.send_to_noc.rdy
      addr_dst_id = getDstId(s.crossbar.send[0].msg.addr)
      s.send_to_noc.msg @= \
          NocPktType(s.crossbar.send[0].msg.src,
                     addr_dst_id,
                     s.crossbar.send[0].msg.opaque,
                     s.crossbar.send[0].msg.vc_id,
                     s.crossbar.send[0].msg.cmd,
                     s.crossbar.send[0].msg.addr,
                     s.crossbar.send[0].msg.data,
                     s.crossbar.send[0].msg.predicate)



  def line_trace(s):
    recv_from_master_load_request_pkt_str = "recv_from_master_load_request_pkt: " + str(s.recv_from_master_load_request_pkt.msg)
    recv_from_master_load_response_pkt_str = "recv_from_master_load_response_pkt: " + str(s.recv_from_master_load_response_pkt.msg)
    recv_from_master_store_request_pkt_str = "recv_from_master_store_request_pkt: " + str(s.recv_from_master_store_request_pkt.msg)
    crossbar_str = "crossbar: {" + s.crossbar.line_trace() + "}"
    send_to_master_load_request_addr_str = "send_to_master_load_request_addr: " + str(s.send_to_master_load_request_addr.msg)
    send_to_master_store_request_addr_str = "send_to_master_store_request_addr: " + str(s.send_to_master_store_request_addr.msg)
    send_to_master_store_request_data_str = "send_to_master_store_request_data: " + str(s.send_to_master_store_request_data.msg)
    recv_from_noc_str = "recv_from_noc_pkt: " + str(s.recv_from_noc.msg)
    send_to_noc_str = "send_to_noc_pkt: " + str(s.send_to_noc.msg) + "; rdy: " + str(s.send_to_noc.rdy) + "; val: " + str(s.send_to_noc.val)
    return f'{recv_from_master_load_request_pkt_str} || {recv_from_master_load_response_pkt_str} || {recv_from_master_store_request_pkt_str} || {crossbar_str} || {send_to_master_load_request_addr_str} || {send_to_master_store_request_addr_str} || {send_to_master_store_request_data_str} || {recv_from_noc_str} || {send_to_noc_str}\n'
