"""
==========================================================================
ContextSwitchRTL.py
==========================================================================
Records/resumes progress (itertion) for functional unit (FU).

Author : Yufei Yang
  Date : Aug 11, 2025
"""
from pymtl3.stdlib.primitive import *
from ...lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ...lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ...lib.cmd_type import *
from ...lib.opt_type import *
from ...lib.util.common import *

class ContextSwitchRTL(Component):

  def construct(s, CgraPayloadType, DataType, CtrlType, num_status = 3):

    # Constant
    StatusType = mk_bits(clog2(num_status))

    # Interface
    s.recv_cmd = RecvIfcRTL(CgraPayloadType)
    s.recv_opt = RecvIfcRTL(CtrlType)
    s.progress_in = RecvIfcRTL(DataType)
    s.progress_out = SendIfcRTL(DataType)
   
    # Component
    s.progress_reg = Reg(DataType)
    s.status_reg = Reg(StatusType)
    #s.condition = Wire(Bits3)
    # How to create a wire that can be bit sliced?
    s.condition_2 = Wire(b1)
    s.condition_1 = Wire(b1)
    s.condition_0 = Wire(b1)

    @update
    def update_msg():
      # Update condition.
      # condition = 3'b111 (3'd7): Records the progress.
      # condition = 3'b001 (3'd1): Resumes the progress.
      s.condition_2 @= (s.progress_reg.out == DataType(0))
      s.condition_1 @= (s.status_reg.out == StatusType(3))
      s.condition_0 @= s.recv_opt.val & (s.recv_opt.msg.operation == OPT_PHI_CONST)

      # Updates recv_opt.
      s.recv_opt.rdy @= 1

      # Updates recv_cmd
      s.recv_cmd.rdy @= 1

      # Updates the status register.
      if (s.recv_cmd.val & (s.recv_cmd.msg.cmd == CMD_PAUSE)):
        # PAUSING: 2'b11
        s.status_reg.in_ @= StatusType(3)
      elif (s.recv_cmd.val & (s.recv_cmd.msg.cmd == CMD_RESUME)):
        # RESUMING: 2'b10
        s.status_reg.in_ @= StatusType(2)
      elif (s.recv_cmd.val & (s.recv_cmd.msg.cmd == CMD_LAUNCH)):
        # RUNNING: 2'b00
        s.status_reg.in_ @= StatusType(0)
      else:
        # Keeps unchanged.
        s.status_reg.in_ @= s.status_reg.out

      # Updates the progress register.
      s.progress_in.rdy @= 1
      if (s.condition_2 & s.condition_1 & s.condition_0 & s.progress_in.val):
        # Records the progress.
        s.progress_reg.in_ @= s.progress_in.msg
      elif (~s.condition_2 & ~s.condition_1 & s.condition_0 & s.progress_in.val & s.progress_out.rdy):
        # Resumes the progress.
        s.progress_reg.in_ @= DataType(0)
      else:
        # Keeps the progress.
        s.progress_reg.in_ @= s.progress_reg.out

      # Updates progress_out
      if (~s.condition_2 & ~s.condition_1 & s.condition_0 & s.progress_in.val & s.progress_out.rdy):
        s.progress_out.val @= 1
        s.progress_out.msg @= s.progress_reg.out
      else:
        s.progress_out.val @= 1
        s.progress_out.msg @= DataType(0,0)

  def line_trace(s):
    recv_cmd_str = f'|| recv_cmd.val: {s.recv_cmd.val} | recv_cmd.msg.cmd: {s.recv_cmd.msg.cmd} | recv_cmd.rdy: {s.recv_cmd.rdy} '
    recv_opt_str = f'|| recv_opt.val: {s.recv_opt.val} | recv_opt.msg: {s.recv_opt.msg} | recv_opt.rdy: {s.recv_opt.rdy} '
    progress_in_str = f'|| progress_in.val: {s.progress_in.val} | progress_in.msg: {s.progress_in.msg} | progress_in.rdy: {s.progress_in.rdy} '
    progress_out_str = f'|| progress_out.val: {s.progress_out.val} | progress_out.msg: {s.progress_out.msg} | progress_out.rdy: {s.progress_out.rdy} '
    register_content_str = f'|| progress_reg: {s.progress_reg.out} | status_reg: {s.status_reg.out} '
    condition_str = f'|| condition: {s.condition_2}{s.condition_1}{s.condition_0} '
    return recv_cmd_str + recv_opt_str + progress_in_str + progress_out_str + register_content_str + condition_str
