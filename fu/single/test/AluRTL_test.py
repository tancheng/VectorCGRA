"""
==========================================================================
AluRTL_test.py
==========================================================================
Test cases for all functional units.

Author : Cheng Tan
  Date : November 27, 2019
"""

from pymtl3 import *
from ..AdderRTL import AdderRTL
from ..LogicRTL import LogicRTL
from ..MulRTL import MulRTL
from ..ShifterRTL import ShifterRTL
from ....lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ....lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ....lib.messages import *
from ....lib.opt_type import *
from ....mem.const.ConstQueueRTL import ConstQueueRTL

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, FunctionUnit, DataType, PredicateType, ConfigType,
                num_inports, num_outports, data_mem_size, src0_msgs,
                src1_msgs, src2_msgs, src_const, ctrl_msgs, sink_msgs):

    s.src_in0 = TestSrcRTL(DataType, src0_msgs)
    s.src_in1 = TestSrcRTL(DataType, src1_msgs)
    s.src_predicate = TestSrcRTL(PredicateType, src2_msgs)
    s.src_opt = TestSrcRTL(ConfigType, ctrl_msgs)
    s.sink_out = TestSinkRTL(DataType, sink_msgs)

    s.const_queue = ConstQueueRTL(DataType, src_const)
    s.dut = FunctionUnit(DataType, PredicateType, ConfigType, num_inports,
                         num_outports, data_mem_size)

    s.src_in0.send //= s.dut.recv_in[0]
    s.src_in1.send //= s.dut.recv_in[1]
    s.src_predicate.send //= s.dut.recv_predicate
    s.dut.recv_const //= s.const_queue.send_const
    s.src_opt.send //= s.dut.recv_opt
    s.dut.send_out[0] //= s.sink_out.recv

  def done(s):
    return s.src_in0.done() and \
           s.src_opt.done() and \
           s.sink_out.done()

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

def test_add_sub():
  FU = AdderRTL
  DataType = mk_data(16, 1)
  PredicateType = mk_predicate(1, 1)
  ConfigType = mk_ctrl()
  data_mem_size = 8
  num_inports = 2
  num_outports = 1
  FuInType = mk_bits(clog2(num_inports + 1))
  pickRegister = [FuInType(x + 1) for x in range(num_inports)]
  src_in0 = [DataType(1, 1), DataType(7, 1), DataType(4, 1)]
  src_in1 = [DataType(2, 1), DataType(3, 1), DataType(1, 1)]
  src_predicate = [PredicateType(1, 0), PredicateType(1, 0), PredicateType(1, 1)]
  src_const = [DataType(5, 1), DataType(1, 0), DataType(7, 1)]
  sink_out = [DataType(6, 0), DataType(5, 0), DataType(5, 1)]
  src_opt = [ConfigType(OPT_ADD_CONST, b1(1), pickRegister),
             ConfigType(OPT_SUB,       b1(1), pickRegister),
             ConfigType(OPT_ADD_CONST, b1(1), pickRegister)]
  th = TestHarness(FU, DataType, PredicateType, ConfigType, num_inports,
                   num_outports, data_mem_size, src_in0, src_in1,
                   src_predicate, src_const, src_opt, sink_out)
  run_sim(th)

def test_logic():
  FU = LogicRTL
  DataType = mk_data(16, 1)
  PredicateType = mk_predicate(1, 1)
  ConfigType = mk_ctrl()
  num_inports = 2
  num_outports = 1
  data_mem_size = 8
  FuInType = mk_bits(clog2(num_inports + 1))
  src_predicate = [PredicateType(1, 0), PredicateType(1, 0), PredicateType(1, 1)]
  pickRegister  = [FuInType(x + 1) for x in range(num_inports)]
  src_in0       = [DataType(1, 1), DataType(2, 1), DataType(4, 1),      DataType(1, 1)]
  src_in1       = [DataType(2, 1), DataType(3, 1),                      DataType(3, 1), DataType(2, 1)]
  src_const     = [DataType(5, 1), DataType(0, 0), DataType(7, 1)]
  sink_out      = [DataType(3, 0), DataType(2, 1), DataType(0xfffb, 1), DataType(2, 1)]
  src_opt       = [ConfigType(OPT_OR , b1(1), pickRegister),
                   ConfigType(OPT_AND, b1(0), pickRegister),
                   ConfigType(OPT_NOT, b1(0), pickRegister),
                   ConfigType(OPT_XOR, b1(0), pickRegister)]
  th = TestHarness(FU, DataType, PredicateType, ConfigType,
                   num_inports, num_outports, data_mem_size,
                   src_in0, src_in1, src_predicate, src_const, src_opt,
                   sink_out )
  run_sim(th)

def test_shifter():
  FU = ShifterRTL
  DataType = mk_data(16, 1)
  PredicateType = mk_predicate(1, 1)
  ConfigType = mk_ctrl()
  num_inports = 2
  num_outports = 1
  data_mem_size = 8
  FuInType = mk_bits(clog2(num_inports + 1))
  pickRegister = [FuInType(x + 1) for x in range(num_inports)]
  src_in0 = [DataType(1, 1), DataType(2, 1), DataType(4, 1)]
  src_in1 = [DataType(2, 1), DataType(3, 1), DataType(1, 1)]
  src_predicate = [PredicateType(1, 0), PredicateType(1, 0), PredicateType(1, 1)]
  src_const = [DataType(2, 1), DataType(3, 1), DataType(1, 1)]
  sink_out = [DataType(4, 1), DataType(16, 1), DataType(2, 1)]
  src_opt = [ConfigType(OPT_LLS, b1(0), pickRegister),
             ConfigType(OPT_LLS, b1(0), pickRegister),
             ConfigType(OPT_LRS, b1(0), pickRegister)]
  th = TestHarness(FU, DataType, PredicateType, ConfigType,
                   num_inports, num_outports, data_mem_size,
                   src_in0, src_in1, src_predicate, src_const, src_opt,
                   sink_out )
  run_sim(th)

def test_mul():
  FU = MulRTL
  DataType = mk_data(16, 1)
  PredicateType = mk_predicate(1, 1)
  ConfigType = mk_ctrl()
  num_inports = 2
  num_outports = 1
  data_mem_size = 8
  FuInType = mk_bits(clog2(num_inports + 1))
  pickRegister = [FuInType(x + 1) for x in range(num_inports)]
  src_in0 = [DataType(1, 1), DataType(2, 1), DataType(4, 1)]
  src_in1 = [DataType(2, 1), DataType(3, 1), DataType(3, 1)]
  src_predicate = [PredicateType(1, 0), PredicateType(1, 0), PredicateType(1, 1)]
  src_const = [DataType(2, 1), DataType(3, 1), DataType(3, 1)]
  sink_out = [DataType(2, 1), DataType(6, 1), DataType(12, 1)]
  src_opt = [ConfigType(OPT_MUL, b1(0), pickRegister),
             ConfigType(OPT_MUL, b1(0), pickRegister),
             ConfigType(OPT_MUL, b1(0), pickRegister)]
  th = TestHarness(FU, DataType, PredicateType, ConfigType, num_inports,
                   num_outports, data_mem_size, src_in0, src_in1,
                   src_predicate, src_const, src_opt, sink_out)
  run_sim(th)

