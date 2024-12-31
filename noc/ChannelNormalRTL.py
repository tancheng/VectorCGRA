'''
=========================================================================
ChannelNormalRTL.py
=========================================================================
RTL channel module for connecting basic components within a CGRA tile
and across tiles. A channel normally takes single cycle while it could
be parameterizable with a few cycles in case the NoC is a torus.

This simple channel has latency insensitive send/recv interfaces.

Author : Cheng Tan
  Date : Nov 26, 2024
'''

from pymtl3 import *
from ..lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ..lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ..lib.basic.val_rdy.queues import NormalQueueRTL

class ChannelNormalRTL(Component):

  def construct(s, DataType, latency = 1, num_entries = 2):
    # Constant
    assert(latency > 0)
    s.latency = latency
    # num_entries indicates how many items could be temporarily
    # stored within the channel when there is congestion. Note
    # that this would contribute to the overall register file size
    # and it has nothing to do with the latency.
    s.num_entries = num_entries
    s.data = DataType()
    s.count = OutPort(mk_bits(clog2(s.num_entries + 1)))

    # Interface
    s.recv = RecvIfcRTL(DataType)
    s.send = SendIfcRTL(DataType)

    # Component
    s.queues = [NormalQueueRTL(DataType, s.num_entries)
                for _ in range(s.latency)]


    # Connections
    s.count //= s.queues[s.latency - 1].count
    for i in range(s.latency - 1):
      s.queues[i+1].recv //= s.queues[i].send

    s.queues[0].recv //= s.recv
    s.queues[s.latency - 1].send //= s.send

  def line_trace( s ):
    trace = " -> ".join("channel_stage_" + str(i) + ": " + s.queues[i].line_trace() for i in range(s.latency))
    return trace

