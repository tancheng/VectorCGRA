"""
==========================================================================
VectorAllReduceRTL_test.py
==========================================================================
Test case for VectorAllReduceRTL functional unit.

Author : Cheng Tan
  Date : April 23, 2022
"""

from pymtl3 import *
from ..VectorAllReduceRTL import VectorAllReduceRTL
from ....lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ....lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ....lib.opt_type import *
from ....lib.messages import *

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, FunctionUnit, DataType, PredicateType, CtrlType,
                num_inports, num_outports, data_mem_size, data_width,
                src0_msgs, src1_msgs, ctrl_msgs, sink_msgs0):

    s.src_in0       = TestSrcRTL (DataType, src0_msgs )
    s.src_in1       = TestSrcRTL (DataType, src1_msgs )
    s.src_opt       = TestSrcRTL (CtrlType, ctrl_msgs )
    s.sink_out0     = TestSinkRTL(DataType, sink_msgs0)

    s.dut = FunctionUnit(DataType, PredicateType, CtrlType,
                         num_inports, num_outports, data_mem_size,
                         data_bitwidth = data_width)

    connect(s.src_in0.send,    s.dut.recv_in[0])
    connect(s.src_in1.send,    s.dut.recv_in[1])
    connect(s.src_opt.send,    s.dut.recv_opt  )
    connect(s.dut.send_out[0], s.sink_out0.recv)

  def done(s):
    return s.src_in0.done() and s.src_opt.done() and s.sink_out0.done()

  def line_trace(s):
    return s.dut.line_trace()

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

def test_vector_all_reduce():
  FU            = VectorAllReduceRTL
  data_width    = 16
  DataType      = mk_data(data_width, 1)
  PredType      = mk_predicate(1, 1)
  num_inports   = 2
  num_outports  = 1
  data_mem_size = 8

  CtrlType      = mk_ctrl(num_inports, num_outports)
  FuInType      = mk_bits(clog2(num_inports + 1))
  pickRegister  = [FuInType(x + 1) for x in range(num_inports)]

  src_in0  = [DataType(0x3402,1), DataType(0x1177,1), DataType(0x0002,1)]
  src_in1  = [DataType(0x32f3,1), DataType(0x89,  1), DataType(0x0003,1)]
  sink_out = [DataType(0x9,   1), DataType(0x31,  1), DataType(0x0,   1)]
  src_opt  = [CtrlType(OPT_VEC_REDUCE_ADD, pickRegister),
              CtrlType(OPT_VEC_REDUCE_MUL, pickRegister),
              CtrlType(OPT_VEC_REDUCE_MUL, pickRegister)]

  th = TestHarness(FU, DataType, PredType, CtrlType,
                   num_inports, num_outports,
                   data_mem_size, data_width,
                   src_in0, src_in1, src_opt, sink_out)
  run_sim(th)
