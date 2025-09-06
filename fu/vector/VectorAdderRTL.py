"""
==========================================================================
VectorAdderRTL.py
==========================================================================
Vectorized adder to support SIMD addition in different granularities.
This basic adder is different from the scalar one:
    1. Need to handle the carry in/out value.
    2. Can directly perform on bits rather than CGRADataType.

Author : Cheng Tan
  Date : March 27, 2022
"""


from pymtl3 import *
from ...lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ...lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ...lib.opt_type import *

class VectorAdderRTL(Component):

  def construct(s, bw, CtrlType, num_inports, num_outports,
                data_mem_size):

    # DataType should be 1-bit more due to the carry-out.
    num_entries = 2
    DataType = mk_bits(bw + 1)
    FuInType = mk_bits(clog2(num_inports + 1))
    CountType = mk_bits(clog2(num_entries + 1))
    FuInType = mk_bits(clog2(num_inports + 1))

    # Constants.
    s.const_zero = DataType(0)
    s.const_one = DataType(1)

    # Interfaces.
    s.recv_in = [RecvIfcRTL(DataType) for _ in range(num_inports)]
    s.recv_const = RecvIfcRTL(DataType)
    s.recv_opt = RecvIfcRTL(CtrlType)
    s.send_out = [SendIfcRTL(DataType) for _ in range(num_outports)]
    s.send_to_controller = SendIfcRTL(DataType)

    # Components.
    s.carry_in = InPort(b1)
    s.combine_adder = InPort(b1)
    s.carry_out = OutPort(b1)
    s.carry_in_temp = Wire(DataType)
    s.in0 = Wire(FuInType)
    s.in1 = Wire(FuInType)
    idx_nbits = clog2(num_inports)
    s.in0_idx = Wire(idx_nbits)
    s.in1_idx = Wire(idx_nbits)
    s.recv_all_val = Wire(1)

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

      s.send_to_controller.val @= 0
      s.send_to_controller.msg @= DataType()

      s.recv_const.rdy @= 0
      s.recv_opt.rdy @= 0

      s.carry_in_temp[0] @= s.carry_in & s.combine_adder
      if s.recv_opt.val:
        if s.recv_opt.msg.fu_in[0] != FuInType(0):
          s.in0 @= s.recv_opt.msg.fu_in[0] - FuInType(1)
        if s.recv_opt.msg.fu_in[1] != FuInType(0):
          s.in1 @= s.recv_opt.msg.fu_in[1] - FuInType(1)

      if s.recv_opt.val:
        if s.recv_opt.msg.operation == OPT_ADD:
          s.send_out[0].msg @= s.recv_in[s.in0_idx].msg + s.recv_in[s.in1_idx].msg + s.carry_in_temp
          s.recv_all_val @= s.recv_in[s.in0_idx].val & s.recv_in[s.in1_idx].val
          s.send_out[0].val @= s.recv_all_val
          s.recv_in[s.in0_idx].rdy @= s.recv_all_val & s.send_out[0].rdy
          s.recv_in[s.in1_idx].rdy @= s.recv_all_val & s.send_out[0].rdy
          s.recv_opt.rdy @= s.recv_all_val & s.send_out[0].rdy

        elif s.recv_opt.msg.operation == OPT_ADD_CONST:
          s.send_out[0].msg @= s.recv_in[s.in0_idx].msg + s.recv_const.msg + s.carry_in_temp
          s.recv_const.rdy @= s.send_out[0].rdy
          s.recv_all_val @= s.recv_in[s.in0_idx].val & s.recv_const.val
          s.send_out[0].val @= s.recv_all_val
          s.recv_in[s.in0_idx].rdy @= s.recv_all_val & s.send_out[0].rdy
          s.recv_const.rdy @= s.recv_all_val & s.send_out[0].rdy
          s.recv_opt.rdy @= s.recv_all_val & s.send_out[0].rdy

        elif s.recv_opt.msg.operation == OPT_INC:
          s.send_out[0].msg @= s.recv_in[s.in0_idx].msg + s.const_one
          s.recv_all_val @= s.recv_in[s.in0_idx].val
          s.send_out[0].val @= s.recv_all_val
          s.recv_in[s.in0_idx].rdy @= s.recv_all_val & s.send_out[0].rdy
          s.recv_opt.rdy @= s.recv_all_val & s.send_out[0].rdy

        elif s.recv_opt.msg.operation == OPT_SUB:
          s.send_out[0].msg @= s.recv_in[s.in0_idx].msg - s.recv_in[s.in1_idx].msg - s.carry_in_temp
          s.recv_all_val @= s.recv_in[s.in0_idx].val & s.recv_in[s.in1_idx].val
          s.send_out[0].val @= s.recv_all_val
          s.recv_in[s.in0_idx].rdy @= s.recv_all_val & s.send_out[0].rdy
          s.recv_in[s.in1_idx].rdy @= s.recv_all_val & s.send_out[0].rdy
          s.recv_opt.rdy @= s.recv_all_val & s.send_out[0].rdy

        elif s.recv_opt.msg.operation == OPT_SUB_CONST:
          s.send_out[0].msg @= s.recv_in[s.in0_idx].msg - s.recv_const.msg - s.carry_in_temp
          s.recv_const.rdy @= s.send_out[0].rdy
          s.recv_all_val @= s.recv_in[s.in0_idx].val & s.recv_const.val
          s.send_out[0].val @= s.recv_all_val
          s.recv_in[s.in0_idx].rdy @= s.recv_all_val & s.send_out[0].rdy
          s.recv_const.rdy @= s.recv_all_val & s.send_out[0].rdy
          s.recv_opt.rdy @= s.recv_all_val & s.send_out[0].rdy

        elif s.recv_opt.msg.operation == OPT_PAS:
          s.send_out[0].msg @= s.recv_in[s.in0_idx].msg
          s.recv_all_val @= s.recv_in[s.in0_idx].val
          s.send_out[0].val @= s.recv_all_val
          s.recv_in[s.in0_idx].rdy @= s.recv_all_val & s.send_out[0].rdy
          s.recv_opt.rdy @= s.recv_all_val & s.send_out[0].rdy

        else:
          for j in range(num_outports):
            s.send_out[j].val @= b1(0)
          s.recv_opt.rdy @= 0
          s.recv_in[s.in0_idx].rdy @= 0
          s.recv_in[s.in1_idx].rdy @= 0

      s.carry_out @= s.send_out[0].msg[bw:bw+1]


  def line_trace( s ):
    opt_str = " #"
    if s.recv_opt.val:
      opt_str = OPT_SYMBOL_DICT[s.recv_opt.msg.operation]
    out_str = ",".join([str(x.msg) for x in s.send_out])
    recv_str = ",".join([str(x.msg) for x in s.recv_in])
    return f'[recv: {recv_str}] {opt_str} (const_reg: {s.recv_const.msg}) ] = [out: {out_str}] (s.recv_opt.rdy: {s.recv_opt.rdy}, {OPT_SYMBOL_DICT[s.recv_opt.msg.operation]}, recv_opt.val: {s.recv_opt.val}, send[0].val: {s.send_out[0].val}) '

