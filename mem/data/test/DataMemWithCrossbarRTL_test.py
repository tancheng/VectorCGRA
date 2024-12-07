"""
==========================================================================
DataMemScalableRTL_test.py
==========================================================================
Test cases for DataMemScalableRTL.

Author : Cheng Tan
  Date : Dec 6, 2024
"""


from pymtl3 import *
from ..DataMemWithCrossbarRTL import DataMemWithCrossbarRTL
from ....lib.basic.en_rdy.test_sinks import TestSinkRTL
from ....lib.basic.en_rdy.test_srcs import TestSrcRTL
from ....lib.messages import *
from ....lib.opt_type import *


#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness( Component ):

  def construct(s, DataType, AddrType, data_mem_size_total, num_banks,
                rd_ports_per_bank, wr_ports_per_bank, read_addr,
                read_data, write_addr, write_data, preload_data_per_bank):

    s.num_banks = num_banks
    s.rd_ports_per_bank = rd_ports_per_bank
    s.wr_ports_per_bank = wr_ports_per_bank
    s.recv_read_addr = [[TestSrcRTL(AddrType, read_addr[b][i])
                         for i in range(rd_ports_per_bank)]
                        for b in range(num_banks)]
    s.send_read_data = [[TestSinkRTL(DataType, read_data[b][i])
                         for i in range(rd_ports_per_bank)]
                        for b in range(num_banks)]

    s.recv_write_addr = [[TestSrcRTL(AddrType, write_addr[b][i])
                          for i in range(wr_ports_per_bank)]
                         for b in range(num_banks)]
    s.recv_write_data = [[TestSrcRTL(DataType, write_data[b][i])
                         for i in range(wr_ports_per_bank)]
                        for b in range(num_banks)]

    s.dataMem = DataMemWithCrossbarRTL(DataType, data_mem_size_total,
                                       num_banks, rd_ports_per_bank,
                                       wr_ports_per_bank,
                                       preload_data_per_bank)

    for b in range(num_banks):
      for i in range(rd_ports_per_bank):
        s.dataMem.recv_from_tile_raddr[b][i] //= s.recv_read_addr[b][i].send
        s.dataMem.send_to_tile_rdata[b][i] //= s.send_read_data[b][i].recv

    for b in range(num_banks):
      for i in range(wr_ports_per_bank):
        s.dataMem.recv_from_tile_waddr[b][i] //= s.recv_write_addr[b][i].send
        s.dataMem.recv_from_tile_wdata[b][i] //= s.recv_write_data[b][i].send

  def done(s):
    for b in range(s.num_banks):
      for i in range(s.rd_ports_per_bank):
        if not s.recv_read_addr[b][i].done() or not s.send_read_data[b][i].done():
          return False

    for b in range(s.num_banks):
      for i in range(s.wr_ports_per_bank):
        if not s.recv_write_addr[b][i].done() or not s.recv_write_data[b][i].done():
          return False

    return True

  def line_trace(s):
    return s.dataMem.line_trace()


def run_sim(test_harness, max_cycles=20):
  test_harness.elaborate()
  test_harness.apply(DefaultPassGroup())
  test_harness.sim_reset()

  # Run simulation

  ncycles = 0
  print()
  print( "{}:{}".format(ncycles, test_harness.line_trace()))
  while not test_harness.done() and ncycles < max_cycles:
    test_harness.sim_tick()
    ncycles += 1
    print("{}:{}".format(ncycles, test_harness.line_trace()))

  # Check timeout

  assert ncycles < max_cycles

  test_harness.sim_tick()
  test_harness.sim_tick()
  test_harness.sim_tick()

def test_const_queue():
  DataType = mk_data(16, 1)
  data_mem_size_per_bank = 20
  num_banks = 2
  data_mem_size_total = data_mem_size_per_bank * num_banks
  AddrType = mk_bits(clog2(data_mem_size_per_bank))
  preload_data_per_bank = [[DataType(i, 1)
                            for i in range(data_mem_size_per_bank)]
                           for _ in range(num_banks)]

  rd_ports_per_bank = 2
  wr_ports_per_bank = 2
  read_addr = [[[AddrType(2), AddrType(2), AddrType(2), AddrType(12), AddrType(12), AddrType(13)]
                for _ in range(rd_ports_per_bank)]
               for _ in range(num_banks)]
  read_data = [[[DataType(2, 1), DataType(9, 1), DataType(8, 1), DataType(12, 1), DataType(13, 1), DataType(14, 1)]
                for _ in range(rd_ports_per_bank)]
               for _ in range(num_banks)]

  write_addr = [[[AddrType(2), AddrType(2), AddrType(13), AddrType(12)]
                 for _ in range(rd_ports_per_bank)]
                for _ in range(num_banks)]
  write_data = [[[DataType(9, 1), DataType(8, 1), DataType(14, 1), DataType(13, 1)]
                 for _ in range(rd_ports_per_bank)]
                for _ in range(num_banks)]

  th = TestHarness(DataType, AddrType, data_mem_size_total, num_banks,
                   rd_ports_per_bank, wr_ports_per_bank,
                   read_addr, read_data, write_addr, write_data,
                   preload_data_per_bank)
  run_sim(th)
