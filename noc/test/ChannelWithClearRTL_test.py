'''
=========================================================================
ChannelWithClearRTL_test.py
=========================================================================
Test for ChannelWithClearRTL using Source and Sink

Author : Yufei Yang
  Date : Sep 9, 2025
'''


from pymtl3 import *
from ..ChannelWithClearRTL import ChannelWithClearRTL
from ...noc.PyOCN.pymtl3_net.ocnlib.utils import run_sim
from ...lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ...lib.basic.val_rdy.queues import NormalQueueRTL
import pytest


#-------------------------------------------------------------------------
# TestHarness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, MsgType, src_msgs, clear_src_msgs, sink_msgs):

    s.src = TestSrcRTL(MsgType, src_msgs)
    s.sink = TestSinkRTL(MsgType, sink_msgs)
    s.src_clear = TestSrcRTL(Bits1, clear_src_msgs)
    s.dut = ChannelWithClearRTL(MsgType)

    # Connections
    s.src.send //= s.dut.recv
    s.dut.send //= s.sink.recv
    s.src_clear.send.msg //= s.dut.clear
  
    @update
    def issue_clear():
      s.src_clear.send.rdy @= 1

  def done(s):
    return s.src.done() and s.sink.done() and s.src_clear.done()

  def line_trace(s):
    return s.src.line_trace() + "-> | " + \
           s.dut.line_trace() + " | -> " + \
           s.sink.line_trace()

#-------------------------------------------------------------------------
# Test cases
#-------------------------------------------------------------------------

input_msgs = [b16(4), b16(1), b16(2), b16(3)]
# Clear signal valids at clock cycle 3 and 4, then channel will no long have value after the rising edge of clock 4.
clear_signals = [b1(0), b1(0), b1(1), b1(1)]
# As we have latency=2, b16(4) can be normally printed at cycle 3,
# but b16(1) cannot be printed as usual at cycle 4 because it has be cleared,
# b16(2) and b16(3) are also not wrote to channel because we keep clear signal to be valid.
expected_output_msgs = [b16(4)]

def test_passthrough():
  th = TestHarness(Bits16, input_msgs, clear_signals, input_msgs)
  run_sim(th)

def test_normal2_simple():
  th = TestHarness(Bits16, input_msgs, clear_signals, expected_output_msgs)
  th.set_param("top.dut.construct", latency= 2)
  run_sim(th)

