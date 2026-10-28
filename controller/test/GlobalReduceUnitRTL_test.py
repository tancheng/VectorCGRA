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

  def construct(s, InterCgraPktType,
                input_count, input_data, expected_output):

    ControllerXbarPktType = mk_controller_noc_xbar_pkt(InterCgraPktType)
    s.src_count = TestSrcRTL(InterCgraPktType, input_count)
    s.src_data = TestSrcRTL(InterCgraPktType, input_data)

    s.sink = TestSinkRTL(ControllerXbarPktType, expected_output)

    s.dut = GlobalReduceUnitRTL(InterCgraPktType)

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

  th = TestHarness(InterCgraPktType,
                   input_count,
                   input_data,
                   expected_output)
  th.elaborate()
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)

#-------------------------------------------------------------------------
# Concurrent reductions, distinguished by payload.data_addr
#-------------------------------------------------------------------------

def mk_reduce_pkt_types():
  num_cgra_columns = 4
  num_cgra_rows = 1
  num_tiles = 4
  num_rd_tiles = 3
  ctrl_mem_size = 16
  data_mem_size_global = 16

  DataType = mk_data(32, 1)
  DataAddrType = mk_bits(clog2(data_mem_size_global))
  CtrlType = mk_ctrl(2, 2, 4, 4, 16)
  CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
  CgraPayloadType = mk_cgra_payload(DataType, DataAddrType, CtrlType,
                                    CtrlAddrType)
  InterCgraPktType = mk_inter_cgra_pkt(num_cgra_columns, num_cgra_rows,
                                       num_tiles, num_rd_tiles,
                                       CgraPayloadType)
  return DataType, CgraPayloadType, InterCgraPktType

def mk_count_pkt(InterCgraPktType, CgraPayloadType, DataType,
                 reduce_id, count):
  return InterCgraPktType(
      payload = CgraPayloadType(CMD_GLOBAL_REDUCE_COUNT,
                                data = DataType(count, 0, 0, 0),
                                data_addr = reduce_id))

def mk_partial_pkt(InterCgraPktType, CgraPayloadType, DataType,
                   cmd, reduce_id, src_cgra, src_tile, value):
  #                       src       dst src_x     src_y dst_x dst_y src_tile_id dst_tile_id
  return InterCgraPktType(src_cgra, 0,  src_cgra, 0,    0,    0,    src_tile,   0,
                          payload = CgraPayloadType(cmd,
                                                    data = DataType(value, 1, 0, 0),
                                                    data_addr = reduce_id))

def mk_response_pkt(InterCgraPktType, CgraPayloadType, DataType,
                    cmd, reduce_id, src_cgra, src_tile, value):
  ControllerXbarPktType = mk_controller_noc_xbar_pkt(InterCgraPktType)
  # The response goes back to the tile that sent the partial value.
  return ControllerXbarPktType(inter_cgra_pkt = InterCgraPktType(
      0, src_cgra, 0, 0, src_cgra, 0, 0, src_tile,
      payload = CgraPayloadType(cmd,
                                data = DataType(value, 1, 0, 0),
                                data_addr = reduce_id)))

def test_interleaved_reductions(cmdline_opts):
  DataType, CgraPayloadType, InterCgraPktType = mk_reduce_pkt_types()
  count = lambda *a: mk_count_pkt(InterCgraPktType, CgraPayloadType, DataType, *a)
  partial = lambda *a: mk_partial_pkt(InterCgraPktType, CgraPayloadType, DataType, *a)
  response = lambda *a: mk_response_pkt(InterCgraPktType, CgraPayloadType, DataType, *a)

  input_count = [count(0, 3), count(1, 3)]

  # Partial sums of reduction 0 (sumA) and reduction 1 (sumB) arrive interleaved.
  input_data = [
    # operation, reduction id (data_addr), src CGRA, src tile, value
    partial(CMD_GLOBAL_REDUCE_ADD, 0, 0, 1,  2),
    partial(CMD_GLOBAL_REDUCE_ADD, 1, 0, 2, 10),
    partial(CMD_GLOBAL_REDUCE_ADD, 0, 1, 1,  4),
    partial(CMD_GLOBAL_REDUCE_ADD, 1, 1, 2, 20),
    partial(CMD_GLOBAL_REDUCE_ADD, 0, 2, 1,  6),
    partial(CMD_GLOBAL_REDUCE_ADD, 1, 2, 2, 30),
  ]

  expected_output = [
    response(CMD_GLOBAL_REDUCE_ADD_RESPONSE, 0, 0, 1, 12),
    response(CMD_GLOBAL_REDUCE_ADD_RESPONSE, 0, 1, 1, 12),
    response(CMD_GLOBAL_REDUCE_ADD_RESPONSE, 0, 2, 1, 12),
    response(CMD_GLOBAL_REDUCE_ADD_RESPONSE, 1, 0, 2, 60),
    response(CMD_GLOBAL_REDUCE_ADD_RESPONSE, 1, 1, 2, 60),
    response(CMD_GLOBAL_REDUCE_ADD_RESPONSE, 1, 2, 2, 60),
  ]

  th = TestHarness(InterCgraPktType, input_count, input_data, expected_output)
  th.elaborate()
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)

def test_later_reduction_completes_first(cmdline_opts):
  DataType, CgraPayloadType, InterCgraPktType = mk_reduce_pkt_types()
  count = lambda *a: mk_count_pkt(InterCgraPktType, CgraPayloadType, DataType, *a)
  partial = lambda *a: mk_partial_pkt(InterCgraPktType, CgraPayloadType, DataType, *a)
  response = lambda *a: mk_response_pkt(InterCgraPktType, CgraPayloadType, DataType, *a)

  # Reduction 0 is an ADD over 3 CGRAs; reduction 3 is a MUL over 2 CGRAs
  # that collects all of its inputs before reduction 0 does.
  input_count = [count(0, 3), count(3, 2)]

  input_data = [
    # operation, reduction id (data_addr), src CGRA, src tile, value
    partial(CMD_GLOBAL_REDUCE_ADD, 0, 0, 1, 2),
    partial(CMD_GLOBAL_REDUCE_MUL, 3, 0, 3, 5),
    partial(CMD_GLOBAL_REDUCE_MUL, 3, 1, 3, 7),
    partial(CMD_GLOBAL_REDUCE_ADD, 0, 1, 1, 4),
    partial(CMD_GLOBAL_REDUCE_ADD, 0, 2, 1, 6),
  ]

  expected_output = [
    response(CMD_GLOBAL_REDUCE_MUL_RESPONSE, 3, 0, 3, 35),
    response(CMD_GLOBAL_REDUCE_MUL_RESPONSE, 3, 1, 3, 35),
    response(CMD_GLOBAL_REDUCE_ADD_RESPONSE, 0, 0, 1, 12),
    response(CMD_GLOBAL_REDUCE_ADD_RESPONSE, 0, 1, 1, 12),
    response(CMD_GLOBAL_REDUCE_ADD_RESPONSE, 0, 2, 1, 12),
  ]

  th = TestHarness(InterCgraPktType, input_count, input_data, expected_output)
  th.elaborate()
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)
