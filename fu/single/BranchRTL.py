"""
==========================================================================
BranchRTL.py
==========================================================================
Functional unit Branch for CGRA tile.

Author : Cheng Tan
  Date : December 1, 2019
"""

from pymtl3 import *
from ..basic.Fu import Fu
from ...lib.opt_type import *

class BranchRTL(Fu):

  def construct(s, DataType, PredicateType, CtrlType,
                num_inports, num_outports, data_mem_size,
                vector_factor_power = 0):

    super(BranchRTL, s).construct(DataType, PredicateType, CtrlType,
                                  num_inports, num_outports,
                                  data_mem_size, 1,
                                  vector_factor_power)

    num_entries = 2
    FuInType = mk_bits(clog2(num_inports + 1))
    CountType = mk_bits(clog2(num_entries + 1))
    s.first = Wire(b1)

    ZeroType = mk_bits(s.const_zero.payload.nbits)

    s.in0 = Wire(FuInType)

    idx_nbits = clog2(num_inports)
    s.in0_idx = Wire(idx_nbits)

    s.in0_idx //= s.in0[0:idx_nbits]

    s.recv_all_val = Wire(1)

    @update
    def comb_logic():

      s.recv_all_val @= 0
      # For pick input register
      s.in0 @= 0
      for i in range(num_inports):
        s.recv_in[i].rdy @= b1(0)
      for i in range(num_outports):
        s.send_out[i].val @= 0
        s.send_out[i].msg @= DataType()

      s.recv_const.rdy @= 0
      s.recv_predicate.rdy @= b1(0)
      s.recv_opt.rdy @= 0

      if s.recv_opt.val:
        if s.recv_opt.msg.fu_in[0] != FuInType(0):
          s.in0 @= s.recv_opt.msg.fu_in[0] - FuInType(1)

      if s.recv_opt.val:
        if s.recv_opt.msg.operation == OPT_BRH:
          # Branch is only used to set predication rather than delivering value.
          s.send_out[0].msg @= DataType(ZeroType(0), b1(0), b1(0), b1(0))
          s.send_out[1].msg @= DataType(ZeroType(0), b1(0), b1(0), b1(0))
          if s.recv_in[s.in0_idx].msg.payload == s.const_zero.payload:
            s.send_out[0].msg.predicate @= (~s.recv_opt.msg.predicate | \
                                            s.recv_predicate.msg.predicate) & \
                                           s.reached_vector_factor
            s.send_out[1].msg.predicate @= Bits1(0)
          else:
            s.send_out[0].msg.predicate @= Bits1(0)
            s.send_out[1].msg.predicate @= (~s.recv_opt.msg.predicate | \
                                            s.recv_predicate.msg.predicate) & \
                                           s.reached_vector_factor
          s.recv_all_val @= s.recv_in[s.in0_idx].val & \
                            ((s.recv_opt.msg.predicate == b1(0)) | s.recv_predicate.val)
          s.send_out[0].val @= s.recv_all_val
          s.send_out[1].val @= s.recv_all_val
          s.recv_in[s.in0_idx].rdy @= s.recv_all_val & s.send_out[0].rdy & s.send_out[1].rdy
          s.recv_opt.rdy @= s.recv_all_val & s.send_out[0].rdy & s.send_out[1].rdy

        elif s.recv_opt.msg.operation == OPT_BRH_START:
          s.send_out[0].msg @= DataType(ZeroType(0), b1(0), b1(0), b1(0))
          s.send_out[1].msg @= DataType(ZeroType(0), b1(0), b1(0), b1(0))
          # branch_start could be the entry of a function, which runs
          # only once.
          if s.first:
            s.send_out[0].msg.predicate @= s.reached_vector_factor
            s.send_out[1].msg.predicate @= Bits1(0)
          else:
            s.send_out[0].msg.predicate @= Bits1(0)
            s.send_out[1].msg.predicate @= s.reached_vector_factor
          s.recv_all_val @= s.recv_in[s.in0_idx].val & \
                            ((s.recv_opt.msg.predicate == b1(0)) | s.recv_predicate.val)
          s.send_out[0].val @= s.recv_all_val
          s.send_out[1].val @= s.recv_all_val
          s.recv_in[s.in0_idx].rdy @= s.recv_all_val & s.send_out[0].rdy & s.send_out[1].rdy
          s.recv_opt.rdy @= s.recv_all_val & s.send_out[0].rdy & s.send_out[1].rdy

        else:
          for j in range( num_outports ):
            s.send_out[j].val @= b1( 0 )
          s.recv_opt.rdy @= 0
          s.recv_in[s.in0_idx].rdy @= 0

        if (s.recv_opt.msg.predicate == 1) & \
           (s.recv_opt.msg.operation != OPT_BRH_START):
          s.recv_predicate.rdy @= s.recv_all_val & s.send_out[0].rdy & s.send_out[1].rdy

    # branch_start could be the entry of a function, which is executed by
    # only once.
    @update_ff
    def br_start_once():
      if s.reset:
        s.first <<= b1(1)
      if (s.recv_opt.msg.operation == OPT_BRH_START) & s.reached_vector_factor:
        s.first <<= b1(0)

  def line_trace( s ):
    symbol0 = "?"
    symbol1 = "?"
    winner  = "nobody"
    if s.recv_opt.msg.operation == OPT_BRH_START:
      symbol0 = " "
      symbol1 = " "
      winner = "nobody"
    elif s.send_out[0].msg.predicate == Bits1(1):
      symbol0 = "*"
      symbol1 = " "
      winner  = "false "
    elif s.send_out[1].msg.predicate == Bits1(1):
      symbol0 = " "
      symbol1 = "*"
      winner  = " true "
    return f'[{s.recv_in[0].msg}|{s.recv_in[1].msg}] => ([{s.send_out[0].msg} {symbol0}] (wnner: {winner}) [{s.send_out[1].msg}(first:{s.first}) {symbol1}])'

