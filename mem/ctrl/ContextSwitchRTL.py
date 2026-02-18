"""
==========================================================================
ContextSwitchRTL.py
==========================================================================
Records/resumes progress (itertion / accumulation) for functional unit (FU).

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
    # Inputs from recv_pkt.
    s.recv_cmd = InPort(CmdType)
    s.recv_cmd_vld = InPort(b1)
    s.phi_addr = InPort(CtrlAddrType)

    # Inputs from ctrl mem and FU.
    # We don't need recv_opt.predicate as progress_in.predicate is enough to tell whether the opt is valid.
    s.recv_opt = InPort(OptType)
    s.progress_in = InPort(DataType)
    s.progress_in_val = InPort(b1) 
    # The ctrl mem address of target PHI_CONST operation in the ctrl mem of current tile.
    s.ctrl_mem_rd_addr = InPort(CtrlAddrType)
    # When s.overwrite_fu_outport.val is high, FU's outport should be replaced with s.overwrite_fu_outport.msg.
    s.overwrite_fu_outport = SendIfcRTL(DataType)
   
    # Component
    s.progress_reg = Wire(DataType)
    s.status_reg = Wire(StatusType)
    s.phi_addr_reg = Wire(CtrlAddrType)
    s.progress_reg_is_null = Wire(b1)
    s.is_pausing = Wire(b1)
    s.is_preserving = Wire(b1)
    s.is_resuming = Wire(b1)
    s.is_executing_phi = Wire(b1)
    # s.recv_pkt_queue in CtrlMemDynamicRTL.py introduces 1 clock cycle delay to recv_pkt,
    # therefore we also add a queue for input recv_cmd and phi_addr within recv_pkt to synchronize.
    s.recv_cmd_queue = NormalQueueRTL(CmdType)
    s.recv_phi_addr_queue = NormalQueueRTL(CtrlAddrType)

    @update
    def update_queue():
      s.recv_cmd_queue.recv.val @= s.recv_cmd_vld
      s.recv_cmd_queue.recv.msg @= s.recv_cmd
      s.recv_cmd_queue.send.rdy @= 1
      s.recv_phi_addr_queue.recv.val @= s.recv_cmd_vld
      s.recv_phi_addr_queue.recv.msg @= s.phi_addr
      s.recv_phi_addr_queue.send.rdy @= 1

    @update
    def update_msg():
      # Update condition.
      s.progress_reg_is_null @= (s.progress_reg == DataType(0, 0))
      s.is_pausing @= (s.status_reg == STATUS_PAUSING)
      s.is_preserving @= (s.status_reg == STATUS_PRESERVING)
      s.is_resuming @= (s.status_reg == STATUS_RESUMING)
      s.is_executing_phi @= (((s.recv_opt == OPT_PHI_CONST) | (s.recv_opt == OPT_PHI_START)) & (s.phi_addr_reg == s.ctrl_mem_rd_addr))

      # Updates overwrite_fu_outport, there are 3 scenarios:
      # (1) During the PAUSING status, FU's output iteration should always be replaced with DataType(0,0) that
      # has predicate=0, so as to avoid initiating new iterations.
      # (2) During the PRESERVING status, only needs to record FU's output iteration/accumulation to progress_reg.
      # (3) During the RESUMING status, PHI_CONST will output the const value with predicate=1 for the first 
      # time execution, this output should be replaced with the value in progress_reg.
      if (s.is_pausing & s.is_executing_phi):
        s.overwrite_fu_outport.val @= 1
        s.overwrite_fu_outport.msg @= DataType(0, 0)
      elif (~s.progress_reg_is_null & s.is_resuming & s.is_executing_phi & \
              s.progress_in.predicate & s.progress_in_val):
        s.overwrite_fu_outport.val @= 1
        s.overwrite_fu_outport.msg @= s.progress_reg
      else:
        s.overwrite_fu_outport.val @= 0
        s.overwrite_fu_outport.msg @= DataType(0, 0)

    @update_ff
    def update_regs():
      # Updates the status register.
      if (s.recv_cmd_queue.send.val & (s.recv_cmd_queue.send.msg == CMD_PAUSE)):
        s.status_reg <<= STATUS_PAUSING
      elif (s.recv_cmd_queue.send.val & (s.recv_cmd_queue.send.msg == CMD_PRESERVE)):
        s.status_reg <<= STATUS_PRESERVING
      elif (s.recv_cmd_queue.send.val & (s.recv_cmd_queue.send.msg == CMD_RESUME)):
        s.status_reg <<= STATUS_RESUMING
      else:
        s.status_reg <<= s.status_reg

      # Updates the progress register.
      if (s.progress_reg_is_null & s.is_pausing & s.is_executing_phi) | \
           (s.is_preserving & s.is_executing_phi) & \
           (s.progress_in.predicate & s.progress_in_val):
        # Records the progress.
        s.progress_reg <<= s.progress_in
      elif (~s.progress_reg_is_null & s.is_resuming & s.is_executing_phi & \
              s.progress_in.predicate & s.progress_in_val):
        # Clears the register at next clock cycle if progress is resumed.
        s.progress_reg <<= DataType(0, 0)
      else:
        # Keeps the progress.
        s.progress_reg <<= s.progress_reg

      # Records the target PHI_CONST's ctrl mem address to the register.
      if (s.recv_cmd_queue.send.val & (s.recv_cmd_queue.send.msg == CMD_RECORD_PHI_ADDR) & s.recv_phi_addr_queue.send.val):
        s.phi_addr_reg <<= s.recv_phi_addr_queue.send.msg
      else:
        s.phi_addr_reg <<= s.phi_addr_reg

  def line_trace(s):
    recv_cmd_str = f'|| recv_cmd_queue.send.val: {s.recv_cmd_queue.send.val} | recv_cmd_queue.send: {s.recv_cmd_queue.send} '
    recv_opt_str = f'|| recv_opt: {s.recv_opt} '
    progress_in_str = f'|| progress_in: {s.progress_in} '
    overwrite_fu_outport_str = f'|| overwrite_fu_outport.val: {s.overwrite_fu_outport.val}, overwrite_fu_outport.msg: {s.overwrite_fu_outport.msg}, overwrite_fu_outport.rdy: {s.overwrite_fu_outport.rdy} '
    phi_addr_str = f'|| phi_addr: {s.phi_addr} '
    ctrl_mem_rd_addr_str = f'|| ctrl_mem_rd_addr: {s.ctrl_mem_rd_addr} '
    register_content_str = f'|| progress_reg: {s.progress_reg} | status_reg: {s.status_reg}i | phi_addr_reg: {s.phi_addr_reg} '
    condition_str = f'|| condition: progress_reg_is_null:{s.progress_reg_is_null}, is_pausing:{s.is_pausing}, is_executing_phi:{s.is_executing_phi} '
    return recv_cmd_str + recv_opt_str + progress_in_str + overwrite_fu_outport_str + phi_addr_str + ctrl_mem_rd_addr_str + register_content_str + condition_str
