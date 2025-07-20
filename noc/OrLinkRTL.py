"""
=========================================================================
OrLinkRTL.py
=========================================================================
RTL link module for taking multiple data and send out the one with valid
predicate.
Link is different from channel as it has no latency.

Author : Cheng Tan
  Date : Feb 7, 2025
"""

from pymtl3 import *
from ..lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ..lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL

class OrLinkRTL(Component):

  def construct(s, DataType, num_in_ports, nbits_payload = 32):

    # Constants.
    PayloadType = mk_bits(nbits_payload)
    InPortType = mk_bits(clog2(num_in_ports))

    # Interfaces.
    s.recv = [RecvIfcRTL(DataType) for _ in range(num_in_ports)]
    s.send = SendIfcRTL(DataType)

    # Components.
    s.recv_valids = Wire(num_in_ports)

    @update
    def process():
      # Initializes the delivered message.
      s.send.msg @= DataType()
      s.send.val @= 0

      temp_predicate = b1(0)
      temp_payload = PayloadType(0)
      for i in range(num_in_ports):
        s.recv_valids[i] @= s.recv[i].val
        temp_predicate |= s.recv[i].msg.predicate
        temp_payload |= s.recv[i].msg.payload

      # # The messages from multiple sources shouldn't be valid
      # # simultaneously (confliction would be caused if more than
      # # one are valid), which is guaranteed by the compiler/software.
      if reduce_or(s.recv_valids):
        s.send.msg.predicate @= temp_predicate
        s.send.msg.payload @= temp_payload
        s.send.val @= 1

      for i in range(num_in_ports):
        s.recv[i].rdy @= s.send.rdy

  def line_trace(s):
    recv_str = "recv: " + "|".join([str(data.msg) for data in s.recv])
    return f"or_link:{recv_str} => out:{s.send.msg} ## "

