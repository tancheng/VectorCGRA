"""
==========================================================================
MulticasterRTL_test.py
==========================================================================
Test cases for Multicaster.

Author : Cheng Tan
  Date : Feb 16, 2019

"""

from pymtl3 import *

from ...lib.test_sinks import TestSinkRTL
from ...lib.test_srcs  import TestSrcRTL
from ...lib.opt_type   import *
from ...lib.messages   import *
from ..MulticasterRTL  import MulticasterRTL

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness( Component ):

  def construct( s, Unit, DataType, num_outports, src_data ):

    s.num_outports = num_outports

    s.src_data     = TestSrcRTL( DataType, src_data  )
    s.sink_out     = [ TestSinkRTL( DataType, src_data )
                     for _ in range( num_outports ) ]

    s.dut = Unit( DataType, num_outports )

    connect( s.src_data.send, s.dut.recv )
    for i in range( num_outports ):
      connect( s.dut.send[i],  s.sink_out[i].recv )

  def done( s ):
    done = True
    for i in range( s.num_outports ):
      if not s.sink_out[i].done():
        done = False
        break
    return done

  def line_trace( s ):
    return s.dut.line_trace()

def run_sim( test_harness, max_cycles=100 ):
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

  # Check timeout

  assert ncycles < max_cycles

  test_harness.sim_tick()
  test_harness.sim_tick()
  test_harness.sim_tick()

def test_Multicaster():
  FU = MulticasterRTL
  num_outports = 3
  DataType     = mk_data( 16, 1 )
  src_data     = [ DataType(3, 1), DataType(2, 1), DataType(9, 1) ]
  th = TestHarness( FU, DataType, num_outports, src_data )
  run_sim( th )

