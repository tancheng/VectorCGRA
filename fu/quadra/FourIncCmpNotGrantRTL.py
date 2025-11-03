"""
==========================================================================
FourIncCmpNotGrantRTL.py
==========================================================================

    inc
    / |
 cmp  |
  | \ |
 not  grt

4 FUs combined together to form above pattern, which requires 4 inputs,
and generates 2 outputs.

Author : Cheng Tan
  Date : Oct 28, 2025
"""

from pymtl3 import *
from ...lib.opt_type   import *
from ..basic.FourCombo import FourCombo
from ..single.AdderRTL import AdderRTL
from ..single.CompRTL  import CompRTL
from ..single.GrantRTL import GrantRTL
from ..single.LogicRTL import LogicRTL

class FourIncCmpNotGrantRTL(FourCombo):

  def construct(s, DataType, CtrlType,
                num_inports, num_outports,
                data_mem_size, ctrl_mem_size = 4,
                data_bitwidth = 32):

    super(FourIncCmpNotGrantRTL, s).construct(DataType,
                                              CtrlType,
                                              AdderRTL,
                                              CompRTL,
                                              LogicRTL,
                                              GrantRTL,
                                              num_inports, num_outports,
                                              data_mem_size, ctrl_mem_size,
                                              data_bitwidth = data_bitwidth)

    @update
    def update_opt():

      s.Fu0.recv_opt.msg @= s.recv_opt.msg
      s.Fu1.recv_opt.msg @= s.recv_opt.msg
      s.Fu2.recv_opt.msg @= s.recv_opt.msg
      s.Fu3.recv_opt.msg @= s.recv_opt.msg

      s.Fu0.recv_opt.msg.fu_in[0] @= 1
      s.Fu0.recv_opt.msg.fu_in[1] @= 2
      s.Fu1.recv_opt.msg.fu_in[0] @= 1
      s.Fu1.recv_opt.msg.fu_in[1] @= 2
      s.Fu2.recv_opt.msg.fu_in[0] @= 1
      s.Fu2.recv_opt.msg.fu_in[1] @= 2
      s.Fu3.recv_opt.msg.fu_in[0] @= 1
      s.Fu3.recv_opt.msg.fu_in[1] @= 2

      if s.recv_opt.msg.operation == OPT_INC_NE_CONST_NOT_GRT:
        s.Fu0.recv_opt.msg.operation @= OPT_INC
        s.Fu1.recv_opt.msg.operation @= OPT_NE_CONST
        s.Fu2.recv_opt.msg.operation @= OPT_NOT
        s.Fu3.recv_opt.msg.operation @= OPT_GRT_PRED
      else:
        # Indicates no computation should happen no this fused FU.
        s.Fu0.recv_opt.msg.operation @= OPT_START
        s.Fu1.recv_opt.msg.operation @= OPT_START
        s.Fu2.recv_opt.msg.operation @= OPT_START
        s.Fu3.recv_opt.msg.operation @= OPT_START

      # TODO: need to handle the other cases

