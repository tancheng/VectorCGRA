"""
==========================================================================
SelRTL.py
==========================================================================
Functional unit Select for CGRA tile.

Author : Cheng Tan
  Date : May 23, 2020
"""

from pymtl3 import *
from ...lib.basic.val_rdy.ifcs import ValRdySendIfcRTL, ValRdyRecvIfcRTL
from ...lib.opt_type import *

class SelRTL(Component):

  def construct(s, DataType, PredicateType, CtrlType, num_inports,
                num_outports, data_mem_size = 4):

    # Constant
    num_entries = 2
    AddrType = mk_bits(clog2(data_mem_size))
    s.const_zero = DataType(0, 0)
    s.true = DataType(1, 1)
    FuInType = mk_bits(clog2(num_inports + 1))
    CountType = mk_bits(clog2(num_entries + 1))

    # Interface
    s.recv_in = [ValRdyRecvIfcRTL(DataType) for _ in range(num_inports)]
    s.recv_predicate = ValRdyRecvIfcRTL(PredicateType)
    s.recv_const = ValRdyRecvIfcRTL(DataType)
    s.recv_opt = ValRdyRecvIfcRTL(CtrlType)
    s.send_out = [ValRdySendIfcRTL(DataType) for _ in range(num_outports)]

    # Redundant interfaces for MemUnit
    s.to_mem_raddr = ValRdySendIfcRTL(AddrType)
    s.from_mem_rdata = ValRdyRecvIfcRTL(DataType)
    s.to_mem_waddr = ValRdySendIfcRTL(AddrType)
    s.to_mem_wdata = ValRdySendIfcRTL(DataType)

    s.in0 = Wire(FuInType)
    s.in1 = Wire(FuInType)
    s.in2 = Wire(FuInType)

    idx_nbits = clog2(num_inports)
    s.in0_idx = Wire(idx_nbits)
    s.in1_idx = Wire(idx_nbits)
    s.in2_idx = Wire(idx_nbits)

    s.in0_idx //= s.in0[0:idx_nbits]
    s.in1_idx //= s.in1[0:idx_nbits]
    s.in2_idx //= s.in2[0:idx_nbits]

    # Components
    s.recv_all_val = Wire(1)

    @update
    def update_mem():
      s.to_mem_waddr.val @= b1(0)
      s.to_mem_wdata.val @= b1(0)
      s.to_mem_wdata.msg @= s.const_zero
      s.to_mem_waddr.msg @= AddrType(0)
      s.to_mem_raddr.msg @= AddrType(0)
      s.to_mem_raddr.val @= b1(0)
      s.from_mem_rdata.rdy @= b1(0)

    @update
    def comb_logic():

      s.recv_all_val @= 0
      # For pick input register, Selector needs at least 3 inputs
      s.in0 @= FuInType(0)
      s.in1 @= FuInType(0)
      s.in2 @= FuInType(0)
      for i in range(num_inports):
        s.recv_in[i].rdy @= b1(0)

      s.recv_const.rdy @= 0
      s.recv_predicate.rdy @= b1(0)
      s.recv_opt.rdy @= s.send_out[0].rdy

      for i in range(num_outports):
        s.send_out[i].val @= 0
        s.send_out[i].msg @= DataType()

      if s.recv_opt.val & s.send_out[0].rdy:
        if s.recv_opt.msg.fu_in[0] != FuInType(0):
          s.in0 @= s.recv_opt.msg.fu_in[0] - FuInType(1)
        if s.recv_opt.msg.fu_in[1] != FuInType(0):
          s.in1 @= s.recv_opt.msg.fu_in[1] - FuInType(1)
        if s.recv_opt.msg.fu_in[2] != FuInType(0):
          s.in2 @= s.recv_opt.msg.fu_in[2] - FuInType(1)

      if s.recv_opt.val:
        if s.recv_opt.msg.ctrl == OPT_SEL:
          if s.recv_in[s.in0_idx].msg.payload == s.true.payload:
            s.send_out[0].msg @= s.recv_in[s.in1_idx].msg
          else:
            s.send_out[0].msg @= s.recv_in[s.in2_idx].msg
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
        else:
          for j in range(num_outports):
            s.send_out[j].val @= b1(0)
          s.recv_opt.rdy @= 0
          s.recv_in[s.in0_idx].rdy @= 0
          s.recv_in[s.in1_idx].rdy @= 0
          s.recv_in[s.in2_idx].rdy @= 0

        if s.send_out[0].rdy & (s.recv_opt.msg.predicate == b1(1)):
          s.recv_predicate.rdy @= s.recv_all_val & s.send_out[0].rdy

  def line_trace(s):
    opt_str = " #"
    if s.recv_opt.val:
      opt_str = OPT_SYMBOL_DICT[s.recv_opt.msg.ctrl]
    out_str = ",".join([str(x.msg) for x in s.send_out])
    recv_str = ",".join([str(x.msg) for x in s.recv_in])
    return f'[recv: {recv_str}] {opt_str}(P{s.recv_opt.msg.predicate}) (const_reg: {s.recv_const.msg}, predicate_reg: {s.recv_predicate.msg}) ] = [out: {out_str}] (s.recv_opt.rdy: {s.recv_opt.rdy}, {OPT_SYMBOL_DICT[s.recv_opt.msg.ctrl]}, send[0].val: {s.send_out[0].val}) '
