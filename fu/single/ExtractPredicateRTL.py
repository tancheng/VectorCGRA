"""
==========================================================================
ExtractPredicateRTL.py
==========================================================================
Functional Unit that extracts the predicate bit from input data and outputs
it as a boolean result with payload = predicate_value, predicate = 1.

This is used to extract loop termination signals from counter outputs.

Author : Shangkun LI
  Date : January 27, 2026

"""

from pymtl3 import *
from ..basic.Fu import Fu
from ...lib.opt_type import *

class ExtractPredicateRTL(Fu):

  def construct(s, DataType, CtrlType, num_inports,
                num_outports, data_mem_size, ctrl_mem_size = 4,
                vector_factor_power = 0,
                data_bitwidth = 32):

    super(ExtractPredicateRTL, s).construct(DataType, CtrlType,
                                            num_inports, num_outports,
                                            data_mem_size, ctrl_mem_size,
                                            1, vector_factor_power,
                                            data_bitwidth = data_bitwidth)

    num_entries = 2
    FuInType = mk_bits(clog2(num_inports + 1))
    CountType = mk_bits(clog2(num_entries + 1))

    s.in0 = Wire(FuInType)
    
    idx_nbits = clog2(num_inports)
    s.in0_idx = Wire(idx_nbits)
    s.in0_idx //= s.in0[0:idx_nbits]

    @update
    def comb_logic():

      # Default values
      s.in0 @= 0
      for i in range(num_inports):
        s.recv_in[i].rdy @= b1(0)
      for i in range(num_outports):
        s.send_out[i].val @= b1(0)
        s.send_out[i].msg @= DataType()

      s.recv_const.rdy @= 0
      s.recv_opt.rdy @= 0

      s.send_to_ctrl_mem.val @= 0
      s.send_to_ctrl_mem.msg @= s.CgraPayloadType(0, 0, 0, 0, 0)
      s.recv_from_ctrl_mem.rdy @= 0

      if s.recv_opt.val:
        if s.recv_opt.msg.fu_in[0] != FuInType(0):
          s.in0 @= s.recv_opt.msg.fu_in[0] - FuInType(1)

      if s.recv_opt.val:
        if s.recv_opt.msg.operation == OPT_EXTRACT_PREDICATE:
          # Extracts predicate bit from input and output as payload.
          # When loop is running (predicate=1) -> payload=1
          # When loop terminates (predicate=0) -> payload=0
          # Downstream NOT will invert: running->0 (no RET), done->1 (trigger RET)
          s.send_out[0].msg.payload @= zext(s.recv_in[s.in0_idx].msg.predicate, DataType.get_field_type('payload'))
          s.send_out[0].msg.predicate @= 1
          
          s.send_out[0].val @= s.recv_in[s.in0_idx].val
          s.recv_in[s.in0_idx].rdy @= s.recv_in[s.in0_idx].val & s.send_out[0].rdy
          s.recv_opt.rdy @= s.recv_in[s.in0_idx].val & s.send_out[0].rdy

        else:
          for j in range(num_outports):
            s.send_out[j].val @= b1(0)
          s.recv_opt.rdy @= 0
          s.recv_in[s.in0_idx].rdy @= 0

  def line_trace(s):
    opt_str = " #"
    if s.recv_opt.val:
      opt_str = OPT_SYMBOL_DICT[s.recv_opt.msg.operation]
    out_str = ",".join([str(x.msg) for x in s.send_out])
    recv_str = ",".join([str(x.msg) for x in s.recv_in])
    return f'[ExtPred|recv: {recv_str}] {opt_str} = [out: {out_str}]'
