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


  # verbose trace
  def verbose_trace( s, verbosity = 1 ):
    # data memory: mem size, reg
    # recv_raddr(rdy, msg), send_rdata(en, msg), recv_waddr(rdy, msg), recv_wdata, tile #
    reg_dicts = [ dict(data.__dict__) for data in s.reg_file.regs ]
    reg_list = []
    for idx, data in enumerate(reg_dicts):
      reg_dict = {"addr": f"addr {idx}"}
      reg_dict.update(data)
      reg_list.append(reg_dict)
    reg_md = markdown_table(reg_list).set_params(quote=False).get_markdown()

    rw_ports_max_count = max(len(s.recv_raddr), len(s.recv_waddr))
    mem_list = []
    for idx in range(rw_ports_max_count):
      recv_raddr_rdy, recv_raddr = None, None
      send_rdata_en, send_rdata = None, None
      recv_waddr_rdy, recv_waddr = None, None
      recv_wdata = None
      if idx <= len(s.recv_raddr) - 1:
        recv_raddr_rdy = s.recv_raddr[idx].rdy
        recv_raddr = s.recv_raddr[idx].msg
        send_rdata_en = s.send_rdata[idx].en
        send_rdata = s.send_rdata[idx].msg.payload
      if idx <= len(s.recv_waddr) - 1:
        recv_waddr_rdy = s.recv_waddr[idx].rdy
        recv_waddr = s.recv_waddr[idx].msg
        recv_wdata = s.recv_wdata[idx].msg.payload
      mem_dict = {"recv_raddr(rdy, msg)": f"{recv_raddr_rdy}, {recv_raddr}",
                  "send_rdata(en, msg)": f"{send_rdata_en}, {send_rdata}",
                  "recv_waddr(rdy, msg)": f"{recv_waddr_rdy}, {recv_waddr}",
                  "recv_wdata": f"{recv_wdata}",
                  "Tiles in Col0": "<--- Tile"}
      mem_list.append(mem_dict)
    mem_md = markdown_table(mem_list).set_params(quote=False).get_markdown()

    return (f'\nclass: {s.__class__.__name__}\n'
            f'- regs(mem size: {len(reg_dicts)}): {reg_md}\n'
            f'- mem_r/w:'
            f'{mem_md}')


  def line_trace( s ):
    recv_raddr_str = "recv_read_addr: " + "|".join([str(data.msg) for data in s.recv_raddr])
    recv_waddr_str = "recv_write_addr: " + "|".join([str(data.msg) for data in s.recv_waddr])
    recv_wdata_str = "recv_write_data: " + "|".join([str(data.msg) for data in s.recv_wdata])
    content_str = "content: " + "|".join([str(data) for data in s.reg_file.regs])
    send_rdata_str = "send_read_data: " + "|".join([str(data.msg) for data in s.send_rdata])
    return f'{recv_raddr_str} || {recv_waddr_str} || {recv_wdata_str} || [{content_str}] || {send_rdata_str}'
    # return f'DataMem: {recv_str} : [{out_str}] : {send_str} initWrites: {s.initWrites}'
    # return s.reg_file.line_trace()
    # return f'<{s.reg_file.wen[0]}>{s.reg_file.waddr[0]}:{s.reg_file.wdata[0]}|{s.reg_file.raddr[0]}:{s.reg_file.rdata[0]}'
    # rf_trace = f'<{s.reg_file.wen[0]}>{s.reg_file.waddr[0]}:{s.reg_file.wdata[0]}|{s.reg_file.raddr[0]}:{s.reg_file.rdata[0]}'
    # return f'[{s.recv_wdata[0].en & s.recv_waddr[0].en}]{s.recv_waddr[0]}<{s.recv_wdata[0]}({rf_trace}){s.recv_raddr[0]}>{s.send_rdata[0]}'

