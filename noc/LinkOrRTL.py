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
    s.fu_xbar_rdy = InPort(b1)
    s.send = SendIfcRTL(DataType)

    @update
    def process():
      # Initializes the delivered message.
      s.send.msg @= DataType()

      fu_active = s.recv_fu.val & s.fu_xbar_rdy
      xbar_active = s.recv_xbar.val

      if fu_active:
        s.send.msg.predicate @= s.send.msg.predicate | s.recv_fu.msg.predicate
        s.send.msg.payload @= s.send.msg.payload | s.recv_fu.msg.payload
      if xbar_active:
        s.send.msg.predicate @= s.send.msg.predicate | s.recv_xbar.msg.predicate
        s.send.msg.payload @= s.send.msg.payload | s.recv_xbar.msg.payload

      # FIXME: bypass won't be necessary any more with separate xbar design.
      # s.send.msg.bypass @= 0
      # s.send.msg.delay @= s.recv_fu.msg.delay | s.recv_xbar.msg.delay

      # Only let FU traffic win once the FU crossbar has actually committed
      # the multicast/send for this cycle; otherwise the link can expose
      # transient FU output and create cross-tile bubbles.
      s.send.val @= fu_active | xbar_active
      s.recv_fu.rdy @= s.send.rdy & s.fu_xbar_rdy
      s.recv_xbar.rdy @= s.send.rdy

  def line_trace(s):
    return f"from_fu:{s.recv_fu.msg} or from_xbar:{s.recv_xbar.msg} => out:{s.send.msg} ## "
