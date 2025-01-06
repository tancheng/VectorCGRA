'''
=========================================================================
RegisterRTL.py
=========================================================================
RTL register module specifically for predication.

Author : Cheng Tan
  Date : Aug 22, 2021
'''

from pymtl3 import *
from ..lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ..lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ..lib.basic.val_rdy.queues import NormalQueueRTL

class RegisterRTL(Component):

  def construct(s, DataType, latency = 1):

    # Constant
    s.latency = latency
    s.num_entries = 2
    s.data = DataType(0)

    # Interface
    s.recv = RecvIfcRTL(DataType)
    s.send = SendIfcRTL(DataType)

    # Component
    s.queues = [NormalQueueRTL(DataType, s.num_entries)
                for _ in range(s.latency)]

    # Connections
    for i in range(s.latency - 1):
      s.queues[i+1].recv //= s.queues[i].send

    s.queues[0].recv //= s.recv
    s.queues[s.latency - 1].send //= s.send

  def line_trace(s):
    trace = '>'
    for i in range(s.latency):
      trace += s.queues[i].line_trace() + '>'
    return f"{s.recv.msg}({trace}){s.send.msg} ## "

