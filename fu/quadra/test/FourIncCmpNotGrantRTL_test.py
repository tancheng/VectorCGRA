"""
==========================================================================
FourIncCmpNotGrantRTL_test.py
==========================================================================
Test cases for FourIncCmpNotGrantRTL.

Author : Cheng Tan
  Date : Oct 29, 2025
"""

from pymtl3 import *
from ..FourIncCmpNotGrantRTL import FourIncCmpNotGrantRTL
from ....lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ....lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ....lib.opt_type import *
from ....lib.messages import *
from ....mem.const.ConstQueueRTL import ConstQueueRTL

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, FunctionUnit, IntraCgraPktType, DataType, CtrlType,
                num_inports, num_outports, data_mem_size, src0_msgs,
                src1_msgs, src2_msgs, src3_msgs, src_const, ctrl_msgs,
                sink0_msgs, sink1_msgs):

    s.src_in0  = TestSrcRTL (DataType, src0_msgs)
    s.src_in1  = TestSrcRTL (DataType, src1_msgs)
    s.src_in2  = TestSrcRTL (DataType, src2_msgs)
    s.src_in3  = TestSrcRTL (DataType, src3_msgs)
    s.src_opt  = TestSrcRTL (CtrlType, ctrl_msgs)
    s.sink_out0 = TestSinkRTL(DataType, sink0_msgs)
    s.sink_out1 = TestSinkRTL(DataType, sink1_msgs)

    s.const_queue = ConstQueueRTL(DataType, src_const)
    s.dut = FunctionUnit(IntraCgraPktType, num_inports, num_outports)

    connect(s.src_in0.send,           s.dut.recv_in[0])
    connect(s.src_in1.send,           s.dut.recv_in[1])
    connect(s.src_in2.send,           s.dut.recv_in[2])
    connect(s.src_in3.send,           s.dut.recv_in[3])
    connect(s.const_queue.send_const, s.dut.recv_const)
    connect(s.src_opt.send ,          s.dut.recv_opt  )
    connect(s.dut.send_out[0],        s.sink_out0.recv)
    connect(s.dut.send_out[1],        s.sink_out1.recv)

  def done(s):
    return s.src_in0.done() and s.src_in1.done()   and \
           s.src_in2.done() and s.src_in3.done()   and \
           s.src_opt.done() and s.sink_out0.done() and s.sink_out1.done()

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

def test_four():
  FU            = FourIncCmpNotGrantRTL
  DataType      = mk_data(16, 1)
  PredicateType = mk_predicate(1, 1)
  num_inports   = 4
  num_outports  = 2
  CtrlType      = mk_ctrl(num_inports, num_outports)
  data_mem_size = 8
  ctrl_mem_size = 8
  DataAddrType  = mk_bits(clog2(data_mem_size))
  CtrlAddrType  = mk_bits(clog2(ctrl_mem_size))
  CgraPayloadType = mk_cgra_payload(DataType, DataAddrType, CtrlType, CtrlAddrType)
  IntraCgraPktType = mk_intra_cgra_pkt(1, 1, 1, CgraPayloadType)

  FuInType      = mk_bits(clog2(num_inports + 1))
  pickRegister  = [FuInType(x + 1) for x in range(num_inports)]

  src_in0       = [DataType(4, 1), DataType(4, 1)]
  src_in1       = []
  src_in2       = []
  src_in3       = []
  src_const     = [DataType(5, 1), DataType(6, 1)]
  sink_out0     = [DataType(1, 1), DataType(0, 1)]
  sink_out1     = [DataType(5, 0), DataType(5, 1)]
  src_opt       = [CtrlType(OPT_INC_NE_CONST_NOT_GRT, pickRegister),
                   CtrlType(OPT_INC_NE_CONST_NOT_GRT, pickRegister)]
  th = TestHarness(FU, IntraCgraPktType, DataType, CtrlType,
                   num_inports, num_outports, data_mem_size,
                   src_in0, src_in1, src_in2, src_in3, src_const,
                   src_opt, sink_out0, sink_out1)
  run_sim(th)

