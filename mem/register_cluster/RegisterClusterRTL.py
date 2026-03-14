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
    s.send_data_to_fu = [SendIfcRTL(DataType) for _ in range(num_reg_banks)]
    # Direct output from register banks towards routing crossbar (bypasses FU).
    s.send_data_to_routing_crossbar = [SendIfcRTL(DataType) for _ in range(num_reg_banks)]

    # Component
    s.reg_bank = [RegisterBankRTL(DataType, CtrlType, i, num_registers_per_reg_bank)
                  for i in range(num_reg_banks)]

    # Connections.
    for i in range(num_reg_banks):
      s.reg_bank[i].inport_opt //= s.inport_opt
      s.reg_bank[i].inport_wdata[PORT_ROUTING_CROSSBAR] //= s.recv_data_from_routing_crossbar[i].msg
      s.reg_bank[i].inport_wdata[PORT_FU_CROSSBAR] //= s.recv_data_from_fu_crossbar[i].msg
      s.reg_bank[i].inport_wdata[PORT_CONST] //= s.recv_data_from_const[i].msg
      s.reg_bank[i].inport_valid[PORT_ROUTING_CROSSBAR] //= s.recv_data_from_routing_crossbar[i].val
      s.reg_bank[i].inport_valid[PORT_FU_CROSSBAR] //= s.recv_data_from_fu_crossbar[i].val
      s.reg_bank[i].inport_valid[PORT_CONST] //= s.recv_data_from_const[i].val

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
        read_towards = s.inport_opt.read_reg_towards[i]
        # Checks if data should go towards FU (1 or 3)
        reg_towards_fu = (read_towards == kReadTowardsFu) | (read_towards == kReadTowardsBoth)
        # Checks if data should go towards routing_xbar (2 or 3)
        reg_towards_routing_xbar = (read_towards == kReadTowardsRoutingXbar) | (read_towards == kReadTowardsBoth)

        # Data from register bank has priority over routing crossbar data for FU path.
        # Note: reg_bank[i].send_data.val is set based on read_reg_towards in RegisterBankRTL.
        if s.reg_bank[i].send_data.val:
          s.send_data_to_fu[i].msg @= \
            s.reg_bank[i].send_data.msg
        elif s.recv_data_from_routing_crossbar[i].val:
          s.send_data_to_fu[i].msg @= \
            s.recv_data_from_routing_crossbar[i].msg

        s.send_data_to_fu[i].val @= \
            s.recv_data_from_routing_crossbar[i].val | \
            s.reg_bank[i].send_data.val
        s.reg_bank[i].send_data.rdy @= s.send_data_to_fu[i].rdy

        s.recv_data_from_routing_crossbar[i].rdy @= s.send_data_to_fu[i].rdy
        s.recv_data_from_fu_crossbar[i].rdy @= 1
        s.recv_data_from_const[i].rdy @= 1

        # Drive the direct reg -> routing_crossbar path.
        if reg_towards_routing_xbar:
          s.send_data_to_routing_crossbar[i].msg @= s.reg_bank[i].send_data.msg
          s.send_data_to_routing_crossbar[i].val @= 1

  def line_trace(s):
    reg_bank_str = "reg_banks: " + "|".join([reg_bank.line_trace() for reg_bank in s.reg_bank])
    return f'{reg_bank_str}'

