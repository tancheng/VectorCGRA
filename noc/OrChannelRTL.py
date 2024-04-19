#=========================================================================
# OrChannelRTL.py
#=========================================================================
# RTL channel module for taking two data, or them, then send out.
# This simple channel has no latency, it is just an OR. It is named as
# channel just because it would be used to connect other channels that
# are related to crossbars.
#
# Author : Cheng Tan
#   Date : April 19, 2024

from pymtl3                       import *
from pymtl3.stdlib.dstruct.queues import BypassQueue, NormalQueue
from ..lib.ifcs import RecvIfcRTL, SendIfcRTL


class OrChannelRTL( Component ):
  def construct(s, DataType ):

    # Interface
    s.recv_fu    = RecvIfcRTL( DataType )
    s.recv_xbar  = RecvIfcRTL( DataType )
    s.send  = SendIfcRTL( DataType )

    @update
    def process():
      s.send.msg           @= DataType()
      s.send.msg.payload   @= s.recv_fu.msg.payload | s.recv_xbar.msg.payload
      s.send.msg.predicate @= s.recv_fu.msg.predicate | s.recv_xbar.msg.predicate
      # bypass won't be necessary at more with separate xbar design.
      s.send.msg.bypass    @= 0
      s.send.msg.delay     @= s.recv_fu.msg.delay | s.recv_xbar.msg.delay

      s.send.en            @= s.send.rdy & ( s.recv_fu.en | s.recv_xbar.en )
      s.recv_fu.rdy        @= s.send.rdy
      s.recv_xbar.rdy      @= s.send.rdy

  def line_trace( s ):
    # trace = '>' + s.send.msg.line_trace() + '>'
    # return trace
    return f"from_fu:{s.recv_fu.msg} or from_xbar:{s.recv_xbar.msg} => out:{s.send.msg} ## "

