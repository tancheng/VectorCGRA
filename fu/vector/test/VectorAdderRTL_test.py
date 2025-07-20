"""
==========================================================================
VAdderRTL_test.py
==========================================================================
Test cases for vector adder.

Author : Cheng Tan
  Date : March 13, 2022
"""


from pymtl3 import *
from ..VectorAdderRTL import VectorAdderRTL
from ....lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ....lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ....lib.opt_type import *
from ....lib.messages import *
from ....mem.const.ConstQueueRTL import ConstQueueRTL

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, FunctionUnit, bandwidth, ConfigType,
                num_inports, num_outports, data_mem_size,
                src0_msgs, src1_msgs, src_const,
                ctrl_msgs, sink_msgs):

    InDataType  = mk_bits(bandwidth)
    OutDataType = mk_bits(bandwidth + 1)
    s.src_in0   = TestSrcRTL (InDataType,  src0_msgs)
    s.src_in1   = TestSrcRTL (InDataType,  src1_msgs)
    s.src_opt   = TestSrcRTL (ConfigType,  ctrl_msgs)
    s.sink_out  = TestSinkRTL(OutDataType, sink_msgs)

    s.const_queue = ConstQueueRTL(InDataType, src_const)
    s.dut = FunctionUnit(bandwidth, ConfigType,
                         num_inports, num_outports,
                         data_mem_size)

    s.src_in0.send.rdy //= s.dut.recv_in[0].rdy
    s.src_in0.send.val //= s.dut.recv_in[0].val
    s.src_in0.send.msg //= s.dut.recv_in[0].msg[0:bandwidth]

    s.src_in1.send.rdy //= s.dut.recv_in[1].rdy
    s.src_in1.send.val //= s.dut.recv_in[1].val
    s.src_in1.send.msg //= s.dut.recv_in[1].msg[0:bandwidth]

    s.const_queue.send_const.rdy //= s.dut.recv_const.rdy
    s.const_queue.send_const.val //= s.dut.recv_const.val
    s.const_queue.send_const.msg //= s.dut.recv_const.msg[0:bandwidth]

    connect(s.src_opt.send,    s.dut.recv_opt )
    connect(s.dut.send_out[0], s.sink_out.recv)

  def done(s):
    return s.src_in0.done() and s.src_in1.done() and\
           s.src_opt.done() and s.sink_out.done()

  def line_trace(s):
    return s.dut.line_trace()

def run_sim(test_harness, max_cycles = 100):
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

def test_vadder():
  FU            = VectorAdderRTL
  bandwidth     = 8
  InDataType    = mk_bits(bandwidth)
  OutDataType   = mk_bits(bandwidth + 1)
  PredicateType = mk_predicate(1, 1)
  data_mem_size = 8
  num_inports   = 2
  num_outports  = 1
  ConfigType    = mk_ctrl(num_inports, num_outports)
  FuInType      = mk_bits(clog2(num_inports + 1))
  pickRegister  = [FuInType(x + 1) for x in range(num_inports)]
  src_in0       = [InDataType(1),  InDataType(7),  InDataType(4)]
  src_in1       = [                InDataType(2)                ]
  src_const     = [InDataType(5),                  InDataType(7)]
  sink_out      = [OutDataType(6), OutDataType(5), OutDataType(11)]
  src_opt       = [ConfigType(OPT_ADD_CONST, pickRegister),
                   ConfigType(OPT_SUB,       pickRegister),
                   ConfigType(OPT_ADD_CONST, pickRegister) ]
  th = TestHarness(FU, bandwidth, ConfigType,
                   num_inports, num_outports, data_mem_size,
                   src_in0, src_in1, src_const, src_opt,
                   sink_out)
  run_sim(th)

