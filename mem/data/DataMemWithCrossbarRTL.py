"""
==========================================================================
DataMemWithCrossbarRTL.py
==========================================================================
Data memory for CGRA. It has addtional port to connect to controller,
which can be used for multi-CGRA fabric. In addition, it contains a
crossbar to handle multi-bank conflicts.

Author : Cheng Tan
  Date : Dec 5, 2024
"""


from pymtl3 import *
from pymtl3.stdlib.primitive import RegisterFile
from ...lib.basic.en_rdy.ifcs import SendIfcRTL, RecvIfcRTL
from ...lib.opt_type import *


class DataMemWithCrossbarRTL(Component):

  def construct(s, DataType, data_mem_size_total, num_banks = 1,
                rd_ports_per_bank = 1, wr_ports_per_bank = 1,
                preload_data_per_bank = None):

    # Constant

    data_mem_size_per_bank = data_mem_size_total // num_banks
    AddrType = mk_bits(clog2(data_mem_size_per_bank))
    s.num_banks = num_banks

    # Interface

    s.recv_from_tile_raddr = [[RecvIfcRTL(AddrType) for _ in range(
        rd_ports_per_bank)] for _ in range(num_banks)]
    s.send_to_tile_rdata = [[SendIfcRTL(DataType) for _ in range(
        rd_ports_per_bank)] for _ in range(num_banks)]
    s.recv_from_tile_waddr = [[RecvIfcRTL(AddrType) for _ in range(
        wr_ports_per_bank)] for _ in range(num_banks)]
    s.recv_from_tile_wdata = [[RecvIfcRTL(DataType) for _ in range(
        wr_ports_per_bank)] for _ in range(num_banks)]

    s.recv_from_noc = RecvIfcRTL(DataType)
    s.send_to_noc = SendIfcRTL(DataType)

    # Component

    s.reg_file = [RegisterFile(DataType, data_mem_size_per_bank,
                               rd_ports_per_bank,
                               wr_ports_per_bank)
                  for _ in range(num_banks)]
    s.initWrites = [[Wire(b1) for _ in range(data_mem_size_per_bank)]
                    for _ in range(num_banks)]

    # FIXME: Following signals need to be set via some logic, i.e.,
    # handling miss accesses.
    s.send_to_noc.en //= 0
    s.send_to_noc.msg //= DataType(0, 0)
    s.recv_from_noc.rdy //= 0

    if preload_data_per_bank == None:
      @update
      def update_read_without_init():
        for b in num_banks:
          for i in range(rd_ports_per_bank):
            # s.reg_file.wen[wr_ports + i] @= b1(0)
            s.reg_file[b].raddr[i] @= s.recv_from_tile_raddr[b][i].msg
            s.send_to_tile_rdata[b][i].msg @= s.reg_file[b].rdata[i]

          for i in range(wr_ports_per_bank):
            s.reg_file[b].wen[i] @= b1(0)
            s.reg_file[b].waddr[i] @= s.recv_from_tile_waddr[b][i].msg
            s.reg_file[b].wdata[i] @= s.recv_from_tile_wdata[b][i].msg
            if s.recv_from_tile_waddr[b][i].en == b1(1):
              s.reg_file[b].wen[i] @= s.recv_from_tile_wdata[b][i].en & s.recv_from_tile_waddr[b][i].en

    else:
      s.preload_data_per_bank = [[Wire(DataType) for _ in range(data_mem_size_per_bank)]
                       for _ in range(num_banks)]
      for b in range(num_banks):
        for i in range(len(preload_data_per_bank[b])):
          s.preload_data_per_bank[b][i] //= preload_data_per_bank[b][i]

      @update
      def update_read_with_init():
        for b in range(num_banks):
          for i in range(rd_ports_per_bank):
            s.reg_file[b].wen[i] @= b1(0)
            # FIXME: xbar needs to be added between the regs and the requires.
            if s.initWrites[b][s.recv_from_tile_raddr[b][i].msg] == b1(0):
              s.send_to_tile_rdata[b][i].msg @= s.preload_data_per_bank[b][s.recv_from_tile_raddr[b][i].msg]
              s.reg_file[b].waddr[i] @= s.recv_from_tile_raddr[b][i].msg
              s.reg_file[b].wdata[i] @= s.preload_data_per_bank[b][s.recv_from_tile_raddr[b][i].msg]
              s.reg_file[b].wen[i] @= b1(1)
            else:
              s.reg_file[b].raddr[i] @= s.recv_from_tile_raddr[b][i].msg
              s.send_to_tile_rdata[b][i].msg @= s.reg_file[b].rdata[i]

          for i in range(wr_ports_per_bank):
            if s.recv_from_tile_waddr[b][i].en == b1(1):
              s.reg_file[b].waddr[i] @= s.recv_from_tile_waddr[b][i].msg
              s.reg_file[b].wdata[i] @= s.recv_from_tile_wdata[b][i].msg
              s.reg_file[b].wen[i] @= s.recv_from_tile_wdata[b][i].en & s.recv_from_tile_waddr[b][i].en

    @update_ff
    def update_init():
      for b in range(num_banks):
        for i in range(rd_ports_per_bank):
          if s.recv_from_tile_raddr[b][i].en == b1(1):
            s.initWrites[b][s.recv_from_tile_raddr[b][i].msg] <<= s.initWrites[b][s.recv_from_tile_raddr[b][i].msg] | b1(1)
        for i in range(wr_ports_per_bank):
          if s.recv_from_tile_waddr[b][i].en == b1(1):
            s.initWrites[b][s.recv_from_tile_waddr[b][i].msg] <<= s.initWrites[b][s.recv_from_tile_waddr[b][i].msg] | b1(1)

    @update
    def update_signal():
      for b in range(num_banks):
        for i in range(rd_ports_per_bank):
          s.recv_from_tile_raddr[b][i].rdy @= s.send_to_tile_rdata[b][i].rdy
          s.send_to_tile_rdata[b][i].en @= s.recv_from_tile_raddr[b][i].en
        for i in range(wr_ports_per_bank):
          s.recv_from_tile_waddr[b][i].rdy @= Bits1(1)
          s.recv_from_tile_wdata[b][i].rdy @= Bits1(1)


  def line_trace(s):
    recv_raddr_str = "recv_from_tile_read_addr: {"
    send_rdata_str = "send_to_tile_read_data: {"
    recv_waddr_str = "recv_from_tile_write_addr: {"
    recv_wdata_str = "recv_from_tile_write_data: {"
    content_str = "content: {"

    for b in range(s.num_banks):
      recv_raddr_str += " bank[" + str(b) + "]: " + "|".join([str(data.msg) for data in s.recv_from_tile_raddr[b]]) + ";"
      recv_waddr_str += " bank[" + str(b) + "]: " + "|".join([str(data.msg) for data in s.recv_from_tile_waddr[b]]) + ";"
      recv_wdata_str += " bank[" + str(b) + "]: " + "|".join([str(data.msg) for data in s.recv_from_tile_wdata[b]]) + ";"
      content_str +=  " bank[" + str(b) + "]: " + "|".join([str(data) for data in s.reg_file[b].regs]) + ";"
      send_rdata_str += " bank[" + str(b) + "]: " + "|".join([str(data.msg) for data in s.send_to_tile_rdata[b]]) + ";"

    recv_raddr_str += "}"
    send_rdata_str += "}"
    recv_waddr_str += "}"
    recv_wdata_str += "}"
    content_str += "}"

    return f'{recv_raddr_str} || {recv_waddr_str} || {recv_wdata_str} || [{content_str}] || {send_rdata_str}'

