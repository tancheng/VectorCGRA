"""
==========================================================================
CtrlMuxRTL.py
==========================================================================
Control multiplexer for selecting between bypass or fu inputs.

"""

from pymtl3 import *
from pymtl3.stdlib.primitive import RegisterFile
from .RegisterBankRTL import RegisterBankRTL
from ...lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ...lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ...lib.opt_type import *
from ...lib.util.common import *

class CtrlMuxRTL(Component):

  def construct(s, DataType, CtrlType, num_fu_in_ports):

    # Interface
    s.inport_opt = InPort(CtrlType)
    s.recv_data_from_routing_crossbar = [RecvIfcRTL(DataType) for _ in range(num_fu_in_ports)]
    s.recv_data_from_fu_crossbar = [RecvIfcRTL(DataType) for _ in range(num_fu_in_ports)]
    s.send_data_to_fu = [SendIfcRTL(DataType) for _ in range(num_fu_in_ports)]

    @update
    def update_msgs_signals():
        # Initializes signals.
        for i in range(num_fu_in_ports):
            s.send_data_to_fu[i].msg @= DataType()
            s.recv_data_from_routing_crossbar[i].rdy @= 0
            s.recv_data_from_fu_crossbar[i].rdy @= 0
            s.send_data_to_fu[i].val @= 0
        
        for i in range(num_fu_in_ports):
            if s.recv_data_from_routing_crossbar[i].val:
                s.send_data_to_fu[i].msg @= \
                    s.recv_data_from_routing_crossbar[i].msg
            else:
                s.send_data_to_fu[i].msg @= \
                    s.reg_bank[i].send_data_to_fu.msg