"""
==========================================================================
CompRTL.py
==========================================================================
Functional unit for performing comparison.

Author : Cheng Tan
  Date : December 2, 2019
"""

from pymtl3 import *
from ..basic.Fu import Fu
from ...lib.opt_type import *

class CompRTL(Fu):

  def construct(s, DataType, PredicateType, CtrlType, num_inports,
                num_outports, data_mem_size, vector_factor_power = 0):

    super(CompRTL, s).construct(DataType, PredicateType, CtrlType,
                                num_inports, num_outports, data_mem_size,
                                1, vector_factor_power)

    num_entries = 2
    s.const_one = DataType(1, 0)
    FuInType = mk_bits(clog2(num_inports + 1))
    CountType = mk_bits(clog2(num_entries + 1))

    # data:      s.recv_in[0]
    # reference: s.recv_in[1] (or recv_const)

    s.in0 = Wire(FuInType)
    s.in1 = Wire(FuInType)

    idx_nbits = clog2(num_inports)
    s.in0_idx = Wire(idx_nbits)
    s.in1_idx = Wire(idx_nbits)

    s.in0_idx //= s.in0[0:idx_nbits]
    s.in1_idx //= s.in1[0:idx_nbits]

    s.recv_all_val = Wire(1)

    @update
    def read_reg():

      s.recv_all_val @= 0
      # For pick input register
      s.in0 @= FuInType(0)
      s.in1 @= FuInType(0)
      for i in range(num_inports):
        s.recv_in[i].rdy @= b1(0)
      for i in range(num_outports):
        s.send_out[i].val @= 0
        s.send_out[i].msg @= DataType()

      s.recv_const.rdy @= 0
      s.recv_predicate.rdy @= b1(0)
      s.recv_opt.rdy @= 0

      if s.recv_opt.val:
        if s.recv_opt.msg.fu_in[0] != FuInType( 0 ):
          s.in0 @= s.recv_opt.msg.fu_in[0] - FuInType(1)
        if s.recv_opt.msg.fu_in[1] != FuInType(0):
          s.in1 @= s.recv_opt.msg.fu_in[1] - FuInType(1)

      if s.recv_opt.val:
        if (s.recv_opt.msg.operation == OPT_EQ) | (s.recv_opt.msg.operation == OPT_NE):
          if (s.recv_opt.msg.operation == OPT_EQ) & \
             (s.recv_in[s.in0_idx].msg.payload == s.recv_in[s.in1_idx].msg.payload):
            s.send_out[0].msg @= s.const_one
          elif (s.recv_opt.msg.operation == OPT_NE) & \
               (s.recv_in[s.in0_idx].msg.payload != s.recv_in[s.in1_idx].msg.payload):
            s.send_out[0].msg @= s.const_one
          else:
            s.send_out[0].msg @= s.const_zero
          s.send_out[0].msg.predicate @= s.recv_in[s.in0_idx].msg.predicate & \
                                         s.recv_in[s.in1_idx].msg.predicate & \
                                         (~s.recv_opt.msg.predicate | \
                                          s.recv_predicate.msg.predicate) & \
                                         s.reached_vector_factor
          s.recv_all_val @= s.recv_in[s.in0_idx].val & s.recv_in[s.in1_idx].val & \
                            ((s.recv_opt.msg.predicate == b1(0)) | s.recv_predicate.val)
          s.send_out[0].val @= s.recv_all_val
          s.recv_in[s.in0_idx].rdy @= s.recv_all_val & s.send_out[0].rdy
          s.recv_in[s.in1_idx].rdy @= s.recv_all_val & s.send_out[0].rdy
          s.recv_opt.rdy @= s.recv_all_val & s.send_out[0].rdy

        elif (s.recv_opt.msg.operation == OPT_EQ_CONST) | (s.recv_opt.msg.operation == OPT_NE_CONST):
          if (s.recv_opt.msg.operation == OPT_EQ_CONST) & \
             (s.recv_in[s.in0_idx].msg.payload == s.recv_const.msg.payload):
            s.send_out[0].msg @= s.const_one
          elif (s.recv_opt.msg.operation == OPT_NE_CONST) & \
               (s.recv_in[s.in0_idx].msg.payload != s.recv_const.msg.payload):
            s.send_out[0].msg @= s.const_one
          else:
            s.send_out[0].msg @= s.const_zero
          s.send_out[0].msg.predicate @= s.recv_in[s.in0_idx].msg.predicate & \
                                         (~s.recv_opt.msg.predicate | \
                                          s.recv_predicate.msg.predicate) & \
                                         s.reached_vector_factor
          s.recv_all_val @= s.recv_in[s.in0_idx].val & s.recv_const.val & \
                            ((s.recv_opt.msg.predicate == b1(0)) | s.recv_predicate.val)
          s.send_out[0].val @= s.recv_all_val
          s.recv_in[s.in0_idx].rdy @= s.recv_all_val & s.send_out[0].rdy
          s.recv_const.rdy @= s.recv_all_val & s.send_out[0].rdy
          s.recv_opt.rdy @= s.recv_all_val & s.send_out[0].rdy

        elif s.recv_opt.msg.operation == OPT_LT:
          if s.recv_in[s.in0_idx].msg.payload < s.recv_in[s.in1_idx].msg.payload:
            s.send_out[0].msg @= s.const_one
          else:
            s.send_out[0].msg @= s.const_zero
          s.send_out[0].msg.predicate @= s.recv_in[s.in0_idx].msg.predicate & \
                                         s.recv_in[s.in1_idx].msg.predicate & \
                                         (~s.recv_opt.msg.predicate | \
                                          s.recv_predicate.msg.predicate) & \
                                         s.reached_vector_factor
          s.recv_all_val @= s.recv_in[s.in0_idx].val & s.recv_in[s.in1_idx].val & \
                            ((s.recv_opt.msg.predicate == b1(0)) | s.recv_predicate.val)
          s.send_out[0].val @= s.recv_all_val
          s.recv_in[s.in0_idx].rdy @= s.recv_all_val & s.send_out[0].rdy
          s.recv_in[s.in1_idx].rdy @= s.recv_all_val & s.send_out[0].rdy
          s.recv_opt.rdy @= s.recv_all_val & s.send_out[0].rdy

        else:
          for j in range(num_outports):
            s.send_out[j].val @= b1(0)
          s.recv_opt.rdy @= 0
          s.recv_in[s.in0_idx].rdy @= 0
          s.recv_in[s.in1_idx].rdy @= 0

        if s.recv_opt.msg.predicate == b1(1):
          s.recv_predicate.rdy @= s.recv_all_val & s.send_out[0].rdy

