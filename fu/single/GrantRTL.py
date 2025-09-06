"""
==========================================================================
GrantRTL.py
==========================================================================
Functional unit for granting predicate.

Author : Cheng Tan
  Date : July 18, 2025
"""

from pymtl3 import *
from ..basic.Fu import Fu
from ...lib.opt_type import *

class GrantRTL(Fu):

  def construct(s, DataType, PredicateType, CtrlType,
                num_inports, num_outports, data_mem_size,
                vector_factor_power = 0, data_bitwidth = 32):

    super(GrantRTL, s).construct(DataType, PredicateType, CtrlType,
                                  num_inports, num_outports,
                                  data_mem_size, 1,
                                  vector_factor_power,
                                  data_bitwidth = data_bitwidth)

    # Constants.
    num_entries = 2
    FuInType = mk_bits(clog2(num_inports + 1))
    CountType = mk_bits(clog2(num_entries + 1))
    idx_nbits = clog2(num_inports)

    # Components.
    s.in0 = Wire(FuInType)
    s.in1 = Wire(FuInType)
    s.in0_idx = Wire(idx_nbits)
    s.in1_idx = Wire(idx_nbits)
    s.recv_all_val = Wire(1)
    s.already_grt_once = Wire(1)

    # Connections.
    s.in0_idx //= s.in0[0:idx_nbits]
    s.in1_idx //= s.in1[0:idx_nbits]

    @update
    def comb_logic():

      s.recv_all_val @= 0
      # For pick input register
      s.in0 @= 0
      s.in1 @= 0
      for i in range(num_inports):
        s.recv_in[i].rdy @= b1(0)
      for i in range(num_outports):
        s.send_out[i].val @= b1(0)
        s.send_out[i].msg @= DataType()

      s.recv_const.rdy @= 0
      s.recv_opt.rdy @= 0

      s.send_to_controller.val @= 0
      s.send_to_controller.msg @= DataType()

      if s.recv_opt.val:
        if s.recv_opt.msg.fu_in[0] != FuInType(0):
          s.in0 @= s.recv_opt.msg.fu_in[0] - FuInType(1)
        if s.recv_opt.msg.fu_in[1] != FuInType(0):
          s.in1 @= s.recv_opt.msg.fu_in[1] - FuInType(1)

      if s.recv_opt.val:
        if s.recv_opt.msg.operation == OPT_GRT_PRED:
          # GRANT_PREDICATE is used to apply (`and` operation) predicate onto a value.
          # The second operand would be used/treated as the predicate condition that
          # is usually coming from a `cmp` operation.
          s.send_out[0].msg.payload @= s.recv_in[s.in0_idx].msg.payload
          # Only updates predicate if the condition is true. Note that we respect
          # condition's (operand_1's) both value and predicate.
          if s.recv_in[s.in1_idx].msg.payload != s.const_zero.payload:
            s.send_out[0].msg.predicate @= s.recv_in[s.in0_idx].msg.predicate & \
                                           s.recv_in[s.in1_idx].msg.predicate & \
                                           s.reached_vector_factor
          s.recv_all_val @= s.recv_in[s.in0_idx].val & s.recv_in[s.in1_idx].val
          s.send_out[0].val @= s.recv_all_val
          s.recv_in[s.in0_idx].rdy @= s.recv_all_val & s.send_out[0].rdy
          s.recv_in[s.in1_idx].rdy @= s.recv_all_val & s.send_out[0].rdy
          s.recv_opt.rdy @= s.recv_all_val & s.send_out[0].rdy
        elif s.recv_opt.msg.operation == OPT_GRT_ALWAYS:
          # GRANT_ALWAYS is used to apply `true` predicate onto a value regardless
          # its original predicate value. This is usually used for the constant declared
          # in the entry block of a function, and then being used as a bound variable
          # in some streaming loop. Note that if we fuse the constant and the grant_always,
          # we may not need this operation, as the constant is usually preloaded into the
          # ConstQueue with `true` predicate.
          s.send_out[0].msg @= s.recv_in[s.in0_idx].msg
          # Always updates predicate as true.
          s.send_out[0].msg.predicate @= s.reached_vector_factor

          s.recv_all_val @= s.recv_in[s.in0_idx].val
          s.send_out[0].val @= s.recv_all_val
          s.recv_in[s.in0_idx].rdy @= s.recv_all_val & s.send_out[0].rdy
          s.recv_opt.rdy @= s.recv_all_val & s.send_out[0].rdy
        elif s.recv_opt.msg.operation == OPT_GRT_ONCE:
          # GRANT_ONCE is used to apply `true` predicate onto a value only once. This
          # is usually used for the constant declared in the entry block of a function.
          s.send_out[0].msg @= s.recv_in[s.in0_idx].msg
          # Only updates predicate as true for the first time.
          s.send_out[0].msg.predicate @= s.reached_vector_factor & ~s.already_grt_once

          s.recv_all_val @= s.recv_in[s.in0_idx].val
          s.send_out[0].val @= s.recv_all_val
          s.recv_in[s.in0_idx].rdy @= s.recv_all_val & s.send_out[0].rdy
          s.recv_opt.rdy @= s.recv_all_val & s.send_out[0].rdy

        else:
          for j in range( num_outports ):
            s.send_out[j].val @= b1( 0 )
          s.recv_opt.rdy @= 0
          s.recv_in[s.in0_idx].rdy @= 0
          s.recv_in[s.in1_idx].rdy @= 0

    @update_ff
    def record_grt_once():
      if s.reset:
        s.already_grt_once <<= 0
      else:
        if ~s.already_grt_once & s.send_out[0].val & s.send_out[0].rdy & (s.recv_opt.msg.operation == OPT_GRT_ONCE):
          s.already_grt_once <<= 1
        else:
          s.already_grt_once <<= s.already_grt_once