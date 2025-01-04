"""
=========================================================================
LinkOrRTL.py
=========================================================================
RTL link module for taking two data and send out the one with valid
predicate.
The link is different from channel that it has no latency. The links
are connected to the channels from crossbar and the outports from the
FUs.

Author : Cheng Tan
  Date : April 19, 2024
"""

from pymtl3 import *
from ..lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ..lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL

class LinkOrRTL(Component):

  def construct(s, DataType):

    # Interface
    s.recv_fu = RecvIfcRTL(DataType)
    s.recv_xbar = RecvIfcRTL(DataType)
    s.send = SendIfcRTL(DataType)

    @update
    def process():
      # Initializes the delivered message.
      s.send.msg @= DataType()

      # The messages from two sources (i.e., xbar and FU) won't be valid
      # simultaneously (confliction would be caused if they both are valid),
      # which is guaranteed by the compiler/software.
      s.send.msg.predicate @= s.recv_fu.msg.predicate | s.recv_xbar.msg.predicate

      if (s.recv_fu.msg.predicate):
        s.send.msg.payload @= s.recv_fu.msg.payload
      else:
        s.send.msg.payload @= s.recv_xbar.msg.payload

      # FIXME: bypass won't be necessary any more with separate xbar design.
      # s.send.msg.bypass @= 0
      # s.send.msg.delay @= s.recv_fu.msg.delay | s.recv_xbar.msg.delay

      # s.send.val @= s.send.rdy & (s.recv_fu.val | s.recv_xbar.val)
      s.send.val @= s.recv_fu.val | s.recv_xbar.val
      s.recv_fu.rdy @= s.send.rdy
      s.recv_xbar.rdy @= s.send.rdy

  def line_trace(s):
    return f"from_fu:{s.recv_fu.msg} or from_xbar:{s.recv_xbar.msg} => out:{s.send.msg} ## "

