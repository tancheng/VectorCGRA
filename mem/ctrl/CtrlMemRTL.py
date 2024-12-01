"""
==========================================================================
CtrlMemRTL.py
==========================================================================
Control memory for CGRA.

Author : Cheng Tan
  Date : Dec 21, 2019

"""

from pymtl3                  import *
from pymtl3.stdlib.primitive import RegisterFile

from ...lib.ifcs     import SendIfcRTL, RecvIfcRTL
from ...lib.opt_type import *

class CtrlMemRTL( Component ):

  def construct( s, CtrlType, ctrl_mem_size, ctrl_count_per_iter = 4,
                 total_ctrl_steps = 4 ):

    # The total_ctrl_steps indicates the number of steps the ctrl
    # signals should proceed. For example, if the number of ctrl
    # signals is 4 and they need to repeat 5 times, then the total
    # number of steps should be 4 * 5 = 20.
    # assert( ctrl_mem_size <= total_ctrl_steps )

    # Constant
    AddrType = mk_bits( clog2( ctrl_mem_size ) )
    PCType   = mk_bits( clog2( ctrl_count_per_iter + 1 ) )
    TimeType = mk_bits( clog2( total_ctrl_steps + 1 ) )
    last_item = AddrType( ctrl_mem_size - 1 )

    # Interface
    s.send_ctrl  = SendIfcRTL( CtrlType )
    s.recv_waddr = RecvIfcRTL( AddrType )
    s.recv_ctrl  = RecvIfcRTL( CtrlType )

    # Component
    s.reg_file   = RegisterFile( CtrlType, ctrl_mem_size, 1, 1 )
    s.times = Wire( TimeType )

    # Connections
    s.send_ctrl.msg //= s.reg_file.rdata[0]
    s.reg_file.waddr[0] //= s.recv_waddr.msg
    s.reg_file.wdata[0] //= s.recv_ctrl.msg
    s.reg_file.wen[0]   //= lambda: s.recv_ctrl.en & s.recv_waddr.en

    @update
    def update_signal():
      if ( ( total_ctrl_steps > 0 ) & \
           ( s.times == TimeType( total_ctrl_steps ) ) ) | \
         (s.reg_file.rdata[0].ctrl == OPT_START):
        s.send_ctrl.en @= b1( 0 )
      else:
        s.send_ctrl.en @= s.send_ctrl.rdy # s.recv_raddr[i].rdy
      s.recv_waddr.rdy @= b1( 1 )
      s.recv_ctrl.rdy @= b1( 1 )

    @update_ff
    def update_raddr():
      if s.reg_file.rdata[0].ctrl != OPT_START:
        if ( total_ctrl_steps == 0 ) | \
           ( s.times < TimeType( total_ctrl_steps ) ):
          s.times <<= s.times + TimeType( 1 )
        # Reads the next ctrl signal only when the current one is done.
        if s.send_ctrl.rdy:
          if zext(s.reg_file.raddr[0] + 1, PCType) == \
             PCType( ctrl_count_per_iter ):
            s.reg_file.raddr[0] <<= AddrType( 0 )
          else:
            s.reg_file.raddr[0] <<= s.reg_file.raddr[0] + AddrType( 1 )

  def line_trace( s ):
    out_str  = f'[{", ".join([ str(data.__dict__) for data in s.reg_file.regs ])}]'
    return f'class: {s.__class__.__name__}, recv_ctrl_msg: {s.recv_ctrl.msg.__dict__} : out: {out_str} : send_ctrl_msg: {str(s.send_ctrl.msg.__dict__)}'

