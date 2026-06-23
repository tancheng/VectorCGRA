"""
==========================================================================
ExclusiveDivRTL.py
==========================================================================
Exclusive integer divisor for CGRA tile.

Author : Jiajun Qin
  Date : May 2, 2025
"""

from pymtl3 import *
from ..basic.Fu import Fu
from ...lib.opt_type import *

class ExclusiveDivRTL(Fu):

  def construct(s, CtrlPktType, num_inports, num_outports, latency = 4, vector_factor_power = 0):

    super(ExclusiveDivRTL, s).construct(CtrlPktType, num_inports, num_outports, latency, vector_factor_power)

    num_entries = 2
    num_cycles = latency

    FuInType = mk_bits(clog2(num_inports + 1))
    CountType = mk_bits(clog2(num_entries + 1))

    s.in0 = Wire(FuInType)
    s.in1 = Wire(FuInType)

    # TODO: how to parameterize the bit widths
    s.div = Div(WIDTH = 32, CYCLE = num_cycles)

    idx_nbits = clog2(num_inports)
    s.in0_idx = Wire(idx_nbits)
    s.in1_idx = Wire(idx_nbits)

    s.in0_idx //= s.in0[0:idx_nbits]
    s.in1_idx //= s.in1[0:idx_nbits]

    s.recv_all_val = Wire(1)
    s.accept_input = Wire(1)
    s.launch_msg = Wire(s.DataType)
    s.pipe_valid = [Wire(1) for _ in range(latency)]
    s.next_pipe_valid = [Wire(1) for _ in range(latency)]
    s.pipe_msg = [Wire(s.DataType) for _ in range(latency)]
    s.next_pipe_msg = [Wire(s.DataType) for _ in range(latency)]
    s.stage_can_advance = [Wire(1) for _ in range(latency)]

    @update_ff
    def comb_ff():
      for i in range(latency):
        if s.reset | s.clear:
          s.pipe_valid[i] <<= 0
          s.pipe_msg[i] <<= s.DataType()
        else:
          s.pipe_valid[i] <<= s.next_pipe_valid[i]
          s.pipe_msg[i] <<= s.next_pipe_msg[i]

    @update
    def comb_logic():

      s.recv_all_val @= 0
      s.accept_input @= 0
      # For pick input register
      s.in0 @= 0
      s.in1 @= 0
      for i in range(num_inports):
        s.recv_in[i].rdy @= b1(0)
      for i in range(num_outports):
        s.send_out[i].val @= 0
        s.send_out[i].msg @= s.DataType()
      s.launch_msg @= s.DataType()

      s.recv_const.rdy @= 0
      s.recv_opt.rdy @= 0

      s.send_to_ctrl_mem.val @= 0
      s.send_to_ctrl_mem.msg @= s.CgraPayloadType(0, 0, 0, 0, 0)
      s.recv_from_ctrl_mem.rdy @= 0
      for i in range(latency):
        s.next_pipe_valid[i] @= s.pipe_valid[i]
        s.next_pipe_msg[i] @= s.pipe_msg[i]
        s.stage_can_advance[i] @= 0

      if s.recv_opt.val:
        if s.recv_opt.msg.fu_in[0] != 0:
          s.in0 @= zext(s.recv_opt.msg.fu_in[0] - 1, FuInType)
        if s.recv_opt.msg.fu_in[1] != 0:
          s.in1 @= zext(s.recv_opt.msg.fu_in[1] - 1, FuInType)

      s.send_out[0].val @= s.pipe_valid[latency - 1]
      s.send_out[0].msg @= s.pipe_msg[latency - 1]

      s.stage_can_advance[latency - 1] @= (~s.pipe_valid[latency - 1]) | s.send_out[0].rdy
      for i in range(latency - 2, -1, -1):
        s.stage_can_advance[i] @= (~s.pipe_valid[i]) | s.stage_can_advance[i + 1]

      for i in range(latency - 1, 0, -1):
        if s.stage_can_advance[i]:
          s.next_pipe_valid[i] @= s.pipe_valid[i - 1]
          s.next_pipe_msg[i] @= s.pipe_msg[i - 1]

      if s.stage_can_advance[0]:
        s.next_pipe_valid[0] @= 0
        s.next_pipe_msg[0] @= s.DataType()

      if s.recv_opt.val:
        if (s.recv_opt.msg.operation == OPT_DIV) | \
           (s.recv_opt.msg.operation == OPT_REM) | \
           (s.recv_opt.msg.operation == OPT_DIV_CONST):
          s.div.dividend @= s.recv_in[s.in0_idx].msg.payload
          if s.recv_opt.msg.operation == OPT_DIV_CONST:
            s.div.divisor @= s.recv_const.msg.payload
            s.launch_msg.predicate @= s.recv_in[s.in0_idx].msg.predicate & \
                                      s.recv_const.msg.predicate & \
                                      s.reached_vector_factor
            s.recv_all_val @= s.recv_in[s.in0_idx].val & s.recv_const.val
            s.recv_const.rdy @= s.recv_all_val & s.stage_can_advance[0]
          else:
            s.div.divisor @= s.recv_in[s.in1_idx].msg.payload
            s.launch_msg.predicate @= s.recv_in[s.in0_idx].msg.predicate & \
                                      s.recv_in[s.in1_idx].msg.predicate & \
                                      s.reached_vector_factor
            s.recv_all_val @= s.recv_in[s.in0_idx].val & s.recv_in[s.in1_idx].val
            s.recv_in[s.in1_idx].rdy @= s.recv_all_val & s.stage_can_advance[0]
          if (s.recv_opt.msg.operation == OPT_DIV) | \
             (s.recv_opt.msg.operation == OPT_DIV_CONST):
            s.launch_msg.payload @= s.div.quotient
          else:
            s.launch_msg.payload @= s.div.remainder
          s.accept_input @= s.recv_all_val & s.stage_can_advance[0]
          s.recv_in[s.in0_idx].rdy @= s.accept_input
          s.recv_opt.rdy @= s.accept_input
          if s.accept_input:
            s.next_pipe_valid[0] @= 1
            s.next_pipe_msg[0] @= s.launch_msg
        else:
          for j in range(num_outports):
            s.send_out[j].val @= b1(0)
          s.recv_opt.rdy @= 0
          s.recv_in[s.in0_idx].rdy @= 0
          s.recv_in[s.in1_idx].rdy @= 0

class Div( Component ):

  # Constructor
  def construct( s, WIDTH = 32, CYCLE = 8 ):

    # Interface
    s.dividend              = InPort ( WIDTH )
    s.divisor              = InPort ( WIDTH )

    s.quotient            = OutPort ( WIDTH )
    s.remainder            = OutPort ( WIDTH )

    @update
    def comb_div():
      if s.divisor == 0:
        s.quotient @= 0
        s.remainder @= 0
      else:
        s.quotient @= s.dividend // s.divisor
        s.remainder @= s.dividend % s.divisor
