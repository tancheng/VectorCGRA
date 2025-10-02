"""
==========================================================================
RegisterBankRTL.py
==========================================================================
Register bank between routing crossbar and FU in CGRA tile. It can be
initialized/modeled/parameterized as multiple instances. Each one contains
multiple registers that can be indexed/picked for read/write. Each has
one write port (from routing crossbar, fu crossbar, or const) and one read
port (towards FU).
Author : Cheng Tan
  Date : Feb 6, 2025
"""
from pymtl3 import *
from pymtl3.stdlib.primitive import RegisterFile
# from pymtl3.stdlib.mem import SramRTL
from ...lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ...lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ...lib.opt_type import *
from ...lib.util.common import *

class STEP_RegisterBankRTL(Component):
  def construct(s, DataType, AddrType, reg_bank_id, num_rd_ports=2, num_wr_ports=2, num_registers=4):
    # Constant
    # AddrType = mk_bits(clog2(num_registers))
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
    s.rd_thread_idx = [InPort( ThreadIdxType ) for _ in range(num_rd_ports)]
    s.wr_thread_idx = [InPort( ThreadIdxType ) for _ in range(num_wr_ports)]
    
    # Component
    s.reg_file = RegisterFile(DataType, num_registers * MAX_THREAD_COUNT, rd_ports=num_rd_ports,
                              wr_ports=num_wr_ports)
    # s.reg_file = SramRTL(
    #                         data_nbits=DataType.nbits,
    #                         num_entries=num_registers * MAX_THREAD_COUNT,
    #                         num_rd_ports=num_rd_ports,
    #                         num_wr_ports=num_wr_ports,
    #                         mask_size=1  # or appropriate mask granularity
    #                     )
    
    @update
    def access_registers():
        # Handle Rd ports
        for i in range(num_rd_ports):
            if s.rd_reg_valid[i]:
                s.reg_file.raddr[i] @= FinalAddrType(ThreadIdxType(s.rd_reg_addr[i]) + s.rd_thread_idx[i] * num_registers)
            else:
                s.reg_file.raddr[i] @= 0
        
        # Handle Wr ports  
        for i in range(num_wr_ports):
            if s.wr_reg_valid[i]:
                s.reg_file.wen[i] @= 1
                s.reg_file.waddr[i] @= FinalAddrType(ThreadIdxType(s.wr_reg_addr[i]) + s.wr_thread_idx[i] * num_registers)
                s.reg_file.wdata[i] @= s.wr_reg_data[i]
            else:
                s.reg_file.wen[i] @= 0
                s.reg_file.waddr[i] @= 0
                s.reg_file.wdata[i] @= 0
        
    # Connect read data directly 
    for i in range(num_rd_ports):
        s.send_reg_data[i] //= s.reg_file.rdata[i]
    
    @update
    def update_send_valid():
        for i in range(num_rd_ports):
            if s.rd_reg_valid[i]:
                s.send_reg_valid[i] @= 1
            else:
                s.send_reg_valid[i] @= 0
  
    def line_trace(s):
        # Note: Some referenced attributes in original trace don't exist in current interface
        # Commenting out problematic references and keeping valid ones
        content_str = "content: " + "|".join([str(data) for data in s.reg_file.regs])
        return f'reg_bank_id: {s.reg_bank_id} || [{content_str}]'
        
        # Original line_trace with non-existent attributes commented:
        # inport_opt_str = "inport_opt: " + str(s.inport_opt)  # Doesn't exist
        # inport_wdata_str = "inport_wdata: " + str(s.inport_wdata)  # Doesn't exist  
        # send_data_to_fu_str = "send_data_to_fu: " + str(s.send_data_to_fu.msg)  # Doesn't exist
        # return f'reg_bank_id: {s.reg_bank_id} || {inport_wdata_str} || {inport_opt_str} || [{content_str}] || {send_data_to_fu_str}'