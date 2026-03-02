"""
==========================================================================
RegisterBankRTL.py
==========================================================================
Register bank using BRAM for synthesis on ZCU102.

Author : Cheng Tan
Date : Feb 6, 2025
"""
from pymtl3 import *
from pymtl3.stdlib.primitive import RegisterFile  # Old implementation
from .STEP_BRAMRTL import STEP_BRAMRTL  # New BRAM implementation

from ...lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ...lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ...lib.opt_type import *
from ...lib.util.common import *

class STEP_RegisterBankRTL(Component):
    def construct(s, DataType, AddrType, reg_bank_id, num_rd_ports=2, 
                  num_wr_ports=2, num_registers=4, mux_enable=True):
        
        # Constant
        s.reg_bank_id = reg_bank_id
        
        # Interface
        ThreadIdxType = mk_bits(clog2(MAX_THREAD_COUNT))
        FinalAddrType = mk_bits(clog2(MAX_THREAD_COUNT * num_registers))
        
        s.rd_reg_addr = [InPort(AddrType) for _ in range(num_rd_ports)]
        s.rd_reg_valid = [InPort(1) for _ in range(num_rd_ports)]
        s.wr_reg_addr = [InPort(AddrType) for _ in range(num_wr_ports)]
        s.wr_reg_data = [InPort(DataType) for _ in range(num_wr_ports)]
        s.wr_reg_valid = [InPort(1) for _ in range(num_wr_ports)]
        s.send_reg_data = [OutPort(DataType) for _ in range(num_rd_ports)]
        s.send_reg_valid = [OutPort(1) for _ in range(num_rd_ports)]
        s.rd_thread_idx = [InPort(ThreadIdxType) for _ in range(num_rd_ports)]
        s.wr_thread_idx = [InPort(ThreadIdxType) for _ in range(num_wr_ports)]
        
        # Component - Using BRAM-optimized register file
        s.reg_file = RegisterFile(
            DataType, 
            nregs=num_registers * MAX_THREAD_COUNT,
            rd_ports=num_rd_ports,
            wr_ports=num_wr_ports
        )
        # s.reg_file = STEP_BRAMRTL(
        #     DataType, 
        #     nregs = MAX_THREAD_COUNT if mux_enable else num_registers * MAX_THREAD_COUNT,
        #     rd_ports = 1 if mux_enable else num_rd_ports,
        #     wr_ports = 1 if mux_enable else num_wr_ports
        # )
        
        if mux_enable:
            # Default Mux Enabled behavior, expects num_banks = num_registers
            # Connect read data directly
            for i in range(num_rd_ports):
                s.send_reg_data[i] //= s.reg_file.rdata[0]

            @update
            def access_registers():
                # Handle Rd ports
                for i in range(num_rd_ports):
                    if s.rd_reg_valid[i]:
                        s.reg_file.raddr[i] @= FinalAddrType( s.rd_thread_idx[i] )
                    else:
                        s.reg_file.raddr[i] @= 0
                
                # Handle Wr ports
                for i in range(num_wr_ports):
                    if s.wr_reg_valid[i]:
                        s.reg_file.wen[i] @= 1
                        s.reg_file.waddr[i] @= FinalAddrType(
                            ThreadIdxType(s.wr_reg_addr[i]) + 
                            s.wr_thread_idx[i] * num_registers
                        )
                        s.reg_file.wdata[i] @= s.wr_reg_data[i]
                    else:
                        s.reg_file.wen[i] @= 0
                        s.reg_file.waddr[i] @= 0
                        s.reg_file.wdata[i] @= 0
        else:
            # Connect read data directly
            for i in range(num_rd_ports):
                s.send_reg_data[i] //= s.reg_file.rdata[i]

            @update
            def access_registers():
                # Handle Rd ports
                for i in range(num_rd_ports):
                    if s.rd_reg_valid[i]:
                        s.reg_file.raddr[i] @= FinalAddrType(
                            ThreadIdxType(s.rd_reg_addr[i]) + 
                            s.rd_thread_idx[i] * num_registers
                        )
                    else:
                        s.reg_file.raddr[i] @= 0
                
                # Handle Wr ports
                for i in range(num_wr_ports):
                    if s.wr_reg_valid[i]:
                        s.reg_file.wen[i] @= 1
                        s.reg_file.waddr[i] @= FinalAddrType(
                            ThreadIdxType(s.wr_reg_addr[i]) + 
                            s.wr_thread_idx[i] * num_registers
                        )
                        s.reg_file.wdata[i] @= s.wr_reg_data[i]
                    else:
                        s.reg_file.wen[i] @= 0
                        s.reg_file.waddr[i] @= 0
                        s.reg_file.wdata[i] @= 0
        
        @update
        def update_send_valid():
            for i in range(num_rd_ports):
                if s.rd_reg_valid[i]:
                    s.send_reg_valid[i] @= 1
                else:
                    s.send_reg_valid[i] @= 0
        
        def line_trace(s):
            content_str = "content: " + "|".join([str(data) for data in s.reg_file.regs])
            return f'reg_bank_id: {s.reg_bank_id} || [{content_str}] [BRAM]'