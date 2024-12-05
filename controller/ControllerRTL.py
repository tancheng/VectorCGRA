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
from ..lib.opt_type import *


class ControllerRTL(Component):

  def construct(s, RingPktType, CGRADataType, CGRAAddrType):

    # # Constant

    # AddrType = mk_bits( clog2( data_mem_size ) )

    # Interface

    # # Read/write Data from local CGRA data memory.
    # s.recv_raddr_from_local = RecvIfcRTL(AddrType)
    # s.send_rdata_from_local = SendIfcRTL(DataType)
    # s.recv_waddr_from_local = RecvIfcRTL(AddrType)
    # s.recv_wdata_from_local = RecvIfcRTL(DataType)

    # # Read/write Data to local CGRA data memory.
    # s.recv_raddr_to_local = RecvIfcRTL(CGRAAddrType)
    # s.send_rdata_to_local = SendIfcRTL(CGRADataType)
    # s.recv_waddr_to_local = RecvIfcRTL(CGRAAddrType)
    # s.recv_wdata_to_local = RecvIfcRTL(CGRADataType)

    # Request from other CGRA.
    s.recv_from_other = ValRdyRecvIfcRTL(RingPktType)
    s.send_to_other = ValRdySendIfcRTL(RingPktType)

    # Request from master.
    s.recv_from_master = RecvIfcRTL(CGRADataType)
    s.send_to_master = SendIfcRTL(CGRADataType)

    # Data formatting to simplify assignment.
    s.pkt2data = Wire(CGRADataType)
    s.data2pkt = Wire(RingPktType)


    # Component
    s.queue = ChannelNormalRTL(CGRADataType, latency = 1, num_entries = 2)

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
    s.queue.recv //= s.recv_from_master


    @update
    def update_data():
      s.pkt2data.payload @= s.recv_from_other.msg.payload
      # s.data2pkt.payload @= s.recv_from_master.msg.payload
      s.data2pkt.payload @= s.queue.send.msg.payload
      s.data2pkt.src @= 1
      s.data2pkt.dst @= 2


    # Can also be @update instead of @update_ff
    @update
    def update_controller():
      s.recv_from_other.rdy @= s.send_to_master.rdy
      s.send_to_master.en @= s.recv_from_other.val & s.send_to_master.rdy
      s.send_to_master.msg @= s.pkt2data

      # s.recv_from_master.rdy @= s.send_to_other.rdy
      # s.send_to_other.val @= s.recv_from_master.en
      s.send_to_other.val @= s.queue.count > 0
      s.send_to_other.msg @= s.data2pkt
      s.queue.send.rdy @= s.send_to_other.rdy


  def line_trace(s):
    recv_from_master_str = "recv_from_master: " + str(s.recv_from_master.msg)
    send_to_master_str = "send_to_master: " + str(s.send_to_master.msg)
    recv_from_other_str = "recv_from_other: " + str(s.recv_from_other.msg)
    send_to_other_str = "send_to_other: " + str(s.send_to_other.msg)
    return f'{recv_from_master_str} || {send_to_master_str} || {recv_from_other_str} || {send_to_other_str}'

