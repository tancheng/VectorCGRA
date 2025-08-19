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
from ...lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ...lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ...lib.opt_type import *

class STEP_RegisterBankRTL(Component):

  def construct(s, DataType, AddrType, reg_bank_id, num_rd_ports = 2, num_wr_ports = 2, num_registers = 4):

    # Constant
    # AddrType = mk_bits(clog2(num_registers))
    s.reg_bank_id = reg_bank_id

    # Interface
    s.rd_reg_addr = [InPort(AddrType) for _ in range(num_rd_ports)]
    s.rd_reg_valid = [InPort(b1) for _ in range(num_rd_ports)]
    s.wr_reg_addr = [InPort(AddrType) for _ in range(num_wr_ports)]
    s.wr_reg_data = [InPort(DataType) for _ in range(num_wr_ports)]
    s.wr_reg_valid = [InPort(b1) for _ in range(num_wr_ports)]
    s.send_reg_data = [OutPort(DataType) for _ in range(num_rd_ports)]
    s.send_reg_valid = [OutPort(b1) for _ in range(num_rd_ports)]

    # Component
    s.reg_file = RegisterFile(DataType, num_registers, rd_ports = num_rd_ports,
                              wr_ports = num_wr_ports)

    @update
    def access_registers():
      # Initialize Signals
      for i in range(num_rd_ports):
        s.reg_file.raddr[i] @= AddrType()
        s.send_reg_data[i] @= DataType()
      for i in range(num_wr_ports):
        s.reg_file.waddr[i] @= AddrType()
        s.reg_file.wdata[i] @= DataType()
        s.reg_file.wen[i] @= 0

      # Handle Rd ports
      for i in range(num_rd_ports):
        if s.rd_reg_valid[i]:
          s.reg_file.raddr[i] @= s.rd_reg_data[i]
          s.send_reg_data[i] @= s.reg_file.rdata[i]

      # Handle Wr ports
      for i in range(num_wr_ports):
        if s.wr_reg_valid[i]:
          s.reg_file.wen[i] @= 1
          s.reg_file.waddr[i] @= s.wr_reg_addr[i]
          s.reg_file.wdata[i] @= s.wr_reg_data[i]

    @update
    def update_send_val():
      for i in range(num_rd_ports):
        s.send_reg_val @= 0
        if ~s.reset & s.rd_reg_val[i]:
          s.send_reg_val @= 1

  def line_trace(s):
    inport_opt_str = "inport_opt: " + str(s.inport_opt)
    inport_wdata_str = "inport_wdata: " + str(s.inport_wdata)
    content_str = "content: " + "|".join([str(data) for data in s.reg_file.regs])
    send_data_to_fu_str = "send_data_to_fu: " +  str(s.send_data_to_fu.msg)
    return f'reg_bank_id: {s.reg_bank_id} || {inport_wdata_str} || {inport_opt_str} || [{content_str}] || {send_data_to_fu_str}'

