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
from .STEP_BRAMRTL import STEP_BRAMRTL
from ...lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ...lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ...lib.opt_type import *
from ...lib.util.common import *

class STEP_RegisterFileFullBankRTL(Component):
  def construct(s, DataType, AddrType, num_registers, num_rd_ports=2, num_wr_ports=2,
                num_registers_per_reg_bank=4):
    # Interface
    s.rd_addr = [RecvIfcRTL(AddrType) for _ in range(num_rd_ports)]
    s.wr_addr = [RecvIfcRTL(AddrType) for _ in range(num_wr_ports)]
    s.wr_data = [RecvIfcRTL(DataType) for _ in range(num_wr_ports)]
    s.rd_data = [OutPort(DataType) for _ in range(num_rd_ports)]
    s.rd_thread_idx = [InPort( clog2(MAX_THREAD_COUNT) ) for _ in range(num_rd_ports)]
    s.wr_thread_idx = [InPort( clog2(MAX_THREAD_COUNT) ) for _ in range(num_wr_ports)]

    # Component
    s.reg_bank = [STEP_BRAMRTL(DataType, num_registers_per_reg_bank)
                  for i in range(num_registers)]
    
    # Default wire connections
    for i in range(num_rd_ports):
        s.rd_addr[i].rdy //= 1
    for i in range(num_wr_ports):
        s.wr_addr[i].rdy //= 1
        s.wr_data[i].rdy //= 1

    # Handle Connections
    @update
    def update_register_access():
        # Set Default State
        for i in range(num_rd_ports):
            s.rd_data[i] @= 0
        for i in range(num_wr_ports):
            s.reg_bank[s.wr_addr[i].msg].wen @= 0

        # Handle read ports
        for i in range(num_rd_ports):
            s.reg_bank[s.rd_addr[i].msg].raddr @= s.rd_thread_idx[i]
            s.rd_data[i] @= s.reg_bank[s.rd_addr[i].msg].rdata

        # Handle write ports
        for i in range(num_wr_ports):
            if s.wr_addr[i].val & s.wr_data[i].val:
                s.reg_bank[s.wr_addr[i].msg].wen @= 1
                s.reg_bank[s.wr_addr[i].msg].waddr @= s.wr_thread_idx[i]
                s.reg_bank[s.wr_addr[i].msg].wdata @= s.wr_data[i].msg
  
  def line_trace(s):
    reg_bank_str = "reg_banks: " + "|".join([reg_bank.line_trace() for reg_bank in s.reg_bank])
    return f'{reg_bank_str}'