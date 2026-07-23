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
  
  def construct(s, CtrlPktType, num_inports, num_outports, vector_factor_power = 0):

    super(RetRTL, s).construct(CtrlPktType, num_inports, num_outports, 1, vector_factor_power)
    
    # Constants.
    FuInType = mk_bits(clog2(num_inports + 1))
    idx_nbits = clog2(num_inports)
    ctrl_mem_size = 2 ** s.CtrlAddrType.nbits

    # Components.
    s.in0 = Wire(FuInType)
    s.in0_idx = Wire(idx_nbits)
    s.recv_all_val = Wire(1)
    # Per-ctrl already_done to support multiple returns on the same tile.
    s.already_done = [Wire(1) for _ in range(ctrl_mem_size)]
    s.last_ret_data = [Wire(s.DataType) for _ in range(ctrl_mem_size)]
    s.last_ret_valid = [Wire(1) for _ in range(ctrl_mem_size)]

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
        s.send_out[j].msg @= s.DataType()

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
          if s.already_done[s.ctrl_addr_inport]:
            s.recv_in[s.in0_idx].rdy @= s.recv_all_val
            s.recv_opt.rdy @= s.recv_all_val
          elif s.recv_opt.msg.is_last_ctrl & \
               (s.recv_in[s.in0_idx].msg.predicate | s.last_ret_valid[s.ctrl_addr_inport]):
            # Emit the last predicated return value at the terminal control step.
            # Some schedules have invalid tail RETURN instances; those carry
            # predicate=0, so the FU keeps the latest valid value seen earlier.
            s.send_to_ctrl_mem.val @= s.recv_all_val & s.reached_vector_factor
            if s.recv_in[s.in0_idx].msg.predicate:
              s.send_to_ctrl_mem.msg @= \
                  s.CgraPayloadType(CMD_COMPLETE, s.recv_in[s.in0_idx].msg, 0, s.recv_opt.msg, 0)
            else:
              s.send_to_ctrl_mem.msg @= \
                  s.CgraPayloadType(CMD_COMPLETE, s.last_ret_data[s.ctrl_addr_inport], 0, s.recv_opt.msg, 0)
            s.recv_in[s.in0_idx].rdy @= s.recv_all_val & s.reached_vector_factor & s.send_to_ctrl_mem.rdy
            s.recv_opt.rdy @= s.recv_all_val & s.reached_vector_factor & s.send_to_ctrl_mem.rdy
          else:
            # Non-final and predicated-off returns only consume the input.
            s.recv_in[s.in0_idx].rdy @= s.recv_all_val & s.reached_vector_factor
            s.recv_opt.rdy @= s.recv_all_val & s.reached_vector_factor
        elif s.recv_opt.msg.operation == OPT_RET_VOID:
          s.recv_all_val @= s.recv_in[s.in0_idx].val
          if s.already_done[s.ctrl_addr_inport]:
            s.recv_in[s.in0_idx].rdy @= s.recv_all_val
            s.recv_opt.rdy @= s.recv_all_val
          elif s.recv_opt.msg.is_last_ctrl & \
               (s.recv_in[s.in0_idx].msg.predicate | s.last_ret_valid[s.ctrl_addr_inport]):
            # RET_VOID emits completion at the terminal control step if any
            # valid return predicate has been observed.
            s.send_to_ctrl_mem.val @= s.recv_all_val & s.reached_vector_factor
            s.send_to_ctrl_mem.msg @= s.CgraPayloadType(CMD_COMPLETE, 0, 0, s.recv_opt.msg, 0)
            s.recv_in[s.in0_idx].rdy @= s.recv_all_val & s.reached_vector_factor & s.send_to_ctrl_mem.rdy
            s.recv_opt.rdy @= s.recv_all_val & s.reached_vector_factor & s.send_to_ctrl_mem.rdy
          else:
            # Non-final and predicated-off returns only consume the input.
            s.recv_in[s.in0_idx].rdy @= s.recv_all_val & s.reached_vector_factor
            s.recv_opt.rdy @= s.recv_all_val & s.reached_vector_factor



    @update_ff
    def update_already_done():
      if s.reset | s.clear:
        for i in range(ctrl_mem_size):
          s.already_done[i] <<= 0
          s.last_ret_data[i] <<= s.DataType()
          s.last_ret_valid[i] <<= 0
      else:
        for i in range(ctrl_mem_size):
          s.last_ret_data[i] <<= s.last_ret_data[i]
          s.last_ret_valid[i] <<= s.last_ret_valid[i]
        if s.recv_opt.val & \
           ((s.recv_opt.msg.operation == OPT_RET) | (s.recv_opt.msg.operation == OPT_RET_VOID)) & \
           s.recv_all_val & s.reached_vector_factor & \
           s.recv_in[s.in0_idx].msg.predicate:
          for i in range(ctrl_mem_size):
            if i == s.ctrl_addr_inport:
              s.last_ret_data[i] <<= s.recv_in[s.in0_idx].msg
              s.last_ret_valid[i] <<= 1
        if s.recv_opt.val & \
           ((s.recv_opt.msg.operation == OPT_RET) | (s.recv_opt.msg.operation == OPT_RET_VOID)) & \
            ~s.already_done[s.ctrl_addr_inport] & \
            s.recv_all_val & \
            (s.recv_in[s.in0_idx].msg.predicate | s.last_ret_valid[s.ctrl_addr_inport]) & \
            s.recv_opt.msg.is_last_ctrl & \
            s.send_to_ctrl_mem.val & \
            s.send_to_ctrl_mem.rdy:
          for i in range(ctrl_mem_size):
            if i == s.ctrl_addr_inport:
              s.already_done[i] <<= 1
            else:
              s.already_done[i] <<= s.already_done[i]
        else:
          for i in range(ctrl_mem_size):
            s.already_done[i] <<= s.already_done[i]

  def line_trace(s):
    opt_str = " #"
    if s.recv_opt.val:
      opt_str = OPT_SYMBOL_DICT[s.recv_opt.msg.operation]
    out_str = str(s.send_to_ctrl_mem.msg)
    recv_str = ",".join([str(x.msg) for x in s.recv_in])
    return f'[recv: {recv_str}] {opt_str} (const_reg: {s.recv_const.msg}) ] = [out_to_ctrl_mem: {out_str}] (s.recv_opt.rdy: {s.recv_opt.rdy}, {OPT_SYMBOL_DICT[s.recv_opt.msg.operation]}, send_to_ctrl_mem.val: {s.send_to_ctrl_mem.val}) '

