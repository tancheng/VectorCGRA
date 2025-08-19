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

class STEP_RegisterFileRTL(Component):

  def construct(s, DataType, AddrType, CtrlType, num_reg_banks, num_rd_ports = 2, num_wr_ports = 2,
                num_registers_per_reg_bank = 4):

    # Interface
    s.inport_opt = InPort(CtrlType)
    s.recv_data_north = RecvIfcRTL(DataType)
    s.recv_data_south = RecvIfcRTL(DataType)
    s.send_data_north = SendIfcRTL(DataType)
    s.send_data_south = SendIfcRTL(DataType)
    
    LowerAddrType = mkbits(AddrType.nbits / 2)
    UpperAddrType = mkbits(AddrType.nbits - LowerAddrType.nbits)
    
    s.rd_reg_addr = [RecvIfcRTL(AddrType) for _ in range(num_rd_ports)]
    s.wr_reg_addr = [RecvIfcRTL(AddrType) for _ in range(num_wr_ports)]
    s.wr_reg_data = [RecvIfcRTL(DataType) for _ in range(num_wr_ports)]
    s.send_reg_data = [SendIfcRTL(DataType) for _ in range(num_rd_ports)]

    # Component
    s.reg_bank = [RegisterBankRTL(DataType, LowerAddrType, i, num_rd_ports, num_wr_ports, num_registers_per_reg_bank)
                  for i in range(num_reg_banks)]

    for i in range(num_reg_banks):
      s.reg_bank[i].rd_reg_addr //= s.rd_reg_addr[i].msg
      s.reg_bank[i].inport_waddr //= s.wr_reg_addr[i].msg
      s.reg_bank[i].inport_wdata //= s.wr_reg_data[i].msg
      s.reg_bank[i].inport_valid //= s.wr_reg_data[i].val

    # Connections.
    for i in range(num_reg_banks):
      s.reg_bank[i].inport_opt //= s.inport_opt
      s.reg_bank[i].inport_wdata[PORT_RF_NORTH] //= s.recv_data_north[i].msg
      s.reg_bank[i].inport_wdata[PORT_RF_SOUTH] //= s.recv_data_south[i].msg
      s.reg_bank[i].inport_valid[PORT_RF_NORTH] //= s.recv_data_north[i].val
      s.reg_bank[i].inport_valid[PORT_RF_SOUTH] //= s.recv_data_south[i].val

    @update
    def update_msgs_signals():
      # Initializes signals.
      s.send_data_to_fu[i].msg @= DataType()
      s.recv_data_north[i].rdy @= 0
      s.recv_data_south[i].rdy @= 0
      s.send_data_north[i].val @= 0
      s.send_data_south[i].val @= 0

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

