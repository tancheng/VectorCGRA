"""
==========================================================================
CompRTL_test.py
==========================================================================
Test cases for functional unit Phi.

Author : Cheng Tan
  Date : November 27, 2019
"""

from pymtl3 import *
from pymtl3.passes.PassGroups import *
from ..SelRTL import SelRTL
from ....lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ....lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ....lib.messages import *
from ....lib.opt_type import *

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, FunctionUnit, DataType, PredicateType, CtrlType,
                num_inports, num_outports, data_mem_size,
                src_data1, src_data2, src_ref0, src_opt,
                sink_msgs):

    s.src_data1 = TestSrcRTL(DataType, src_data1)
    s.src_data2 = TestSrcRTL(DataType, src_data2)
    s.src_ref0 = TestSrcRTL(DataType, src_ref0)
    s.src_opt = TestSrcRTL(CtrlType, src_opt)
    s.sink_out = TestSinkRTL( DataType, sink_msgs)

    s.dut = FunctionUnit(DataType, PredicateType, CtrlType,
                         num_inports, num_outports, data_mem_size)

    s.src_data1.send //= s.dut.recv_in[1]
    s.src_data2.send //= s.dut.recv_in[2]
    s.src_ref0.send //= s.dut.recv_in[0]
    s.src_opt.send //= s.dut.recv_opt
    s.dut.send_out[0] //= s.sink_out.recv

  def done(s):
    return s.src_data1.done() and s.src_data2.done() and \
           s.src_ref0.done()  and s.sink_out.done()

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

def test_Select():
  FU = SelRTL
  DataType = mk_data(32, 1)
  PredicateType = mk_predicate(1, 1)
  # Selector needs more than 2 inputs
  num_inports = 4
  num_outports = 1
  CtrlType = mk_ctrl(num_inports, num_outports)
  data_mem_size = 8
  FuInType = mk_bits(clog2(num_inports + 1))
  pickRegister = [FuInType(x + 1) for x in range(num_inports)]
  src_data1 = [DataType(9, 1), DataType(3, 1), DataType(4, 1)]
  src_data2 = [DataType(2, 1), DataType(7, 1), DataType(5, 1)]
  src_ref0 =  [DataType(1, 1), DataType(0, 1), DataType(1, 1)]
  src_opt =   [CtrlType(OPT_SEL, pickRegister),
               CtrlType(OPT_SEL, pickRegister),
               CtrlType(OPT_SEL, pickRegister)]
  sink_out =  [DataType(9, 1), DataType(7, 1), DataType(4, 1)]
  th = TestHarness(FU, DataType, PredicateType, CtrlType,
                   num_inports, num_outports, data_mem_size,
                   src_data1, src_data2, src_ref0, src_opt,
                   sink_out)
  run_sim(th)
