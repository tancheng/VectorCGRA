'''
==========================================================================
LinkOrRTL_test.py
==========================================================================
Simple test for LinkOrRTL.

Author : Cheng Tan
  Date : April 19, 2024
'''

import pytest
from pymtl3 import *
from pymtl3.stdlib.test_utils import TestVectorSimulator
from ..LinkOrRTL import LinkOrRTL
from ...lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ...lib.messages import *

#-------------------------------------------------------------------------
# TestHarness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, MsgType, src_msgs_0, src_msgs_1, sink_msgs):

    s.src0 = TestSrcRTL(MsgType, src_msgs_0)
    s.src1 = TestSrcRTL(MsgType, src_msgs_1)
    s.sink = TestSinkRTL(MsgType, sink_msgs)
    s.dut = LinkOrRTL(MsgType)

    # Connections
    s.src0.send //= s.dut.recv_fu
    s.src1.send //= s.dut.recv_xbar
    s.dut.send //= s.sink.recv
    s.dut.fu_xbar_rdy //= 1

  def done(s):
    return s.src0.done() and s.src1.done() and s.sink.done()

  def line_trace(s):
    return s.src0.line_trace() + " or " + s.src1.line_trace() + "-> | " + \
        s.dut.line_trace() + " | -> " + s.sink.line_trace()

#-------------------------------------------------------------------------
# run_rtl_sim
#-------------------------------------------------------------------------

def run_sim(test_harness, max_cycles = 100):

  # Create a simulator
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
    print( "{}:{}".format(ncycles, test_harness.line_trace()))
    if ncycles >= 4:
      test_harness.dut.send.rdy @= 1

  # Check timeout
  assert ncycles < max_cycles

  test_harness.sim_tick()
  test_harness.sim_tick()
  test_harness.sim_tick()

#-------------------------------------------------------------------------
# Test cases
#-------------------------------------------------------------------------

DataType = mk_data(16, 1)
test_msgs_0 = [DataType(7,0,1), DataType(4,1), DataType(1,1), DataType(0,1), DataType(0,0)]
test_msgs_1 = [DataType(0,1,1), DataType(0,0), DataType(2,0), DataType(2,1), DataType(3,1)]
sink_msgs = [DataType(7,1), DataType(4,1), DataType(3,1), DataType(2,1), DataType(3,1)]

def test_simple():
  th = TestHarness(DataType, test_msgs_0, test_msgs_1, sink_msgs)
  run_sim(th)

def test_invalid_fu_msg_does_not_pollute_xbar_output():
  dut = LinkOrRTL(DataType)
  dut.elaborate()
  dut.apply(DefaultPassGroup())
  dut.sim_reset()

  dut.recv_fu.val @= 0
  dut.recv_fu.msg @= DataType(0, 1)
  dut.recv_xbar.val @= 1
  dut.recv_xbar.msg @= DataType(1, 1)
  dut.fu_xbar_rdy @= 1
  dut.send.rdy @= 1
  dut.sim_eval_combinational()

  assert dut.send.val == b1(1)
  assert dut.send.msg == DataType(1, 1)

def test_uncommitted_fu_msg_is_not_consumed():
  dut = LinkOrRTL(DataType)
  dut.elaborate()
  dut.apply(DefaultPassGroup())
  dut.sim_reset()

  dut.recv_fu.val @= 1
  dut.recv_fu.msg @= DataType(7, 1)
  dut.recv_xbar.val @= 1
  dut.recv_xbar.msg @= DataType(1, 1)
  dut.fu_xbar_rdy @= 0
  dut.send.rdy @= 1
  dut.sim_eval_combinational()

  assert dut.send.val == b1(1)
  assert dut.send.msg == DataType(1, 1)
  assert dut.recv_fu.rdy == b1(0)
  assert dut.recv_xbar.rdy == b1(1)
