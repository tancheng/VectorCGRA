'''
=========================================================================
ChannelWithClearRTL.py
=========================================================================
RTL channel module for connecting routers to form network. This simple
channel has latency insensitive send/recv interfaces. It also has
additional clear port for context switch.

Author : Yufei Yang
  Date : Sep 9, 2025
'''


from pymtl3 import *
from ..noc.PyOCN.pymtl3_net.ocnlib.ifcs.PhysicalDimension import PhysicalDimension
from ..lib.basic.val_rdy.ifcs import RecvIfcRTL, SendIfcRTL
from ..lib.basic.val_rdy.queues import NormalQueueWithClearRTL


class ChannelWithClearRTL( Component ):

  def construct(s, PacketType, QueueType=NormalQueueWithClearRTL, latency=0 ):

    # Constant
    s.dim         = PhysicalDimension()
    s.QueueType   = QueueType
    s.latency     = latency
    s.num_entries = 2

    # Interface
    s.recv  = RecvIfcRTL( PacketType )
    s.send  = SendIfcRTL( PacketType )
    s.clear = InPort( 1 )

    #---------------------------------------------------------------------
    # If latency > 0 and channel queue exists
    #---------------------------------------------------------------------

    if s.QueueType != None and s.latency > 0:

      # Component

      s.queues = [ s.QueueType( PacketType, s.num_entries )
                   for _ in range( s.latency ) ]

      # Connections

      s.recv //= s.queues[0].recv

      for i in range(s.latency-1):
        s.queues[i+1].recv //= s.queues[i].send
      s.queues[-1].send //= s.send

      for i in range(s.latency):
        s.queues[i].clear //= s.clear

    #---------------------------------------------------------------------
    # If latency==0 simply bypass
    #---------------------------------------------------------------------

    else:

      s.recv //= s.send

  def line_trace( s ):
    if s.QueueType != None and s.latency != 0:
      trace = '>'
      for i in range( s.latency ):
        trace += s.queues[i].line_trace() + '>'
      return f"{s.recv}({trace}){s.send}"
    else:
      return f"{s.recv}(0){s.send}"
