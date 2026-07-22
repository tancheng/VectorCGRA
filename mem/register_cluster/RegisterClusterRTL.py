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

# Canonical definitions live in common.py; keep local aliases to minimize churn.
from ...lib.util.common import (
  READ_TOWARDS_NOTHING,
  READ_TOWARDS_FU,
  READ_TOWARDS_ROUTING_XBAR,
  READ_TOWARDS_BOTH,
)

kReadTowardsNothing     = READ_TOWARDS_NOTHING
kReadTowardsFu          = READ_TOWARDS_FU
kReadTowardsRoutingXbar = READ_TOWARDS_ROUTING_XBAR
kReadTowardsBoth        = READ_TOWARDS_BOTH

class RegisterClusterRTL(Component):

  def construct(s, DataType, CtrlType, num_reg_banks,
                num_registers_per_reg_bank = 4):

    # Interface
    s.inport_opt = InPort(CtrlType)
    s.recv_data_from_routing_crossbar = [RecvIfcRTL(DataType) for _ in range(num_reg_banks)]
    s.recv_data_from_fu_crossbar = [RecvIfcRTL(DataType) for _ in range(num_reg_banks)]
    s.recv_data_from_const = [RecvIfcRTL(DataType) for _ in range(num_reg_banks)]
    s.write_data_from_routing_crossbar = [InPort(DataType) for _ in range(num_reg_banks)]
    s.write_valid_from_routing_crossbar = [InPort(b1) for _ in range(num_reg_banks)]
    s.send_data_to_fu = [SendIfcRTL(DataType) for _ in range(num_reg_banks)]
    # Direct output from register banks towards routing crossbar (bypasses FU).
    s.send_data_to_routing_crossbar = [SendIfcRTL(DataType) for _ in range(num_reg_banks)]

    # Component
    s.reg_bank = [RegisterBankRTL(DataType, CtrlType, i, num_registers_per_reg_bank)
                  for i in range(num_reg_banks)]

    # Connections.
    for i in range(num_reg_banks):
      s.reg_bank[i].inport_opt //= s.inport_opt
      s.reg_bank[i].inport_wdata[PORT_INDEX_ROUTING_CROSSBAR] //= s.write_data_from_routing_crossbar[i]
      s.reg_bank[i].inport_wdata[PORT_INDEX_FU_CROSSBAR] //= s.recv_data_from_fu_crossbar[i].msg
      s.reg_bank[i].inport_wdata[PORT_INDEX_CONST] //= s.recv_data_from_const[i].msg
      s.reg_bank[i].inport_valid[PORT_INDEX_ROUTING_CROSSBAR] //= s.write_valid_from_routing_crossbar[i]
      s.reg_bank[i].inport_valid[PORT_INDEX_FU_CROSSBAR] //= s.recv_data_from_fu_crossbar[i].val
      s.reg_bank[i].inport_valid[PORT_INDEX_CONST] //= s.recv_data_from_const[i].val

    @update
    def update_msgs_signals():
      # Initializes signals.
      for i in range(num_reg_banks):
        s.send_data_to_fu[i].msg @= DataType()
        s.recv_data_from_routing_crossbar[i].rdy @= 0
        s.recv_data_from_fu_crossbar[i].rdy @= 0
        s.recv_data_from_const[i].rdy @= 0
        s.send_data_to_fu[i].val @= 0
        s.send_data_to_routing_crossbar[i].msg @= DataType()
        s.send_data_to_routing_crossbar[i].val @= 0

      for i in range(num_reg_banks):
        active_ctrl = s.inport_opt.operation != OPT_START
        read_towards = s.inport_opt.read_reg_towards[i]
        # Checks if data should go towards FU (1 or 3)
        reg_towards_fu = active_ctrl & \
                          ((read_towards == kReadTowardsFu) | (read_towards == kReadTowardsBoth))
        # Checks if data should go towards routing_xbar (2 or 3)
        reg_towards_routing_xbar = active_ctrl & \
                                    ((read_towards == kReadTowardsRoutingXbar) | (read_towards == kReadTowardsBoth))
        # Same ctrl slot can both write a routing value into a register and
        # read that register for the FU. The register file would expose the old
        # value for that cycle, so bypass the routing write when the read/write
        # indices match. Example: routing_xbar writes r3=99 while RET reads r3.
        routing_write_to_fu_bypass = active_ctrl & \
            reg_towards_fu & \
            (s.inport_opt.write_reg_from[i] == PORT_ROUTING_CROSSBAR) & \
            (s.inport_opt.write_reg_idx[i] == s.inport_opt.read_reg_idx[i]) & \
            s.write_valid_from_routing_crossbar[i] & \
            ((s.inport_opt.operation != OPT_RET) | \
             s.write_data_from_routing_crossbar[i].predicate)

        # Same-slot routing write/read should be visible to the FU immediately.
        # Example: a final RET can write reg3 from the routing xbar and read
        # reg3 for the FU in the same control step. Use the routing value only
        # when the write is valid; a predicated-off RET write must not hide the
        # register bank's last valid value.
        if routing_write_to_fu_bypass:
          s.send_data_to_fu[i].msg @= s.write_data_from_routing_crossbar[i]
        elif s.reg_bank[i].send_data.val & reg_towards_fu:
          s.send_data_to_fu[i].msg @= \
            s.reg_bank[i].send_data.msg
        elif s.recv_data_from_routing_crossbar[i].val:
          s.send_data_to_fu[i].msg @= \
            s.recv_data_from_routing_crossbar[i].msg

        s.send_data_to_fu[i].val @= active_ctrl & \
            (routing_write_to_fu_bypass | \
             s.recv_data_from_routing_crossbar[i].val | \
             (s.reg_bank[i].send_data.val & reg_towards_fu))
        s.reg_bank[i].send_data.rdy @= s.send_data_to_fu[i].rdy

        # A ready response consumes the routing token. It is safe only when
        # it performs the legacy NAH register write or the FU accepts it.
        s.recv_data_from_routing_crossbar[i].rdy @= \
            (((s.inport_opt.write_reg_from[i] == PORT_ROUTING_CROSSBAR) & \
              (s.inport_opt.operation == OPT_NAH)) | \
             s.send_data_to_fu[i].rdy)
        s.recv_data_from_fu_crossbar[i].rdy @= 1
        s.recv_data_from_const[i].rdy @= 1

        # Drive the direct reg -> routing_crossbar path.
        if reg_towards_routing_xbar:
          s.send_data_to_routing_crossbar[i].msg @= s.reg_bank[i].send_data.msg
          s.send_data_to_routing_crossbar[i].val @= 1

  def line_trace(s):
    reg_bank_str = "reg_banks: " + "|".join([reg_bank.line_trace() for reg_bank in s.reg_bank])
    return f'{reg_bank_str}'

