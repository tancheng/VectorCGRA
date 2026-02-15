"""
==========================================================================
ConstRTL_test.py
==========================================================================
Test cases for Constiplier.

Author : Cheng Tan
  Date : Oct 28, 2025
"""

import pytest
import hypothesis
from hypothesis import strategies as st
from itertools import product
from pymtl3 import *
from ..ConstRTL import ConstRTL
from ....lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ....lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ....lib.opt_type import *
from ....lib.messages import *
from ....mem.const.ConstQueueRTL import ConstQueueRTL

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, FunctionUnit, IntraCgraPktType, DataType, ConfigType,
                num_inports, num_outports, data_mem_size,
                src0_msgs, src1_msgs, src_const, ctrl_msgs,
                sink_msgs):

    s.src_in0 = TestSrcRTL(DataType, src0_msgs)
    s.src_in1 = TestSrcRTL(DataType, src1_msgs)
    s.src_in2 = TestSrcRTL(DataType, src1_msgs)
    s.src_opt = TestSrcRTL(ConfigType, ctrl_msgs)
    s.sink_out = TestSinkRTL(DataType, sink_msgs)

    s.const_queue = ConstQueueRTL(DataType, src_const)
    s.dut = FunctionUnit(IntraCgraPktType, num_inports, num_outports)

    connect(s.src_in0.send, s.dut.recv_in[0])
    connect(s.src_in1.send, s.dut.recv_in[1])
    connect(s.src_in2.send, s.dut.recv_in[2])
    connect(s.dut.recv_const, s.const_queue.send_const)
    connect(s.src_opt.send, s.dut.recv_opt)
    connect(s.dut.send_out[0], s.sink_out.recv)

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

def test_const():
  FU = ConstRTL
  DataType = mk_data(32, 1)
  PredicateType = mk_predicate(1, 1)
  num_inports = 4
  num_outports = 1
  ConfigType = mk_ctrl(num_inports, num_outports)
  FuInType = mk_bits(clog2(num_inports + 1))
  pickRegister = [FuInType(x + 1) for x in range(num_inports)]
  data_mem_size = 8
  ctrl_mem_size = 8
  DataAddrType  = mk_bits(clog2(data_mem_size))
  CtrlAddrType  = mk_bits(clog2(ctrl_mem_size))
  CgraPayloadType = mk_cgra_payload(DataType, DataAddrType, ConfigType, CtrlAddrType)
  IntraCgraPktType = mk_intra_cgra_pkt(1, 1, 1, CgraPayloadType)
  src_in0 =   []
  src_in1 =   []
  src_const = [DataType(1, 0), DataType(3, 1), DataType(2, 0)]
  sink_out =  [DataType(1, 0), DataType(3, 1), DataType(2, 0)]
  src_opt =   [ConfigType(OPT_CONST, pickRegister),
               ConfigType(OPT_CONST, pickRegister),
               ConfigType(OPT_CONST, pickRegister)]
  th = TestHarness(FU, IntraCgraPktType, DataType, ConfigType,
                   num_inports, num_outports, data_mem_size,
                   src_in0, src_in1, src_const, src_opt,
                   sink_out)
  run_sim(th)
