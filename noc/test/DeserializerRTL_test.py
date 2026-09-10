'''
=========================================================================
DeserializerRTL_test.py
=========================================================================
Simple test for DeserializerRTL.

Author : Yufei Yang
  Date : Aug 27, 2026
'''

from pymtl3 import *
from pymtl3.stdlib.test_utils import config_model_with_cmdline_opts

from ..DeserializerRTL import DeserializerRTL
from ...lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ...lib.messages import *
from ...lib.util.common import *


#-------------------------------------------------------------------------
# TestHarness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, NoCPktType, NoCFlitType, flit_msgs, expected_pkt_msgs):

    # Instantiates the DUT and the test source/sink.
    s.dut = DeserializerRTL( NoCPktType, NoCFlitType )
    s.src = TestSrcRTL( NoCFlitType, flit_msgs )

    # Delays consuming the output packet to test backpressure on incoming flits.
    s.sink = TestSinkRTL( NoCPktType, expected_pkt_msgs, initial_delay=10, interval_delay=10 )

    # Connects the modules.
    s.src.send //= s.dut.in_flit
    s.dut.out_pkt //= s.sink.recv

  def done(s):
    return s.src.done() and s.sink.done()

  def line_trace(s):
    return s.dut.line_trace()


#-------------------------------------------------------------------------
# run_sim
#-------------------------------------------------------------------------

def run_sim(test_harness, max_cycles = 100):

  # Creates a simulator.
  test_harness.elaborate()
  test_harness.apply( DefaultPassGroup() )
  test_harness.sim_reset()

  # Tracks whether the next flit is blocked while the current packet waits.
  saw_blocked_next_flit = False

  # Runs the simulation.
  ncycles = 0
  print()
  print("{}:{}".format(ncycles, test_harness.line_trace()))
  while not test_harness.done() and ncycles < max_cycles:

    # Checks that no new flit can enter while an output packet is waiting.
    if ( test_harness.dut.out_pkt.val and
         not test_harness.dut.out_pkt.rdy and
         test_harness.dut.in_flit.val ):

      saw_blocked_next_flit = True
      assert not test_harness.dut.in_flit.rdy

    test_harness.sim_tick()
    ncycles += 1
    print("{}:{}".format(ncycles, test_harness.line_trace()))

  # Checks timeout.
  assert ncycles < max_cycles

  # Checks that the backpressure case was actually exercised.
  assert saw_blocked_next_flit

  test_harness.sim_tick()
  test_harness.sim_tick()
  test_harness.sim_tick()


#-------------------------------------------------------------------------
# Test cases
#-------------------------------------------------------------------------

def test_simple(cmdline_opts):

  # Defines parameters. Sets data_nbits to 128 to generate 4 flits per packet.
  flit_width = 32
  pkt_width = 128
  num_cgra_columns = 1
  num_cgra_rows = 1
  num_tiles = 1
  num_rd_tiles = 1

  # Constructs NoCPktType and NoCFlitType.
  PktType = mk_bits(pkt_width)
  NoCPktType = mk_inter_cgra_pkt(
    num_cgra_columns,
    num_cgra_rows,
    num_tiles,
    num_rd_tiles,
    PktType
  )

  # Defines FlitType with a 32-bit width.
  FlitType = mk_bits(flit_width)
  NoCFlitType = mk_inter_cgra_pkt(
    num_cgra_columns,
    num_cgra_rows,
    num_tiles,
    num_rd_tiles,
    FlitType
  )

  # Constructs input flits for Packet 1.
  flit1_1 = NoCFlitType(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, FlitType(0xFFFFFFFF))
  flit1_2 = NoCFlitType(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, FlitType(0xEEEEEEEE))
  flit1_3 = NoCFlitType(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, FlitType(0xDDDDDDDD))
  flit1_4 = NoCFlitType(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, FlitType(0xCCCCCCCC))
  
  # Constructs input flits for Packet 2.
  flit2_1 = NoCFlitType(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, FlitType(0x77777777))
  flit2_2 = NoCFlitType(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, FlitType(0x66666666))
  flit2_3 = NoCFlitType(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, FlitType(0x55555555))
  flit2_4 = NoCFlitType(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, FlitType(0x44444444))

  flit_msgs = [
    flit1_1, flit1_2, flit1_3, flit1_4,
    flit2_1, flit2_2, flit2_3, flit2_4
  ]

  # Expected Packet 1.
  pkt1 = NoCPktType(
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    PktType(0xCCCCCCCCDDDDDDDDEEEEEEEEFFFFFFFF)
  )

  # Expected Packet 2.
  pkt2 = NoCPktType(
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    PktType(0x44444444555555556666666677777777)
  )

  expected_pkt_msgs = [ pkt1, pkt2 ]

  # Generates TestHarness and runs the simulation.
  th = TestHarness(
    NoCPktType,
    NoCFlitType,
    flit_msgs,
    expected_pkt_msgs
  )

  th.elaborate()
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)
