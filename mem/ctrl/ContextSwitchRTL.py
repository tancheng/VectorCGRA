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
from ...lib.messages import *
from ...lib.opt_type import *
from ...lib.status_type import *
from ...lib.util.common import *

class ContextSwitchRTL(Component):

  def construct(s, data_nbits, ctrl_addr_nbits):

    # Constant
    CmdType = mk_bits(clog2(NUM_CMDS))
    StatusType = mk_bits(clog2(NUM_STATUS))
    DataType = mk_data(data_nbits)
    CtrlAddrType = mk_bits(ctrl_addr_nbits)
    OptType = mk_bits(clog2(NUM_OPTS))

    # Interface
    s.recv_cmd = InPort(CmdType)
    s.recv_cmd_vld = InPort(b1)
    # We don't need recv_opt.predicate as progress_in.predicate is enough 
    # to tell whether the opt is valid.
    s.recv_opt = InPort(OptType)
    s.progress_in = InPort(DataType)
    s.progress_out = OutPort(DataType)
    # s.overwrite_fu_output_predicate is used for resetting FU's output predicate to 0.
    # During the PAUSING status, FU's output when executing PHI_CONST operation
    # should always have predicate=0, so as to avoid initiating new iteration.
    s.overwrite_fu_output_predicate = OutPort(b1)
    # CPU should preload the unique ctrl mem address of the DFG's first PHI_CONST
    # through the port 'init_phi_addr' to the register 'init_phi_addr_reg'.
    # Then compare with the read address of ctrl mem at each cycle to make sure
    # progress is only recorded when executing the first PHI_CONST during PAUSING status.
    s.init_phi_addr = InPort(CtrlAddrType)
    s.ctrl_mem_rd_addr = InPort(CtrlAddrType)
   
    # Component
    s.progress_reg = Wire(DataType)
    s.status_reg = Wire(StatusType)
    s.init_phi_addr_reg = Wire(CtrlAddrType)
    s.progress_is_null = Wire(b1)
    s.is_pausing = Wire(b1)
    s.is_resuming = Wire(b1)
    s.is_executing_phi = Wire(b1)

    @update
    def update_msg():
      # Update condition.
      s.progress_is_null @= (s.progress_reg == DataType(0, 0))
      s.is_pausing @= (s.status_reg == STATUS_PAUSING)
      s.is_resuming @= (s.status_reg == STATUS_RESUMING)
      s.is_executing_phi @= ((s.recv_opt == OPT_PHI_CONST) and (s.init_phi_addr_reg == s.ctrl_mem_rd_addr))

      # Updates progress_out with the recorded progress.
      if (~s.progress_is_null & s.is_resuming & s.is_executing_phi):
        s.progress_out @= s.progress_reg
      else:
        s.progress_out @= DataType(0, 0)

      # The output of PHI_CONST (first node in DFG) during the PAUSING
      # status should always have predicate=0, as it will be broadcasted 
      # to all other operations in this iteration via the dataflow. 
      if (s.is_pausing & s.is_executing_phi):
        s.overwrite_fu_output_predicate @= 1
      else:
        s.overwrite_fu_output_predicate @= 0

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
      if (s.progress_is_null & s.is_pausing & s.is_executing_phi & s.progress_in.predicate):
        # Records the progress.
        s.progress_reg <<= s.progress_in
      elif (~s.progress_is_null & s.is_resuming & s.is_executing_phi):
        # Clears the progress at next clock cycle.
        s.progress_reg <<= DataType(0, 0)
      else:
        # Keeps the progress.
        s.progress_reg <<= s.progress_reg

      # Loads the PHI_CONST's unqiue ctrl mem address to the register.
      if (s.recv_cmd_vld & (s.recv_cmd == CMD_TERMINATE)):
        s.init_phi_addr_reg <<= s.init_phi_addr
      else:
        s.init_phi_addr_reg <<= s.init_phi_addr_reg

  def line_trace(s):
    recv_cmd_str = f'|| recv_cmd_vld: {s.recv_cmd_vld} | recv_cmd: {s.recv_cmd} '
    recv_opt_str = f'|| recv_opt: {s.recv_opt} '
    progress_in_str = f'|| progress_in: {s.progress_in} '
    progress_out_str = f'|| progress_out: {s.progress_out} '
    init_phi_addr_str = f'|| init_phi_addr: {s.init_phi_addr} '
    ctrl_mem_rd_addr_str = f'|| ctrl_mem_rd_addr: {s.ctrl_mem_rd_addr} '
    overwrite_fu_output_predicate_str = f'|| overwrite_fu_output_predicate: {s.overwrite_fu_output_predicate} '
    register_content_str = f'|| progress_reg: {s.progress_reg} | status_reg: {s.status_reg}i | init_phi_addr_reg: {s.init_phi_addr_reg} '
    condition_str = f'|| condition: {s.progress_is_null}{s.is_pausing}{s.is_executing_phi} '
    return recv_cmd_str + recv_opt_str + progress_in_str + progress_out_str + init_phi_addr_str + ctrl_mem_rd_addr_str + overwrite_fu_output_predicate_str + register_content_str + condition_str
