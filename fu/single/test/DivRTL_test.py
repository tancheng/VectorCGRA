"""
==========================================================================
DivRTL_test.py
==========================================================================
Test cases for Divider.

Author : Jiajun Qin
  Date : May 2, 2025
"""

import pytest
import hypothesis
from hypothesis import strategies as st
from itertools import product
from pymtl3 import *
from ..DivRTL import DivRTL
from ....lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ....lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ....lib.opt_type import *
from ....lib.messages import *
from ....mem.const.ConstQueueRTL import ConstQueueRTL

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, FunctionUnit, DataType, PredicateType, ConfigType,
                num_inports, num_outports, data_mem_size,
                src0_msgs, src1_msgs, src_const, ctrl_msgs,
                sink_msgs):

    s.src_in0 = TestSrcRTL(DataType, src0_msgs)
    s.src_in1 = TestSrcRTL(DataType, src1_msgs)
    s.src_in2 = TestSrcRTL(DataType, src1_msgs)
    s.src_opt = TestSrcRTL(ConfigType, ctrl_msgs)
    s.sink_out = TestSinkRTL(DataType, sink_msgs)

    s.const_queue = ConstQueueRTL(DataType, src_const)
    s.dut = FunctionUnit(DataType, ConfigType,
                         num_inports, num_outports, data_mem_size)

    connect(s.src_in0.send, s.dut.recv_in[0])
    connect(s.src_in1.send, s.dut.recv_in[1])
    connect(s.src_in2.send, s.dut.recv_in[2])
    connect(s.dut.recv_const, s.const_queue.send_const)
    connect(s.src_opt.send, s.dut.recv_opt)
    connect(s.dut.send_out[0], s.sink_out.recv)

  def done(s):
    return s.src_in0.done() and s.src_in2.done() and \
           s.src_opt.done() and s.sink_out.done()

  def line_trace(s):
    return s.dut.line_trace()

def run_sim(test_harness, max_cycles = 20):
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
    print("{}:{}".format( ncycles, test_harness.line_trace()))

  # Check timeout
  assert ncycles < max_cycles

  test_harness.sim_tick()
  test_harness.sim_tick()
  test_harness.sim_tick()

@pytest.mark.parametrize(
  'input_a, input_b',
  product(range(5, 8), range(2, 4))
)
def test_div0(input_a, input_b):
  FU = DivRTL
  DataType = mk_data(32, 1)
  PredicateType = mk_predicate(1, 1)
  num_inports = 4
  num_outports = 2
  ConfigType = mk_ctrl(num_inports, num_outports)
  FuInType = mk_bits(clog2(num_inports + 1))
  data_mem_size = 8
  src_in0 =   [DataType(input_a, 1)]
  src_in1 =   [DataType(input_b, 1)]
  src_const = [DataType(0, 1) ]
  sink_out =  [DataType(input_a // input_b, 1)]
  src_opt =   [ConfigType(OPT_DIV,
               [FuInType(1), FuInType(3), FuInType(0), FuInType(0)])]
  th = TestHarness(FU, DataType, PredicateType, ConfigType,
                   num_inports, num_outports, data_mem_size,
                   src_in0, src_in1, src_const,
                   src_opt, sink_out)
  run_sim(th)

