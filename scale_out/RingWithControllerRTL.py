"""
==========================================================================
RingWithControllerRTL.py
==========================================================================
Ring connecting multiple controllers.

Author : Cheng Tan
  Date : Dec 3, 2024
"""


from pymtl3 import *
from pymtl3.stdlib.primitive import RegisterFile
from ..lib.basic.en_rdy.ifcs import SendIfcRTL, RecvIfcRTL
from ..lib.basic.val_rdy.ifcs import SendIfcRTL as ValRdySendIfcRTL
from ..lib.basic.val_rdy.ifcs import RecvIfcRTL as ValRdyRecvIfcRTL
from ..lib.opt_type import *
from ..noc.PyOCN.pymtl3_net.ringnet.RingNetworkRTL import RingNetworkRTL
from ..controller.ControllerRTL import ControllerRTL
from ..noc.PyOCN.pymtl3_net.ocnlib.ifcs.positions import mk_ring_pos


class RingWithControllerRTL(Component):

  def construct(s, RingPktType, CGRADataType, CGRAAddrType, num_terminals):

    # Constant
    RingPos = mk_ring_pos(num_terminals)
    s.num_terminals = num_terminals

    # Interface

    # Request from/to master.
    s.recv_from_master = [RecvIfcRTL(CGRADataType) for _ in range(s.num_terminals)]
    s.send_to_master = [SendIfcRTL(CGRADataType) for _ in range(s.num_terminals)]

    # Components
    s.controller = [ControllerRTL(RingPktType, CGRADataType, CGRAAddrType)
                    for i in range(s.num_terminals)]
    s.ring = RingNetworkRTL(RingPktType, RingPos, num_terminals, 0)

    # Connections
    for i in range(s.num_terminals):
      s.recv_from_master[i] //= s.controller[i].recv_from_master
      s.send_to_master[i] //= s.controller[i].send_to_master

      # s.controller[i].recv_from_other //= s.ring.send[i]
      # s.controller[i].send_to_other //= s.ring.recv[i]
      s.ring.send[i] //= s.controller[i].recv_from_other
      s.ring.recv[i] //= s.controller[i].send_to_other


  def line_trace(s):
    res = "||\n".join([(("[controller["+str(i)+"]: ") + x.line_trace())
                       for (i,x) in enumerate(s.controller)])
    res += " ## ring: " + s.ring.line_trace()
    return res

