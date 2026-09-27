'''
=========================================================================
SerializerRTL_test.py
=========================================================================
Simple test for SerializerRTL.

Author : Yufei Yang
  Date : Aug 24, 2026
'''

from pymtl3 import *
from pymtl3.stdlib.test_utils import config_model_with_cmdline_opts

from ..SerializerRTL import SerializerRTL
from ...lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ...lib.messages import *
from ...lib.util.common import *


#-------------------------------------------------------------------------
# TestHarness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, NoCPktType, NoCFlitType, pkt_msgs, expected_flit_msgs):
    
    # Instantiates the DUT and the test source/sink.
    s.dut = SerializerRTL( NoCPktType, NoCFlitType )
    s.src = TestSrcRTL( NoCPktType, pkt_msgs )
    
    # Sets initial_delay and interval_delay to 1 to pull down rdy every 2 cycles, simulating NoC congestion.
    s.sink = TestSinkRTL( NoCFlitType, expected_flit_msgs, initial_delay=2, interval_delay=2 )

    # Connects the modules.
    s.src.send //= s.dut.in_pkt
    s.dut.out_flit //= s.sink.recv

  def done(s):
    return s.src.done() and s.sink.done()

  def line_trace(s):
    return s.dut.line_trace()


#-------------------------------------------------------------------------
# run_sim
#-------------------------------------------------------------------------

def run_sim(test_harness, max_cycles = 50):

  # Creates a simulator.
  test_harness.elaborate()
  test_harness.apply( DefaultPassGroup() )
  test_harness.sim_reset()

  # Runs the simulation.
  ncycles = 0
  print()
  print("{}:{}".format(ncycles, test_harness.line_trace()))
  while not test_harness.done() and ncycles < max_cycles:
    test_harness.sim_tick()
    ncycles += 1
    print("{}:{}".format(ncycles, test_harness.line_trace()))

  # Checks timeout.
  assert ncycles < max_cycles

  test_harness.sim_tick()
  test_harness.sim_tick()
  test_harness.sim_tick()


#-------------------------------------------------------------------------
# Test cases
#-------------------------------------------------------------------------

def test_simple(cmdline_opts):

  # Defines parameters. Sets data_nbits to 128 to satisfy the requirement of generating 4 flits.
  flit_width = 32
  pkt_width = 128
  num_cgra_columns = 1
  num_cgra_rows = 1
  num_tiles = 1
  num_rd_tiles = 1

  # Constructs NoCPktType and NoCFlitType.
  PktType = mk_bits(pkt_width)
  NoCPktType = mk_inter_cgra_pkt(num_cgra_columns, num_cgra_rows, num_tiles, num_rd_tiles, PktType)
  
  # Defines FlitType with a 32-bit width.
  FlitType = mk_bits(flit_width)
  NoCFlitType = mk_inter_cgra_pkt(num_cgra_columns, num_cgra_rows, num_tiles, num_rd_tiles, FlitType)

  # Constructs packets. DataType is the only non-zero field; all other fields (Cmd, DataAddr, Ctrl, CtrlAddr.) are zero for easy debugging.
  # Note: The data is reversed to ensure the output Flit sequence is FFFFFFFF, EEEEEEEE, DDDDDDDD, CCCCCCCC.
  pkt1 = NoCPktType(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, PktType(0xCCCCCCCCDDDDDDDDEEEEEEEEFFFFFFFF))
  
  pkt2 = NoCPktType(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, PktType(0x44444444555555556666666677777777))
  
  pkt_msgs = [ pkt1, pkt2 ]

  # Expected Flits for Packet 1 (4 flits).
  flit1_1 = NoCFlitType(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, Bits(flit_width, 0xFFFFFFFF))
  flit1_2 = NoCFlitType(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, Bits(flit_width, 0xEEEEEEEE))
  flit1_3 = NoCFlitType(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, Bits(flit_width, 0xDDDDDDDD))
  flit1_4 = NoCFlitType(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, Bits(flit_width, 0xCCCCCCCC))

  # Expected Flits for Packet 2 (4 flits).
  flit2_1 = NoCFlitType(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, Bits(flit_width, 0x77777777))
  flit2_2 = NoCFlitType(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, Bits(flit_width, 0x66666666))
  flit2_3 = NoCFlitType(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, Bits(flit_width, 0x55555555))
  flit2_4 = NoCFlitType(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, Bits(flit_width, 0x44444444))

  expected_flit_msgs = [ flit1_1, flit1_2, flit1_3, flit1_4,
                         flit2_1, flit2_2, flit2_3, flit2_4 ]

  # Generates TestHarness and runs the simulation.
  th = TestHarness( NoCPktType, NoCFlitType, pkt_msgs, expected_flit_msgs )

  th.elaborate()
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)
