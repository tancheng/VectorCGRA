'''
==========================================================================
OrLinkRTL_test.py
==========================================================================
Test for OrLinkRTL.

Author : Cheng Tan
  Date : Feb 7, 2025
'''

import pytest
from pymtl3 import *
from pymtl3.stdlib.test_utils import TestVectorSimulator
from ..SelectorRTL import SelectorRTL
from ...lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ...lib.messages import *

#-------------------------------------------------------------------------
# TestHarness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, MsgType, src_msgs_0, src_msgs_1, src_msgs_2, sink_msgs):

    s.src0 = TestSrcRTL(MsgType, src_msgs_0)
    s.src1 = TestSrcRTL(MsgType, src_msgs_1)
    s.src2 = TestSrcRTL(MsgType, src_msgs_2)
    s.sink = TestSinkRTL(MsgType, sink_msgs)
    s.dut = SelectorRTL(MsgType, 3)

    # Connections
    s.src0.send //= s.dut.recv[0]
    s.src1.send //= s.dut.recv[1]
    s.src2.send //= s.dut.recv[2]
    s.dut.send //= s.sink.recv
    s.dut.recv_from //= 2

  def done(s):
    return s.src2.done() and s.sink.done()

  def line_trace(s):
    return s.src0.line_trace() + " or " + s.src1.line_trace() + " or " + \
           s.src2.line_trace() + " -> | " + \
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

nbits_payload = 16
DataType = mk_data(nbits_payload, 1)
src_msgs_0 = [DataType(7,0,1), DataType(0,1)]
src_msgs_1 = [DataType(0,1,0), DataType(0,0)]
src_msgs_2 = [DataType(0,1,0), DataType(4,1)]
sink_msgs = [DataType(0,1), DataType(4,1)]

def test_simple():
  th = TestHarness(DataType, src_msgs_0, src_msgs_1, src_msgs_2, sink_msgs)
  run_sim(th)

