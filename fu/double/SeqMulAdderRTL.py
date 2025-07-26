"""
==========================================================================
SeqMulAdderRTL.py
==========================================================================
Mul followed by Adder in sequential for CGRA tile.

Author : Cheng Tan
  Date : November 28, 2019
"""

from pymtl3 import *
from ..basic.TwoSeqCombo import TwoSeqCombo
from ..single.MulRTL import MulRTL
from ..single.AdderRTL import AdderRTL
from ...lib.opt_type import *

class SeqMulAdderRTL(TwoSeqCombo):

  def construct(s, DataType, PredicateType, CtrlType,
                num_inports, num_outports, data_mem_size):

    super(SeqMulAdderRTL, s).construct(DataType, PredicateType, CtrlType,
                                       MulRTL, AdderRTL, num_inports,
                                       num_outports, data_mem_size)

    FuInType = mk_bits(clog2(num_inports + 1))

    @update
    def update_opt():

      s.Fu0.recv_opt.msg @= s.recv_opt.msg
      s.Fu1.recv_opt.msg @= s.recv_opt.msg
  
      s.Fu0.recv_opt.msg.fu_in[0] @= 1
      s.Fu0.recv_opt.msg.fu_in[1] @= 2
      s.Fu1.recv_opt.msg.fu_in[0] @= 1
      s.Fu1.recv_opt.msg.fu_in[1] @= 2

      if s.recv_opt.msg.operation == OPT_MUL_ADD:
        s.Fu0.recv_opt.msg.operation @= OPT_MUL
        s.Fu1.recv_opt.msg.operation @= OPT_ADD
      elif s.recv_opt.msg.operation == OPT_MUL_CONST_ADD:
        s.Fu0.recv_opt.msg.operation @= OPT_MUL_CONST
        s.Fu1.recv_opt.msg.operation @= OPT_ADD
      elif s.recv_opt.msg.operation == OPT_MUL_CONST:
        s.Fu0.recv_opt.msg.operation @= OPT_MUL_CONST
        s.Fu1.recv_opt.msg.operation @= OPT_PAS
      elif s.recv_opt.msg.operation == OPT_MUL_SUB:
        s.Fu0.recv_opt.msg.operation @= OPT_MUL
        s.Fu1.recv_opt.msg.operation @= OPT_SUB
      else:
        # Indicates no computation should happen no this fused FU.
        # This is necessary to avoid the OPT_MUL_CONST be executed
        # by both Mul and MulAdder.
        s.Fu0.recv_opt.msg.operation @= OPT_START
        s.Fu1.recv_opt.msg.operation @= OPT_START

      # TODO: need to handle the other cases

