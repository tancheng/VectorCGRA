"""
==========================================================================
DataMemWithCrossbarRTL_test.py
==========================================================================
Test cases for DataMemWithCrossbarRTL.

Author : Cheng Tan
  Date : Dec 6, 2024
"""

from pymtl3 import *
from pymtl3.passes.backends.verilog import (VerilogTranslationPass,
                                            VerilogVerilatorImportPass)
from pymtl3.stdlib.test_utils import config_model_with_cmdline_opts
from ..DataMemWithCrossbarRTL import DataMemWithCrossbarRTL
from ....lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ....lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ....lib.cmd_type import *
from ....lib.messages import *
from ....lib.opt_type import *

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, NocPktType, DataType, AddrType, data_mem_size_global,
                data_mem_size_per_bank, num_banks, rd_tiles, wr_tiles,
                read_addr, read_data, write_addr, write_data,
                # noc_send_read_addr, noc_recv_read_data,
                # noc_send_write_addr, noc_send_write_data,
                noc_recv_load_data, send_to_noc_load_request_pkt,
                send_to_noc_store_pkt, preload_data_per_bank):

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

    s.recv_from_noc_rdata = TestSrcRTL(DataType, noc_recv_load_data)

    s.send_to_noc_load_request_pkt = TestSinkRTL(NocPktType, send_to_noc_load_request_pkt)
    s.send_to_noc_store_pkt = TestSinkRTL(NocPktType, send_to_noc_store_pkt)

    s.data_mem = DataMemWithCrossbarRTL(NocPktType, DataType,
                                        data_mem_size_global,
                                        data_mem_size_per_bank,
                                        num_banks, rd_tiles, wr_tiles,
                                        preload_data_per_bank)

    for i in range(rd_tiles):
      s.data_mem.recv_raddr[i] //= s.recv_raddr[i].send
      s.data_mem.send_rdata[i] //= s.send_rdata[i].recv

    for i in range(wr_tiles):
      s.data_mem.recv_waddr[i] //= s.recv_waddr[i].send
      s.data_mem.recv_wdata[i] //= s.recv_wdata[i].send

    s.data_mem.recv_from_noc_rdata //= s.recv_from_noc_rdata.send
    s.data_mem.send_to_noc_load_request_pkt //= s.send_to_noc_load_request_pkt.recv
    s.data_mem.send_to_noc_store_pkt //= s.send_to_noc_store_pkt.recv

  def done(s):
    for i in range(s.rd_tiles):
      if not s.recv_raddr[i].done() or not s.send_rdata[i].done():
        return False

    for i in range(s.wr_tiles):
      if not s.recv_waddr[i].done() or not s.recv_wdata[i].done():
        return False

    if not s.send_to_noc_load_request_pkt.done() or \
       not s.send_to_noc_store_pkt.done() or \
       not s.recv_from_noc_rdata.done():
      return False

    return True

  def line_trace(s):
    return s.data_mem.line_trace()

def run_sim(test_harness, max_cycles = 40):
  test_harness.apply(DefaultPassGroup())
  test_harness.sim_reset()

  # Run simulation

  ncycles = 0
  print()
  print("{}:{}".format(ncycles, test_harness.line_trace()))
  while not test_harness.done() and ncycles < max_cycles:
    test_harness.sim_tick()
    ncycles += 1
    print("{}:{}".format(ncycles, test_harness.line_trace()))

  # Check timeout
  assert ncycles < max_cycles

  test_harness.sim_tick()
  test_harness.sim_tick()
  test_harness.sim_tick()

def test_const_queue(cmdline_opts):
  data_nbits = 32
  predicate_nbits = 1
  DataType = mk_data(data_nbits, predicate_nbits)
  data_mem_size_global = 64
  data_mem_size_per_bank = 16
  num_banks = 2
  nterminals = 4
  addr_nbits = clog2(data_mem_size_global)
  AddrType = mk_bits(addr_nbits)

  width = 2
  height = 2
  num_terminals = 4
  num_ctrl_actions = 64
  num_ctrl_operations = 64
  ctrl_mem_size = 6
  num_tile_inports  = 4
  num_tile_outports =4
  num_fu_inports = 4
  num_fu_outports = 2
  NocPktType = mk_multi_cgra_noc_pkt(ncols = num_terminals,
                                     nrows = 1,
                                     ntiles = width * height,
                                     addr_nbits = addr_nbits,
                                     data_nbits = data_nbits,
                                     predicate_nbits = 1,
                                     ctrl_actions = num_ctrl_actions,
                                     ctrl_mem_size = ctrl_mem_size,
                                     ctrl_operations = num_ctrl_operations,
                                     ctrl_fu_inports = num_fu_inports,
                                     ctrl_fu_outports = num_fu_outports,
                                     ctrl_tile_inports = num_tile_inports,
                                     ctrl_tile_outports = num_tile_outports)


  test_meta_data = [
      # addr:  0     1     2     3     4     5     6     7     8     9    10    11    12    13    14    15
           [0xa6, 0xa7, 0xa8, 0xa9, 0xb0, 0xb1, 0xb2, 0xb3, 0xb4, 0xb5, 0xb6, 0xb7, 0xb8, 0xb9, 0xc0, 0xc1],
      # addr: 16    17    18    19    20    21    22    23    24    25    26    27    28    29    30    31
           [0xc2, 0xc3, 0xc4, 0xc5, 0xc6, 0xc7, 0xc8, 0xc9, 0xd0, 0xd1, 0xd2, 0xd3, 0xd4, 0xd5, 0xd6, 0xd7]]

  preload_data_per_bank = [[DataType(test_meta_data[j][i], 1)
                            for i in range(data_mem_size_per_bank)]
                           for j in range(num_banks)]

  rd_tiles = 4
  wr_tiles = 4
  # Input data.
  read_addr = [
               [AddrType(2), AddrType(31), AddrType(42), AddrType(3)],
               [AddrType(30), AddrType(31), AddrType(2)],
               [],
               [AddrType(2), AddrType(25)]
              ]
  # Expected.
  read_data = [
               [DataType(0xa8, 1), DataType(0xd7, 1), DataType(0xbbbb, 1), DataType(0xa9, 1)],
               [DataType(0xd6, 1), DataType(0xd70, 1), DataType(0xa800, 1)],
               [],
               [DataType(0xa80, 1), DataType(0xd1, 1)]
              ]
  # Input data.
  write_addr = [
                [AddrType(2), AddrType(45)],
                [AddrType(40), AddrType(31)],
                [AddrType(2)],
                []
               ]
  write_data = [
                [DataType(0xa80, 1), DataType(0xd545, 1)],
                [DataType(0xd040, 1), DataType(0xd70, 1)],
                [DataType(0xa800, 1)],
                []
               ]

  # Input data.
  # noc_send_read_addr = [AddrType(42)]
  send_to_noc_load_request_pkt = [
             #   src  dst src_x src_y dst_x dst_y dst_tile_id opq vc  addr data predicate payload ctrl_action
      NocPktType(0,   0,  0,    0,    0,    0,    0,          0,  0,  42,  0,   1,        0,      CMD_LOAD_REQUEST),
  ]
  noc_recv_load_data = [DataType(0xbbbb, 1)]

  # Expected.
  # noc_send_write_addr = [AddrType(40), AddrType(45)]
  # noc_send_write_data = [DataType(0xd040, 1), DataType(0xd545, 1)]
  send_to_noc_store_pkt = [
             #   src  dst src_x src_y dst_x dst_y dst_tile_id opq vc addr data    predicate payload ctrl_action
      NocPktType(0,   0,  0,    0,    0,    0,    0,          0,  0, 40,  0xd040, 1,        0,      CMD_STORE_REQUEST),
      NocPktType(0,   0,  0,    0,    0,    0,    0,          0,  0, 45,  0xd545, 1,        0,      CMD_STORE_REQUEST),
  ]

  th = TestHarness(NocPktType, DataType, AddrType, data_mem_size_global,
                   data_mem_size_per_bank, num_banks, rd_tiles, wr_tiles,
                   read_addr, read_data, write_addr, write_data,
                   noc_recv_load_data,
                   send_to_noc_load_request_pkt, send_to_noc_store_pkt,
                   preload_data_per_bank)
                   # noc_send_read_addr, noc_recv_read_data, noc_send_write_addr,
                   # noc_send_write_data, preload_data_per_bank)

  th.elaborate()
  th.data_mem.set_metadata(VerilogTranslationPass.explicit_module_name,
                           f'DataMemWithCrossbarRTL_translation')
  th = config_model_with_cmdline_opts( th, cmdline_opts, duts=['data_mem'] )

  run_sim(th)

