#=========================================================================
# LinkOrRTL_test.py
#=========================================================================
# Simple test for LinkOrRTL.
#
# Author : Cheng Tan
#   Date : April 19, 2024

import pytest
from pymtl3                   import *
from pymtl3.stdlib.test_utils import TestVectorSimulator

from ...lib.test_sinks        import TestSinkRTL
from ...lib.test_srcs         import TestSrcRTL
from ...lib.messages          import *
from ..LinkOrRTL import LinkOrRTL

#-------------------------------------------------------------------------
# TestHarness
#-------------------------------------------------------------------------

class TestHarness( Component ):

  def construct( s, MsgType, src_msgs_0, src_msgs_1, sink_msgs ):

    s.src0  = TestSrcRTL ( MsgType, src_msgs_0  )
    s.src1  = TestSrcRTL ( MsgType, src_msgs_1  )
    s.sink = TestSinkRTL ( MsgType, sink_msgs )
    s.dut  = LinkOrRTL( MsgType )

    # Connections
    s.src0.send //= s.dut.recv_fu
    s.src1.send //= s.dut.recv_xbar
    s.dut.send  //= s.sink.recv

  def done( s ):
    return s.src0.done() and s.src1.done() and s.sink.done()

  def line_trace( s ):
    # return s.src.line_trace() + "-> | " + s.dut.line_trace()
    return s.src0.line_trace() + " or "   + s.src1.line_trace() + "-> | " + \
           s.dut.line_trace()  + " | -> " + s.sink.line_trace()

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
test_msgs_0 = [ DataType(7,0,1), DataType(4,1), DataType(1,1), DataType(0,1), DataType(0,0) ]
test_msgs_1 = [ DataType(0,1,1), DataType(0,0), DataType(2,0), DataType(2,1), DataType(3,1) ]
sink_msgs   = [ DataType(0,1), DataType(4,1), DataType(1,1), DataType(0,1), DataType(3,1) ]

def test_simple():
  th = TestHarness( DataType, test_msgs_0, test_msgs_1, sink_msgs )
  run_sim( th )

