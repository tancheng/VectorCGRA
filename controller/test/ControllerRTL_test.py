'''
=========================================================================
ChannelRTL_test.py
=========================================================================
Simple test for Channel.

Author : Cheng Tan
  Date : Dec 2, 2024
'''


from pymtl3 import *
from pymtl3.stdlib.test_utils import TestVectorSimulator
from ..ControllerRTL import ControllerRTL
from ...lib.basic.en_rdy.test_sinks import TestSinkRTL
from ...lib.basic.en_rdy.test_srcs import TestSrcRTL
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestValRdySrcRTL
from ...lib.basic.val_rdy.ifcs import SendIfcRTL as ValRdySendIfcRTL
from ...lib.basic.val_rdy.ifcs import RecvIfcRTL as ValRdyRecvIfcRTL
from ...lib.messages import *
from ...noc.PyOCN.pymtl3_net.ocnlib.test.stream_sinks import NetSinkRTL as TestNetSinkRTL
import pytest


#-------------------------------------------------------------------------
# TestHarness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, MsgType, PktType, AddrType, src_msgs, sink_msgs, src_pkts, sink_pkts):

    cmp_fn = lambda a, b : a.payload == b.payload
    s.src_en_rdy = TestSrcRTL(MsgType, src_msgs)
    s.sink_en_rdy = TestSinkRTL(MsgType, sink_msgs)
    s.src_val_rdy = TestValRdySrcRTL(PktType, src_pkts)
    s.sink_val_rdy = TestNetSinkRTL(PktType, sink_pkts, cmp_fn = cmp_fn)

    s.dut = ControllerRTL(PktType, MsgType, AddrType)

    # Connections
    s.src_en_rdy.send //= s.dut.recv_from_master
    s.dut.send_to_master //= s.sink_en_rdy.recv
    s.src_val_rdy.send //= s.dut.recv_from_other
    s.dut.send_to_other //= s.sink_val_rdy.recv

  def done(s):
    return s.src_en_rdy.done() and s.sink_en_rdy.done() and \
           s.src_val_rdy.done() and s.sink_val_rdy.done()

  def line_trace( s ):
    return s.dut.line_trace()
    # return s.src.line_trace() + "-> | " + s.dut.line_trace()
    # return s.src.line_trace() + "-> | " + s.dut.line_trace() + \
    #                            " | -> " + s.sink.line_trace()

#-------------------------------------------------------------------------
# run_rtl_sim
#-------------------------------------------------------------------------

def run_sim(test_harness, max_cycles=20):

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

  # Check timeout
  assert ncycles < max_cycles

  test_harness.sim_tick()
  test_harness.sim_tick()
  test_harness.sim_tick()

#-------------------------------------------------------------------------
# Test cases
#-------------------------------------------------------------------------

def mk_src_pkts( nterminals, lst ):
  src_pkts = [ [] for _ in range( nterminals ) ]
  src = 0
  for pkt in lst:
    if hasattr(pkt, 'fl_type'):
      if pkt.fl_type == 0:
        src = pkt.src
    else:
      src = pkt.src
    src_pkts[ src ].append( pkt )
  return src_pkts

DataType = mk_data(32, 1)
test_msgs = [DataType(7, 1, 1), DataType(2, 1), DataType(3, 1)]
sink_msgs = [DataType(0xdeadbeef, 0), DataType(0xbeefdead, 0), DataType(0xdeedbeed, 0)]

nterminals = 4
Pkt = mk_ring_multi_cgra_pkt(nterminals, payload_nbits = 32,
                             predicate_nbits = 1)
src_pkts = [
    #   src  dst opq vc payload     predicate
    Pkt(0,   0,  0,  0, 0xdeadbeef, 0),
    Pkt(0,   0,  0,  0, 0xbeefdead, 0),
    Pkt(0,   0,  0,  0, 0xdeedbeed, 0),
]

sink_pkts = [
    #   src  dst opq vc payload     predicate
    Pkt(0,   0,  0,  0, 7, 0),
    Pkt(0,   0,  0,  0, 2, 0),
    Pkt(0,   0,  0,  0, 3, 0),
]

ctrl_mem_size = 4
AddrType = mk_bits(clog2(ctrl_mem_size))

def test_simple():
  th = TestHarness(DataType, Pkt, AddrType, test_msgs, sink_msgs, src_pkts, sink_pkts)
  run_sim(th)

