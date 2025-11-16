"""
==========================================================================
ConstQueueRTL_test.py
==========================================================================
Test cases for constant queue.

Author : Cheng Tan
  Date : Jan 20, 2020
"""


from pymtl3 import *
from ..ConstQueueRTL import ConstQueueRTL
from ....fu.single.AdderRTL import AdderRTL
# from ....lib.basic.en_rdy.test_sinks import TestSinkRTL
# from ....lib.basic.en_rdy.test_srcs import TestSrcRTL
from ....lib.basic.val_rdy.SourceRTL import SourceRTL as ValRdyTestSrcRTL
from ....lib.basic.val_rdy.SinkRTL import SinkRTL as ValRdyTestSinkRTL
from ....lib.opt_type import *
from ....lib.messages import *

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, DataType, ConfigType, src0_msgs,
                src_const, ctrl_msgs, sink_msgs):

    s.src_in0 = ValRdyTestSrcRTL(DataType, src0_msgs)
    s.src_opt = ValRdyTestSrcRTL(ConfigType, ctrl_msgs)
    s.sink_out = ValRdyTestSinkRTL(DataType, sink_msgs)

    s.alu = AdderRTL(DataType, ConfigType, 2, 1, 8)
    s.const_queue = ConstQueueRTL(DataType, src_const)

    connect(s.src_in0.send, s.alu.recv_in[0])
    connect(s.alu.recv_in[1], s.const_queue.send_const)
    connect(s.src_opt.send, s.alu.recv_opt)
    connect(s.alu.send_out[0], s.sink_out.recv)

  def done(s):
    return s.src_in0.done() and s.src_opt.done() and s.sink_out.done()

  def line_trace(s):
    return s.const_queue.line_trace() + s.alu.line_trace()

def run_sim(test_harness, max_cycles = 10):
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
  PredicateType = mk_predicate(1, 1)
  num_inports = 2
  FuInType = mk_bits(clog2(num_inports + 1))
  pickRegister = [FuInType(x + 1) for x in range(num_inports)]
  ConfigType = mk_ctrl(num_inports)
  src_in0 =   [DataType(1,  1), DataType(3,  1), DataType(9, 1)]
  src_const = [DataType(9,  1), DataType(8,  1), DataType(7, 1)]
  sink_out =  [DataType(10, 1), DataType(11, 1), DataType(2, 1)]
  src_opt =   [ConfigType(OPT_ADD, pickRegister),
               ConfigType(OPT_ADD, pickRegister),
               ConfigType(OPT_SUB, pickRegister)]
  th = TestHarness(DataType, ConfigType, src_in0,
                   src_const, src_opt, sink_out)
  run_sim(th)
