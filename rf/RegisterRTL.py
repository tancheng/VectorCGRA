'''
=========================================================================
RegisterRTL.py
=========================================================================
RTL register module specifically for predication.

Author : Cheng Tan
  Date : Aug 22, 2021
'''


from pymtl3 import *
from pymtl3.stdlib.dstruct.queues import NormalQueue
from ..lib.basic.en_rdy.ifcs import RecvIfcRTL, SendIfcRTL


class RegisterRTL( Component ):

  def construct(s, DataType, latency = 1 ):

    # Constant
    s.latency     = latency
    s.num_entries = 2
    s.data = DataType( 0 )

    # Interface
    s.recv  = RecvIfcRTL( DataType )
    s.send  = SendIfcRTL( DataType )

    # Component
    s.queues = [ NormalQueue( DataType, s.num_entries )
                 for _ in range( s.latency ) ]

    @update
    def process():
      s.recv.rdy @= s.queues[0].enq_rdy
      s.queues[0].enq_msg @= s.recv.msg
      s.queues[0].enq_en  @= s.recv.en & s.queues[0].enq_rdy
      for i in range(s.latency - 1):
        s.queues[i+1].enq_msg @= s.queues[i].deq_msg
        s.queues[i+1].enq_en  @= s.queues[i].deq_rdy & s.queues[i+1].enq_rdy
        s.queues[i].deq_en    @= s.queues[i+1].enq_en

      s.send.msg @= s.queues[s.latency-1].deq_msg
      s.send.en  @= s.send.rdy & s.queues[s.latency-1].deq_rdy
      s.queues[s.latency-1].deq_en @= s.send.en

  def line_trace( s ):
    trace = '>'
    for i in range( s.latency ):
      trace += s.queues[i].line_trace() + '>'
    return f"{s.recv.msg}({trace}){s.send.msg} ## "

