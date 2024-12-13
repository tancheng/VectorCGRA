"""
=========================================================================
RingNetworkRTL_test.py
=========================================================================
Test for RingNetworkRTL with CGRA message.

Author : Cheng Tan
  Date : Dec 1, 2024
"""


from pymtl3 import *
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ...lib.messages import *
from ...lib.opt_type import *
# from ...noc.PyOCN.pymtl3_net.ocnlib.ifcs.packets import mk_ring_pkt
from ...noc.PyOCN.pymtl3_net.ocnlib.ifcs.positions import mk_ring_pos
from ...noc.PyOCN.pymtl3_net.ocnlib.utils import run_sim
from ...noc.PyOCN.pymtl3_net.ocnlib.test.stream_sinks import NetSinkRTL as TestNetSinkRTL
from ...noc.PyOCN.pymtl3_net.ringnet.RingNetworkFL import ringnet_fl
from ...noc.PyOCN.pymtl3_net.ringnet.RingNetworkRTL import RingNetworkRTL


#-------------------------------------------------------------------------
# TestHarness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, MsgType, num_routers, src_msgs, sink_msgs):

    s.num_routers = num_routers
    RingPos = mk_ring_pos(num_routers)
    cmp_fn = lambda a, b : a.payload == b.payload

    s.srcs  = [TestSrcRTL(MsgType, src_msgs[i])
               for i in range(num_routers)]
    s.dut   = RingNetworkRTL(MsgType, RingPos, num_routers, 0)
    s.sinks = [TestNetSinkRTL(MsgType, sink_msgs[i], cmp_fn = cmp_fn)
               for i in range( num_routers)]

    # Connections
    for i in range (s.dut.num_routers):
      s.srcs[i].send //= s.dut.recv[i]
      s.dut.send[i] //= s.sinks[i].recv

  def done(s):
    srcs_done = True
    sinks_done = True
    for i in range(s.num_routers):
      srcs_done = srcs_done and s.srcs[i].done()
      sinks_done = sinks_done and s.sinks[i].done()
    return srcs_done and sinks_done

  def line_trace(s):
    return s.dut.line_trace()

#-------------------------------------------------------------------------
# mk_src_pkts
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

#=========================================================================
# Test cases
#=========================================================================

class RingNetwork_Tests:

  @classmethod
  def setup_class(cls):
    cls.DutType = RingNetworkRTL

  def _test_cgra_data(s, translation = ''):
    DataType = mk_data(16, 1)
    nterminals = 4
    Pkt = mk_ring_multi_cgra_pkt(nterminals, payload_nbits = 32,
                                 predicate_nbits = 1)
    src_pkts = mk_src_pkts(nterminals, [
      #   src  dst opq vc payload     predicate
      Pkt(0,   1,  0,  0, 0xfaceb00c, 1),
      Pkt(1,   2,  1,  0, 0xdeadbeef, 0),
      Pkt(2,   3,  2,  0, 0xbaadface, 1),
      Pkt(3,   0,  0,  0, 0xfaceb00c, 0),
    ])
    dst_pkts = ringnet_fl(src_pkts)
    th = TestHarness(Pkt, nterminals, src_pkts, dst_pkts)
    # cmdline_opts={'dump_vcd': False, 'test_verilog': translation,
    cmdline_opts={'dump_vcd': False, 'test_verilog': False,
                  'dump_vtb': False}
    run_sim(th, cmdline_opts)

  def test_cgra_data(self):
    self._test_cgra_data('zeros')

