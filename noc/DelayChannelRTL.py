#=========================================================================
# DelayChannelRTL.py
#=========================================================================
# RTL channel module for testing the delayed data arrival. Basically, it
# set the send.msg.delay signal for a few cycles. The consumer shouldn't
# accept/consume the data (i.e., set the rdy) before the delay signal is
# clear.
#
# Author : Cheng Tan
#   Date : Aug 26, 2023

from pymtl3                       import *
from pymtl3.stdlib.dstruct.queues import BypassQueue, NormalQueue
from ..lib.ifcs                   import RecvIfcRTL, SendIfcRTL


class DelayChannelRTL( Component ):
  def construct(s, DataType, delay = 5 ):

    # Constant
    s.num_entries = 2
    s.data = DataType(0, 0)
    s.count = OutPort( mk_bits( clog2( s.num_entries+1 ) ) )

    # Interface
    s.recv  = RecvIfcRTL( DataType )
    s.send  = SendIfcRTL( DataType )


    # Component
    s.queue    = NormalQueue( DataType, s.num_entries )
    s.bypass_q = BypassQueue( DataType, num_entries=1 )

    s.bypass_q.enq_en  //= s.recv.en
    s.bypass_q.enq_msg //= s.recv.msg
    s.bypass_q.enq_rdy //= s.recv.rdy

    s.count            //= s.queue.count

    # Tracks the cycles spent in this channel..
    s.timing = Wire( mk_bits( clog2( delay + 1 ) ) )

    @update
    def process():
      if ~s.bypass_q.deq_msg.bypass:
        s.queue.enq_msg   @= s.bypass_q.deq_msg
        s.bypass_q.deq_en @= s.queue.enq_rdy & s.bypass_q.deq_rdy
        s.queue.enq_en    @= s.queue.enq_rdy & s.bypass_q.deq_rdy

        s.send.msg        @= s.queue.deq_msg
        s.send.msg.delay  @= (s.timing != delay)
        s.send.en         @= s.send.rdy & s.queue.deq_rdy
        s.queue.deq_en    @= s.send.rdy & s.queue.deq_rdy

      else:
        s.queue.enq_en       @= 0
        s.queue.enq_msg      @= DataType()
        s.queue.deq_en       @= 0

        s.send.msg           @= DataType()
        s.send.msg.payload   @= s.bypass_q.deq_msg.payload
        s.send.msg.predicate @= s.bypass_q.deq_msg.predicate
        s.send.msg.bypass    @= 0
        s.send.msg.delay     @= (s.timing != delay)
        s.send.en            @= s.send.rdy & s.bypass_q.deq_rdy
        s.bypass_q.deq_en    @= s.send.rdy & s.bypass_q.deq_rdy

    @update_ff
    def update_timing():
      if s.timing == delay + 1:
        s.timing <<= 0
      else:
        s.timing <<= s.timing + 1

  def line_trace( s ):
    trace = '>'
    trace += s.bypass_q.line_trace() + '>'
    trace += s.queue.line_trace() + '>'
    return trace # f'{s.bypass_q.line_trace()}'
    return f"in:{s.recv.msg}({trace})out:{s.send.msg}.count:{s.count} ## "

