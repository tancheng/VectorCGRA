"""
=========================================================================
SelectorRTL.py
=========================================================================
RTL selector module.

Author : Cheng Tan
  Date : Feb 7, 2025
"""

from pymtl3 import *
from ..lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ..lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL

class SelectorRTL(Component):

  def construct(s, DataType, num_in_ports):

    # Constants.
    InPortType = mk_bits(clog2(num_in_ports))

    # Interfaces.
    s.recv = [RecvIfcRTL(DataType) for _ in range(num_in_ports)]
    s.send = SendIfcRTL(DataType)
    s.recv_from = InPort(InPortType)

    @update
    def process():
      # The messages from multiple sources shouldn't be valid
      # simultaneously (confliction would be caused if more than
      # one are valid), which is guaranteed by the compiler/software.
      s.send.msg @= s.recv[s.recv_from].msg
      s.send.val @= s.recv[s.recv_from].val
      s.recv[s.recv_from].rdy @= s.send.rdy

  def line_trace(s):
    recv_str = "recv: " + "|".join([str(data.msg) for data in s.recv])
    return f"or_link:{recv_str} (recv_from:{s.recv_from}) => out:{s.send.msg} ## "

