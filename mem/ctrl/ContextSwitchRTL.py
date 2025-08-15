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
from ...lib.status_type import *
from ...lib.util.common import *

class ContextSwitchRTL(Component):

  def construct(s, data_nbits):

    # Constant
    CmdType = mk_bits(clog2(NUM_CMDS))
    StatusType = mk_bits(clog2(NUM_STATUS))
    DataType = mk_bits(data_nbits)
    OptType = mk_bits(clog2(NUM_OPTS))

    # Interface
    s.recv_cmd = InPort(CmdType)
    s.recv_cmd_vld = InPort(b1)
    s.recv_opt = InPort(OptType)
    s.progress_in = InPort(DataType)
    s.progress_in_vld = InPort(b1)
    s.progress_out = OutPort(DataType)
    s.progress_out_vld = OutPort(b1)
   
    # Component
    s.progress_reg = Wire(DataType)
    s.status_reg = Wire(StatusType)
    s.progress_is_null = Wire(b1)
    s.is_pausing = Wire(b1)
    s.is_resuming = Wire(b1)
    s.is_executing_phi = Wire(b1)

    @update
    def update_msg():
      # Update condition.
      s.progress_is_null @= (s.progress_reg == DataType(0))
      s.is_pausing @= (s.status_reg == STATUS_PAUSING)
      s.is_resuming @= (s.status_reg == STATUS_RESUMING)
      s.is_executing_phi @= (s.recv_opt == OPT_PHI_CONST)

      # Updates progress_out with the recorded progress.
      if (~s.progress_is_null & s.is_resuming & s.is_executing_phi):
        s.progress_out_vld @= 1
        s.progress_out @= s.progress_reg
      else:
        s.progress_out_vld @= 0
        s.progress_out @= DataType(0)

    @update_ff
    def update_regs():
      # Updates the status register.
      if (s.recv_cmd_vld & (s.recv_cmd == CMD_PAUSE)):
        s.status_reg <<= STATUS_PAUSING
      elif (s.recv_cmd_vld & (s.recv_cmd == CMD_RESUME)):
        s.status_reg <<= STATUS_RESUMING
      elif (s.recv_cmd_vld & (s.recv_cmd == CMD_LAUNCH)):
        s.status_reg <<= STATUS_RUNNING
      else:
        s.status_reg <<= s.status_reg

      # Updates the progress register.
      if (s.progress_is_null & s.is_pausing & s.is_executing_phi & s.progress_in_vld):
        # Records the progress.
        s.progress_reg <<= s.progress_in
      elif (~s.progress_is_null & s.is_resuming & s.is_executing_phi):
        # Clears the progress at next clock cycle.
        s.progress_reg <<= DataType(0)
      else:
        # Keeps the progress.
        s.progress_reg <<= s.progress_reg

  def line_trace(s):
    recv_cmd_str = f'|| recv_cmd_vld: {s.recv_cmd_vld} | recv_cmd: {s.recv_cmd} '
    recv_opt_str = f'|| recv_opt: {s.recv_opt} '
    progress_in_str = f'|| progress_in_vld: {s.progress_in_vld} | progress_in: {s.progress_in} '
    progress_out_str = f'|| progress_out_vld: {s.progress_out_vld} | progress_out: {s.progress_out} '
    register_content_str = f'|| progress_reg: {s.progress_reg} | status_reg: {s.status_reg} '
    condition_str = f'|| condition: {s.progress_is_null}{s.is_pausing}{s.is_executing_phi} '
    return recv_cmd_str + recv_opt_str + progress_in_str + progress_out_str + register_content_str + condition_str
