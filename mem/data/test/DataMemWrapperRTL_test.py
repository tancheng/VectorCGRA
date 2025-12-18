"""
==========================================================================
DataMemWrapperRTL_test.py
==========================================================================
Test cases for DataMemWrapperRTL.

Author : Cheng Tan
  Date : Aug 28, 2025
"""

from pymtl3 import *
from ..DataMemWrapperRTL import DataMemWrapperRTL
from ....lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ....lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ....lib.messages import *
from ....lib.opt_type import *
from pymtl3.stdlib.test_utils import (run_sim, config_model_with_cmdline_opts)

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, DataType, MemReadType, MemWriteType, MemResponseType,
                global_data_mem_size, per_bank_data_mem_size,
                mem_rd_request, mem_wr_request, mem_response):

    s.mem_rd_request = TestSrcRTL(MemReadType, mem_rd_request)
    s.mem_wr_request = TestSrcRTL(MemWriteType, mem_wr_request)

    s.mem_response = TestSinkRTL(MemResponseType, mem_response)

    s.data_mem_wrapper = DataMemWrapperRTL(DataType,
                                           MemReadType,
                                           MemWriteType,
                                           MemResponseType,
                                           global_data_mem_size,
                                           per_bank_data_mem_size,
                                           False)

    s.data_mem_wrapper.recv_rd //= s.mem_rd_request.send
    s.data_mem_wrapper.recv_wr //= s.mem_wr_request.send
    s.data_mem_wrapper.send //= s.mem_response.recv

  def done(s):
    return s.mem_rd_request.done() and s.mem_wr_request.done() and s.mem_response.done()

  def line_trace(s):
    return s.data_mem_wrapper.line_trace()

def run_sim(test_harness, max_cycles = 30):
  test_harness.elaborate()
  test_harness.apply(DefaultPassGroup())
  test_harness.sim_reset()

  # Run simulation
  ncycles = 0
  print()
  print("{}:{}".format( ncycles, test_harness.line_trace()))
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
  global_data_mem_size = 32
  per_bank_data_mem_size = 8
  rd_tiles = 4
  wr_tiles = 4
  rd_banks = 4
  wr_banks = 4
  num_cgras = 4
  num_tiles = 4

  MemReadType = mk_mem_access_pkt(DataType, rd_tiles, rd_banks, global_data_mem_size, num_cgras, num_tiles)
  MemWriteType = mk_mem_access_pkt(DataType, wr_tiles, wr_banks, global_data_mem_size, num_cgras, num_tiles)
  # Reverses the source and destination for response packet.
  MemResponseType = mk_mem_access_pkt(DataType, rd_banks, rd_tiles, global_data_mem_size, num_cgras, num_tiles)

                                     # dst addr data
  mem_wr_request = [MemWriteType   (0, 0,  2,   DataType(0xc, 1), 0, 0, 0),
                    MemWriteType   (0, 0,  4,   DataType(0xb, 1), 0, 0, 0),
                    MemWriteType   (0, 0,  6,   DataType(0xa, 1), 0, 0, 0)
                   ]
  mem_rd_request = [MemReadType    (0, 1,  6,   DataType(0x0, 0), 0, 0, 0),
                    MemReadType    (0, 2,  6,   DataType(0x0, 0), 0, 0, 0),
                    MemReadType    (0, 3,  6,   DataType(0x0, 0), 0, 0, 0),
                    MemReadType    (0, 1,  6,   DataType(0x0, 0), 0, 0, 0),
                    MemReadType    (0, 2,  4,   DataType(0x0, 0), 0, 0, 0),
                    MemReadType    (0, 3,  2,   DataType(0x0, 0), 0, 0, 3)
                   ]
  mem_response =   [MemResponseType(1, 0,  6,   DataType(0x0, 0), 0, 0, 0),
                    MemResponseType(2, 0,  6,   DataType(0x0, 0), 0, 0, 0),
                    MemResponseType(3, 0,  6,   DataType(0x0, 0), 0, 0, 0),
                    MemResponseType(1, 0,  6,   DataType(0xa, 1), 0, 0, 0),
                    MemResponseType(2, 0,  4,   DataType(0xb, 1), 0, 0, 0),
                    MemResponseType(3, 0,  2,   DataType(0xc, 1), 0, 0, 3)
                   ]

  th = TestHarness(DataType, MemReadType, MemWriteType, MemResponseType,
                   global_data_mem_size, per_bank_data_mem_size,
                   mem_rd_request, mem_wr_request, mem_response)
  run_sim(th)

def test_streaming_read(cmdline_opts):
  DataType = mk_data(16, 1)
  global_data_mem_size = 32
  per_bank_data_mem_size = 8
  rd_tiles = 4
  wr_tiles = 4
  rd_banks = 4
  wr_banks = 4
  num_cgras = 4
  num_tiles = 4

  MemReadType = mk_mem_access_pkt(DataType, rd_tiles, rd_banks, global_data_mem_size, num_cgras, num_tiles)
  MemWriteType = mk_mem_access_pkt(DataType, wr_tiles, wr_banks, global_data_mem_size, num_cgras, num_tiles)
  # Reverses the source and destination for response packet.
  MemResponseType = mk_mem_access_pkt(DataType, rd_banks, rd_tiles, global_data_mem_size, num_cgras, num_tiles)

                                     # dst addr data
  mem_wr_request = [MemWriteType   (0, 0,  2,   DataType(0xc, 1), 0, 0, 0),
                    MemWriteType   (0, 0,  4,   DataType(0xb, 1), 0, 0, 0),
                    MemWriteType   (0, 0,  6,   DataType(0xa, 1), 0, 0, 0)
                   ]      

  mem_rd_request = [# Waiting for wr requests to complete
                    MemReadType    (0, 1,  6,   DataType(0x0, 0), 0, 0, 0),
                    MemReadType    (0, 2,  6,   DataType(0x0, 0), 0, 0, 0),
                    MemReadType    (0, 3,  6,   DataType(0x0, 0), 0, 0, 0),
                    # Sends a streaming read request.
                                                                         # streaming, stride, end_addr
                    MemReadType    (0, 1,  2,   DataType(0x0, 0), 0, 0, 0, 1,         2,      6)]

  mem_response =   [MemResponseType(1, 0,  6,   DataType(0x0, 0), 0, 0, 0),
                    MemResponseType(2, 0,  6,   DataType(0x0, 0), 0, 0, 0),
                    MemResponseType(3, 0,  6,   DataType(0x0, 0), 0, 0, 0),
                    # Streaming results. One streaming request has multiple responses.
                    MemResponseType(1, 0,  2,   DataType(0xc, 1), 0, 0, 0),
                    MemResponseType(1, 0,  4,   DataType(0xb, 1), 0, 0, 0),
                    MemResponseType(1, 0,  6,   DataType(0xa, 1), 0, 0, 0)
                   ]

  th = TestHarness(DataType, MemReadType, MemWriteType, MemResponseType,
                   global_data_mem_size, per_bank_data_mem_size,
                   mem_rd_request, mem_wr_request, mem_response)
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['data_mem_wrapper', 'mem_response'])
  run_sim(th)

