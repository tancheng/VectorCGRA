"""
==========================================================================
DivRTL.py
==========================================================================
Integer divider for CGRA tile.

Author : Jiajun Qin
  Date : May 2, 2025
"""

from pymtl3 import *
from ..basic.Fu import Fu
from ...lib.opt_type import *

class DivRTL(Fu):

  def construct(s, CtrlPktType, num_inports, num_outports, vector_factor_power = 0):

    super(DivRTL, s).construct(CtrlPktType, num_inports, num_outports, 1, vector_factor_power)

    num_entries = 2
    FuInType = mk_bits(clog2(num_inports + 1))
    CountType = mk_bits(clog2(num_entries + 1))

    s.in0 = Wire(FuInType)
    s.in1 = Wire(FuInType)

    idx_nbits = clog2(num_inports)
    s.in0_idx = Wire(idx_nbits)
    s.in1_idx = Wire(idx_nbits)

    s.in0_idx //= s.in0[0:idx_nbits]
    s.in1_idx //= s.in1[0:idx_nbits]

    PayloadType = s.DataType.get_field_type('payload')
    RemainderType = mk_bits(PayloadType.nbits + 1)

    s.recv_all_val = Wire(1)
    s.dividend = Wire(PayloadType)
    s.divisor = Wire(PayloadType)
    s.div_quotient = Wire(PayloadType)
    s.div_remainder = Wire(PayloadType)

    @update
    def comb_div_rem():
      quotient = PayloadType(0)
      remainder = RemainderType(0)

      if s.divisor != 0:
        for i in range(PayloadType.nbits):
          remainder = (remainder << 1) | \
              zext(s.dividend[PayloadType.nbits - 1 - i], RemainderType.nbits)
          if remainder >= zext(s.divisor, RemainderType.nbits):
            remainder = remainder - zext(s.divisor, RemainderType.nbits)
            quotient = quotient | \
                (PayloadType(1) << (PayloadType.nbits - 1 - i))

      s.div_quotient @= quotient
      if s.divisor != 0:
        s.div_remainder @= s.dividend % s.divisor
      else:
        s.div_remainder @= 0

    @update
    def comb_logic():

      s.recv_all_val @= 0
      # For pick input register
      s.in0 @= 0
      s.in1 @= 0
      for i in range(num_inports):
        s.recv_in[i].rdy @= b1(0)
      for i in range(num_outports):
        s.send_out[i].val @= 0
        s.send_out[i].msg @= s.DataType()

      s.recv_const.rdy @= 0
      s.recv_opt.rdy @= 0
      s.dividend @= 0
      s.divisor @= 0

      s.send_to_ctrl_mem.val @= 0
      s.send_to_ctrl_mem.msg @= s.CgraPayloadType(0, 0, 0, 0, 0)
      s.recv_from_ctrl_mem.rdy @= 0

      if s.recv_opt.val:
        if s.recv_opt.msg.fu_in[0] != 0:
          s.in0 @= zext(s.recv_opt.msg.fu_in[0] - 1, FuInType)
        if s.recv_opt.msg.fu_in[1] != 0:
          s.in1 @= zext(s.recv_opt.msg.fu_in[1] - 1, FuInType)

      if s.recv_opt.val:
        if s.recv_opt.msg.operation == OPT_DIV:
          s.dividend @= s.recv_in[s.in0_idx].msg.payload
          s.divisor @= s.recv_in[s.in1_idx].msg.payload
          s.send_out[0].msg.payload @= s.div_quotient
          s.send_out[0].msg.predicate @= s.recv_in[s.in0_idx].msg.predicate & \
                                         s.recv_in[s.in1_idx].msg.predicate & \
                                         s.reached_vector_factor
          s.recv_all_val @= s.recv_in[s.in0_idx].val & s.recv_in[s.in1_idx].val
          s.send_out[0].val @= s.recv_all_val
          s.recv_in[s.in0_idx].rdy @= s.recv_all_val & s.send_out[0].rdy
          s.recv_in[s.in1_idx].rdy @= s.recv_all_val & s.send_out[0].rdy
          s.recv_opt.rdy @= s.recv_all_val & s.send_out[0].rdy

        elif s.recv_opt.msg.operation == OPT_DIV_CONST:
          s.dividend @= s.recv_in[s.in0_idx].msg.payload
          s.divisor @= s.recv_const.msg.payload
          s.send_out[0].msg.payload @= s.div_quotient
          s.send_out[0].msg.predicate @= s.recv_in[s.in0_idx].msg.predicate & \
                                         s.reached_vector_factor
          s.recv_all_val @= s.recv_in[s.in0_idx].val & s.recv_const.val
          s.send_out[0].val @= s.recv_all_val
          s.recv_in[s.in0_idx].rdy @= s.recv_all_val & s.send_out[0].rdy
          s.recv_const.rdy @= s.recv_all_val & s.send_out[0].rdy
          s.recv_opt.rdy @= s.recv_all_val & s.send_out[0].rdy

        elif s.recv_opt.msg.operation == OPT_REM:
          s.dividend @= s.recv_in[s.in0_idx].msg.payload
          s.divisor @= s.recv_in[s.in1_idx].msg.payload
          s.send_out[0].msg.payload @= s.div_remainder
          s.send_out[0].msg.predicate @= \
              s.recv_in[s.in0_idx].msg.predicate & \
              s.recv_in[s.in1_idx].msg.predicate & \
              s.reached_vector_factor
          s.recv_all_val @= \
              s.recv_in[s.in0_idx].val & s.recv_in[s.in1_idx].val
          s.send_out[0].val @= s.recv_all_val
          s.recv_in[s.in0_idx].rdy @= \
              s.recv_all_val & s.send_out[0].rdy
          s.recv_in[s.in1_idx].rdy @= \
              s.recv_all_val & s.send_out[0].rdy
          s.recv_opt.rdy @= s.recv_all_val & s.send_out[0].rdy

        elif s.recv_opt.msg.operation == OPT_REM_CONST:
          s.dividend @= s.recv_in[s.in0_idx].msg.payload
          s.divisor @= s.recv_const.msg.payload
          s.send_out[0].msg.payload @= s.div_remainder
          s.send_out[0].msg.predicate @= \
              s.recv_in[s.in0_idx].msg.predicate & s.reached_vector_factor
          s.recv_all_val @= s.recv_in[s.in0_idx].val & s.recv_const.val
          s.send_out[0].val @= s.recv_all_val
          s.recv_in[s.in0_idx].rdy @= \
              s.recv_all_val & s.send_out[0].rdy
          s.recv_const.rdy @= s.recv_all_val & s.send_out[0].rdy
          s.recv_opt.rdy @= s.recv_all_val & s.send_out[0].rdy

        else:
          for j in range(num_outports):
            s.send_out[j].val @= b1(0)
          s.recv_opt.rdy @= 0
          s.recv_in[s.in0_idx].rdy @= 0
          s.recv_in[s.in1_idx].rdy @= 0
