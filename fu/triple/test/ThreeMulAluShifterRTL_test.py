"""
==========================================================================
ThreeMulAdderShifterRTL_test.py
==========================================================================
Test cases for two parallelly combined functional unit followed by single
functional unit.

Author : Cheng Tan
  Date : November 29, 2019
"""

from pymtl3 import *
from ..ThreeMulAdderShifterRTL import ThreeMulAdderShifterRTL
from ....lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ....lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ....lib.opt_type import *
from ....lib.messages import *

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, FunctionUnit, DataType, PredicateType, CtrlType,
                num_inports, num_outports, data_mem_size, src0_msgs,
                src1_msgs, src2_msgs, src3_msgs, ctrl_msgs,
                sink_msgs):

    s.src_in0  = TestSrcRTL (DataType, src0_msgs)
    s.src_in1  = TestSrcRTL (DataType, src1_msgs)
    s.src_in2  = TestSrcRTL (DataType, src2_msgs)
    s.src_in3  = TestSrcRTL (DataType, src3_msgs)
    s.src_opt  = TestSrcRTL (CtrlType, ctrl_msgs)
    s.sink_out = TestSinkRTL(DataType, sink_msgs)

    s.dut = FunctionUnit(DataType, CtrlType,
                         num_inports, num_outports, data_mem_size)

    connect(s.src_in0.send,    s.dut.recv_in[0])
    connect(s.src_in1.send,    s.dut.recv_in[1])
    connect(s.src_in2.send,    s.dut.recv_in[2])
    connect(s.src_in3.send,    s.dut.recv_in[3])
    connect(s.src_opt.send ,   s.dut.recv_opt  )
    connect(s.dut.send_out[0], s.sink_out.recv )

  def done(s):
    return s.src_in0.done() and s.src_in1.done()  and \
           s.src_in2.done() and s.src_in3.done()  and \
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

def test_mul_alu_shifter():
  FU            = ThreeMulAdderShifterRTL
  DataType      = mk_data(16, 1)
  PredicateType = mk_predicate(1, 1)
  num_inports   = 4
  num_outports  = 2
  data_mem_size = 8
  CtrlType      = mk_ctrl(num_inports, num_outports)

  FuInType      = mk_bits(clog2(num_inports + 1))
  pickRegister  = [FuInType(x + 1) for x in range(num_inports)]

  src_in0       = [DataType(1, 1), DataType(2, 1), DataType(4, 1)]
  src_in1       = [DataType(2, 1), DataType(3, 1), DataType(3, 0)]
  src_in2       = [DataType(1, 1), DataType(3, 1), DataType(3, 1)]
  src_in3       = [DataType(1, 1), DataType(2, 1), DataType(2, 1)]
  sink_out      = [DataType(8, 1), DataType(12, 1), DataType(6, 0)]
  src_opt       = [CtrlType(OPT_MUL_ADD_LLS, pickRegister),
                   CtrlType(OPT_MUL_SUB_LLS, pickRegister),
                   CtrlType(OPT_MUL_SUB_LRS, pickRegister)]
  th = TestHarness(FU, DataType, PredicateType, CtrlType,
                   num_inports, num_outports, data_mem_size,
                   src_in0, src_in1, src_in2, src_in3, src_opt,
                   sink_out)
  run_sim(th)

