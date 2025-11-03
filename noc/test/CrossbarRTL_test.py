"""
==========================================================================
CrossbarRTL_test.py
==========================================================================
Test cases for Crossbar.

Author : Cheng Tan
  Date : Dec 9, 2019

"""

from pymtl3 import *
from ..CrossbarRTL import CrossbarRTL
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ...lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ...lib.opt_type import *
from ...lib.messages import *

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, CrossbarUnit, DataType, PredicateType, CtrlType,
                num_inports, num_outports, src_data, src_routing,
                sink_out):

    num_tiles = 1
    ctrl_mem_size = 6
    s.num_inports  = num_inports
    s.num_outports = num_outports

    s.src_opt = TestSrcRTL(CtrlType, src_routing)
    s.src_data = [TestSrcRTL(DataType, src_data[i])
                  for i in range(num_inports)]
    s.sink_out = [TestSinkRTL(DataType, sink_out[i])
                  for i in range(num_outports)]

    s.dut = CrossbarUnit(DataType, CtrlType, num_inports,
                         num_outports, num_tiles, ctrl_mem_size)

    for i in range(num_inports):
      s.src_data[i].send //= s.dut.recv_data[i]
      s.dut.send_data[i] //= s.sink_out[i].recv
      for addr in range(ctrl_mem_size):
        s.dut.prologue_count_inport[addr][i] //= 0
    s.src_opt.send //= s.dut.recv_opt

    for i in range(num_outports):
      s.dut.crossbar_outport[i] //= s.src_opt.send.msg.routing_xbar_outport[i]

  def done(s):
    done = True
    for i in range(s.num_inports):
      if not s.src_data[i].done():
        done = False
        break
    for i in range(s.num_outports):
      if not s.sink_out[i].done():
        done = False
        break
    return done

  def line_trace(s):
    return s.dut.line_trace()

def run_sim(test_harness, max_cycles = 20):
  test_harness.elaborate()
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

FU = CrossbarRTL
num_fu_inports = 2
num_fu_outports = 2
num_tile_inports = 3
num_tile_outports = 1
num_routing_outports = num_fu_inports + num_tile_outports
num_ctrl_operations = 64
TileInType = mk_bits(clog2(num_tile_inports + 1))
FuInType = mk_bits(clog2(num_fu_inports + 1))
FuOutType = mk_bits(clog2(num_fu_outports + 1))
DataType = mk_data(16, 1)
PredicateType = mk_predicate(1, 1)
CtrlType = mk_ctrl(num_fu_inports,
                   num_fu_outports,
                   num_tile_inports,
                   num_tile_outports)
pickRegister = [FuInType(x + 1) for x in range(num_fu_inports)]

def test_crossbar():
  src_opt  = [CtrlType(OPT_ADD, pickRegister,
                       # routing_xbar_output
                       [TileInType(2), TileInType(3), TileInType(1)],
                       # fu_xbar_output
                       [FuOutType(0),  FuOutType(0),  FuOutType(0)])]
  src_data = [[DataType(3, 1)], [DataType(2, 1)], [DataType(9, 1)]]
  sink_out = [[DataType(2, 1)], [DataType(9, 1)], [DataType(3, 1)]]
  th = TestHarness(FU, DataType, PredicateType, CtrlType, num_tile_inports,
                   num_routing_outports, src_data, src_opt, sink_out)
  run_sim(th)

def test_multi_cast():
  src_opt  = [CtrlType(OPT_ADD, pickRegister,
                       # routing_xbar_output
                       [TileInType(2), TileInType(1), TileInType(1)],
                       # fu_xbar_output
                       [FuOutType(0),  FuOutType(0),  FuOutType(0)]),
              CtrlType(OPT_NAH, pickRegister,
                       # routing_xbar_output
                       [TileInType(0), TileInType(0), TileInType(3)],
                       # fu_xbar_output
                       [FuOutType(0),  FuOutType(0),  FuOutType(0)])]
  src_data      = [[DataType(3, 1)], [DataType(2, 1)], [DataType(9, 1)]]
  sink_out      = [[DataType(2, 1)], [DataType(3, 1)], [DataType(3, 1), DataType(9, 1)]]
  th = TestHarness(FU, DataType, PredicateType, CtrlType, num_tile_inports,
                   num_routing_outports, src_data, src_opt, sink_out)
  run_sim(th)

