"""
==========================================================================
AluGenMacRTL.py
==========================================================================
Floating point add unit.

Author : Yanghui Ou & Ron Jokai
  Date : Jan 6, 2024
"""

from pymtl3 import *
from ..basic.Fu import Fu
from .AluGenMacWrapperRTL import AluGenMacWrapperRTL
from ...lib.opt_type import *

class AluGenMacRTL(Fu):

  def construct(s, DataType, PredicateType, CtrlType,
                num_inports, num_outports, data_mem_size):

    super(AluGenMacRTL, s).construct(DataType, PredicateType, CtrlType,
                                     num_inports, num_outports,
                                     data_mem_size)

    # Local parameters
    assert DataType.get_field_type('payload').nbits == 16

    num_entries = 3
    FuInType    = mk_bits(clog2(num_inports + 1))
    CountType   = mk_bits(clog2(num_entries + 1))

    # Components
    s.fALU = AluGenMacWrapperRTL()
    s.fALU.rhs_2 //= lambda:   0 if s.recv_opt.msg.ctrl == OPT_ADD     else \
                             ( 1 if s.recv_opt.msg.ctrl == OPT_SUB     else \
                             ( 3 if s.recv_opt.msg.ctrl == OPT_LT      else \
                             ( 7 if s.recv_opt.msg.ctrl == OPT_GTE     else \
                             (10 if s.recv_opt.msg.ctrl == OPT_GT      else \
                             (14 if s.recv_opt.msg.ctrl == OPT_LTE     else \
                             (16 if s.recv_opt.msg.ctrl == OPT_MUL     else \
                             (48 if s.recv_opt.msg.ctrl == OPT_MUL_ADD else 0)))))))

    # Wires
    s.in0 = Wire( FuInType )
    s.in1 = Wire( FuInType )
    s.in2 = Wire( FuInType )

    idx_nbits = clog2( num_inports )
    s.in0_idx = Wire( idx_nbits )
    s.in1_idx = Wire( idx_nbits )
    s.in2_idx = Wire( idx_nbits )

    s.in0_idx //= s.in0[0:idx_nbits]
    s.in1_idx //= s.in1[0:idx_nbits]
    s.in2_idx //= s.in2[0:idx_nbits]

    s.recv_all_val = Wire(1)

    @update
    def comb_logic():

      s.recv_all_val @= 0
      # For pick input register
      s.in0 @= 0
      s.in1 @= 0
      s.in2 @= 0
      for i in range(num_inports):
        s.recv_in[i].rdy @= b1(0)

      for i in range(num_outports):
        s.send_out[i].val @= 0
        s.send_out[i].msg @= DataType()

      s.recv_const.rdy @= 0
      s.recv_predicate.rdy @= b1(0)
      s.recv_opt.rdy @= 0

      if s.recv_opt.val & s.send_out[0].rdy:
        if s.recv_opt.msg.fu_in[0] != 0:
          s.in0 @= zext(s.recv_opt.msg.fu_in[0] - 1, FuInType)
        if s.recv_opt.msg.fu_in[1] != 0:
          s.in1 @= zext(s.recv_opt.msg.fu_in[1] - 1, FuInType)
        if s.recv_opt.msg.fu_in[2] != 0:
          s.in2 @= zext(s.recv_opt.msg.fu_in[2] - 1, FuInType)

      if s.recv_opt.val:
        # FIXME: Handle recv_all_val for different cases, e.g., some ops do not need
        # 3 operands, some ops do not need const.
        if (s.recv_opt.msg.ctrl == OPT_ADD    ) | \
           (s.recv_opt.msg.ctrl == OPT_SUB    ) | \
           (s.recv_opt.msg.ctrl == OPT_LT     ) | \
           (s.recv_opt.msg.ctrl == OPT_GTE    ) | \
           (s.recv_opt.msg.ctrl == OPT_GT     ) | \
           (s.recv_opt.msg.ctrl == OPT_LTE    ) | \
           (s.recv_opt.msg.ctrl == OPT_MUL    ) | \
           (s.recv_opt.msg.ctrl == OPT_MUL_ADD):
          s.fALU.rhs_0  @= s.recv_in[s.in0_idx].msg.payload
          s.fALU.rhs_1  @= s.recv_in[s.in1_idx].msg.payload
          s.fALU.rhs_1b @= s.recv_in[s.in2_idx].msg.payload
          s.send_out[0].msg.predicate @= s.recv_in[s.in0_idx].msg.predicate & \
                                         s.recv_in[s.in1_idx].msg.predicate & \
                                         s.recv_in[s.in2_idx].msg.predicate & \
                                         (~s.recv_opt.msg.predicate | \
                                          s.recv_predicate.msg.predicate)
          s.recv_all_val @= s.recv_in[s.in0_idx].val & \
                            s.recv_in[s.in1_idx].val & \
                            s.recv_in[s.in2_idx].val & \
                            ((s.recv_opt.msg.predicate == b1(0)) | s.recv_predicate.val)
          s.send_out[0].val @= s.recv_all_val
          s.recv_in[s.in0_idx].rdy @= s.recv_all_val & s.send_out[0].rdy
          s.recv_in[s.in1_idx].rdy @= s.recv_all_val & s.send_out[0].rdy
          s.recv_in[s.in2_idx].rdy @= s.recv_all_val & s.send_out[0].rdy
          s.recv_opt.rdy @= s.recv_all_val & s.send_out[0].rdy
          # FIXME: @RJ, what is the following for?
          #elif s.recv_opt.msg.ctrl == OPT_FADD_CONST:
          #  s.fadd.rhs_0 @= s.recv_in[s.in0_idx].msg.payload
          #  s.fadd.rhs_1 @= s.recv_const.msg.payload
          #  s.send_out[0].msg.predicate @= s.recv_in[s.in0_idx].msg.predicate

          #elif s.recv_opt.msg.ctrl == OPT_FINC:
          #  s.fadd.rhs_0 @= s.recv_in[s.in0_idx].msg.payload
          #  s.fadd.rhs_1 @= s.FLOATING_ONE
          #  s.send_out[0].msg.predicate @= s.recv_in[s.in0_idx].msg.predicate

          #elif s.recv_opt.msg.ctrl == OPT_FSUB:
          #  s.fadd.rhs_0 @= s.recv_in[s.in0_idx].msg.payload
          #  s.fadd.rhs_1 @= s.recv_in[s.in1_idx].msg.payload
          #  s.send_out[0].msg.predicate @= s.recv_in[s.in0_idx].msg.predicate
          #  if s.recv_opt.en & ( (s.recv_in_count[s.in0_idx] == 0) | \
          #                       (s.recv_in_count[s.in1_idx] == 0) ):
          #    s.recv_in[s.in0_idx].rdy @= b1( 0 )
          #    s.recv_in[s.in1_idx].rdy @= b1( 0 )
          #    s.send_out[0].msg.predicate @= b1( 0 )

        else:
          for j in range(num_outports):
            s.send_out[j].val @= b1(0)
          s.recv_opt.rdy @= 0
          s.recv_in[s.in0_idx].rdy @= 0
          s.recv_in[s.in1_idx].rdy @= 0
          s.recv_in[s.in2_idx].rdy @= 0

        if s.recv_opt.msg.predicate == b1(1):
          s.recv_predicate.rdy @= s.recv_all_val & s.send_out[0].rdy

        s.send_out[0].msg.payload @= s.fALU.lhs_0

