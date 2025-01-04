"""
==========================================================================
CompRTL_test.py
==========================================================================
Test cases for functional unit Comp.

Author : Cheng Tan
  Date : November 27, 2019
"""

from pymtl3 import *
from ..CompRTL import CompRTL
from ....lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ....lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ....lib.messages import *
from ....lib.opt_type import *

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, FunctionUnit, DataType, PredicateType, CtrlType,
                num_inports, num_outports, data_mem_size, src_data,
                src_ref, src_predicate, src_opt, sink_msgs):

    s.src_data = TestSrcRTL(DataType, src_data)
    s.src_ref = TestSrcRTL(DataType, src_ref)
    s.src_predicate = TestSrcRTL(PredicateType, src_predicate)
    s.src_opt = TestSrcRTL(CtrlType, src_opt)
    s.sink_out = TestSinkRTL(DataType, sink_msgs)

    s.dut = FunctionUnit(DataType, PredicateType, CtrlType, num_inports,
                         num_outports, data_mem_size)

    s.src_data.send //= s.dut.recv_in[0]
    s.src_ref.send //= s.dut.recv_in[1]
    s.src_predicate.send //= s.dut.recv_predicate
    s.src_opt.send //= s.dut.recv_opt
    s.dut.send_out[0] //= s.sink_out.recv

  def done(s):
    return s.src_data.done() and s.sink_out.done()

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

def test_Comp():
  FU = CompRTL
  DataType = mk_data(32, 1)
  PredicateType = mk_predicate(1, 1)
  CtrlType = mk_ctrl()
  num_inports = 2
  num_outports = 1
  data_mem_size = 8
  FuInType = mk_bits(clog2(num_inports + 1))
  pickRegister = [FuInType(x + 1) for x in range(num_inports)]
  src_data = [DataType(9, 1), DataType(3, 1), DataType(3, 1)]
  src_ref = [DataType(9, 1), DataType(5, 1), DataType(2, 1)]
  src_predicate = [PredicateType(1,0), PredicateType(1,0), PredicateType(1,1)]
  src_opt = [CtrlType(OPT_EQ, b1(0), pickRegister),
             CtrlType(OPT_LT, b1(0), pickRegister),
             CtrlType(OPT_EQ, b1(0), pickRegister)]
  sink_out = [DataType(1, 1), DataType(1, 1), DataType(0, 1)]
  th = TestHarness(FU, DataType, PredicateType, CtrlType, num_inports,
                   num_outports, data_mem_size, src_data, src_ref,
                   src_predicate, src_opt, sink_out)
  run_sim(th)

