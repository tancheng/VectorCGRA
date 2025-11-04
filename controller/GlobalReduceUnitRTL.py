'''
==========================================================================
GlobalReduceUnitRTL.py
==========================================================================
A global reduce unit to record the count that data needs to be reduced,
and received the corresponding data. The unit will send the reduced data
back to the controller.

Author : Cheng Tan
  Date : Sep 8, 2025
'''

from ..lib.basic.val_rdy.ifcs import RecvIfcRTL
from ..lib.basic.val_rdy.ifcs import SendIfcRTL
from ..lib.basic.val_rdy.queues import NormalQueueRTL
from ..lib.cmd_type import *

from pymtl3 import *
from ..lib.messages import mk_controller_noc_xbar_pkt
from ..lib.util.data_struct_attr import *

class GlobalReduceUnitRTL(Component):

  def construct(s, InterCgraPktType):

    CgraPayloadType = InterCgraPktType.get_field_type(kAttrPayload)
    DataType = CgraPayloadType.get_field_type(kAttrData)
    ControllerXbarPktType = mk_controller_noc_xbar_pkt(InterCgraPktType)
    # Interfaces.
    s.recv_count = RecvIfcRTL(InterCgraPktType)
    s.recv_data = RecvIfcRTL(InterCgraPktType)
    s.send = SendIfcRTL(ControllerXbarPktType)

    # Components
    s.queue = NormalQueueRTL(InterCgraPktType, 16)
    s.target_count = Wire(DataType)
    s.receiving_count = Wire(DataType)
    s.sending_count = Wire(DataType)
    s.reduce_add_value = Wire(DataType)
    s.reduce_mul_value = Wire(DataType)

    # Connections.
    s.recv_count.rdy //= 1

    @update
    def set_recv_rdy():
      s.recv_data.rdy @= 0
      s.queue.recv.val @= 0
      s.queue.recv.msg @= InterCgraPktType(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
      if s.target_count.payload > s.receiving_count.payload:
        s.recv_data.rdy @= s.queue.recv.rdy
        s.queue.recv.msg @= s.recv_data.msg
        s.queue.recv.val @= s.recv_data.val

    @update_ff
    def update_count():
      if s.reset:
        s.target_count <<= DataType(0, 0, 0, 0)
        s.receiving_count <<= DataType(0, 0, 0, 0)
        s.sending_count <<= DataType(0, 0, 0, 0)
      else:
        if s.recv_count.val & s.recv_count.rdy:
          s.target_count <<= DataType(s.recv_count.msg.payload.data.payload, 0, 0, 0)
        if s.recv_data.val & s.recv_data.rdy:
          s.receiving_count <<= DataType(s.receiving_count.payload + 1, 0, 0, 0)
        if s.send.rdy & s.send.val:
          s.sending_count <<= DataType(s.sending_count.payload + 1, 0, 0, 0)
        elif (s.sending_count == s.receiving_count) & \
             (s.sending_count == s.target_count) & \
             (s.target_count.payload > 0):
          s.sending_count <<= DataType(0, 0, 0, 0)
          s.receiving_count <<= DataType(0, 0, 0, 0)

    @update
    def update_send():
      s.send.msg @= ControllerXbarPktType(0, 0)
      s.send.val @= 0
      s.queue.send.rdy @= 0
      if (s.target_count.payload > 0) & (s.receiving_count.payload == s.target_count.payload):
        # Updates the cmd type, result value, and src/dst.
        if s.queue.send.msg.payload.cmd == CMD_GLOBAL_REDUCE_ADD:
          s.send.msg.inter_cgra_pkt.payload.cmd @= CMD_GLOBAL_REDUCE_ADD_RESPONSE
          s.send.msg.inter_cgra_pkt.payload.data @= s.reduce_add_value
        elif s.queue.send.msg.payload.cmd == CMD_GLOBAL_REDUCE_MUL:
          s.send.msg.inter_cgra_pkt.payload.cmd @= CMD_GLOBAL_REDUCE_MUL_RESPONSE
          s.send.msg.inter_cgra_pkt.payload.data @= s.reduce_mul_value
        s.send.msg.inter_cgra_pkt.src @= s.queue.send.msg.dst
        s.send.msg.inter_cgra_pkt.dst @= s.queue.send.msg.src
        s.send.msg.inter_cgra_pkt.src_x @= s.queue.send.msg.dst_x
        s.send.msg.inter_cgra_pkt.src_y @= s.queue.send.msg.dst_y
        s.send.msg.inter_cgra_pkt.dst_x @= s.queue.send.msg.src_x
        s.send.msg.inter_cgra_pkt.dst_y @= s.queue.send.msg.src_y
        s.send.msg.inter_cgra_pkt.src_tile_id @= s.queue.send.msg.dst_tile_id
        s.send.msg.inter_cgra_pkt.dst_tile_id @= s.queue.send.msg.src_tile_id
        s.queue.send.rdy @= s.send.rdy
        s.send.val @= s.queue.send.val

    @update_ff
    def accumulate_value():
      if s.reset | (s.sending_count == s.target_count):
        s.reduce_add_value <<= DataType(0, 0, 0, 0)
        s.reduce_mul_value <<= DataType(1, 0, 0, 0)
      else:
        if s.recv_data.val & \
           s.recv_data.rdy:
          if s.recv_data.msg.payload.cmd == CMD_GLOBAL_REDUCE_ADD:
            s.reduce_add_value <<= DataType(s.reduce_add_value.payload + s.recv_data.msg.payload.data.payload,
                                            s.recv_data.msg.payload.data.predicate,
                                            0,
                                            0)
          elif s.recv_data.msg.payload.cmd == CMD_GLOBAL_REDUCE_MUL:
            s.reduce_mul_value <<= DataType(s.reduce_mul_value.payload * s.recv_data.msg.payload.data.payload,
                                            s.recv_data.msg.payload.data.predicate,
                                            0,
                                            0)

  def line_trace( s ):
    input_str = 'count:' + str(s.recv_count) + ', data:' + str(s.recv_data) + ", receiving_count:" + str(s.receiving_count)
    output_str = 'out:'+str(s.send)
    return f'{input_str}(){output_str}'