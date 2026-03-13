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

class RegisterBankRTL(Component):

  def construct(s, DataType, CtrlType, reg_bank_id, num_registers = 4):

    # Constant
    AddrType = mk_bits(clog2(num_registers))
    s.reg_bank_id = reg_bank_id

    # Interface
    s.inport_opt = InPort(CtrlType)
    s.send_data_to_fu = SendIfcRTL(DataType)
    # InPort is enough to expose the data. Recv ifc would complicate
    # the design and handshake.
    s.inport_wdata = [InPort(DataType) for _ in range(3)]
    s.inport_valid = [InPort(b1) for _ in range(3)]

    # Component
    s.reg_file = RegisterFile(DataType, num_registers, rd_ports = 1,
                              wr_ports = 1)

    # Constants for read_reg_towards semantics:
    # 0: towards nothing (no read)
    # 1: towards FU (reg data consumed by operation)
    # 2: towards routing_xbar (reg data routed out to outport)
    # 3: towards both FU and routing_xbar
    READ_TOWARDS_NOTHING = 0
    READ_TOWARDS_FU = 1
    READ_TOWARDS_ROUTING_XBAR = 2
    READ_TOWARDS_BOTH = 3

    @update
    def access_registers():
      # Initializes signals.
      s.reg_file.raddr[0] @= AddrType()
      s.send_data_to_fu.msg @= DataType()
      s.reg_file.waddr[0] @= AddrType()
      s.reg_file.wdata[0] @= DataType()
      s.reg_file.wen[0] @= 0

      read_towards = s.inport_opt.read_reg_towards[reg_bank_id]
      # Reads from register if towards FU (1), routing_xbar (2), or both (3)
      if read_towards > 0:
        s.reg_file.raddr[0] @= s.inport_opt.read_reg_idx[reg_bank_id]
        s.send_data_to_fu.msg @= s.reg_file.rdata[0]

      write_reg_from = s.inport_opt.write_reg_from[reg_bank_id]
      if ~s.reset & (write_reg_from > 0):
        if s.inport_valid[write_reg_from - 1]:
          s.reg_file.waddr[0] @= s.inport_opt.write_reg_idx[reg_bank_id]
          s.reg_file.wdata[0] @= s.inport_wdata[write_reg_from - 1]
          s.reg_file.wen[0] @= 1

    @update
    def update_send_val():
      s.send_data_to_fu.val @= 0
      read_towards = s.inport_opt.read_reg_towards[reg_bank_id]
      # Sends to FU if towards FU (1) or both (3)
      if ~s.reset & ((read_towards == READ_TOWARDS_FU) | (read_towards == READ_TOWARDS_BOTH)):
        s.send_data_to_fu.val @= 1

  def line_trace(s):
    inport_opt_str = "inport_opt: " + str(s.inport_opt)
    inport_wdata_str = "inport_wdata: " + str(s.inport_wdata)
    content_str = "content: " + "|".join([str(data) for data in s.reg_file.regs])
    send_data_to_fu_str = "send_data_to_fu: " +  str(s.send_data_to_fu.msg)
    return f'reg_bank_id: {s.reg_bank_id} || {inport_wdata_str} || {inport_opt_str} || [{content_str}] || {send_data_to_fu_str}'

