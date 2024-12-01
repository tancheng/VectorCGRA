#=========================================================================
# ChannelRTL.py
#=========================================================================
# RTL channel module for connecting basic components to form accelerator.
# This simple channel has latency insensitive send/recv interfaces.
#
# Author : Cheng Tan
#   Date : Feb 22, 2020

from pymtl3                       import *
from pymtl3.stdlib.dstruct.queues import BypassQueue, NormalQueue
from ..lib.basic.en_rdy.ifcs import RecvIfcRTL, SendIfcRTL


class ChannelRTL( Component ):
  def construct(s, DataType, latency = 1 ):

    # Constant
    s.latency     = latency
    s.num_entries = 2
    s.data = DataType(0, 0)
    s.count = OutPort( mk_bits( clog2( s.num_entries+1 ) ) )

    # Interface
    s.recv  = RecvIfcRTL( DataType )
    s.send  = SendIfcRTL( DataType )


    # Component
    s.queues = [ NormalQueue( DataType, s.num_entries )
                 for _ in range( s.latency ) ]

    s.bypass_q = BypassQueue( DataType, num_entries=1 )
    s.bypass_q.enq_en  //= s.recv.en
    s.bypass_q.enq_msg //= s.recv.msg
    s.bypass_q.enq_rdy //= s.recv.rdy


    s.count //= s.queues[s.latency - 1].count

    @update
    def process():
      for i in range(s.latency - 1):
        s.queues[i+1].enq_msg @= s.queues[i].deq_msg
        s.queues[i+1].enq_en  @= s.queues[i].deq_rdy & s.queues[i+1].enq_rdy
        s.queues[i].deq_en    @= s.queues[i+1].enq_en

      if ~s.bypass_q.deq_msg.bypass:
        s.queues[0].enq_msg @= s.bypass_q.deq_msg
        s.bypass_q.deq_en   @= s.queues[0].enq_rdy & s.bypass_q.deq_rdy
        s.queues[0].enq_en  @= s.queues[0].enq_rdy & s.bypass_q.deq_rdy

        s.send.msg                   @= s.queues[s.latency-1].deq_msg
        # s.send.msg.delay             @= s.queues[s.latency-1].deq_rdy
        # s.send.msg.delay             @= s.queues[s.latency-1].deq_msg.delay
        # Set the delay if FU not yet completes pipeline (the msg.delay is
        # set by the FU) or the data has not yet arrived due to the delay
        # propagation.
        # s.send.msg.delay             @= s.queues[s.latency-1].deq_msg.delay | \
        #                                 ~s.queues[s.latency-1].deq_rdy
        s.send.msg.delay             @= s.queues[s.latency-1].deq_msg.delay
        s.send.en                    @= s.send.rdy & s.queues[s.latency-1].deq_rdy
        s.queues[s.latency-1].deq_en @= s.send.rdy & s.queues[s.latency-1].deq_rdy
        # print("s.queues[0].deq_en: ", s.queues[0].deq_en)
        # print("s.queues[0].enq_en: ", s.queues[0].enq_en)
        # print("s.bypass_q.deq_rdy: ", s.bypass_q.deq_rdy)

      else:
        s.queues[0].enq_en           @= 0
        s.queues[0].enq_msg          @= DataType()
        s.queues[s.latency-1].deq_en @= 0

        s.send.msg           @= DataType()
        s.send.msg.payload   @= s.bypass_q.deq_msg.payload
        s.send.msg.predicate @= s.bypass_q.deq_msg.predicate
        s.send.msg.bypass    @= 0
        # s.send.msg.delay     @= s.bypass_q.deq_rdy
        # Set the delay if FU not yet completes pipeline (the msg.delay is
        # set by the FU) or the data has not yet arrived due to the delay
        # propagation.
        # s.send.msg.delay     @= s.bypass_q.deq_msg.delay | ~s.bypass_q.deq_rdy
        s.send.msg.delay     @= s.bypass_q.deq_msg.delay
        s.send.en            @= s.send.rdy & s.bypass_q.deq_rdy
        s.bypass_q.deq_en    @= s.send.rdy & s.bypass_q.deq_rdy

  def line_trace( s ):
    trace = '>'
    trace += s.bypass_q.line_trace() + '>'
    for i in range( s.latency ):
      trace += s.queues[i].line_trace() + '>'
    return trace # f'{s.bypass_q.line_trace()}'
    return f"in:{s.recv.msg}({trace})out:{s.send.msg}.count:{s.count} ## "

