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
    ThreadIdxType = mk_bits(clog2(MAX_THREAD_COUNT))
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
        # Drive each BRAM instance from local bank-hit signals instead of
        # dynamically indexing the bank array. This keeps the generated muxing
        # shallow without changing the visible RF timing contract.
        for i in range(num_rd_ports):
            s.rd_data[i] @= DataType(0)
            for bank in range(num_registers):
                if s.rd_addr[i].msg == AddrType(bank):
                    s.rd_data[i] @= s.reg_bank[bank].rdata

        for bank in range(num_registers):
            s.reg_bank[bank].wen @= Bits1(0)
            s.reg_bank[bank].waddr @= ThreadIdxType(0)
            s.reg_bank[bank].wdata @= DataType(0)
            if s.reset:
                s.reg_bank[bank].raddr @= ThreadIdxType(0)
            for i in range(num_rd_ports):
                if s.rd_addr[i].val & (s.rd_addr[i].msg == AddrType(bank)):
                    s.reg_bank[bank].raddr @= s.rd_thread_idx[i]
            for i in range(num_wr_ports):
                if s.wr_addr[i].val & s.wr_data[i].val & (s.wr_addr[i].msg == AddrType(bank)):
                    s.reg_bank[bank].wen @= Bits1(1)
                    s.reg_bank[bank].waddr @= s.wr_thread_idx[i]
                    s.reg_bank[bank].wdata @= s.wr_data[i].msg
  
  def line_trace(s):
    reg_bank_str = "reg_banks: " + "|".join([reg_bank.line_trace() for reg_bank in s.reg_bank])
    return f'{reg_bank_str}'
