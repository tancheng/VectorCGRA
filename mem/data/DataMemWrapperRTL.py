"""
==========================================================================
DataMemWrapperRTL.py
==========================================================================
Data memory for CGRA.

Author : Cheng Tan
  Date : Aug 27, 2025
"""

from pymtl3 import *
from pymtl3.stdlib.primitive import RegisterFile
from ...lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ...lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ...lib.messages import *
from ...lib.opt_type import *
from ...noc.PyOCN.pymtl3_net.channel.ChannelRTL import ChannelRTL

class DataMemWrapperRTL(Component):

  def construct(s,
                DataType,
                MemReadType,
                MemWriteType,
                MemResponseType,
                global_data_mem_size,
                per_bank_data_mem_size,
                is_combinational = True):

    # Constant.
    GlobalAddrType = mk_bits(clog2(global_data_mem_size))
    PerBankAddrType = mk_bits(clog2(per_bank_data_mem_size))

    # Interface.
    s.recv_rd = RecvIfcRTL(MemReadType)
    s.recv_wr = RecvIfcRTL(MemWriteType)
    s.send    = SendIfcRTL(MemResponseType)

    # Component.
    # As we include xbar and multi-bank for the memory hierarchy,
    # we prefer as few as possible number of ports.
    rd_ports_per_bank = 1
    wr_ports_per_bank = 1
    s.memory = RegisterFile(DataType, per_bank_data_mem_size,
                            rd_ports_per_bank, wr_ports_per_bank)
    # TODO: We need to replace channel (normal queue) with bypass
    # queue when replacing register file with SRAM. This channel
    # here is used to mimic the SRAM 1 cycle latency. Bypass queue
    # can still queue up the load requests, facilitating streaming.
    latency = 0 if is_combinational else 1
    s.channel_rd = ChannelRTL(MemReadType, latency = latency)
    s.channel_wr = ChannelRTL(MemWriteType, latency = latency)
    # s.recv_raddr = Wire(AddrType)
    # s.recv_waddr = Wire(AddrType)
    # s.recv_wdata = Wire(DataType)
    # s.recv_wen   = Wire(1)

    # Connection.
    s.recv_rd //= s.channel_rd.recv
    s.recv_wr //= s.channel_wr.recv

    # @update
    # def decompose_recv_msg():
    #   s.recv_raddr @= AddrType(0)
    #   s.recv_waddr @= AddrType(0)
    #   s.recv_wdata @= DataType(0, 0)
    #   s.recv_wen   @= b1(0)
    #   if s.channel_rd.send.val:
    #     s.recv_raddr @= s.channel_rd.send.msg.addr
    #   if s.channel_wr.send.val:
    #     s.recv_waddr @= s.channel_wr.send.msg.addr
    #     s.recv_wdata @= s.channel_wr.send.msg.data
    #     s.recv_wen   @= 1

    @update
    def compose_send_msg():
      s.send.msg @= MemResponseType(0, 0, 0, DataType(0, 0), 0, 0, 0)
      # TODO: change to pipe's out's wen.
      if s.channel_rd.send.val:
        s.send.msg      @= s.channel_rd.send.msg
        s.send.msg.src  @= s.channel_rd.send.msg.dst
        s.send.msg.dst  @= s.channel_rd.send.msg.src
        s.send.msg.data @= s.memory.rdata[0]
        print("[cheng] assembling response msg: ", s.send.msg)

    @update
    def request_memory():
      # Default values.
      s.memory.wen[0]   @= 0
      s.memory.raddr[0] @= PerBankAddrType(0)
      s.memory.waddr[0] @= PerBankAddrType(0)
      s.memory.wdata[0] @= DataType(0, 0)

      if s.channel_rd.send.val:
        s.memory.raddr[0] @= \
          trunc(s.channel_rd.send.msg.addr % per_bank_data_mem_size, PerBankAddrType)
      if s.channel_wr.send.val:
        s.memory.waddr[0] @= \
          trunc(s.channel_wr.send.msg.addr % per_bank_data_mem_size, PerBankAddrType)
        s.memory.wdata[0] @= s.channel_wr.send.msg.data
        s.memory.wen[0]   @= 1

    @update
    def notify_channel_rdy():
      # TODO: change to SRAM's rdy when replacing register file
      # with SRAM.
      s.channel_rd.send.rdy @= s.send.rdy
      s.channel_wr.send.rdy @= 1

    @update
    def notify_send_val():
      # TODO: change to SRAM's valid when replacing register file
      # with SRAM.
      s.send.val @= s.channel_rd.send.val

  def line_trace(s):
    recv_rd_str = "recv_rd_msg: " + str(s.recv_rd.msg)
    recv_wr_str = "recv_wr_msg: " + str(s.recv_wr.msg)
    content_str = "content: " + "|".join([str(data) for data in s.memory.regs])
    send_str = "send_msg: " + str(s.send.msg)
    return f'{recv_rd_str} || {recv_wr_str} || [{content_str}] || {send_str}'

