"""
==========================================================================
NahRTL.py
==========================================================================
Handling nothing, but proceeding ctrl index.

Author : Cheng Tan
  Date : Dec 28, 2024
"""

from pymtl3 import *
from ..basic.Fu import Fu
from ...lib.opt_type import *

class NahRTL(Fu):

  def construct(s, DataType, PredicateType, CtrlType,
                num_inports, num_outports, data_mem_size,
                vector_factor_power = 0, data_bitwidth = 32):

    super(NahRTL, s).construct(DataType, PredicateType, CtrlType,
                               num_inports, num_outports,
                               data_mem_size, 1,
                               vector_factor_power,
                               data_bitwidth = data_bitwidth)

    @update
    def comb_logic():

      s.recv_const.rdy @= 0
      s.recv_opt.rdy @= 0
      # For pick input register
      for i in range(num_inports):
        s.recv_in[i].rdy @= b1(0)

      for i in range( num_outports ):
        # s.send_out[i].val @= s.recv_opt.val
        s.send_out[i].val @= 0
        s.send_out[i].msg @= DataType()

      s.send_to_controller.val @= 0
      s.send_to_controller.msg @= DataType()

      if s.recv_opt.msg.operation == OPT_NAH:
        s.recv_opt.rdy @= 1
      else:
        for j in range(num_outports):
          s.send_out[j].val @= b1(0)
        s.recv_opt.rdy @= 0
