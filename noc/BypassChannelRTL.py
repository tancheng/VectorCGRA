#=========================================================================
# BypassChannelRTL.py
#=========================================================================
# RTL channel module for connecting basic components to form accelerator.
# This simple channel has latency insensitive send/recv interfaces.
#
# Author : Cheng Tan
#   Date : Feb 22, 2020

from pymtl3 import *
from pymtl3.stdlib.dstruct.queues import BypassQueue
from ..lib.basic.en_rdy.ifcs import RecvIfcRTL, SendIfcRTL


class BypassChannelRTL( Component ):
  def construct(s, DataType ):

    # Constant
    s.data = DataType(0, 0)

    # Interface
    s.recv  = RecvIfcRTL( DataType )
    s.send  = SendIfcRTL( DataType )

    # Component
    s.bypass_q = BypassQueue( DataType, num_entries=1 )
    s.bypass_q.enq_en  //= s.recv.en
    s.bypass_q.enq_msg //= s.recv.msg
    s.bypass_q.enq_rdy //= s.recv.rdy

    @update
    def process():
      s.send.msg           @= DataType()
      s.send.msg.payload   @= s.bypass_q.deq_msg.payload
      s.send.msg.predicate @= s.bypass_q.deq_msg.predicate
      s.send.msg.bypass    @= 0
      s.send.msg.valid     @= s.bypass_q.deq_rdy
      s.send.en            @= s.send.rdy & s.bypass_q.deq_rdy
      s.bypass_q.deq_en    @= s.send.rdy & s.bypass_q.deq_rdy

  def line_trace( s ):
    trace = '>'
    return f'{s.bypass_q.line_trace()}'

