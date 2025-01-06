"""
==========================================================================
DataMemScalableRTL.py
==========================================================================
Data memory for CGRA. It has addtional port to connect to controller,
which can be used for multi-CGRA fabric.

Author : Cheng Tan
  Date : Dec 4, 2024
"""

from pymtl3 import *
from pymtl3.stdlib.primitive import RegisterFile
from ...lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ...lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ...lib.opt_type import *

class DataMemScalableRTL(Component):

  def construct(s, DataType, data_mem_size, rd_ports = 1, wr_ports = 1,
                preload_data = None):

    # Constant
    AddrType = mk_bits(clog2(data_mem_size))

    # Interface
    s.recv_raddr = [RecvIfcRTL(AddrType) for _ in range(rd_ports)]
    s.send_rdata = [SendIfcRTL(DataType) for _ in range(rd_ports)]
    s.recv_waddr = [RecvIfcRTL(AddrType) for _ in range(wr_ports)]
    s.recv_wdata = [RecvIfcRTL(DataType) for _ in range(wr_ports)]

    s.recv_from_noc = RecvIfcRTL(DataType)
    s.send_to_noc = SendIfcRTL(DataType)

    # Component

    s.reg_file   = RegisterFile( DataType, data_mem_size, rd_ports, wr_ports + rd_ports )
    s.initWrites = [ Wire( b1 ) for _ in range( data_mem_size ) ]

    # FIXME: Following signals need to be set via some logic, i.e.,
    # handling miss accesses.
    s.send_to_noc.val //= 0
    s.send_to_noc.msg //= DataType(0, 0)
    s.recv_from_noc.rdy //= 0

    if preload_data == None:
      @update
      def update_read_without_init():
        for i in range( rd_ports ):
          # s.reg_file.wen[wr_ports + i] @= b1(0)
          s.reg_file.raddr[i] @= s.recv_raddr[i].msg
          s.send_rdata[i].msg @= s.reg_file.rdata[i]

        for i in range( wr_ports ):
          s.reg_file.wen[i]   @= b1(0)
          s.reg_file.waddr[i] @= s.recv_waddr[i].msg
          s.reg_file.wdata[i] @= s.recv_wdata[i].msg
          if s.recv_waddr[i].val == b1(1):
            s.reg_file.wen[i] @= s.recv_wdata[i].val & s.recv_waddr[i].val

    else:
      s.preloadData = [Wire(DataType) for _ in range(data_mem_size)]
      for i in range(len( preload_data)):
        s.preloadData[i] //= preload_data[i]

      @update
      def update_read_with_init():

        for i in range(rd_ports):
          s.reg_file.wen[wr_ports + i] @= b1(0)
          if s.initWrites[s.recv_raddr[i].msg] == b1(0):
            s.send_rdata[i].msg @= s.preloadData[s.recv_raddr[i].msg]
            s.reg_file.waddr[wr_ports + i] @= s.recv_raddr[i].msg
            s.reg_file.wdata[wr_ports + i] @= s.preloadData[s.recv_raddr[i].msg]
            s.reg_file.wen[wr_ports + i]   @= b1(1)
          else:
            s.reg_file.raddr[i] @= s.recv_raddr[i].msg
            s.send_rdata[i].msg @= s.reg_file.rdata[i]

        for i in range( wr_ports ):
          if s.recv_waddr[i].val == b1(1):
            s.reg_file.waddr[i] @= s.recv_waddr[i].msg
            s.reg_file.wdata[i] @= s.recv_wdata[i].msg
            s.reg_file.wen[i]   @= s.recv_wdata[i].val & s.recv_waddr[i].val

    # Connections

    @update_ff
    def update_init():
      for i in range( rd_ports ):
        if s.recv_raddr[i].val == b1(1):
          s.initWrites[s.recv_raddr[i].msg] <<= s.initWrites[s.recv_raddr[i].msg] | b1(1)
      for i in range( wr_ports ):
        if s.recv_waddr[i].val == b1(1):
          s.initWrites[s.recv_waddr[i].msg] <<= s.initWrites[s.recv_waddr[i].msg] | b1(1)

    @update
    def update_signal():
      for i in range( rd_ports ):
        s.recv_raddr[i].rdy @= s.send_rdata[i].rdy
        s.send_rdata[i].val  @= s.recv_raddr[i].val
      for i in range( wr_ports ):
        s.recv_waddr[i].rdy @= Bits1( 1 )
        s.recv_wdata[i].rdy @= Bits1( 1 )

  def line_trace(s):
    recv_raddr_str = "recv_read_addr: " + "|".join([str(data.msg) for data in s.recv_raddr])
    recv_waddr_str = "recv_write_addr: " + "|".join([str(data.msg) for data in s.recv_waddr])
    recv_wdata_str = "recv_write_data: " + "|".join([str(data.msg) for data in s.recv_wdata])
    content_str = "content: " + "|".join([str(data) for data in s.reg_file.regs])
    send_rdata_str = "send_read_data: " + "|".join([str(data.msg) for data in s.send_rdata])
    return f'{recv_raddr_str} || {recv_waddr_str} || {recv_wdata_str} || [{content_str}] || {send_rdata_str}'

