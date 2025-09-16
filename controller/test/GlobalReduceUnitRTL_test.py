'''
=========================================================================
GlobalReduceUnitRTL_test.py
=========================================================================
Simple test for GlobalReduceUnitRTL.

Author : Cheng Tan
  Date : Sep 8, 2025
'''

from pymtl3.stdlib.test_utils import config_model_with_cmdline_opts

from ..GlobalReduceUnitRTL import GlobalReduceUnitRTL
from ...lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ...lib.cmd_type import *
from ...lib.messages import *
from ...lib.opt_type import *

#-------------------------------------------------------------------------
# TestHarness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, DataType, InterCgraPktType, ControllerXbarPktType,
                input_count, input_data, expected_output):

    s.src_count = TestSrcRTL(InterCgraPktType, input_count)
    s.src_data = TestSrcRTL(InterCgraPktType, input_data)

    s.sink = TestSinkRTL(ControllerXbarPktType, expected_output)

    s.dut = GlobalReduceUnitRTL(DataType,
                                InterCgraPktType,
                                ControllerXbarPktType)

    # Connections
    s.dut.recv_count //= s.src_count.send
    s.dut.recv_data //= s.src_data.send
    s.dut.send //= s.sink.recv

  def done(s):
    return s.src_count.done()  and \
           s.src_data.done() and \
           s.sink.done()

  def line_trace(s):
    return s.dut.line_trace()

#-------------------------------------------------------------------------
# run_rtl_sim
#-------------------------------------------------------------------------

def run_sim(test_harness, max_cycles = 100):

  # Creates a simulator.
  test_harness.elaborate()
  test_harness.apply(DefaultPassGroup())
  test_harness.sim_reset()

  # Runs simulation.
  ncycles = 0
  print()
  print("{}:{}".format(ncycles, test_harness.line_trace()))
  while not test_harness.done() and ncycles < max_cycles:
    test_harness.sim_tick()
    ncycles += 1
    print("{}:{}".format(ncycles, test_harness.line_trace()))

  # Checks timeout.
  assert ncycles < max_cycles

  test_harness.sim_tick()
  test_harness.sim_tick()
  test_harness.sim_tick()

#-------------------------------------------------------------------------
# Test cases
#-------------------------------------------------------------------------

def test_simple(cmdline_opts):
  data_nbits = 32
  predicate_nbits = 1

  num_cgra_columns = 4
  num_cgra_rows = 1
  num_cgras = num_cgra_columns * num_cgra_rows
  num_tiles = 4
  num_rd_tiles = 3
  cgra_id_nbits = clog2(num_cgras)
  ControllerIdType = mk_bits(cgra_id_nbits)
  ctrl_mem_size = 16
  num_fu_inports = 2
  num_fu_outports = 2
  num_tile_inports = 4
  num_tile_outports = 4
  data_mem_size_global = 16
  addr_nbits = clog2(data_mem_size_global)
  num_registers_per_reg_bank = 16
  cgra_id = 0

  idTo2d_map = {
          0: [0, 0],
          1: [1, 0],
          2: [2, 0],
          3: [3, 0]
  }

  controller2addr_map = {
          0: [0, 3],
          1: [4, 7],
          2: [8, 11],
          3: [12, 15],
  }

  DataType = mk_data(data_nbits, predicate_nbits)
  DataAddrType = mk_bits(addr_nbits)
  
  CtrlType = mk_ctrl(num_fu_inports,
                  num_fu_outports,
                  num_tile_inports,
                  num_tile_outports,
                  num_registers_per_reg_bank)

  CtrlAddrType = mk_bits(clog2(ctrl_mem_size))

  CgraPayloadType = mk_cgra_payload(DataType,
                                    DataAddrType,
                                    CtrlType,
                                    CtrlAddrType)

  InterCgraPktType = mk_inter_cgra_pkt(num_cgra_columns,
                                       num_cgra_rows,
                                       num_tiles,
                                       num_rd_tiles,
                                       CgraPayloadType)

  ControllerXbarPktType = mk_controller_noc_xbar_pkt(InterCgraPktType)

  input_count = [
    InterCgraPktType(payload = CgraPayloadType(CMD_GLOBAL_REDUCE_COUNT, data = DataType(3, 0, 0, 0))),
  ]

  input_data = [
                   # src dst src_x src_y dst_x dst_y src_tile_id dst_tile_id
    InterCgraPktType(0, 0, 0, 0, 0, 0, 0, 0, payload = CgraPayloadType(CMD_GLOBAL_REDUCE_ADD,   data = DataType(2, 1, 0, 0))),
    InterCgraPktType(0, 1, 0, 0, 1, 0, 2, 4, payload = CgraPayloadType(CMD_GLOBAL_REDUCE_ADD,   data = DataType(4, 1, 0, 0))),
    InterCgraPktType(0, 2, 0, 0, 2, 0, 3, 4, payload = CgraPayloadType(CMD_GLOBAL_REDUCE_ADD,   data = DataType(6, 1, 0, 0))),
    InterCgraPktType(0, 0, 0, 0, 0, 0, 0, 0, payload = CgraPayloadType(CMD_GLOBAL_REDUCE_ADD,   data = DataType(3, 1, 0, 0))),
    InterCgraPktType(0, 1, 0, 0, 1, 0, 2, 4, payload = CgraPayloadType(CMD_GLOBAL_REDUCE_ADD,   data = DataType(5, 1, 0, 0))),
    InterCgraPktType(0, 2, 0, 0, 2, 0, 3, 4, payload = CgraPayloadType(CMD_GLOBAL_REDUCE_ADD,   data = DataType(7, 1, 0, 0))),
    InterCgraPktType(0, 0, 0, 0, 0, 0, 0, 0, payload = CgraPayloadType(CMD_GLOBAL_REDUCE_MUL,   data = DataType(3, 1, 0, 0))),
    InterCgraPktType(0, 1, 0, 0, 1, 0, 2, 4, payload = CgraPayloadType(CMD_GLOBAL_REDUCE_MUL,   data = DataType(5, 1, 0, 0))),
    InterCgraPktType(0, 2, 0, 0, 2, 0, 3, 4, payload = CgraPayloadType(CMD_GLOBAL_REDUCE_MUL,   data = DataType(7, 1, 0, 0))),
  ]

  expected_output = [
                                                          # Reversed src/dst.
    ControllerXbarPktType(inter_cgra_pkt = InterCgraPktType(0, 0, 0, 0, 0, 0, 0, 0, payload = CgraPayloadType(CMD_GLOBAL_REDUCE_ADD_RESPONSE, data = DataType(12,  1, 0, 0)))),
    ControllerXbarPktType(inter_cgra_pkt = InterCgraPktType(1, 0, 1, 0, 0, 0, 4, 2, payload = CgraPayloadType(CMD_GLOBAL_REDUCE_ADD_RESPONSE, data = DataType(12,  1, 0, 0)))),
    ControllerXbarPktType(inter_cgra_pkt = InterCgraPktType(2, 0, 2, 0, 0, 0, 4, 3, payload = CgraPayloadType(CMD_GLOBAL_REDUCE_ADD_RESPONSE, data = DataType(12,  1, 0, 0)))),
    ControllerXbarPktType(inter_cgra_pkt = InterCgraPktType(0, 0, 0, 0, 0, 0, 0, 0, payload = CgraPayloadType(CMD_GLOBAL_REDUCE_ADD_RESPONSE, data = DataType(15,  1, 0, 0)))),
    ControllerXbarPktType(inter_cgra_pkt = InterCgraPktType(1, 0, 1, 0, 0, 0, 4, 2, payload = CgraPayloadType(CMD_GLOBAL_REDUCE_ADD_RESPONSE, data = DataType(15,  1, 0, 0)))),
    ControllerXbarPktType(inter_cgra_pkt = InterCgraPktType(2, 0, 2, 0, 0, 0, 4, 3, payload = CgraPayloadType(CMD_GLOBAL_REDUCE_ADD_RESPONSE, data = DataType(15,  1, 0, 0)))),
    ControllerXbarPktType(inter_cgra_pkt = InterCgraPktType(0, 0, 0, 0, 0, 0, 0, 0, payload = CgraPayloadType(CMD_GLOBAL_REDUCE_MUL_RESPONSE, data = DataType(105, 1, 0, 0)))),
    ControllerXbarPktType(inter_cgra_pkt = InterCgraPktType(1, 0, 1, 0, 0, 0, 4, 2, payload = CgraPayloadType(CMD_GLOBAL_REDUCE_MUL_RESPONSE, data = DataType(105, 1, 0, 0)))),
    ControllerXbarPktType(inter_cgra_pkt = InterCgraPktType(2, 0, 2, 0, 0, 0, 4, 3, payload = CgraPayloadType(CMD_GLOBAL_REDUCE_MUL_RESPONSE, data = DataType(105, 1, 0, 0)))),
  ]

  th = TestHarness(DataType,
                   InterCgraPktType,
                   ControllerXbarPktType,
                   input_count,
                   input_data,
                   expected_output)
  th.elaborate()
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)
