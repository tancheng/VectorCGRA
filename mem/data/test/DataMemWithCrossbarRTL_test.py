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

  def construct(s, DataType, AddrType, data_mem_size_global,
                data_mem_size_per_bank, num_banks, rd_tiles, wr_tiles,
                read_addr, read_data, write_addr, write_data,
                noc_send_read_addr, noc_recv_read_data,
                noc_send_write_addr, noc_send_write_data,
                preload_data_per_bank):

    s.num_banks = num_banks
    s.rd_tiles = rd_tiles
    s.wr_tiles = wr_tiles
    s.recv_raddr = [TestSrcRTL(AddrType, read_addr[i])
                    for i in range(rd_tiles)]
    s.send_rdata = [TestSinkRTL(DataType, read_data[i])
                    for i in range(rd_tiles)]

    s.recv_waddr = [TestSrcRTL(AddrType, write_addr[i])
                    for i in range(wr_tiles)]
    s.recv_wdata = [TestSrcRTL(DataType, write_data[i])
                    for i in range(wr_tiles)]

    s.send_to_noc_raddr = TestSinkRTL(AddrType, noc_send_read_addr)
    s.recv_from_noc_rdata = TestSrcRTL(DataType, noc_recv_read_data)

    s.send_to_noc_waddr = TestSinkRTL(AddrType, noc_send_write_addr)
    s.send_to_noc_wdata = TestSinkRTL(DataType, noc_send_write_data)

    s.dataMem = DataMemWithCrossbarRTL(DataType, data_mem_size_global,
                                       data_mem_size_per_bank,
                                       num_banks, rd_tiles, wr_tiles,
                                       preload_data_per_bank)

    for i in range(rd_tiles):
      s.dataMem.recv_raddr[i] //= s.recv_raddr[i].send
      s.dataMem.send_rdata[i] //= s.send_rdata[i].recv

    for i in range(wr_tiles):
      s.dataMem.recv_waddr[i] //= s.recv_waddr[i].send
      s.dataMem.recv_wdata[i] //= s.recv_wdata[i].send

    s.dataMem.send_to_noc_raddr //= s.send_to_noc_raddr.recv
    s.dataMem.recv_from_noc_rdata //= s.recv_from_noc_rdata.send
    s.dataMem.send_to_noc_waddr //= s.send_to_noc_waddr.recv
    s.dataMem.send_to_noc_wdata //= s.send_to_noc_wdata.recv


  def done(s):
    for i in range(s.rd_tiles):
      if not s.recv_raddr[i].done() or not s.send_rdata[i].done():
        return False

    for i in range(s.wr_tiles):
      if not s.recv_waddr[i].done() or not s.recv_wdata[i].done():
        return False

    if not s.send_to_noc_raddr.done() or \
       not s.recv_from_noc_rdata.done() or \
       not s.send_to_noc_waddr.done() or \
       not s.send_to_noc_wdata.done():
      return False

    return True

  def line_trace(s):
    return s.dataMem.line_trace()


def run_sim(test_harness, max_cycles=40):
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
  data_mem_size_global = 50
  data_mem_size_per_bank = 20
  num_banks = 2
  AddrType = mk_bits(clog2(data_mem_size_global))

  test_meta_data = [
      # addr:  0     1     2     3     4     5     6     7     8     9    10    11    12    13    14    15    16    17    18    19  
           [0xa6, 0xa7, 0xa8, 0xa9, 0xb0, 0xb1, 0xb2, 0xb3, 0xb4, 0xb5, 0xb6, 0xb7, 0xb8, 0xb9, 0xc0, 0xc1, 0xc2, 0xc3, 0xc4, 0xc5],
      # addr: 20    21    22    23    24    25    26    27    28    29    30    31    32    33    34    35    36    37    38    39  
           [0xc2, 0xc3, 0xc4, 0xc5, 0xc6, 0xc7, 0xc8, 0xc9, 0xd0, 0xd1, 0xd2, 0xd3, 0xd4, 0xd5, 0xd6, 0xd7, 0xd8, 0xd9, 0xe0, 0xe1]]

  preload_data_per_bank = [[DataType(test_meta_data[j][i], 1)
                            for i in range(data_mem_size_per_bank)]
                           for j in range(num_banks)]

  rd_tiles = 4
  wr_tiles = 4
  # Input data.
  read_addr = [
               [AddrType(2), AddrType(33), AddrType(42), AddrType(3)],
               [AddrType(30), AddrType(33), AddrType(2)],
               [],
               [AddrType(2), AddrType(25)]
              ]
  # Expected.
  read_data = [
               [DataType(0xa8, 1), DataType(0xd5, 1), DataType(0xbbbb, 1), DataType(0xa9, 1)],
               [DataType(0xd2, 1), DataType(0xd50, 1), DataType(0xa800, 1)],
               [],
               [DataType(0xa80, 1), DataType(0xc7, 1)]
              ]
  # Input data.
  write_addr = [
                [AddrType(2), AddrType(45)],
                [AddrType(40), AddrType(33)],
                [AddrType(2)],
                []
               ]
  write_data = [
                [DataType(0xa80, 1), DataType(0xd545, 1)],
                [DataType(0xd040, 1), DataType(0xd50, 1)],
                [DataType(0xa800, 1)],
                []
               ]

  # Input data.
  noc_send_read_addr = [AddrType(42)]
  noc_recv_read_data = [DataType(0xbbbb, 1)]

  # Expected.
  noc_send_write_addr = [AddrType(40), AddrType(45)]
  noc_send_write_data = [DataType(0xd040, 1), DataType(0xd545, 1)]


  th = TestHarness(DataType, AddrType, data_mem_size_global, data_mem_size_per_bank,
                   num_banks, rd_tiles, wr_tiles, read_addr, read_data, write_addr,
                   write_data, noc_send_read_addr, noc_recv_read_data, noc_send_write_addr,
                   noc_send_write_data, preload_data_per_bank)
  run_sim(th)

