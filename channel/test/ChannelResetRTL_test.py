'''
=========================================================================
ChannelResetRTL_test.py
=========================================================================
Test for ChannelResetRTL using Source and Sink

Author : Yufei Yang
  Date : Sep 9, 2025
'''


from pymtl3 import *
from ..ChannelResetRTL import ChannelResetRTL
from ...noc.PyOCN.pymtl3_net.ocnlib.utils import run_sim
from ...lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ...lib.basic.val_rdy.queues import NormalQueueRTL
import pytest


#-------------------------------------------------------------------------
# TestHarness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, MsgType, src_msgs, sink_msgs, count_reset_src_msgs):

    s.src = TestSrcRTL(MsgType, src_msgs)
    s.sink = TestSinkRTL(MsgType, sink_msgs)
    s.src_reset = TestSrcRTL(Bits1, count_reset_src_msgs)
    s.dut = ChannelResetRTL(MsgType)

    # Connections
    s.src.send //= s.dut.recv
    s.dut.send //= s.sink.recv
    s.src_reset.send.msg //= s.dut.count_reset
  
    @update
    def issue_count_reset():
      s.src_reset.send.rdy @= 1

  def done(s):
    return s.src.done() and s.sink.done() and s.src_reset.done()

  def line_trace(s):
    return s.src.line_trace() + "-> | " + \
           s.dut.line_trace() + " | -> " + \
           s.sink.line_trace()

#-------------------------------------------------------------------------
# Test cases
#-------------------------------------------------------------------------

test_msgs = [b16(4), b16(1), b16(2), b16(3)]
# Resets the count at clock cycle 2, then b16(2), b16(3) should be cleared.
count_reset_msgs = [b1(0), b1(0), b1(1), b1(0)]
test_reset_msgs = [b16(4), b16(1)]

def test_passthrough():
  th = TestHarness(Bits16, test_msgs, test_msgs, count_reset_msgs)
  run_sim(th)

def test_normal2_simple():
  th = TestHarness(Bits16, test_msgs, test_reset_msgs, count_reset_msgs)
  th.set_param("top.dut.construct", latency= 2)
  run_sim(th)

