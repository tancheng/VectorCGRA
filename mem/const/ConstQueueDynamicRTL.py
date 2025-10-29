"""
==========================================================================
ConstQueueDynamicRTL.py
==========================================================================
Constant Queue with regs used for simulation.
If queue is full, will stop receiving new data.

Author : Yuqi Sun
  Date : Jan 11, 2025
"""
from py_markdown_table.markdown_table import markdown_table
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

    # Makes write cursor type 1 bit more than mem addr type as need compare with const_mem_size,
    # otherwise, number will be back to 000 when 111 + 1 (given const_mem_size = 8)
    WrCurType = mk_bits(clog2(const_mem_size + 1))

    # write cursor and read cursor
    s.wr_cur = Wire(WrCurType)
    s.rd_cur = Wire(AddrType)

    # Interface
    s.send_const = SendIfcRTL(DataType)
    s.recv_const = RecvIfcRTL(DataType)

    s.ctrl_proceed = InPort(b1)
    s.clear = InPort(b1)

    # Component
    # 1 rd_port: number of read port is 0.
    # 1 wr_port: number of write port is 0.
    #                         Type,     nregs,          rd_ports, wr_ports
    s.reg_file = RegisterFile(DataType, const_mem_size, 1,        1)

    # Connections
    s.send_const.msg //= s.reg_file.rdata[0]
    s.reg_file.raddr[0] //= s.rd_cur


    @update
    def load_const():
      # Initializes signals.
      s.reg_file.waddr[0] @= AddrType()
      s.reg_file.wdata[0] @= DataType()
      s.reg_file.wen[0] @= 0

      not_full = s.wr_cur < const_mem_size
      s.recv_const.rdy @= not_full

      if s.recv_const.val & not_full:
        s.reg_file.waddr[0] @= trunc(s.wr_cur, AddrType)
        s.reg_file.wdata[0] @= s.recv_const.msg
        s.reg_file.wen[0] @= 1


    @update_ff
    def update_wr_cur():
      not_full = (s.wr_cur < const_mem_size)
      if s.reset:
        s.wr_cur <<= 0
      # Checks if there's a valid const (from producer) to be written.
      else:
        if s.recv_const.val & not_full:
          s.wr_cur <<= s.wr_cur + 1


    @update
    def update_send_val():
      # Checks if read cursor is in front of write cursor.
      if (zext(s.rd_cur, WrCurType) < s.wr_cur):
        s.send_const.val @= 1
      else:
        s.send_const.val @= 0


    @update_ff
    def update_rd_cur():
      if s.reset | s.clear:
        s.rd_cur <<= 0
      else:
        # Checks whether the "reader" successfully read the data at rd_cur,
        # and proceed rd_cur accordingly.
        if s.send_const.rdy & s.ctrl_proceed:
          if zext((s.rd_cur), WrCurType) < (s.wr_cur - 1):
            s.rd_cur <<= s.rd_cur + 1
          else:
            s.rd_cur <<= 0


  def line_trace(s, verbosity = 0):
    if verbosity == 0:
      const_mem_str  = "|".join([str(data) for data in s.reg_file.regs])
      return f'const_mem_str: {const_mem_str}'
    else:
      return s.verbose_trace(verbosity = verbosity)


  def verbose_trace(s, verbosity = 1):
    reg_list = []
    for addr, data in enumerate(s.reg_file.regs):
      reg_dict = {
        'addr': addr,
        'payload': data.payload,
        'predicate': data.predicate,
        'wr_cur': '<-' if addr == s.wr_cur else '',
        'rd_cur': '<-' if addr == s.rd_cur else ''
      }
      reg_list.append(reg_dict)
    res_md = markdown_table(reg_list).set_params(quote = False).get_markdown()
    return (f"wr_cur: {s.wr_cur}, rd_cur: {s.rd_cur}, send_const.val: {s.send_const.val}, send_const.rdy: {s.send_const.rdy}, send_const.msg: {s.send_const.msg}, ctrl_proceed: {s.ctrl_proceed}"
            f"{res_md}")

