"""
==========================================================================
RegisterFile.py
==========================================================================
Register file for CGRA tile.

Author : Cheng Tan
  Date : Dec 10, 2019
"""


from pymtl3 import *
from pymtl3.stdlib.primitive import RegisterFile
from ..lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ..lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ..lib.opt_type import *

class RegFile( Component ):

  def construct( s, DataType, nregs ):

    # Constant

    AddrType = mk_bits( max(clog2( nregs ), 1) )

    # Interface

    s.recv_waddr = RecvIfcRTL( AddrType )
    s.recv_wdata = RecvIfcRTL( DataType )
    s.recv_raddr = RecvIfcRTL( AddrType )
    s.send_rdata = SendIfcRTL( DataType )

    # Component

    s.reg_file   = RegisterFile( DataType, nregs )

    # Connections

    s.reg_file.raddr[0] //= s.recv_raddr.msg
    s.reg_file.waddr[0] //= s.recv_waddr.msg
    s.reg_file.wdata[0] //= s.recv_wdata.msg
    s.send_rdata.msg    //= s.reg_file.rdata[0]
    s.reg_file.wen[0]   //= b1( 1 )

    @update
    def update_signal():
      s.recv_raddr.rdy @= s.send_rdata.rdy
      s.recv_waddr.rdy @= s.send_rdata.rdy
      s.recv_wdata.rdy @= s.send_rdata.rdy
      s.send_rdata.val @= s.recv_raddr.val

  def line_trace( s ):
    out_str = "|".join([ str(data) for data in s.reg_file.regs ])
    return f'[{out_str}] : {s.recv_wdata.msg}'

