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

    # When the FU crossbar multicasts to multiple outputs, it asserts val
    # on all of them. But it only commits (dequeues its input) when ALL
    # outputs accept simultaneously. Without this guard, an output that
    # is ready can accept data even though the crossbar hasn't committed,
    # causing duplicate data delivery on subsequent cycles.
    #
    # Example: In the FIR LoopCounter test, Tile 0's LoopCounter produces
    # the loop index `i` and multicasts it to 3 destinations via the FU
    # crossbar:
    #   fu_xbar_outport = [FuOutType(1), 0, 0, FuOutType(1), 0, 0, 0, 0,
    #                      FuOutType(1), 0, 0, 0]
    #   - Index 0 (NORTH)   -> Tile 2 for ADD
    #   - Index 3 (EAST)    -> Tile 1 for EXTRACT_PREDICATE
    #   - Index 8 (FU_IN_0) -> register bank for next-cycle reuse
    # Without this guard, if EAST is ready but NORTH isn't, EAST's
    # LinkOrRTL forwards the data prematurely, causing EAST to receive a
    # duplicate on the next cycle, which leads to a deadlock.
    #
    # fu_xbar_multi_cast_committed indicates the FU crossbar has committed
    # its multicast transaction, i.e., all destination outputs accepted.
    s.fu_xbar_multi_cast_committed = InPort(b1)

    @update
    def process():
      # Initializes the delivered message.
      s.send.msg @= DataType()

      # The messages from two sources (i.e., xbar and FU) won't be valid
      # simultaneously (confliction would be caused if they both are valid),
      # which is guaranteed by the compiler/software.
      s.send.msg.predicate @= s.recv_fu.msg.predicate | s.recv_xbar.msg.predicate
      s.send.msg.payload @= s.recv_xbar.msg.payload | s.recv_fu.msg.payload

      # FIXME: bypass won't be necessary any more with separate xbar design.
      # s.send.msg.bypass @= 0
      # s.send.msg.delay @= s.recv_fu.msg.delay | s.recv_xbar.msg.delay

      # s.send.val @= s.send.rdy & (s.recv_fu.val | s.recv_xbar.val)
      # Gate recv_fu's contribution to send.val with fu_xbar_multi_cast_committed
      # to prevent the downstream channel from accepting data unless the FU
      # crossbar has actually committed its multicast (all destinations ready).
      s.send.val @= (s.recv_fu.val & s.fu_xbar_multi_cast_committed) | s.recv_xbar.val
      s.recv_fu.rdy @= s.send.rdy
      s.recv_xbar.rdy @= s.send.rdy

  def line_trace(s):
    return f"from_fu:{s.recv_fu.msg} or from_xbar:{s.recv_xbar.msg} => out:{s.send.msg} ## "

