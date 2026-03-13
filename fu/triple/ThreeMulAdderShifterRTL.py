"""
==========================================================================
ThreeMulShifterRTL.py
==========================================================================
Mul and Adder in parallel followed by a shifter for CGRA tile.

Author : Cheng Tan
  Date : November 28, 2019
"""

from pymtl3 import *
from ...lib.opt_type       import *
from ..basic.ThreeCombo    import ThreeCombo
from ..single.MulRTL       import MulRTL
from ..single.AdderRTL     import AdderRTL
from ..single.ShifterRTL   import ShifterRTL

class ThreeMulAdderShifterRTL(ThreeCombo):

  def construct(s, CtrlPktType, num_inports, num_outports):

    super(ThreeMulAdderShifterRTL, s).construct(CtrlPktType, MulRTL,
                                                AdderRTL, ShifterRTL,
                                                num_inports, num_outports)

    @update
    def update_opt():

      s.Fu0.recv_opt.msg.fu_in[0] @= 1
      s.Fu0.recv_opt.msg.fu_in[1] @= 2
      s.Fu1.recv_opt.msg.fu_in[0] @= 1
      s.Fu1.recv_opt.msg.fu_in[1] @= 2
      s.Fu2.recv_opt.msg.fu_in[0] @= 1
      s.Fu2.recv_opt.msg.fu_in[1] @= 2

      if s.recv_opt.msg.operation == OPT_MUL_ADD_LLS:
        s.Fu0.recv_opt.msg.operation @= OPT_MUL
        s.Fu1.recv_opt.msg.operation @= OPT_ADD
        s.Fu2.recv_opt.msg.operation @= OPT_LLS
      elif s.recv_opt.msg.operation == OPT_MUL_SUB_LLS:
        s.Fu0.recv_opt.msg.operation @= OPT_MUL
        s.Fu1.recv_opt.msg.operation @= OPT_SUB
        s.Fu2.recv_opt.msg.operation @= OPT_LLS
      elif s.recv_opt.msg.operation == OPT_MUL_SUB_LRS:
        s.Fu0.recv_opt.msg.operation @= OPT_MUL
        s.Fu1.recv_opt.msg.operation @= OPT_SUB
        s.Fu2.recv_opt.msg.operation @= OPT_LRS
      else:
        # Indicates no computation should happen no this fused FU.
        s.Fu0.recv_opt.msg.operation @= OPT_START
        s.Fu1.recv_opt.msg.operation @= OPT_START
        s.Fu2.recv_opt.msg.operation @= OPT_START

      # TODO: need to handle the other cases

