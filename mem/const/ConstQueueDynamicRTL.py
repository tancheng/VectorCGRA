"""
==========================================================================
ConstQueueDynamicRTL.py
==========================================================================
Constant Queue with regs used for simulation.
If queue is full, will stop receiving new data.

Author : Yuqi Sun
  Date : Jan 11, 2025
"""

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
    AddrType = mk_bits(max(1, clog2(const_mem_size)))

    # cur to record the current valid address, max is const_mem_size - 1
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


    @update
    def load_const():
      s.recv_const.rdy @= 1
      # check if there's a valid const(producer) to be written
      if s.recv_const.val:
        s.reg_file.waddr[0] @= s.cur
        s.reg_file.wdata[0] @= s.recv_const.msg
        s.reg_file.wen[0] @= 1
      # s.recv_const.rdy @= 0(consumer: self) will stop receive const from inport immediately even there's rdy @= 1(self) in @update
      # so will avoid receiving new data when regs full
      # can NOT do this by comparing cur > AddrType(const_mem_size - 1)
      # for example: mem size=8, cur will be Bits3(0x0) once it reaches Bits3(0x7) + AddrType(1) in loop
      # and can NOT use bigger AddrType for cur as it will be used to update waddr: (s.reg_file.waddr[0] @= s.cur), waddr is binded with mem size
      if s.cur == AddrType(const_mem_size - 1):
          s.recv_const.rdy @= 0


    @update_ff
    def move_cur():
      # move cur in @update_ff
      # if producer(remote) val and consumer(self) rdy
      if s.recv_const.val & s.recv_const.rdy:
        # move cur only if cur less than const_mem_size - 1
        # and cur will plus 1 in the last loop
        # then will update the last element in @update
        # after the last element insert, will not move cur and receive const from inport/producer(as set rdy 0 in @update)
        if s.cur < AddrType(const_mem_size - 1):
          s.cur <<= s.cur + AddrType(1)

          # once there's value in regs, start to set self val 1 to enable read
          s.send_const.val <<= 1


    @update_ff
    def update_raddr():
      # check remote rdy and self val(val = 1 when there's const in regs)
      if s.send_const.rdy & s.send_const.val:
        # Approach 1:
        # read to the last element in mem, reset to addr to read from addr 0
        # read needs wait until write finish
        # if s.reg_file.raddr[0] == s.cur:
        #   s.reg_file.raddr[0] <<= AddrType(0)
        # else:
        #   s.reg_file.raddr[0] <<= s.reg_file.raddr[0] + AddrType(1)

        # Approach 2:
        # will NOT reset addr to 0 when read to the last element in mem
        # as this approach read/write simultaneously
        # raddr[0] always equals to cur - 1
        # if wants to change to reset mode, can make read start after write finish
        s.reg_file.raddr[0] <<= s.reg_file.raddr[0] + AddrType(1)


  def line_trace(s):
    const_mem_str  = "|".join([str(data) for data in s.reg_file.regs])
    return f'const_mem_str: {const_mem_str}'

