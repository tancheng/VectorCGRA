"""
==========================================================================
PhiRTL.py
==========================================================================
Functional unit Phi for CGRA tile. Note that only one phi_const or
phi_start can be mapped onto the same tile, as we only have one 'first'
bit to record whether it is the first execution.

Author : Cheng Tan
  Date : November 30, 2019
"""

from pymtl3 import *
from ..basic.Fu import Fu
from ...lib.opt_type import *
import copy

class PhiRTL(Fu):

  def construct(s, CtrlPktType, num_inports, num_outports, vector_factor_power = 0):

    super(PhiRTL, s).construct(CtrlPktType, num_inports, num_outports, 1, vector_factor_power)
    
    num_entries = 2
    FuInType = mk_bits(clog2(num_inports + 1))
    CountType = mk_bits(clog2(num_entries + 1))
    s.first = Wire(b1)

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

      s.send_to_ctrl_mem.val @= 0
      s.send_to_ctrl_mem.msg @= s.CgraPayloadType(0, 0, 0, 0, 0)
      s.recv_from_ctrl_mem.rdy @= 0

      if s.recv_opt.val:
        if s.recv_opt.msg.fu_in[0] != FuInType(0):
          s.in0 @= s.recv_opt.msg.fu_in[0] - FuInType(1)
        if s.recv_opt.msg.fu_in[1] != FuInType(0):
          s.in1 @= s.recv_opt.msg.fu_in[1] - FuInType(1)

      # TODO: decision needs to be made. Adder could be in FU vector width. Or only effective once on the boundary.
      # if s.recv_opt.val:
      if s.recv_opt.val:
        if s.recv_opt.msg.operation == OPT_PHI:
          if s.recv_in[s.in0_idx].msg.predicate == Bits1(1):
            s.send_out[0].msg.payload @= s.recv_in[s.in0_idx].msg.payload
            s.send_out[0].msg.predicate @= s.reached_vector_factor
          elif s.recv_in[s.in1_idx].msg.predicate == Bits1(1):
            s.send_out[0].msg.payload @= s.recv_in[s.in1_idx].msg.payload
            s.send_out[0].msg.predicate @= s.reached_vector_factor
          else: # No predecessor is active.
            s.send_out[0].msg.payload @= s.recv_in[s.in0_idx].msg.payload
            s.send_out[0].msg.predicate @= 0
          s.recv_all_val @= s.recv_in[s.in0_idx].val & s.recv_in[s.in1_idx].val
          s.send_out[0].val @= s.recv_all_val
          s.recv_in[s.in0_idx].rdy @= s.recv_all_val & s.send_out[0].rdy
          s.recv_in[s.in1_idx].rdy @= s.recv_all_val & s.send_out[0].rdy
          s.recv_opt.rdy @= s.recv_all_val & s.send_out[0].rdy

        elif s.recv_opt.msg.operation == OPT_PHI_START:
          if s.first:
            s.send_out[0].msg.payload @= s.recv_in[s.in0_idx].msg.payload
            s.send_out[0].msg.predicate @= s.reached_vector_factor
          elif s.recv_in[s.in0_idx].msg.predicate == Bits1(1):
            s.send_out[0].msg.payload @= s.recv_in[s.in0_idx].msg.payload
            s.send_out[0].msg.predicate @= s.reached_vector_factor
          elif s.recv_in[s.in1_idx].msg.predicate == Bits1(1):
            s.send_out[0].msg.payload @= s.recv_in[s.in1_idx].msg.payload
            s.send_out[0].msg.predicate @= s.reached_vector_factor
          else: # No predecessor is active.
            s.send_out[0].msg.payload @= s.recv_in[s.in0_idx].msg.payload
            s.send_out[0].msg.predicate @= 0
          s.recv_all_val @= ((s.first & s.recv_in[s.in0_idx].val) | \
                             (~s.first & s.recv_in[s.in0_idx].val & s.recv_in[s.in1_idx].val))
          s.send_out[0].val @= s.recv_all_val
          s.recv_in[s.in0_idx].rdy @= s.recv_all_val & s.send_out[0].rdy
          s.recv_in[s.in1_idx].rdy @= ~s.first & s.recv_all_val & s.send_out[0].rdy
          s.recv_opt.rdy @= s.recv_all_val & s.send_out[0].rdy
 
        elif s.recv_opt.msg.operation == OPT_PHI_CONST:
          if s.first:
            s.send_out[0].msg.payload @= s.recv_const.msg.payload
          else:
            s.send_out[0].msg.payload @= s.recv_in[s.in0_idx].msg.payload

          s.recv_all_val @= ((s.first & s.recv_const.val) | \
                             (~s.first & s.recv_in[s.in0_idx].val))
          s.send_out[0].val @= s.recv_all_val
          s.recv_in[s.in0_idx].rdy @= s.recv_all_val & s.send_out[0].rdy
          s.recv_const.rdy @= s.recv_all_val & s.send_out[0].rdy
          s.recv_opt.rdy @= s.recv_all_val & s.send_out[0].rdy

          if s.first:
            s.send_out[0].msg.predicate @= s.recv_const.msg.predicate & \
                                           s.reached_vector_factor
          else:
            s.send_out[0].msg.predicate @= s.recv_in[s.in0_idx].msg.predicate & \
                                           s.reached_vector_factor
 
        else:
          for j in range(num_outports):
            s.send_out[j].val @= b1(0)
          s.recv_opt.rdy @= 0
          s.recv_in[s.in0_idx].rdy @= 0
          s.recv_in[s.in1_idx].rdy @= 0

    # branch_start could be the entry of a function, which is executed by
    # only once.
    @update_ff
    def br_start_once():
      if s.reset | s.clear:
        s.first <<= b1(1)
      if ((s.recv_opt.msg.operation == OPT_PHI_CONST) | (s.recv_opt.msg.operation == OPT_PHI_START)) & s.reached_vector_factor:
        s.first <<= b1(0)

  def line_trace(s):
    opt_str = " #"
    if s.recv_opt.val:
      opt_str = OPT_SYMBOL_DICT[s.recv_opt.msg.operation]
    out_str = ",".join([str(x.msg) for x in s.send_out])
    recv_str = ",".join([str(x.msg) for x in s.recv_in])
    return f'[recv: {recv_str}] {opt_str} (const_reg: {s.recv_const.msg}) ] = [out: {out_str}] (s.recv_opt.rdy: {s.recv_opt.rdy}, {OPT_SYMBOL_DICT[s.recv_opt.msg.operation]}, send[0].val: {s.send_out[0].val}) reached_vector_factor: {s.reached_vector_factor}; vector_factor_counter: {s.vector_factor_counter}'

