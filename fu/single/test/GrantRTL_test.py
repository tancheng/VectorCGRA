"""
==========================================================================
GrantRTL_test.py
==========================================================================
Test cases for GrantRTL.

Author : Cheng Tan
  Date : July 18, 2025
"""

from pymtl3 import *
from ..GrantRTL import GrantRTL
from ....lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ....lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ....lib.messages import *
from ....lib.opt_type import *

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, FunctionUnit, DataType, PredicateType, CtrlType,
                num_inports, num_outports, data_mem_size, src_value,
                src_predicate, src_opt, sink_out):

    s.src_value = TestSrcRTL(DataType, src_value)
    s.src_predicate = TestSrcRTL(DataType, src_predicate)
    s.src_opt = TestSrcRTL(CtrlType, src_opt)
    s.sink_out = TestSinkRTL(DataType, sink_out)

    s.dut = FunctionUnit(DataType, CtrlType,
                         num_inports, num_outports,
                         data_mem_size)

    s.src_value.send //= s.dut.recv_in[0]
    s.src_predicate.send //= s.dut.recv_in[1]
    s.src_opt.send //= s.dut.recv_opt
    s.dut.send_out[0] //= s.sink_out.recv

  def done(s):
    return s.src_opt.done() and s.sink_out.done()

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


def test_grant():
  FU = GrantRTL
  DataType = mk_data(16, 1)
  PredicateType = mk_predicate(1, 1)
  num_inports = 2
  num_outports = 1
  ConfigType = mk_ctrl(num_inports, num_outports)
  data_mem_size = 8
  FuInType = mk_bits(clog2(num_inports + 1))
  pickRegister  = [FuInType(x + 1) for x in range(num_inports)]
  src_value     = [DataType(1, 1), DataType(2, 0), DataType(3, 1), DataType(4, 1), DataType(5, 0), DataType(6, 0), DataType(6, 1)]
  src_condition = [DataType(2, 0), DataType(1, 1), DataType(0, 1), DataType(1, 1)                                                ]
  sink_out      = [DataType(1, 0), DataType(2, 0), DataType(3, 0), DataType(4, 1), DataType(5, 1), DataType(6, 1), DataType(6, 0)]
  src_opt       = [ConfigType(OPT_GRT_PRED,   pickRegister),
                   ConfigType(OPT_GRT_PRED,   pickRegister),
                   ConfigType(OPT_GRT_PRED,   pickRegister),
                   ConfigType(OPT_GRT_PRED,   pickRegister),
                   ConfigType(OPT_GRT_ALWAYS, pickRegister),
                   ConfigType(OPT_GRT_ONCE,   pickRegister),
                   ConfigType(OPT_GRT_ONCE,   pickRegister)]
  th = TestHarness(FU, DataType, PredicateType, ConfigType,
                   num_inports, num_outports, data_mem_size,
                   src_value, src_condition, src_opt, sink_out)
  run_sim(th)
