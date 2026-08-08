"""
==========================================================================
RegisterClusterRTL.py
==========================================================================
Register cluster contains multiple register banks.

Author : Cheng Tan
  Date : Feb 7, 2025
"""

from pymtl3 import *
from pymtl3.stdlib.primitive import RegisterFile
from .RegisterBankRTL import RegisterBankRTL
from ...lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ...lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ...lib.opt_type import *
from ...lib.util.common import *

# Direction filtering of the register read paths happens inside
# RegisterBankRTL (which asserts each send interface's val only for its
# own configured direction), so this module no longer needs the
# READ_TOWARDS_* constants.

class RegisterClusterRTL(Component):

  def construct(s, DataType, CtrlType, num_reg_banks,
                num_registers_per_reg_bank = 4,
                enable_token_discipline = True):

    # Interface
    s.inport_opt = InPort(CtrlType)
    # Pulses when the current ctrl step completes; consumes the tokens
    # of the registers read by the completing step.
    s.inport_ctrl_proceed = InPort(mk_bits(1))
    # Clears the banks' token bookkeeping on task switching.
    s.clear = InPort(mk_bits(1))
    s.recv_data_from_routing_crossbar = [RecvIfcRTL(DataType) for _ in range(num_reg_banks)]
    s.recv_data_from_fu_crossbar = [RecvIfcRTL(DataType) for _ in range(num_reg_banks)]
    s.recv_data_from_const = [RecvIfcRTL(DataType) for _ in range(num_reg_banks)]
    s.send_data_to_fu = [SendIfcRTL(DataType) for _ in range(num_reg_banks)]
    # Direct output from register banks towards routing crossbar (bypasses FU).
    s.send_data_to_routing_crossbar = [SendIfcRTL(DataType) for _ in range(num_reg_banks)]

    # Component
    s.reg_bank = [RegisterBankRTL(DataType, CtrlType, i,
                                  num_registers_per_reg_bank,
                                  enable_token_discipline)
                  for i in range(num_reg_banks)]

    # Connections.
    for i in range(num_reg_banks):
      s.reg_bank[i].inport_opt //= s.inport_opt
      s.reg_bank[i].inport_ctrl_proceed //= s.inport_ctrl_proceed
      s.reg_bank[i].clear //= s.clear
      s.reg_bank[i].inport_wdata[PORT_INDEX_ROUTING_CROSSBAR] //= s.recv_data_from_routing_crossbar[i].msg
      s.reg_bank[i].inport_wdata[PORT_INDEX_FU_CROSSBAR] //= s.recv_data_from_fu_crossbar[i].msg
      s.reg_bank[i].inport_wdata[PORT_INDEX_CONST] //= s.recv_data_from_const[i].msg
      s.reg_bank[i].inport_valid[PORT_INDEX_ROUTING_CROSSBAR] //= s.recv_data_from_routing_crossbar[i].val
      s.reg_bank[i].inport_valid[PORT_INDEX_FU_CROSSBAR] //= s.recv_data_from_fu_crossbar[i].val
      s.reg_bank[i].inport_valid[PORT_INDEX_CONST] //= s.recv_data_from_const[i].val
      # The direct reg -> routing_crossbar read path is a plain val/rdy
      # handshake owned by the bank (val is only asserted while the
      # selected register holds an unconsumed token).
      s.reg_bank[i].send_data_to_xbar //= s.send_data_to_routing_crossbar[i]

    @update
    def update_msgs_signals():
      # Initializes signals.
      for i in range(num_reg_banks):
        s.send_data_to_fu[i].msg @= DataType()
        s.recv_data_from_routing_crossbar[i].rdy @= 0
        s.recv_data_from_fu_crossbar[i].rdy @= 0
        s.recv_data_from_const[i].rdy @= 0
        s.send_data_to_fu[i].val @= 0

      for i in range(num_reg_banks):
        # Data from register bank has priority over routing crossbar data
        # for FU path. Note: the bank asserts send_data_to_fu.val only when
        # read_reg_towards includes FU and the selected register either
        # holds an unconsumed token or has never been written (legacy
        # default-token source), so no additional direction check is
        # needed here.
        if s.reg_bank[i].send_data_to_fu.val:
          s.send_data_to_fu[i].msg @= \
            s.reg_bank[i].send_data_to_fu.msg
        elif s.recv_data_from_routing_crossbar[i].val:
          s.send_data_to_fu[i].msg @= \
            s.recv_data_from_routing_crossbar[i].msg

        s.send_data_to_fu[i].val @= \
            s.recv_data_from_routing_crossbar[i].val | \
            s.reg_bank[i].send_data_to_fu.val
        s.reg_bank[i].send_data_to_fu.rdy @= s.send_data_to_fu[i].rdy

        # fu_in[] is indexed by operand slot, and each non-zero value is a
        # one-based physical FU-input lane. Check every operand slot instead
        # of assuming operand slot i always selects physical lane i.
        lane_used_by_fu = (s.inport_opt.fu_in[0] == (i + 1))
        for operand_slot in range(1, num_reg_banks):
          lane_used_by_fu |= \
              (s.inport_opt.fu_in[operand_slot] == (i + 1))

        read_towards = s.inport_opt.read_reg_towards[i]
        reg_towards_fu = \
            (read_towards == READ_TOWARDS_FU) | \
            (read_towards == READ_TOWARDS_BOTH)

        # A routing value can be written independently while the register
        # bank supplies this physical lane to the FU. Treat that combined
        # move as the selected write path as well, so it is accepted only
        # when the destination register can take the token.
        routing_selected_for_write = \
            (s.inport_opt.write_reg_from[i] == PORT_ROUTING_CROSSBAR) & \
            ((s.inport_opt.operation == OPT_NAH) | reg_towards_fu)

        # A write source is backpressured (not ready) while the
        # destination register still holds an unconsumed token
        # (reg_bank[i].outport_wr_rdy). During OPT_NAH, every other routing
        # lane must drain regardless of the otherwise-default fu_in mapping;
        # during an FU operation, an unselected lane drains only when no
        # operand slot selects that physical lane.
        s.recv_data_from_routing_crossbar[i].rdy @= \
            (routing_selected_for_write & s.reg_bank[i].outport_wr_rdy) | \
            (~routing_selected_for_write & \
             ((s.inport_opt.operation == OPT_NAH) | ~lane_used_by_fu | \
              reg_towards_fu | s.send_data_to_fu[i].rdy))
        s.recv_data_from_fu_crossbar[i].rdy @= \
            (s.inport_opt.write_reg_from[i] != PORT_FU_CROSSBAR) | s.reg_bank[i].outport_wr_rdy
        s.recv_data_from_const[i].rdy @= \
            (s.inport_opt.write_reg_from[i] != PORT_CONST) | s.reg_bank[i].outport_wr_rdy

  def line_trace(s):
    reg_bank_str = "reg_banks: " + "|".join([reg_bank.line_trace() for reg_bank in s.reg_bank])
    return f'{reg_bank_str}'
