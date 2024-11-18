"""
==========================================================================
CtrlMemCL.py
==========================================================================
CL control memory used for simulation.

Author : Cheng Tan
  Date : Dec 27, 2019

"""

from pymtl3                  import *
from pymtl3.stdlib.primitive import RegisterFile

from ...lib.ifcs     import SendIfcRTL, RecvIfcRTL
from ...lib.opt_type import *

class CtrlMemCL( Component ):

  def construct( s, CtrlType, ctrl_mem_size, ctrl_count_per_iter = 4,
                 total_ctrl_steps = 4, opt_list = None, id = 0 ):

    # Constant
    s.id = id
    AddrType = mk_bits( clog2( ctrl_mem_size ) )
    PCType   = mk_bits( clog2( ctrl_count_per_iter + 1 ) )
    TimeType = mk_bits( clog2( total_ctrl_steps + 2 ) )

    # Interface
    s.send_ctrl  = SendIfcRTL( CtrlType )

    # Component
    s.sram = [ CtrlType( 0 ) for _ in range( ctrl_mem_size ) ]
    for i in range( len( opt_list ) ):
      s.sram[ i ] = opt_list[i]
    s.times = Wire( TimeType )
    s.cur  = Wire( AddrType )

    @update
    def load():
      if s.times != 0:
        s.send_ctrl.msg @= s.sram[ s.cur ]

    @update
    def update_signal():
      if s.times == 0:
        s.send_ctrl.en @= b1( 0 )
      elif s.times == TimeType( total_ctrl_steps ) or s.sram[s.cur].ctrl == OPT_START:
        s.send_ctrl.en @= b1( 0 )
      else:
        s.send_ctrl.en  @= s.send_ctrl.rdy

    @update_ff
    def update_raddr():

      if s.times < TimeType( total_ctrl_steps ):
        s.times <<= s.times + TimeType( 1 )

      if s.send_ctrl.rdy:
        if zext(s.cur + 1, PCType) == PCType( ctrl_count_per_iter ):
          s.cur <<= AddrType( 0 )
        else:
          s.cur <<= s.cur + AddrType( 1 )


  def line_trace( s ):
    out_str  = "||".join([ str(data) for data in s.sram ])
    return f'[{out_str}] : {OPT_SYMBOL_DICT[s.send_ctrl.msg.ctrl]}'

