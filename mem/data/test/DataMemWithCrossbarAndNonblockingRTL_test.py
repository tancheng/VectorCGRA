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
from ..DataMemWithCrossbarAndNonblockingRTL import DataMemWithCrossbarAndNonblockingRTL
from ....lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ....lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ....lib.cmd_type import *
from ....lib.messages import *
from ....lib.opt_type import *

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, NocPktType, CgraPayloadType, DataType, NonblockingAddrType, NonblockingDataType,
                data_mem_size_global, data_mem_size_per_bank, num_banks,
                rd_tiles, wr_tiles, num_cgra_rows, num_cgra_columns,
                num_tiles,
                read_addr, read_data,
                noc_recv_load_data,
                preload_data_per_bank):

    s.num_banks = num_banks
    s.rd_tiles = rd_tiles
    s.wr_tiles = wr_tiles
    s.recv_raddr = [TestSrcRTL(NonblockingAddrType, read_addr[i])
                    for i in range(rd_tiles)]
    s.send_rdata = [TestSinkRTL(DataType, read_data[i])
                    for i in range(rd_tiles)]

    s.recv_from_noc_rdata = TestSrcRTL(NonblockingDataType, noc_recv_load_data)

    s.data_mem = DataMemWithCrossbarAndNonblockingRTL(NocPktType,
                                                      CgraPayloadType,
                                                      DataType,
                                                      NonblockingAddrType,
                                                      NonblockingDataType,
                                                      data_mem_size_global,
                                                      data_mem_size_per_bank,
                                                      num_banks, 
                                                      rd_tiles,
                                                      wr_tiles,
                                                      num_cgra_rows,
                                                      num_cgra_columns,
                                                      num_tiles,
                                                      preload_data_per_bank = preload_data_per_bank)

    for i in range(rd_tiles):
      s.data_mem.recv_raddr[i] //= s.recv_raddr[i].send
      s.data_mem.send_rdata[i] //= s.send_rdata[i].recv

    s.data_mem.recv_from_noc_rdata //= s.recv_from_noc_rdata.send

    s.data_mem.address_lower //= 0
    s.data_mem.address_upper //= 31

    s.cgra_id = 0

  def done(s):
    for i in range(s.rd_tiles):
      if not s.recv_raddr[i].done() or not s.send_rdata[i].done():
        return False

    if not s.recv_from_noc_rdata.done():
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
  kernel_id_nbits = 2 # 4 kernels
  ld_id_nbits = 5 # 32 load operations
  DataType = mk_data(data_nbits, predicate_nbits)
  NonblockingDataType = nb_data(data_nbits, predicate_nbits, kernel_id_nbits, ld_id_nbits)
  data_mem_size_global = 64
  data_mem_size_per_bank = 16
  num_banks = 2
  nterminals = 4

  num_registers_per_reg_bank = 16
  num_cgra_columns = 1
  num_cgra_rows = 1
  width = 2
  height = 2
  num_tiles = 4
  ctrl_mem_size = 6
  num_tile_inports  = 4
  num_tile_outports =4
  num_fu_inports = 4
  num_fu_outports = 2

  NonblockingAddrType = nb_addr(clog2(data_mem_size_global), kernel_id_nbits, ld_id_nbits)
  DataAddrType = mk_bits(clog2(data_mem_size_global))
  CtrlAddrType = mk_bits(clog2(ctrl_mem_size))

  CtrlType = mk_ctrl(num_fu_inports,
                     num_fu_outports,
                     num_tile_inports,
                     num_tile_outports,
                     num_registers_per_reg_bank)

  CgraPayloadType = mk_cgra_payload(DataType,
                                    DataAddrType,
                                    CtrlType,
                                    CtrlAddrType)

  InterCgraPktType = mk_inter_cgra_pkt(num_cgra_columns,
                                       num_cgra_rows,
                                       num_tiles,
                                       CgraPayloadType)

  IntraCgraPktType = mk_intra_cgra_pkt(num_cgra_columns,
                                       num_cgra_rows,
                                       num_tiles,
                                       CgraPayloadType)

  test_meta_data = [
      # addr:  0     1     2     3     4     5     6     7     8     9    10    11    12    13    14    15
           [0xa6, 0xa7, 0xa8, 0xa9, 0xb0, 0xb1, 0xb2, 0xb3, 0xb4, 0xb5, 0xb6, 0xb7, 0xb8, 0xb9, 0xc0, 0xc1],
      # addr: 16    17    18    19    20    21    22    23    24    25    26    27    28    29    30    31
           [0xc2, 0xc3, 0xc4, 0xc5, 0xc6, 0xc7, 0xc8, 0xc9, 0xd0, 0xd1, 0xd2, 0xd3, 0xd4, 0xd5, 0xd6, 0xd7]]

  preload_data_per_bank = [[DataType(test_meta_data[j][i], 1)
                            for i in range(data_mem_size_per_bank)]
                           for j in range(num_banks)]

  rd_tiles = 2
  wr_tiles = 2
  # Input data, two memory access addr 44 and  58, one is from kernel 1 ld 1, another is from kernel 2 ld 2.
  # NonblockingAddrType(addr, kernel_id, ld_id)
  read_addr = [
               #Cycle0, in range, miss        Cycle1, in range, hit     Cycle2, out of range, miss         Cycle3, out of range, hit      Cycle4, out of range, miss (data has been read out)
               [NonblockingAddrType(0, 1, 1), NonblockingAddrType(2, 0, 0), NonblockingAddrType(44, 1, 1), NonblockingAddrType(44, 1, 1), NonblockingAddrType(44, 1, 1)], # Bank 0
               [NonblockingAddrType(16, 2, 2), NonblockingAddrType(31, 0, 0), NonblockingAddrType(58, 2, 2), NonblockingAddrType(58, 2, 2), NonblockingAddrType(58, 2, 2)], # Bank 1
              ]
  
  # Expected.
  # DataType(data, predicate)
  read_data = [
               #Cycle0, miss         Cycle1, hit        Cycle2, miss,        Cycle3, hit          Cycle4, miss 
               [DataType(0xa6, 1), DataType(0xa8, 1), DataType(0x0000, 0), DataType(0xabcd, 1), DataType(0x0000, 0)],
               [DataType(0xc2, 1), DataType(0xd7, 1), DataType(0x0000, 0), DataType(0xdcba, 1), DataType(0x0000, 0)]
              ]

  # Input data, simulate noc behavior.
  # NonblockingDataType(data, predicate, kernel_id, ld_id)
  noc_recv_load_data = [
                        NonblockingDataType(0xffff, 0, 0, 0), # Cycle 0, nothing
                        NonblockingDataType(0xabcd, 1, 1, 1), # Cycle 1, assume remote access returns kernel 1 ld 1 at Cycle 1
                        NonblockingDataType(0xdcba, 1, 2, 2), # Cycle 2, assume remote access returns kernel 2 ld 2 at Cycle 2
                        NonblockingDataType(0xffff, 0, 0, 0), # Cycle 3, nothing
                        NonblockingDataType(0xffff, 0, 0, 0), # Cycle 4, nothing
                       ]

  th = TestHarness(InterCgraPktType,
                   CgraPayloadType,
                   DataType,
                   NonblockingAddrType,
                   NonblockingDataType,
                   data_mem_size_global,
                   data_mem_size_per_bank,
                   num_banks,
                   rd_tiles,
                   wr_tiles,
                   num_cgra_rows,
                   num_cgra_columns,
                   num_tiles,
                   read_addr,
                   read_data,
                   noc_recv_load_data,
                   preload_data_per_bank)

  th.elaborate()
  th.data_mem.set_metadata(VerilogTranslationPass.explicit_module_name,
                           f'DataMemWithCrossbarRTL_translation')
  th = config_model_with_cmdline_opts( th, cmdline_opts, duts=['data_mem'] )

  run_sim(th)

