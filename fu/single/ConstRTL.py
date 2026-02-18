"""
==========================================================================
ConstRTL.py
==========================================================================
Functional Unit for constant in a CGRA tile.

Author : Cheng Tan
  Date : Oct 28, 2025
"""

from pymtl3 import *
from ..basic.Fu import Fu
from ...lib.opt_type import *

class ConstRTL(Fu):

  def construct(s, CtrlPktType, num_inports, num_outports, vector_factor_power = 0):

    super(ConstRTL, s).construct(CtrlPktType, num_inports, num_outports, 1, vector_factor_power)

    num_entries = 2
    FuInType = mk_bits(clog2(num_inports + 1))
    CountType = mk_bits(clog2(num_entries + 1))

    s.recv_all_val = Wire(1)

    @update
    def comb_logic():

      s.recv_all_val @= 0
      for i in range(num_inports):
        s.recv_in[i].rdy @= b1(0)
      for i in range( num_outports ):
        s.send_out[i].val @= b1(0)
        s.send_out[i].msg @= s.DataType()

      s.recv_const.rdy @= 0
      s.recv_opt.rdy @= 0

      s.send_to_ctrl_mem.val @= 0
      s.send_to_ctrl_mem.msg @= s.CgraPayloadType(0, 0, 0, 0, 0)
      s.recv_from_ctrl_mem.rdy @= 0

      if s.recv_opt.val:
        if s.recv_opt.msg.operation == OPT_CONST:
          s.send_out[0].msg.payload @= s.recv_const.msg.payload
          s.send_out[0].msg.predicate @= s.recv_const.msg.predicate & \
                                         s.reached_vector_factor
          s.recv_all_val @= s.recv_const.val
          s.send_out[0].val @= s.recv_all_val
          s.recv_const.rdy @= s.recv_all_val & s.send_out[0].rdy
          s.recv_opt.rdy @= s.recv_all_val & s.send_out[0].rdy
        else:
          for j in range(num_outports):
            s.send_out[j].val @= b1(0)
          s.recv_opt.rdy @= 0
