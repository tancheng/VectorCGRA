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
from ...lib.basic.val_rdy.queues import NormalQueueRTL

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
    # CPU should preload the unique ctrl mem address of the DFG's first PHI_CONST
    # through the port 'init_phi_addr' to the register 'init_phi_addr_reg'.
    # Then compare with the read address of ctrl mem at each cycle to make sure
    # progress is only recorded when executing the first PHI_CONST during PAUSING status.
    s.init_phi_addr = InPort(CtrlAddrType)
    s.ctrl_mem_rd_addr = InPort(CtrlAddrType)
    # When s.overwrite_fu_outport.val is high, FU's outport should be replaced with s.overwrite_fu_outport.msg
    # During the PAUSING status, FU's output when executing PHI_CONST operation
    # should always be DataType(0,0), so as to avoid initiating new iteration.
    # During the RESUMING status, FU's output when executing PHI_CONST operation for the first time
    # should be replaced with the recorded progress, so as to resume the progress.
    s.overwrite_fu_outport = SendIfcRTL(DataType)
   
    # Component
    s.progress_reg = Wire(DataType)
    s.status_reg = Wire(StatusType)
    s.init_phi_addr_reg = Wire(CtrlAddrType)
    s.progress_is_null = Wire(b1)
    s.is_pausing = Wire(b1)
    s.is_resuming = Wire(b1)
    s.is_executing_phi = Wire(b1)
    # s.recv_pkt_queue in CtrlMemDynamicRTL.py introduces 1 clock cycle delay to commands,
    # therefore we also add a queue for input recv_cmd to make timing right.
    s.recv_cmd_queue = NormalQueueRTL(CmdType)

    @update
    def update_queue():
      s.recv_cmd_queue.recv.val @= s.recv_cmd_vld
      s.recv_cmd_queue.recv.msg @= s.recv_cmd
      s.recv_cmd_queue.send.rdy @= 1

    @update
    def update_msg():
      # Update condition.
      s.progress_is_null @= (s.progress_reg == DataType(0, 0))
      s.is_pausing @= (s.status_reg == STATUS_PAUSING)
      s.is_resuming @= (s.status_reg == STATUS_RESUMING)
      s.is_executing_phi @= ((s.recv_opt == OPT_PHI_CONST) and (s.init_phi_addr_reg == s.ctrl_mem_rd_addr))

      # The output of PHI_CONST (first node in DFG) during the PAUSING status should always 
      # have DataType(0, 0), as it will be broadcasted to all other operations in this iteration 
      # via the dataflow, thereby stop initiating new iterations. 
      # PHI_CONST's output of the first time execution during the RESUMING
      # status should be replaced with the value of progress_reg to resume the progress.
      if (s.is_pausing & s.is_executing_phi):
        s.overwrite_fu_outport.val @= 1
        s.overwrite_fu_outport.msg @= DataType(0, 0)
      elif (~s.progress_is_null & s.is_resuming & s.is_executing_phi):
        s.overwrite_fu_outport.val @= 1
        s.overwrite_fu_outport.msg @= s.progress_reg
      else:
        s.overwrite_fu_outport.val @= 0
        s.overwrite_fu_outport.msg @= DataType(-1, 0)

    @update_ff
    def update_regs():
      # Updates the status register.
      if (s.recv_cmd_queue.send.val & (s.recv_cmd_queue.send.msg == CMD_PAUSE)):
        s.status_reg <<= STATUS_PAUSING
      elif (s.recv_cmd_queue.send.val & (s.recv_cmd_queue.send.msg == CMD_RESUME)):
        s.status_reg <<= STATUS_RESUMING
      elif (s.recv_cmd_queue.send.val & (s.recv_cmd_queue.send.msg == CMD_LAUNCH)):
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

      # Records the PHI_CONST's unqiue ctrl mem address to the register.
      if (s.recv_cmd_queue.send.val & (s.recv_cmd_queue.send.msg == CMD_RECORD_INIT_PHI_ADDR)):
        s.init_phi_addr_reg <<= s.init_phi_addr
      else:
        s.init_phi_addr_reg <<= s.init_phi_addr_reg

  def line_trace(s):
    recv_cmd_str = f'|| recv_cmd_queue.send.val: {s.recv_cmd_queue.send.val} | recv_cmd_queue.send: {s.recv_cmd_queue.send} '
    recv_opt_str = f'|| recv_opt: {s.recv_opt} '
    progress_in_str = f'|| progress_in: {s.progress_in} '
    overwrite_fu_outport_str = f'|| overwrite_fu_outport: {s.overwrite_fu_outport} '
    init_phi_addr_str = f'|| init_phi_addr: {s.init_phi_addr} '
    ctrl_mem_rd_addr_str = f'|| ctrl_mem_rd_addr: {s.ctrl_mem_rd_addr} '
    register_content_str = f'|| progress_reg: {s.progress_reg} | status_reg: {s.status_reg}i | init_phi_addr_reg: {s.init_phi_addr_reg} '
    condition_str = f'|| condition: progress_is_null:{s.progress_is_null}, is_pausing:{s.is_pausing}, is_executing_phi:{s.is_executing_phi} '
    return recv_cmd_str + recv_opt_str + progress_in_str + overwrite_fu_outport_str + init_phi_addr_str + ctrl_mem_rd_addr_str + register_content_str + condition_str
