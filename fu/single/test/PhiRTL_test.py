"""
==========================================================================
PhiRTL_test.py
==========================================================================
Test cases for functional unit Phi.

Author : Cheng Tan
  Date : November 27, 2019
"""

from pymtl3                       import *
from ..PhiRTL                     import PhiRTL
from ....lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ....lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ....lib.opt_type             import *
from ....lib.messages             import *

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, FunctionUnit, DataType, CtrlType,
                num_inports, num_outports, data_mem_size, src0_msgs,
                src1_msgs, src_const, src_opt, sink_msgs):

    s.src_in0 = TestSrcRTL(DataType, src0_msgs)
    s.src_in1 = TestSrcRTL(DataType, src1_msgs)
    s.src_const = TestSrcRTL(DataType, src_const)
    s.src_opt = TestSrcRTL(CtrlType, src_opt)
    s.sink_out = TestSinkRTL(DataType, sink_msgs)

    s.dut = FunctionUnit(DataType, CtrlType, num_inports,
                         num_outports, data_mem_size,
                         vector_factor_power = 0)

    s.src_in0.send //= s.dut.recv_in[0]
    s.src_in1.send //= s.dut.recv_in[1]
    s.src_const.send //= s.dut.recv_const
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

def test_Phi():
  FU = PhiRTL
  DataType = mk_data(16, 1, 1)
  PredicateType = mk_predicate(1, 1)
  num_inports = 2
  num_outports = 1
  CtrlType = mk_ctrl(num_inports, num_outports)
  data_mem_size = 8
  ctrl_mem_size = 8
  FuInType = mk_bits(clog2(num_inports + 1))
  pickRegister = [FuInType(x + 1) for x in range(num_inports)]
  src_in0 =   [DataType(1, 0), DataType(3, 1), DataType(6, 0)]
  src_in1 =   [DataType(0, 0), DataType(5, 0), DataType(2, 1)]
  src_const = [DataType(0, 0), DataType(5, 0), DataType(2, 1)]
  src_opt =   [CtrlType(OPT_PHI, pickRegister),
               CtrlType(OPT_PHI, pickRegister),
               CtrlType(OPT_PHI, pickRegister)]

  sink_out = [DataType(1, 0), DataType(3, 1), DataType(2, 1)]
  th = TestHarness(FU, DataType, CtrlType, num_inports,
                   num_outports, data_mem_size, src_in0, src_in1,
                   src_const, src_opt, sink_out)
  run_sim(th)

def test_Phi_start():
  FU = PhiRTL
  DataType = mk_data(16, 1, 1)
  PredicateType = mk_predicate(1, 1)
  num_inports = 2
  num_outports = 1
  CtrlType = mk_ctrl(num_inports, num_outports)
  data_mem_size = 8
  ctrl_mem_size = 8
  FuInType = mk_bits(clog2(num_inports + 1))
  pickRegister = [FuInType(x + 1) for x in range(num_inports)]
  src_in0 =   [DataType(2, 1), DataType(3, 0), DataType(6, 0)]
  src_in1 =   [                DataType(5, 1), DataType(2, 1)]
  src_const = [DataType(0, 0), DataType(5, 0), DataType(2, 1)]
  src_opt =   [CtrlType(OPT_PHI_START, pickRegister),
               CtrlType(OPT_PHI_START, pickRegister),
               CtrlType(OPT_PHI_START, pickRegister)]

  sink_out = [DataType(2, 1), DataType(5, 1), DataType(2, 1)]
  th = TestHarness(FU, DataType, CtrlType, num_inports,
                   num_outports, data_mem_size, src_in0, src_in1,
                   src_const, src_opt, sink_out)
  run_sim(th)

def test_Phi_const():
  FU = PhiRTL
  DataType = mk_data(16, 1, 1)
  PredicateType = mk_predicate(1, 1)
  num_inports = 2
  num_outports = 1
  CtrlType = mk_ctrl(num_inports, num_outports)
  data_mem_size = 8
  ctrl_mem_size = 8
  FuInType = mk_bits(clog2(num_inports + 1))
  pickRegister = [FuInType(x + 1) for x in range(num_inports)]
  src_in0 =   [DataType(1, 1), DataType(4, 1), DataType(7, 0)]
  src_in1 =   [DataType(2, 0), DataType(5, 1), DataType(8, 1)]
  # `PHI_CONST` normally is the starting point of a kernel.
  # The const value is only picked at the first time.
  src_const = [DataType(3, 0), DataType(6, 0), DataType(9, 1)]
  src_opt =   [CtrlType(OPT_PHI_CONST, pickRegister),
               CtrlType(OPT_PHI_CONST, pickRegister),
               CtrlType(OPT_PHI_CONST, pickRegister) ]
  sink_out =  [DataType(3, 0), DataType(4, 1), DataType(7, 0)]
  th = TestHarness(FU, DataType, CtrlType,
                   num_inports, num_outports, data_mem_size,
                   src_in0, src_in1, src_const, src_opt,
                   sink_out)
  run_sim(th)

def test_Phi_vector():
  FU = PhiRTL
  DataType = mk_data(16, 1, 1)
  PredicateType = mk_predicate(1, 1)
  num_inports = 2
  num_outports = 1
  CtrlType = mk_ctrl(num_inports, num_outports)
  data_mem_size = 8
  ctrl_mem_size = 8
  FuInType = mk_bits(clog2(num_inports + 1))
  pickRegister = [FuInType(x + 1) for x in range(num_inports)]
  # We can consume the inputs as the producer is also performed
  # in the vectorization fashion.
  src_in0 =   [DataType(1, 1), DataType(3, 1), DataType(6, 0),
               # Second round, vector factor 2/4.
               DataType(1, 1), DataType(3, 1), DataType(6, 0),
               # Third round, vector factor 3/4.
               DataType(1, 1), DataType(3, 1), DataType(6, 0),
               # Fouth round, vector factor 4/4.
               DataType(1, 1), DataType(3, 1), DataType(6, 0)]

  src_in1 =   [DataType(0, 0), DataType(5, 0), DataType(2, 1),
               DataType(0, 0), DataType(5, 0), DataType(2, 1),
               DataType(0, 0), DataType(5, 0), DataType(2, 1),
               DataType(0, 0), DataType(5, 0), DataType(2, 1)]

  src_const = [DataType(0, 0), DataType(5, 0), DataType(2, 1)]

  src_opt =   [CtrlType(OPT_PHI, pickRegister),
               CtrlType(OPT_PHI, pickRegister),
               CtrlType(OPT_PHI, pickRegister),
               CtrlType(OPT_PHI, pickRegister),
               CtrlType(OPT_PHI, pickRegister),
               CtrlType(OPT_PHI, pickRegister),
               CtrlType(OPT_PHI, pickRegister),
               CtrlType(OPT_PHI, pickRegister),
               CtrlType(OPT_PHI, pickRegister),
               CtrlType(OPT_PHI, pickRegister),
               CtrlType(OPT_PHI, pickRegister),
               CtrlType(OPT_PHI, pickRegister)]

  # Assigns vector factor to each control signal.
  for i in range(len(src_opt)):
    src_opt[i].vector_factor_power = b3(2)

  src_opt[2].is_last_ctrl = b1(1)
  src_opt[5].is_last_ctrl = b1(1)
  src_opt[8].is_last_ctrl = b1(1)
  src_opt[11].is_last_ctrl = b1(1)

  # The third output's predicate is 0 due to reached_vector_factor
  # is not 1.
  sink_out = [DataType(1, 0), DataType(3, 0), DataType(2, 0),
              DataType(1, 0), DataType(3, 0), DataType(2, 0),
              DataType(1, 0), DataType(3, 0), DataType(2, 0),
              DataType(1, 1), DataType(3, 1), DataType(2, 1)]
  th = TestHarness(FU, DataType, CtrlType,
                   num_inports, num_outports, data_mem_size,
                   src_in0, src_in1, src_const, src_opt,
                   sink_out)
  run_sim(th)
