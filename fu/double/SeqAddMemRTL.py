"""
==========================================================================
SeqAddMemRTL.py
==========================================================================
Add followed by MemUnit in sequential for CGRA tile.

Author : Cheng Tan
  Date : Oct 28, 2025
"""

from pymtl3 import *
from ..basic.TwoSeqCombo import TwoSeqCombo
from ..single.AdderRTL import AdderRTL
from ..single.MemUnitRTL import MemUnitRTL
from ...lib.opt_type import *

class SeqAddMemRTL(TwoSeqCombo):

  def construct(s, DataType, PredicateType, CtrlType,
                num_inports, num_outports,
                data_mem_size, ctrl_mem_size = 4,
                data_bitwidth = 32):

    super(SeqAddMemRTL, s).construct(DataType, PredicateType, CtrlType,
                                     AdderRTL, MemUnitRTL,
                                     num_inports, num_outports,
                                     data_mem_size, ctrl_mem_size,
                                     data_bitwidth = data_bitwidth)

    FuInType = mk_bits(clog2(num_inports + 1))

    @update
    def update_opt():

      s.Fu0.recv_opt.msg @= s.recv_opt.msg
      s.Fu1.recv_opt.msg @= s.recv_opt.msg
  
      s.Fu0.recv_opt.msg.fu_in[0] @= 1
      s.Fu0.recv_opt.msg.fu_in[1] @= 2
      s.Fu1.recv_opt.msg.fu_in[0] @= 1
      s.Fu1.recv_opt.msg.fu_in[1] @= 2

      if s.recv_opt.msg.operation == OPT_ADD_CONST_LD:
        s.Fu0.recv_opt.msg.operation @= OPT_ADD_CONST
        s.Fu1.recv_opt.msg.operation @= OPT_LD
      else:
        s.Fu0.recv_opt.msg.operation @= OPT_START
        s.Fu1.recv_opt.msg.operation @= OPT_START

      # TODO: need to handle the other cases

