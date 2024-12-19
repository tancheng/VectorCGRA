"""
==========================================================================
DataMemRTL.py
==========================================================================
Data memory for CGRA.

Author : Cheng Tan
  Date : Dec 20, 2019
"""
from py_markdown_table.markdown_table import markdown_table
from pymtl3 import *
from pymtl3.stdlib.primitive import RegisterFile
from ...lib.basic.en_rdy.ifcs import SendIfcRTL, RecvIfcRTL
from ...lib.opt_type import *


class DataMemRTL( Component ):

  def construct( s, DataType, data_mem_size, rd_ports = 1, wr_ports = 1,
                 preload_data = None ):

    # Constant

    AddrType = mk_bits( clog2( data_mem_size ) )

    # Interface

    s.recv_raddr = [ RecvIfcRTL( AddrType ) for _ in range( rd_ports ) ]
    s.send_rdata = [ SendIfcRTL( DataType ) for _ in range( rd_ports ) ]
    s.recv_waddr = [ RecvIfcRTL( AddrType ) for _ in range( wr_ports ) ]
    s.recv_wdata = [ RecvIfcRTL( DataType ) for _ in range( wr_ports ) ]

    # Component

    s.reg_file   = RegisterFile( DataType, data_mem_size, rd_ports, wr_ports + rd_ports )
    s.initWrites = [ Wire( b1 ) for _ in range( data_mem_size ) ]

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
          if s.recv_waddr[i].en == b1(1):
            s.reg_file.wen[i] @= s.recv_wdata[i].en & s.recv_waddr[i].en

    else:
      s.preloadData = [ Wire( DataType ) for _ in range( data_mem_size ) ]
      for i in range( len( preload_data ) ):
        s.preloadData[ i ] //= preload_data[i]

      @update
      def update_read_with_init():

        for i in range( rd_ports ):
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
          if s.recv_waddr[i].en == b1(1):
            s.reg_file.waddr[i] @= s.recv_waddr[i].msg
            s.reg_file.wdata[i] @= s.recv_wdata[i].msg
            s.reg_file.wen[i]   @= s.recv_wdata[i].en & s.recv_waddr[i].en

    # Connections

    @update_ff
    def update_init():
      for i in range( rd_ports ):
        if s.recv_raddr[i].en == b1(1):
          s.initWrites[s.recv_raddr[i].msg] <<= s.initWrites[s.recv_raddr[i].msg] | b1(1)
      for i in range( wr_ports ):
        if s.recv_waddr[i].en == b1(1):
          s.initWrites[s.recv_waddr[i].msg] <<= s.initWrites[s.recv_waddr[i].msg] | b1(1)

    @update
    def update_signal():
      for i in range( rd_ports ):
        s.recv_raddr[i].rdy @= s.send_rdata[i].rdy
                              # b1( 1 ) # s.send_rdata[i].rdy
        s.send_rdata[i].en  @= s.recv_raddr[i].en
                              # s.send_rdata[i].rdy # s.recv_raddr[i].en
      for i in range( wr_ports ):
        s.recv_waddr[i].rdy @= Bits1( 1 )
        s.recv_wdata[i].rdy @= Bits1( 1 )

  def line_trace(s):
    recv_raddr_str = f'[{", ".join([str(data.msg) for data in s.recv_raddr])}]'
    recv_waddr_str = f'[{", ".join([str(data.msg) for data in s.recv_waddr])}]'
    recv_wdata_dicts = [dict(data.msg.__dict__) for data in s.recv_wdata]
    recv_wdata_md = markdown_table(recv_wdata_dicts).set_params(quote=False).get_markdown()
    reg_dicts = [dict(data.__dict__) for data in s.reg_file.regs]
    reg_md = markdown_table(reg_dicts).set_params(quote=False).get_markdown()
    send_rdata_dicts = [dict(data.msg.__dict__) for data in s.send_rdata]
    send_rdata_md = markdown_table(send_rdata_dicts).set_params(quote=False).get_markdown()
    return (f'\nclass: {s.__class__.__name__}\n'
            f'- recv_raddr: {recv_raddr_str}\n'
            f'- recv_waddr: {recv_waddr_str}\n'
            f'- recv_wdata: {recv_wdata_md}\n'
            f'- regs: {reg_md}\n'
            f'- send_rdata: {send_rdata_md}')
