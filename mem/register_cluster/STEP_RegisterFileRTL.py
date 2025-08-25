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

  def construct(s, DataType, AddrType, num_reg_banks, num_rd_ports = 2, num_wr_ports = 2,
                num_registers_per_reg_bank = 4):

    # Interface
    s.rd_addr = [RecvIfcRTL(AddrType) for _ in range(num_rd_ports)]
    s.wr_addr = [RecvIfcRTL(AddrType) for _ in range(num_wr_ports)]
    s.wr_data = [RecvIfcRTL(DataType) for _ in range(num_wr_ports)]
    s.send_data = [RecvIfcRTL(DataType) for _ in range(num_rd_ports)]
    
    LowerAddrType = mkbits(AddrType.nbits / 2)
    UpperAddrType = mkbits(AddrType.nbits - LowerAddrType.nbits)

    # Component
    s.reg_bank = [RegisterBankRTL(DataType, LowerAddrType, i, num_rd_ports, num_wr_ports, num_registers_per_reg_bank)
                  for i in range(num_reg_banks)]

    # Internal signals to mux for register banks
    s.reg_bank_rd_addr = [[Wire(LowerAddrType) for _ in range(num_rd_ports)] for _ in range(num_reg_banks)]
    s.reg_bank_wr_addr = [[Wire(LowerAddrType) for _ in range(num_wr_ports)] for _ in range(num_reg_banks)]
    s.reg_bank_wr_data = [[Wire(DataType) for _ in range(num_wr_ports)] for _ in range(num_reg_banks)]
    s.reg_bank_send_data = [[Wire(DataType) for _ in range(num_rd_ports)] for _ in range(num_reg_banks)]
  
    @update
    def update_msgs_signals():
      # Initializes signals.
      for i in range(num_reg_banks):
        for j in range(num_rd_ports):
          s.reg_bank_rd_addr[i][j] @= LowerAddrType()
          s.reg_bank_send_data[i][j] @= DataType()
        for j in range(num_wr_ports):
          s.reg_bank_wr_addr[i][j] @= LowerAddrType()
          s.reg_bank_wr_data[i][j] @= DataType()

      # Handle read ports
      for i in range(num_rd_ports):
        if s.rd_addr[i].val:
          # Extract the lower and upper address from the received address.
          lower_addr = s.rd_addr[i].msg[:LowerAddrType.nbits]
          upper_addr = s.rd_addr[i].msg[LowerAddrType.nbits:]
          
          # Determine which register bank to access based on the upper address.
          reg_bank_id = int(upper_addr, 2)
          if reg_bank_id < num_reg_banks:
            s.reg_bank_rd_addr[reg_bank_id][i] @= lower_addr
            s.send_data[i].msg @= s.reg_bank_send_data[reg_bank_id][i]
            s.send_data[i].val @= 1
          else:
            s.send_data[i].val @= 0
      
      # Handle write ports
      for i in range(num_wr_ports):
        if s.wr_addr[i].val and s.wr_data[i].val:
          # Extract the lower and upper address from the received address.
          lower_addr = s.wr_addr[i].msg[:LowerAddrType.nbits]
          upper_addr = s.wr_addr[i].msg[LowerAddrType.nbits:]
          
          # Determine which register bank to access based on the upper address.
          reg_bank_id = int(upper_addr, 2)
          if reg_bank_id < num_reg_banks:
            s.reg_bank_wr_addr[reg_bank_id][i] @= lower_addr
            s.reg_bank_wr_data[reg_bank_id][i] @= s.wr_data[i].msg
            s.reg_bank[i].wr_reg_valid[i] @= 1
          else:
            s.wr_data[i].val @= 0

  def line_trace(s):
    reg_bank_str = "reg_banks: " + "|".join([reg_bank.line_trace() for reg_bank in s.reg_bank])
    return f'{reg_bank_str}'

