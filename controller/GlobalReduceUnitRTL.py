'''
==========================================================================
GlobalReduceUnitRTL.py
==========================================================================
A global reduce unit to record the count that data needs to be reduced,
and received the corresponding data. The unit will send the reduced data
back to the controller.

Multiple reductions can be in flight at once. Each one is identified by
payload.data_addr of its COUNT/ADD/MUL packets, which indexes an entry
that holds its own counters, accumulators, and senders to respond to.

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

  def construct(s, InterCgraPktType, num_entries = 4, queue_depth = 16):

    CgraPayloadType = InterCgraPktType.get_field_type(kAttrPayload)
    DataType = CgraPayloadType.get_field_type(kAttrData)
    DataAddrType = CgraPayloadType.get_field_type(kAttrDataAddr)
    ControllerXbarPktType = mk_controller_noc_xbar_pkt(InterCgraPktType)
    assert num_entries >= 2 and (num_entries & (num_entries - 1)) == 0, \
        "num_entries must be a power of two and at least 2"
    entry_idx_nbits = clog2(num_entries)
    EntryIdxType = mk_bits(entry_idx_nbits)
    assert DataAddrType.nbits >= entry_idx_nbits, \
        "data_addr is too narrow to carry a reduction id"

    # Interfaces.
    s.recv_count = RecvIfcRTL(InterCgraPktType)
    s.recv_data = RecvIfcRTL(InterCgraPktType)
    s.send = SendIfcRTL(ControllerXbarPktType)

    # Components. Each entry keeps the received packets so that it can
    # respond to every sender once its reduction completes.
    s.queue = [NormalQueueRTL(InterCgraPktType, queue_depth)
               for _ in range(num_entries)]
    s.target_count = [Wire(DataType) for _ in range(num_entries)]
    s.receiving_count = [Wire(DataType) for _ in range(num_entries)]
    s.sending_count = [Wire(DataType) for _ in range(num_entries)]
    s.reduce_add_value = [Wire(DataType) for _ in range(num_entries)]
    s.reduce_mul_value = [Wire(DataType) for _ in range(num_entries)]
    s.entry_done = [Wire(1) for _ in range(num_entries)]

    # Reduction ids must be smaller than num_entries; higher bits are ignored.
    s.recv_count_idx = Wire(EntryIdxType)
    s.recv_data_idx = Wire(EntryIdxType)
    s.send_idx = Wire(EntryIdxType)
    s.send_found = Wire(1)

    # Connections.
    s.recv_count.rdy //= 1
    s.recv_count_idx //= s.recv_count.msg.payload.data_addr[0:entry_idx_nbits]
    s.recv_data_idx //= s.recv_data.msg.payload.data_addr[0:entry_idx_nbits]

    @update
    def set_recv_rdy():
      s.recv_data.rdy @= 0
      for i in range(num_entries):
        s.queue[i].recv.val @= 0
        s.queue[i].recv.msg @= InterCgraPktType(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        if (s.recv_data_idx == i) & \
           (s.target_count[i].payload > s.receiving_count[i].payload):
          s.recv_data.rdy @= s.queue[i].recv.rdy
          s.queue[i].recv.msg @= s.recv_data.msg
          s.queue[i].recv.val @= s.recv_data.val

    @update
    def update_entry_done():
      for i in range(num_entries):
        s.entry_done[i] @= (s.target_count[i].payload > 0) & \
                           (s.receiving_count[i].payload == s.target_count[i].payload) & \
                           s.queue[i].send.val

    # Lowest-indexed completed entry gets the single send port.
    @update
    def select_send_entry():
      s.send_found @= 0
      s.send_idx @= 0
      for i in range(num_entries):
        if ~s.send_found & s.entry_done[i]:
          s.send_found @= 1
          s.send_idx @= i

    @update_ff
    def update_count():
      for i in range(num_entries):
        if s.reset:
          s.target_count[i] <<= DataType(0, 0, 0, 0)
          s.receiving_count[i] <<= DataType(0, 0, 0, 0)
          s.sending_count[i] <<= DataType(0, 0, 0, 0)
        else:
          if s.recv_count.val & s.recv_count.rdy & (s.recv_count_idx == i):
            s.target_count[i] <<= DataType(s.recv_count.msg.payload.data.payload, 0, 0, 0)
          if s.recv_data.val & s.recv_data.rdy & (s.recv_data_idx == i):
            s.receiving_count[i] <<= DataType(s.receiving_count[i].payload + 1, 0, 0, 0)
          if s.send.rdy & s.send.val & (s.send_idx == i):
            s.sending_count[i] <<= DataType(s.sending_count[i].payload + 1, 0, 0, 0)
          elif (s.sending_count[i] == s.receiving_count[i]) & \
               (s.sending_count[i] == s.target_count[i]) & \
               (s.target_count[i].payload > 0):
            s.sending_count[i] <<= DataType(0, 0, 0, 0)
            s.receiving_count[i] <<= DataType(0, 0, 0, 0)

    @update
    def update_send():
      s.send.msg @= ControllerXbarPktType(0, 0)
      s.send.val @= 0
      for i in range(num_entries):
        s.queue[i].send.rdy @= 0
      for i in range(num_entries):
        if s.send_found & (s.send_idx == i):
          # Updates the cmd type, result value, and src/dst.
          if s.queue[i].send.msg.payload.cmd == CMD_GLOBAL_REDUCE_ADD:
            s.send.msg.inter_cgra_pkt.payload.cmd @= CMD_GLOBAL_REDUCE_ADD_RESPONSE
            s.send.msg.inter_cgra_pkt.payload.data @= s.reduce_add_value[i]
          elif s.queue[i].send.msg.payload.cmd == CMD_GLOBAL_REDUCE_MUL:
            s.send.msg.inter_cgra_pkt.payload.cmd @= CMD_GLOBAL_REDUCE_MUL_RESPONSE
            s.send.msg.inter_cgra_pkt.payload.data @= s.reduce_mul_value[i]
          s.send.msg.inter_cgra_pkt.payload.data_addr @= s.queue[i].send.msg.payload.data_addr
          s.send.msg.inter_cgra_pkt.src @= s.queue[i].send.msg.dst
          s.send.msg.inter_cgra_pkt.dst @= s.queue[i].send.msg.src
          s.send.msg.inter_cgra_pkt.src_x @= s.queue[i].send.msg.dst_x
          s.send.msg.inter_cgra_pkt.src_y @= s.queue[i].send.msg.dst_y
          s.send.msg.inter_cgra_pkt.dst_x @= s.queue[i].send.msg.src_x
          s.send.msg.inter_cgra_pkt.dst_y @= s.queue[i].send.msg.src_y
          s.send.msg.inter_cgra_pkt.src_tile_id @= s.queue[i].send.msg.dst_tile_id
          s.send.msg.inter_cgra_pkt.dst_tile_id @= s.queue[i].send.msg.src_tile_id
          s.queue[i].send.rdy @= s.send.rdy
          s.send.val @= s.queue[i].send.val

    @update_ff
    def accumulate_value():
      for i in range(num_entries):
        if s.reset | (s.sending_count[i] == s.target_count[i]):
          s.reduce_add_value[i] <<= DataType(0, 0, 0, 0)
          s.reduce_mul_value[i] <<= DataType(1, 0, 0, 0)
        else:
          if s.recv_data.val & \
             s.recv_data.rdy & \
             (s.recv_data_idx == i):
            if s.recv_data.msg.payload.cmd == CMD_GLOBAL_REDUCE_ADD:
              s.reduce_add_value[i] <<= DataType(s.reduce_add_value[i].payload + s.recv_data.msg.payload.data.payload,
                                                 s.recv_data.msg.payload.data.predicate,
                                                 0,
                                                 0)
            elif s.recv_data.msg.payload.cmd == CMD_GLOBAL_REDUCE_MUL:
              s.reduce_mul_value[i] <<= DataType(s.reduce_mul_value[i].payload * s.recv_data.msg.payload.data.payload,
                                                 s.recv_data.msg.payload.data.predicate,
                                                 0,
                                                 0)

  def line_trace( s ):
    input_str = 'count:' + str(s.recv_count) + ', data:' + str(s.recv_data) + \
                ", receiving_count:" + '|'.join(str(c) for c in s.receiving_count)
    output_str = 'out:'+str(s.send)
    return f'{input_str}(){output_str}'
