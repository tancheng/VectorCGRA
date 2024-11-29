#=========================================================================
# ChannelNormalRTL.py
#=========================================================================
# RTL channel module for connecting basic components within a CGRA tile
# and across tiles. A channel normally takes single cycle while it could
# be parameterizable with a few cycles in case the NoC is a torus.
#
# This simple channel has latency insensitive send/recv interfaces.
#
# Author : Cheng Tan
#   Date : Nov 26, 2024

from pymtl3 import *
from pymtl3.stdlib.dstruct.queues import NormalQueue
from ..lib.ifcs import RecvIfcRTL, SendIfcRTL

class ChannelNormalRTL( Component ):
  def construct(s, DataType, latency = 1, num_entries = 2):

    # Constant
    assert(latency > 0)
    s.latency = latency
    # num_entries indicates how many items could be temporarily
    # stored within the channel when there is congestion. Note
    # that this would contribute to the overall register file size
    # and it has nothing to do with the latency.
    s.num_entries = num_entries
    s.data = DataType(0, 0)
    s.count = OutPort(mk_bits(clog2(s.num_entries+1)))

    # Interface
    s.recv = RecvIfcRTL(DataType)
    s.send = SendIfcRTL(DataType)

    # Component
    s.queues = [NormalQueue(DataType, s.num_entries)
                for _ in range(s.latency)]

    s.count //= s.queues[s.latency - 1].count

    # Connections
    s.recv.rdy //= s.queues[0].enq_rdy

    @update
    def process():
      for i in range(s.latency - 1):
        s.queues[i+1].enq_msg @= s.queues[i].deq_msg
        s.queues[i+1].enq_en @= s.queues[i].deq_rdy & s.queues[i+1].enq_rdy
        s.queues[i].deq_en @= s.queues[i+1].enq_en

      s.queues[0].enq_msg @= s.recv.msg
      s.queues[0].enq_en @= s.queues[0].enq_rdy & s.recv.en

      s.send.msg @= s.queues[s.latency-1].deq_msg
      # s.send.msg.delay @= s.queues[s.latency-1].deq_msg.delay
      s.send.en @= s.send.rdy & s.queues[s.latency-1].deq_rdy
      s.queues[s.latency-1].deq_en @= s.send.en
      # print("s.queues[0].deq_en: ", s.queues[0].deq_en)
      # print("s.queues[0].enq_en: ", s.queues[0].enq_en)


  def line_trace( s ):
    trace = " -> ".join("channel_stage_" + str(i) + ": " + s.queues[i].line_trace() for i in range(s.latency))

