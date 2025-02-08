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

class RegisterClusterRTL(Component):

  def construct(s, DataType, CtrlType, num_reg_banks,
                num_registers_per_reg_bank = 4):

    # Interface
    s.inport_opt = InPort(CtrlType)
    s.recv_data_from_routing_crossbar = [RecvIfcRTL(DataType) for _ in range(num_reg_banks)]
    s.recv_data_from_fu_crossbar = [RecvIfcRTL(DataType) for _ in range(num_reg_banks)]
    s.recv_data_from_const = [RecvIfcRTL(DataType) for _ in range(num_reg_banks)]
    s.send_data_to_fu = [SendIfcRTL(DataType) for _ in range(num_reg_banks)]

    # Component
    s.reg_bank = [RegisterBankRTL(DataType, CtrlType, i, num_registers_per_reg_bank)
                  for i in range(num_reg_banks)]

    # Connections.
    for i in range(num_reg_banks):
      s.reg_bank[i].inport_opt //= s.inport_opt
      s.reg_bank[i].inport_wdata[0] //= s.recv_data_from_routing_crossbar[i].msg
      s.reg_bank[i].inport_wdata[1] //= s.recv_data_from_fu_crossbar[i].msg
      s.reg_bank[i].inport_wdata[2] //= s.recv_data_from_const[i].msg
      s.reg_bank[i].inport_valid[0] //= s.recv_data_from_routing_crossbar[i].val
      s.reg_bank[i].inport_valid[1] //= s.recv_data_from_fu_crossbar[i].val
      s.reg_bank[i].inport_valid[2] //= s.recv_data_from_const[i].val

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
        if s.recv_data_from_routing_crossbar[i].val:
          s.send_data_to_fu[i].msg @= \
            s.recv_data_from_routing_crossbar[i].msg
        else:
          s.send_data_to_fu[i].msg @= \
            s.reg_bank[i].send_data_to_fu.msg

        s.send_data_to_fu[i].val @= \
            s.recv_data_from_routing_crossbar[i].val | \
            s.reg_bank[i].send_data_to_fu.val
        s.reg_bank[i].send_data_to_fu.rdy @= s.send_data_to_fu[i].rdy

        s.recv_data_from_routing_crossbar[i].rdy @= s.send_data_to_fu[i].rdy
        s.recv_data_from_fu_crossbar[i].rdy @= 1
        s.recv_data_from_const[i].rdy @= 1

  def line_trace(s):
    reg_bank_str = "reg_banks: " + "|".join([reg_bank.line_trace() for reg_bank in s.reg_bank])
    return f'{reg_bank_str}'

