"""
==========================================================================
CrossbarRTL_test.py
==========================================================================
Test cases for Crossbar.

Author : Cheng Tan
  Date : Dec 9, 2019

"""

from pymtl3            import *
from ...lib.test_sinks import TestSinkRTL
from ...lib.test_srcs  import TestSrcRTL

from ..CrossbarRTL     import CrossbarRTL
from ..ChannelRTL      import ChannelRTL
from ...lib.opt_type   import *
from ...lib.messages   import *

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness( Component ):

  def construct( s, CrossbarUnit, DataType, PredicateType, CtrlType,
                 num_inports, num_outports,
                 src_data, src_routing, sink_out ):

    s.num_inports  = num_inports
    s.num_outports = num_outports

    s.src_opt      = TestSrcRTL( CtrlType, src_routing )
    s.src_data     = [ TestSrcRTL( DataType, src_data[i]  )
                     for i in range( num_inports  ) ]
    s.sink_out     = [ TestSinkRTL( DataType, sink_out[i] )
                     for i in range( num_outports ) ]

    s.dut = CrossbarUnit( DataType, PredicateType, CtrlType, num_inports,
                          num_outports, num_inports-1 )
    latency   = 2
    s.channel = ChannelRTL( DataType, latency )

    assert( num_inports == 3 )
    connect( s.src_data[0].send,  s.dut.recv_data[0] )
    connect( s.dut.send_data[0],  s.sink_out[0].recv )

    # The channel/fifo connecting with inport 1 has latency of 2.
    connect( s.src_data[1].send,  s.channel.recv )
    connect( s.channel.send,      s.dut.recv_data[1] )
    connect( s.dut.send_data[1],  s.sink_out[1].recv )

    connect( s.src_data[2].send,  s.dut.recv_data[2] )
    connect( s.dut.send_data[2],  s.sink_out[2].recv )

    connect( s.src_opt.send,     s.dut.recv_opt )

  def done( s ):
    done = True
    for i in range( s.num_inports  ):
      if not s.src_data[i].done():
        done = False
        break
    for i in range( s.num_outports ):
      if not s.sink_out[i].done():
        done = False
        break
    return done

  def line_trace( s ):
    return s.dut.line_trace()

def run_sim( test_harness, max_cycles=10 ):
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

  assert ncycles <= max_cycles

  test_harness.sim_tick()
  test_harness.sim_tick()
  test_harness.sim_tick()

def test_mul_with_long_latency_input():
  FU = CrossbarRTL
  num_fu_in     = 3
  num_inports   = 3
  num_outports  = 3
  DataType      = mk_data( 16, 1 )
  PredicateType = mk_predicate( 1, 1 )
  CtrlType      = mk_ctrl( num_fu_in, num_inports, num_outports )
  FuInType      = mk_bits( clog2( num_inports + 1 ) )
  pickRegister  = [ FuInType( x+1 ) for x in range( num_inports ) ]
  RouteType     = mk_bits( clog2( num_inports + 1 ) )
  src_opt       = [ CtrlType( OPT_ADD, b1(0), pickRegister, [RouteType(2), RouteType(1), RouteType(1)]) ]
  src_data      = [ [DataType(3, 1, 0, 1), DataType(7, 1, 0, 1)], [DataType(2, 1, 0, 1)], [DataType(9, 1, 0, 1)] ]
  sink_out      = [ [DataType(2, 1)], [DataType(3, 1)], [DataType(3, 1)] ]
  th = TestHarness( FU, DataType, PredicateType, CtrlType, num_inports, num_outports,
                    src_data, src_opt, sink_out )
  run_sim( th )

def test_mul_with_long_latency_input_and_additional_blocked_input():
  FU = CrossbarRTL
  num_fu_in     = 3
  num_inports   = 3
  num_outports  = 3
  DataType      = mk_data( 16, 1 )
  PredicateType = mk_predicate( 1, 1 )
  CtrlType      = mk_ctrl( num_fu_in, num_inports, num_outports )
  FuInType      = mk_bits( clog2( num_inports + 1 ) )
  pickRegister  = [ FuInType( x+1 ) for x in range( num_inports ) ]
  RouteType     = mk_bits( clog2( num_inports + 1 ) )
  src_opt       = [ CtrlType( OPT_ADD, b1(0), pickRegister, [RouteType(2), RouteType(1), RouteType(1)]) ]
  src_data      = [ [DataType(3, 1, 0, 1), DataType(7, 1, 0, 1)], [DataType(2, 1, 0, 1)], [DataType(9, 1, 0, 1)] ]
  sink_out      = [ [DataType(2, 1)], [DataType(3, 1)], [DataType(3, 1)] ]
  th = TestHarness( FU, DataType, PredicateType, CtrlType, num_inports, num_outports,
                    src_data, src_opt, sink_out )
  run_sim( th )


