"""
==========================================================================
SeqAdderMemRTL.py
==========================================================================
Adder followed by MemUnit in sequential for CGRA tile.
This enables fused address-computation + load operations.

Author : Cheng Tan
  Date : December 2, 2024
"""

from pymtl3 import *
from ..basic.TwoSeqCombo import TwoSeqCombo
from ..single.AdderRTL import AdderRTL
from ..single.MemUnitRTL import MemUnitRTL
from ...lib.opt_type import *

class SeqAdderMemRTL(TwoSeqCombo):

  # Class attribute to indicate this combo FU contains MemUnitRTL
  contains_mem_unit = True

  def construct(s, DataType, CtrlType,
                num_inports, num_outports,
                data_mem_size, ctrl_mem_size = 4,
                data_bitwidth = 32):

    super(SeqAdderMemRTL, s).construct(DataType, CtrlType,
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
        # First add the constant offset to the address, then load
        s.Fu0.recv_opt.msg.operation @= OPT_ADD_CONST
        s.Fu1.recv_opt.msg.operation @= OPT_LD
      else:
        # Indicates no computation should happen on this fused FU.
        s.Fu0.recv_opt.msg.operation @= OPT_START
        s.Fu1.recv_opt.msg.operation @= OPT_START
