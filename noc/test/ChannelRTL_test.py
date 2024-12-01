#=========================================================================
# ChannelRTL_test.py
#=========================================================================
# Simple test for Channel
#
# Author : Cheng Tan
#   Date : Dec 11, 2019

import pytest
from pymtl3                   import *
from pymtl3.stdlib.test_utils import TestVectorSimulator

from ...lib.basic.en_rdy.test_sinks import TestSinkRTL
from ...lib.basic.en_rdy.test_srcs  import TestSrcRTL
from ...lib.messages   import *
from ..ChannelRTL      import ChannelRTL

#-------------------------------------------------------------------------
# TestHarness
#-------------------------------------------------------------------------

class TestHarness( Component ):

  def construct( s, MsgType, src_msgs, sink_msgs, latency ):

    s.src  = TestSrcRTL ( MsgType, src_msgs  )
    s.sink = TestSinkRTL( MsgType, sink_msgs )
    s.dut  = ChannelRTL( MsgType, latency )

    # Connections
    s.src.send //= s.dut.recv
    s.dut.send //= s.sink.recv
    # s.dut.send.rdy //= 0

  def done( s ):
    return s.src.done() and s.sink.done()

  def line_trace( s ):
    # return s.src.line_trace() + "-> | " + s.dut.line_trace()
    return s.src.line_trace() + "-> | " + s.dut.line_trace() + \
                               " | -> " + s.sink.line_trace()

#-------------------------------------------------------------------------
# run_rtl_sim
#-------------------------------------------------------------------------

def run_sim( test_harness, max_cycles=100 ):

  # Create a simulator
  test_harness.elaborate()
  test_harness.apply( DefaultPassGroup() )
  test_harness.sim_reset()

  # Run simulation
  ncycles = 0
  print()
  print( "{}:{}".format( ncycles, test_harness.line_trace() ))
  while not test_harness.done() and ncycles < max_cycles:
    test_harness.sim_tick()
    ncycles += 1
    print( "{}:{}".format( ncycles, test_harness.line_trace() ))
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

DataType  = mk_data( 16, 1 )
test_msgs = [ DataType(7,1,1), DataType(4,1), DataType(1,1), DataType(2,1), DataType(3,1) ]
sink_msgs = [ DataType(7,1), DataType(4,1), DataType(1,1), DataType(2,1), DataType(3,1) ]

def test_simple():
  latency = 1
  th = TestHarness( DataType, test_msgs, sink_msgs, latency)
  run_sim( th )

def test_latency():
  latency = 2
  th = TestHarness( DataType, test_msgs, sink_msgs, latency)
  run_sim( th )
