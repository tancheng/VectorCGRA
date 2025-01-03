"""
==========================================================================
FpMulRTL.py
==========================================================================
Floating-point Muliplier for CGRA tile.

Rounding mode:
round_near_even   = 0b000
round_minMag      = 0b001
round_min         = 0b010
round_max         = 0b011
round_near_maxMag = 0b100
round_odd         = 0b110

Author : Cheng Tan
  Date : August 9, 2023
"""

from pymtl3 import *
from ..basic.Fu import Fu
from ..pymtl3_hardfloat.HardFloat.MulFNRTL import MulFN
from ...lib.opt_type import *

class FpMulRTL(Fu):

  def construct(s, DataType, PredicateType, CtrlType,
                num_inports, num_outports, data_mem_size, exp_nbits = 4,
                sig_nbits = 11):

    super(FpMulRTL, s).construct(DataType, PredicateType, CtrlType,
                                 num_inports, num_outports,
                                 data_mem_size)

    # Local parameters
    assert DataType.get_field_type('payload').nbits == exp_nbits + sig_nbits + 1

    num_entries = 2
    FuInType    = mk_bits(clog2(num_inports + 1))
    CountType   = mk_bits(clog2(num_entries + 1))

    # TODO: parameterize rounding mode
    s.rounding_mode = 0b000

    # Components
    s.fmul = MulFN(exp_nbits+1, sig_nbits)
    s.fmul.roundingMode //= s.rounding_mode

    # Wires
    s.in0 = Wire(FuInType)
    s.in1 = Wire(FuInType)

    idx_nbits = clog2(num_inports)
    s.in0_idx = Wire(idx_nbits)
    s.in1_idx = Wire(idx_nbits)

    s.in0_idx //= s.in0[0:idx_nbits]
    s.in1_idx //= s.in1[0:idx_nbits]

    s.recv_all_val = Wire(1)

    @update
    def comb_logic():

      # For pick input register
      s.in0 @= 0
      s.in1 @= 0
      for i in range( num_inports ):
        s.recv_in[i].rdy @= b1(0)

      for i in range( num_outports ):
        s.send_out[i].en  @= s.recv_opt.en
        s.send_out[i].msg @= DataType()

      s.recv_const.rdy @= 0
      s.recv_predicate.rdy @= b1(0)
      s.recv_opt.rdy @= 0

      if s.recv_opt.en:
        if s.recv_opt.msg.fu_in[0] != 0:
          s.in0 @= zext(s.recv_opt.msg.fu_in[0] - 1, FuInType)
        if s.recv_opt.msg.fu_in[1] != 0:
          s.in1 @= zext(s.recv_opt.msg.fu_in[1] - 1, FuInType)

      s.send_out[0].msg.predicate @= s.recv_in[s.in0_idx].msg.predicate & \
                                     s.recv_in[s.in1_idx].msg.predicate

      if s.recv_opt.val:
        if s.recv_opt.msg.ctrl == OPT_FMUL:
          s.fmul.a @= s.recv_in[s.in0_idx].msg.payload
          s.fmul.b @= s.recv_in[s.in1_idx].msg.payload
          s.send_out[0].msg.predicate @= s.recv_in[s.in0_idx].msg.predicate & \
                                         s.recv_in[s.in1_idx].msg.predicate & \
                                         (~s.recv_opt.msg.predicate | \
                                          s.recv_predicate.msg.predicate)
          s.recv_all_val @= s.recv_in[s.in0_idx].val & s.recv_in[s.in1_idx].val & \
                            ((s.recv_opt.msg.predicate == b1(0)) | s.recv_predicate.val)
          s.send_out[0].val @= s.recv_all_val
          s.recv_in[s.in0_idx].rdy @= s.recv_all_val & s.send_out[0].rdy
          s.recv_in[s.in1_idx].rdy @= s.recv_all_val & s.send_out[0].rdy
          s.recv_opt.rdy @= s.recv_all_val & s.send_out[0].rdy

        elif s.recv_opt.msg.ctrl == OPT_FMUL_CONST:
          s.fmul.a @= s.recv_in[s.in0_idx].msg.payload
          s.fmul.b @= s.recv_const.msg.payload
          s.send_out[0].msg.predicate @= s.recv_in[s.in0_idx].msg.predicate & \
                                         (~s.recv_opt.msg.predicate | \
                                          s.recv_predicate.msg.predicate)
          s.recv_all_val @= s.recv_in[s.in0_idx].val & s.recv_in[s.in1_idx].val & \
                            ((s.recv_opt.msg.predicate == b1(0)) | s.recv_predicate.val)
          s.send_out[0].val @= s.recv_all_val
          s.recv_in[s.in0_idx].rdy @= s.recv_all_val & s.send_out[0].rdy
          s.recv_in[s.in1_idx].rdy @= s.recv_all_val & s.send_out[0].rdy
          s.recv_opt.rdy @= s.recv_all_val & s.send_out[0].rdy

        else:
          for j in range( num_outports ):
            s.send_out[j].val @= b1( 0 )
          s.recv_opt.rdy @= 0
          s.recv_in[s.in0_idx].rdy @= 0
          s.recv_in[s.in1_idx].rdy @= 0

        if s.recv_opt.msg.predicate == b1(1):
          s.recv_predicate.rdy @= s.recv_all_val & s.send_out[0].rdy

        s.send_out[0].msg.payload @= s.fmul.out
