"""
==========================================================================
DataMemCL.py
==========================================================================
CL data memory with preloaded data for simulation.

Author : Cheng Tan
  Date : Dec 27, 2019
"""

from copy import deepcopy
from pymtl3 import *
from ...lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ...lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ...lib.opt_type import *

class DataMemCL(Component):

  def construct(s, DataType, data_mem_size, rd_ports = 1, wr_ports = 1,
                preload_data=[]):

    # Constant
    AddrType = mk_bits(clog2(data_mem_size))

    # Interface
    s.recv_raddr = [RecvIfcRTL(AddrType) for _ in range(rd_ports)]
    s.send_rdata = [SendIfcRTL(DataType) for _ in range(rd_ports)]
    s.recv_waddr = [RecvIfcRTL(AddrType) for _ in range(wr_ports)]
    s.recv_wdata = [RecvIfcRTL(DataType) for _ in range(wr_ports)]

    # Component
    s.sram = [DataType(0, 0) for _ in range(data_mem_size)]
    for i in range(len(preload_data)):
      s.sram[i] = preload_data[i]

    @update
    def load():
      for i in range(rd_ports):
        s.send_rdata[i].msg @= s.sram[s.recv_raddr[i].msg]

    @update_once
    def store():
      for i in range(wr_ports):
        if s.recv_wdata[i].val and s.recv_waddr[i].val:
          s.sram[s.recv_waddr[i].msg] = deepcopy(s.recv_wdata[i].msg)

    @update
    def update_signal():
      for i in range(rd_ports):
        s.recv_raddr[i].rdy @= s.send_rdata[i].rdy
                              # b1( 1 ) # s.send_rdata[i].rdy
        s.send_rdata[i].val @= s.recv_raddr[i].val
                              # s.send_rdata[i].rdy # s.recv_raddr[i].en
      for i in range(wr_ports):
        s.recv_waddr[i].rdy @= Bits1(1)
        s.recv_wdata[i].rdy @= Bits1(1)

  def line_trace(s):
    recv_str = "|".join([str(data.msg) for data in s.recv_wdata])
    out_str  = "|".join([str(data)     for data in s.sram])
    send_str = "|".join([str(data.msg) for data in s.send_rdata])
    # return f'{recv_str} : [{out_str}] : {send_str}'
    sram_trace =  f'{"|".join([str(x) for x in s.sram])}'
    return f'{s.recv_waddr[0]}<{s.recv_wdata[0]}({sram_trace}){s.recv_raddr[0]}>{s.send_rdata[0]}'

