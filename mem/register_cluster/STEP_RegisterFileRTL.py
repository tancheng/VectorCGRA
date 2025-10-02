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
from .STEP_RegisterBankRTL import STEP_RegisterBankRTL
from ...lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ...lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ...lib.opt_type import *
from ...lib.util.common import *

class STEP_RegisterFileRTL(Component):
  def construct(s, DataType, AddrType, num_reg_banks, num_rd_ports=2, num_wr_ports=2,
                num_registers_per_reg_bank=4):
    # Interface
    s.rd_addr = [RecvIfcRTL(AddrType) for _ in range(num_rd_ports)]
    s.wr_addr = [RecvIfcRTL(AddrType) for _ in range(num_wr_ports)]
    s.wr_data = [RecvIfcRTL(DataType) for _ in range(num_wr_ports)]
    s.rd_data = [OutPort(DataType) for _ in range(num_rd_ports)]
    s.rd_thread_idx = [InPort( clog2(MAX_THREAD_COUNT) ) for _ in range(num_rd_ports)]
    s.wr_thread_idx = [InPort( clog2(MAX_THREAD_COUNT) ) for _ in range(num_wr_ports)]
   
    # Calculate address splitting
    lower_addr_bits = clog2(num_registers_per_reg_bank)
    upper_addr_bits = AddrType.nbits - lower_addr_bits
    LowerAddrType = mk_bits(lower_addr_bits) if lower_addr_bits > 0 else mk_bits(1)
    UpperAddrType = mk_bits(upper_addr_bits) if upper_addr_bits > 0 else mk_bits(1)
    
    # Component
    s.reg_bank = [STEP_RegisterBankRTL(DataType, LowerAddrType, i, num_rd_ports, num_wr_ports, num_registers_per_reg_bank)
                  for i in range(num_reg_banks)]
    
    # Create Wire signals for address decoding
    s.rd_lower_addr = [[Wire(LowerAddrType) for _ in range(num_rd_ports)] for _ in range(num_reg_banks)]
    s.rd_upper_addr = [[Wire(UpperAddrType) for _ in range(num_rd_ports)] for _ in range(num_reg_banks)]
    s.wr_lower_addr = [[Wire(LowerAddrType) for _ in range(num_wr_ports)] for _ in range(num_reg_banks)]
    s.wr_upper_addr = [[Wire(UpperAddrType) for _ in range(num_wr_ports)] for _ in range(num_reg_banks)]
    
    # Create selection signals for each bank and port
    s.rd_bank_sel = [[Wire(Bits1) for _ in range(num_rd_ports)] for _ in range(num_reg_banks)]
    s.wr_bank_sel = [[Wire(Bits1) for _ in range(num_wr_ports)] for _ in range(num_reg_banks)]

    # Wire Connections
    for i in range(num_reg_banks):
        for j in range(num_rd_ports):
            s.reg_bank[i].rd_thread_idx[j] //= s.rd_thread_idx[j]
        for j in range(num_wr_ports):
            s.reg_bank[i].wr_thread_idx[j] //= s.wr_thread_idx[j]
 
    @update
    def update_address_decode():
      # Initialize all bank selection signals
      for bank_id in range(num_reg_banks):
        for port_id in range(num_rd_ports):
          s.rd_bank_sel[bank_id][port_id] @= 0
          s.rd_lower_addr[bank_id][port_id] @= 0
          s.rd_upper_addr[bank_id][port_id] @= 0
        for port_id in range(num_wr_ports):
          s.wr_bank_sel[bank_id][port_id] @= 0
          s.wr_lower_addr[bank_id][port_id] @= 0
          s.wr_upper_addr[bank_id][port_id] @= 0
      
      # Decode read addresses
      for port_id in range(num_rd_ports):
        if s.rd_addr[port_id].val:
          for bank_id in range(num_reg_banks):
            # Handle lower address bits - avoid empty slice when lower_addr_bits is 0
            if lower_addr_bits > 0:
              s.rd_lower_addr[bank_id][port_id] @= s.rd_addr[port_id].msg[0:lower_addr_bits]
            else:
              s.rd_lower_addr[bank_id][port_id] @= 0
            
            # Handle bank selection based on upper bits
            if upper_addr_bits > 0:
              s.rd_upper_addr[bank_id][port_id] @= s.rd_addr[port_id].msg[lower_addr_bits:lower_addr_bits+upper_addr_bits]
              s.rd_bank_sel[bank_id][port_id] @= (s.rd_addr[port_id].msg[lower_addr_bits:lower_addr_bits+upper_addr_bits] == bank_id)
            else:
              s.rd_upper_addr[bank_id][port_id] @= 0
              s.rd_bank_sel[bank_id][port_id] @= (bank_id == 0)
      
      # Decode write addresses  
      for port_id in range(num_wr_ports):
        if s.wr_addr[port_id].val:
          for bank_id in range(num_reg_banks):
            # Handle lower address bits - avoid empty slice when lower_addr_bits is 0
            if lower_addr_bits > 0:
              s.wr_lower_addr[bank_id][port_id] @= s.wr_addr[port_id].msg[0:lower_addr_bits]
            else:
              s.wr_lower_addr[bank_id][port_id] @= 0
            
            # Handle bank selection based on upper bits
            if upper_addr_bits > 0:
              s.wr_upper_addr[bank_id][port_id] @= s.wr_addr[port_id].msg[lower_addr_bits:lower_addr_bits+upper_addr_bits]
              s.wr_bank_sel[bank_id][port_id] @= (s.wr_addr[port_id].msg[lower_addr_bits:lower_addr_bits+upper_addr_bits] == bank_id)
            else:
              s.wr_upper_addr[bank_id][port_id] @= 0
              s.wr_bank_sel[bank_id][port_id] @= (bank_id == 0)

    @update
    def update_register_access():
      # Initialize all register bank inputs
      for bank_id in range(num_reg_banks):
        for port_id in range(num_rd_ports):
          s.reg_bank[bank_id].rd_reg_addr[port_id] @= 0
          s.reg_bank[bank_id].rd_reg_valid[port_id] @= 0
        for port_id in range(num_wr_ports):
          s.reg_bank[bank_id].wr_reg_addr[port_id] @= 0
          s.reg_bank[bank_id].wr_reg_data[port_id] @= 0
          s.reg_bank[bank_id].wr_reg_valid[port_id] @= 0
      
      # Initialize output interfaces
      for port_id in range(num_rd_ports):
        s.rd_data[port_id] @= 0
      
      # Handle read ports - drive selected banks
      for bank_id in range(num_reg_banks):
        for port_id in range(num_rd_ports):
          if s.rd_bank_sel[bank_id][port_id]:
            s.reg_bank[bank_id].rd_reg_addr[port_id] @= s.rd_lower_addr[bank_id][port_id]
            s.reg_bank[bank_id].rd_reg_valid[port_id] @= 1
            s.rd_data[port_id] @= s.reg_bank[bank_id].send_reg_data[port_id]
     
      # Handle write ports - drive selected banks
      for bank_id in range(num_reg_banks):
        for port_id in range(num_wr_ports):
          if s.wr_bank_sel[bank_id][port_id] & s.wr_data[port_id].val:
            s.reg_bank[bank_id].wr_reg_addr[port_id] @= s.wr_lower_addr[bank_id][port_id]
            s.reg_bank[bank_id].wr_reg_data[port_id] @= s.wr_data[port_id].msg
            s.reg_bank[bank_id].wr_reg_valid[port_id] @= 1
    
    # Connect ready signals (assuming simple ready logic)
    for port_id in range(num_rd_ports):
      s.rd_addr[port_id].rdy //= 1
    
    for port_id in range(num_wr_ports):
      s.wr_addr[port_id].rdy //= 1
  
  def line_trace(s):
    reg_bank_str = "reg_banks: " + "|".join([reg_bank.line_trace() for reg_bank in s.reg_bank])
    return f'{reg_bank_str}'