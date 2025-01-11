"""
==========================================================================
ConstQueueDynamicRTL.py
==========================================================================
Constant memory with regs used for simulation.

Author : Yuqi Sun
  Date : Jan 11, 2025
"""

from pymtl3 import *
from pymtl3.stdlib.primitive import RegisterFile
from ...lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ...lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ...lib.opt_type import *

class ConstQueueDynamicRTL(Component):
  def construct(s, DataType, const_mem_size):
    # Constant
    # addr type: number of bits to represent the address
    # 2^addr_size = const_mem_size
    # i.e. const_mem_size = 8
    # ConstMemAddrType is 3 bits
    # ConstMemAddrTyp(1) = 001
    # ConstMemAddrType(2) = 010
    AddrType = mk_bits(clog2(const_mem_size))

    # cur to record the current valid address
    s.cur = Wire(AddrType)

    # Interface
    s.send_const = SendIfcRTL(DataType)
    s.recv_const = RecvIfcRTL(DataType)

    # Component
    #                               Type,     nregs,     rd_ports, wr_ports
    # 1 rd_port: number of read port is 0
    # 1 wr_port: number of write port is 0
    s.reg_file = RegisterFile(DataType, const_mem_size, 1,        1)

    # Connections
    s.send_const.msg //= s.reg_file.rdata[0]

    @update_ff
    def write_to_reg():
      s.recv_const.rdy <<= 1
      # check if there's a valid const to be written
      if s.recv_const.val:
        # .wen: enable write
        # wen=1 to enable write, port 0
        # data can be written only if wen
        s.reg_file.wen[0] <<= 1
        # if cur point to last element in mem
        # drop data for now
        if s.cur == AddrType(const_mem_size - 1):
          print(f"Drop data as full const mem, size: {const_mem_size}")
        else:
          s.cur <<= s.cur + AddrType(1)
          s.reg_file.waddr[0] <<= s.cur
          s.reg_file.wdata[0] <<= s.recv_const.msg

    @update_ff
    def update_raddr():
      if s.send_const.rdy:
        # read to the last element in mem, reset to addr to read from addr 0
        if s.reg_file.raddr[0] == s.cur:
          s.reg_file.raddr[0] <<= AddrType(0)
        else:
          s.reg_file.raddr[0] <<= s.reg_file.raddr[0] + AddrType(1)


  def line_trace(s):
    const_mem_str  = "|".join([str(data) for data in s.reg_file.regs])
    return f'const_mem_str: {const_mem_str}'

