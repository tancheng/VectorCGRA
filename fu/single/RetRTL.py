"""
==========================================================================
RetRTL.py
==========================================================================
Functional unit Ret as a CGRA FU.
 - It requires one input, which is usually granted with predicate.
   - Only when the predicate is true, the value will be sent back to CPU.
 - It returns the value back to the CPU via CMD_COMPLETE command.
   - By notifiying the ctrl mem controller to initiate the command.
   - The returned value is embedded in the CMD_COMPLETE package.

Author : Cheng Tan
  Date : Aug 29, 2025
"""

from pymtl3 import *
from pymtl3.stdlib.primitive import Reg
from ..basic.Fu import Fu
from ...lib.cmd_type import *
from ...lib.messages import *
from ...lib.opt_type import *

class RetRTL(Fu):
  def construct(s, DataType, CtrlType, num_inports,
                num_outports, data_mem_size, ctrl_mem_size = 4,
                vector_factor_power = 0, data_bitwidth = 32):

    super(RetRTL, s).construct(DataType, CtrlType,
                               num_inports, num_outports,
                               data_mem_size, ctrl_mem_size,
                               1, vector_factor_power,
                               data_bitwidth = data_bitwidth)

    # Constants.
    kDelayCycles = 100
    CounterType = mk_bits(clog2(kDelayCycles + 1))
    FuInType = mk_bits(clog2(num_inports + 1))
    idx_nbits = clog2(num_inports)

    # Components.
    s.in0 = Wire(FuInType)
    s.in0_idx = Wire(idx_nbits)
    s.recv_all_val = Wire(1)
    s.already_done = Wire(1)
    s.delay_counter = Wire(CounterType)
    s.is_counting = Wire(1)

    # Connections.
    s.in0_idx //= s.in0[0:idx_nbits]

    @update
    def comb_logic():

      s.recv_all_val @= 0
      # For pick input register.
      s.in0 @= 0
      for i in range(num_inports):
        s.recv_in[i].rdy @= b1(0)

      for j in range(num_outports):
        s.send_out[j].val @= 0
        s.send_out[j].msg @= DataType()

      s.send_to_ctrl_mem.val @= 0
      s.send_to_ctrl_mem.msg @= s.CgraPayloadType(0, 0, 0, 0, 0)
      s.recv_from_ctrl_mem.rdy @= 0

      s.recv_const.rdy @= 0
      s.recv_opt.rdy @= 0

      if s.recv_opt.val:
        if s.recv_opt.msg.fu_in[0] != FuInType(0):
          s.in0 @= s.recv_opt.msg.fu_in[0] - FuInType(1)

      if s.recv_opt.val:
        if s.recv_opt.msg.operation == OPT_RET:
          s.recv_all_val @= s.recv_in[s.in0_idx].val
          # Value to be returned is usually granted with a predicate:
          # https://github.com/coredac/dataflow/blob/b9ffc097d67429017323e3d50d3984655f756b91/test/neura/ctrl/branch_for.mlir#L150.
          if s.already_done:
            s.recv_in[s.in0_idx].rdy @= s.recv_all_val
            s.recv_opt.rdy @= s.recv_all_val
          elif s.recv_in[s.in0_idx].msg.predicate:
            # Only when the predicate is true, the value will be sent back to CPU.
            s.send_to_ctrl_mem.val @= s.recv_all_val & s.reached_vector_factor
            # s.send_to_ctrl_mem.msg @= s.recv_in[s.in0_idx].msg
            s.send_to_ctrl_mem.msg @= s.CgraPayloadType(CMD_COMPLETE, s.recv_in[s.in0_idx].msg, 0, s.recv_opt.msg, 0)
            s.recv_in[s.in0_idx].rdy @= s.recv_all_val & s.reached_vector_factor & s.send_to_ctrl_mem.rdy
            s.recv_opt.rdy @= s.recv_all_val & s.reached_vector_factor & s.send_to_ctrl_mem.rdy
          else:
            s.recv_in[s.in0_idx].rdy @= s.recv_all_val & s.reached_vector_factor
            s.recv_opt.rdy @= s.recv_all_val & s.reached_vector_factor
        elif s.recv_opt.msg.operation == OPT_RET_VOID:
          s.recv_all_val @= s.recv_in[s.in0_idx].val
          if s.already_done:
            s.recv_in[s.in0_idx].rdy @= s.recv_all_val
            s.recv_opt.rdy @= s.recv_all_val
          elif s.is_counting:
            # When counting, checks if we have reached the delay cycles.
            if s.delay_counter == CounterType(kDelayCycles):
              s.send_to_ctrl_mem.val @= s.recv_all_val & s.reached_vector_factor
              # Returns the 0 signal to the controller.
              s.send_to_ctrl_mem.msg @= s.CgraPayloadType(CMD_COMPLETE, 0, 0, s.recv_opt.msg, 0)
              s.recv_in[s.in0_idx].rdy @= s.recv_all_val & s.reached_vector_factor & s.send_to_ctrl_mem.rdy
              s.recv_opt.rdy @= s.recv_all_val & s.reached_vector_factor & s.send_to_ctrl_mem.rdy
          elif s.recv_in[s.in0_idx].msg.predicate:
            # Starts counting when predicate is true
            s.recv_in[s.in0_idx].rdy @= s.recv_all_val & s.reached_vector_factor
            s.recv_opt.rdy @= s.recv_all_val & s.reached_vector_factor
          else:
            # Predicate is false, just consumes the input
            s.recv_in[s.in0_idx].rdy @= s.recv_all_val & s.reached_vector_factor
            s.recv_opt.rdy @= s.recv_all_val & s.reached_vector_factor



    @update_ff
    def update_already_done():
      if s.reset | s.clear:
        s.already_done <<= 0
      else:
        if s.recv_opt.val & \
           (s.recv_opt.msg.operation == OPT_RET) & \
            ~s.already_done & \
            s.recv_all_val & \
            s.send_to_ctrl_mem.val & \
            s.send_to_ctrl_mem.rdy:
          s.already_done <<= 1
        elif s.recv_opt.val & \
             (s.recv_opt.msg.operation == OPT_RET_VOID) & \
              ~s.already_done & \
              s.is_counting & \
              (s.delay_counter == CounterType(kDelayCycles)) & \
              s.send_to_ctrl_mem.val & \
              s.send_to_ctrl_mem.rdy:
          s.already_done <<= 1
        else:
          s.already_done <<= s.already_done

    @update_ff
    def update_delay_counter():
      if s.reset | s.clear:
        s.delay_counter <<= CounterType(0)
        s.is_counting <<= b1(0)
      else:
        if s.recv_opt.val & \
           (s.recv_opt.msg.operation == OPT_RET_VOID) & \
            ~s.already_done & \
            ~s.is_counting & \
            s.recv_all_val & \
            s.recv_in[s.in0_idx].msg.predicate & \
            s.recv_in[s.in0_idx].rdy & \
            s.reached_vector_factor:
          # Starts counting.
          s.delay_counter <<= CounterType(1)
          s.is_counting <<= b1(1)
        elif s.is_counting:
          if s.delay_counter == CounterType(kDelayCycles):
            # Stops counting when CMD_COMPLETE is sent.
            if s.send_to_ctrl_mem.val & s.send_to_ctrl_mem.rdy:
              s.delay_counter <<= CounterType(0)
              s.is_counting <<= b1(0)
            else:
              s.delay_counter <<= s.delay_counter
              s.is_counting <<= s.is_counting
          else:
            # Continues counting.
            s.delay_counter <<= s.delay_counter + CounterType(1)
            s.is_counting <<= s.is_counting
        else:
          s.delay_counter <<= s.delay_counter
          s.is_counting <<= s.is_counting

  def line_trace(s):
    opt_str = " #"
    if s.recv_opt.val:
      opt_str = OPT_SYMBOL_DICT[s.recv_opt.msg.operation]
    out_str = str(s.send_to_ctrl_mem.msg)
    recv_str = ",".join([str(x.msg) for x in s.recv_in])
    return f'[recv: {recv_str}] {opt_str} (const_reg: {s.recv_const.msg}) ] = [out_to_ctrl_mem: {out_str}] (s.recv_opt.rdy: {s.recv_opt.rdy}, {OPT_SYMBOL_DICT[s.recv_opt.msg.operation]}, send_to_ctrl_mem.val: {s.send_to_ctrl_mem.val}) '

