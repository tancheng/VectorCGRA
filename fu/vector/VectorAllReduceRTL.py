"""
==========================================================================
VectorAllReduceRTL.py
==========================================================================
AllReduce functional unit.

Author : Cheng Tan
  Date : April 23, 2022
"""

from pymtl3 import *
from ..basic.SumUnit import SumUnit
from ..basic.ReduceMulUnit import ReduceMulUnit
from ...lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ...lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ...lib.cmd_type import *
from ...lib.messages import *
from ...lib.opt_type import *

class VectorAllReduceRTL(Component):

  def construct(s, DataType, CtrlType,
                num_inports, num_outports,
                data_mem_size,
                ctrl_mem_size = 4,
                vector_factor_power = 0,
                num_lanes = 4,
                data_bitwidth = 64):

    PredicateType = DataType.get_field_type(kAttrPredicate)
    data_bitwidth = DataType.get_field_type(kAttrPayload).nbits
    # Constants.
    assert(data_bitwidth % num_lanes == 0)
    # currently only support 4 due to the shift logic.
    assert(num_lanes % 4 == 0)
    num_entries = 4
    CountType = mk_bits(clog2(num_entries + 1))
    DataAddrType = mk_bits(clog2(data_mem_size))
    CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
    s.ctrl_addr_inport = InPort(CtrlAddrType)
    sub_bw = data_bitwidth // num_lanes
    s.const_zero = DataType(0, 0, 0, 0)
    s.CgraPayloadType = mk_cgra_payload(DataType,
                                        DataAddrType,
                                        CtrlType,
                                        CtrlAddrType)

    # Interfaces.
    s.recv_in = [RecvIfcRTL(DataType) for _ in range(num_inports)]
    s.recv_const = RecvIfcRTL(DataType)
    s.recv_opt = RecvIfcRTL(CtrlType)
    s.send_out = [SendIfcRTL(DataType) for _ in range(num_outports)]
    s.send_to_ctrl_mem = SendIfcRTL(s.CgraPayloadType)
    s.recv_from_ctrl_mem = RecvIfcRTL(s.CgraPayloadType)
    TempDataType = mk_bits(data_bitwidth)
    s.temp_result = [Wire(TempDataType) for _ in range(num_lanes)]

    # Redundant interface, only used by PhiRTL.
    s.clear = InPort(b1)

    # Redundant interfaces for MemUnit.
    s.to_mem_raddr = SendIfcRTL(DataAddrType)
    s.from_mem_rdata = RecvIfcRTL(DataType)
    s.to_mem_waddr = SendIfcRTL(DataAddrType)
    s.to_mem_wdata = SendIfcRTL(DataType)
    # Redundant interfaces for streamimg LD in MemUnit.
    s.streaming_start_raddr = InPort(DataAddrType)
    s.streaming_stride = InPort(DataAddrType)
    s.streaming_end_raddr = InPort(DataAddrType)
    # This is for blocking fu_crossbar and routing_crossbar
    # when performing streaming LD operation.
    s.streaming_done = OutPort(b1)

    # Components.
    s.already_sent_to_controller = Wire(1)
  
    # Reduction units.
    s.reduce_add = SumUnit(TempDataType, num_lanes)
    for i in range(num_lanes):
      s.reduce_add.in_[i] //= lambda: (s.temp_result[i]
          if (s.recv_opt.msg.operation == OPT_VEC_REDUCE_ADD) | \
             (s.recv_opt.msg.operation == OPT_VEC_REDUCE_ADD_BASE) | \
             (s.recv_opt.msg.operation == OPT_VEC_REDUCE_ADD_GLOBAL) | \
             (s.recv_opt.msg.operation == OPT_VEC_REDUCE_ADD_BASE_GLOBAL) else 0)

    s.reduce_mul = ReduceMulUnit(TempDataType, num_lanes)
    for i in range(num_lanes):
      s.reduce_mul.in_[i] //= lambda: (s.temp_result[i]
          if (s.recv_opt.msg.operation == OPT_VEC_REDUCE_MUL) | \
             (s.recv_opt.msg.operation == OPT_VEC_REDUCE_MUL_BASE) | \
             (s.recv_opt.msg.operation == OPT_VEC_REDUCE_MUL_GLOBAL) | \
             (s.recv_opt.msg.operation == OPT_VEC_REDUCE_MUL_BASE_GLOBAL) else 0)


    for i in range( num_lanes ):
      # Calculate the constant bounds for each specific connection
      low  = i * sub_bw
      high = (i + 1) * sub_bw
      # s.connect() works with slice objects directly during elaboration.
      s.temp_result[i][0:sub_bw] //= s.recv_in[0].msg.payload[low:high]
      s.temp_result[i][sub_bw:data_bitwidth] //= 0

    @update
    def update_result():
      # Connection: splits data into vectorized wires.
      s.send_out[0].msg.payload @= 0

      if s.recv_opt.msg.operation == OPT_VEC_REDUCE_ADD:
        s.send_out[0].msg.payload[0:data_bitwidth] @= s.reduce_add.out
      elif s.recv_opt.msg.operation == OPT_VEC_REDUCE_ADD_BASE:
        s.send_out[0].msg.payload[0:data_bitwidth] @= s.reduce_add.out + s.recv_in[1].msg.payload
      elif s.recv_opt.msg.operation == OPT_VEC_REDUCE_MUL:
        s.send_out[0].msg.payload[0:data_bitwidth] @= s.reduce_mul.out
      elif s.recv_opt.msg.operation == OPT_VEC_REDUCE_MUL_BASE:
        s.send_out[0].msg.payload[0:data_bitwidth] @= s.reduce_mul.out * s.recv_in[1].msg.payload
      elif s.recv_opt.msg.operation == OPT_VEC_REDUCE_ADD_GLOBAL:
        s.send_out[0].msg.payload[0:data_bitwidth] @= s.recv_from_ctrl_mem.msg.data.payload[0:data_bitwidth]
      elif s.recv_opt.msg.operation == OPT_VEC_REDUCE_MUL_GLOBAL:
        s.send_out[0].msg.payload[0:data_bitwidth] @= s.recv_from_ctrl_mem.msg.data.payload[0:data_bitwidth]
      elif s.recv_opt.msg.operation == OPT_VEC_REDUCE_ADD_BASE_GLOBAL:
        s.send_out[0].msg.payload[0:data_bitwidth] @= s.recv_from_ctrl_mem.msg.data.payload[0:data_bitwidth] + s.recv_in[1].msg.payload
      elif s.recv_opt.msg.operation == OPT_VEC_REDUCE_MUL_BASE_GLOBAL:
        s.send_out[0].msg.payload[0:data_bitwidth] @= s.recv_from_ctrl_mem.msg.data.payload[0:data_bitwidth] * s.recv_in[1].msg.payload

    @update
    def update_signal():
      for i in range(num_inports):
        s.recv_in[i].rdy @= b1(0)

      s.send_to_ctrl_mem.val @= 0
      s.send_to_ctrl_mem.msg @= s.CgraPayloadType(0, 0, 0, 0, 0)

      s.recv_from_ctrl_mem.rdy @= 0

      s.recv_in[0].rdy @= (((s.recv_opt.msg.operation == OPT_VEC_REDUCE_ADD) | \
                            (s.recv_opt.msg.operation == OPT_VEC_REDUCE_MUL) | \
                            (s.recv_opt.msg.operation == OPT_VEC_REDUCE_ADD_BASE) | \
                            (s.recv_opt.msg.operation == OPT_VEC_REDUCE_MUL_BASE)) & \
                           s.send_out[0].rdy) | \
                          (((s.recv_opt.msg.operation == OPT_VEC_REDUCE_ADD_GLOBAL) | \
                            (s.recv_opt.msg.operation == OPT_VEC_REDUCE_MUL_GLOBAL) | \
                            (s.recv_opt.msg.operation == OPT_VEC_REDUCE_ADD_BASE_GLOBAL) | \
                            (s.recv_opt.msg.operation == OPT_VEC_REDUCE_MUL_BASE_GLOBAL)) & \
                           s.send_to_ctrl_mem.rdy)
      s.recv_opt.rdy @= s.send_out[0].rdy
      s.recv_in[1].rdy @= (((s.recv_opt.msg.operation == OPT_VEC_REDUCE_ADD_BASE) | \
                            (s.recv_opt.msg.operation == OPT_VEC_REDUCE_MUL_BASE)) & \
                           s.send_out[0].rdy) | \
                          (((s.recv_opt.msg.operation == OPT_VEC_REDUCE_MUL_BASE_GLOBAL) | \
                            (s.recv_opt.msg.operation == OPT_VEC_REDUCE_MUL_BASE_GLOBAL)) & \
                           s.send_to_ctrl_mem.rdy)
      s.send_out[0].val @= (s.recv_in[0].val & \
                            s.recv_opt.val & \
                            ((s.recv_opt.msg.operation == OPT_VEC_REDUCE_ADD) | \
                             (s.recv_opt.msg.operation == OPT_VEC_REDUCE_MUL))) | \
                           (s.recv_in[0].val & \
                            s.recv_in[1].val & \
                            s.recv_opt.val & \
                            ((s.recv_opt.msg.operation == OPT_VEC_REDUCE_ADD_BASE) | \
                             (s.recv_opt.msg.operation == OPT_VEC_REDUCE_MUL_BASE))) | \
                           (s.recv_opt.val & \
                            s.recv_from_ctrl_mem.val & \
                            ((s.recv_opt.msg.operation == OPT_VEC_REDUCE_ADD_GLOBAL) | \
                             (s.recv_opt.msg.operation == OPT_VEC_REDUCE_MUL_GLOBAL))) | \
                           (s.recv_opt.val & \
                            s.recv_from_ctrl_mem.val & \
                            s.recv_in[1].val & \
                            ((s.recv_opt.msg.operation == OPT_VEC_REDUCE_ADD_BASE_GLOBAL) | \
                             (s.recv_opt.msg.operation == OPT_VEC_REDUCE_MUL_BASE_GLOBAL)))

      if s.recv_opt.val & \
         ~s.already_sent_to_controller & \
         (s.recv_in[0].val & \
          ((s.recv_opt.msg.operation == OPT_VEC_REDUCE_ADD_GLOBAL) | \
           (s.recv_opt.msg.operation == OPT_VEC_REDUCE_MUL_GLOBAL))) | \
         (s.recv_in[0].val & \
          s.recv_in[1].val & \
          ((s.recv_opt.msg.operation == OPT_VEC_REDUCE_ADD_BASE_GLOBAL) | \
           (s.recv_opt.msg.operation == OPT_VEC_REDUCE_MUL_BASE_GLOBAL))):
        s.send_to_ctrl_mem.val @= 1
        if (s.recv_opt.msg.operation == OPT_VEC_REDUCE_ADD_GLOBAL) | \
           (s.recv_opt.msg.operation == OPT_VEC_REDUCE_ADD_BASE_GLOBAL):
          s.send_to_ctrl_mem.msg @= \
              s.CgraPayloadType(CMD_GLOBAL_REDUCE_ADD,
                                DataType(s.reduce_add.out,
                                         s.recv_in[0].msg.predicate, 0, 0),
                                0,
                                s.recv_opt.msg,
                                0)
        if (s.recv_opt.msg.operation == OPT_VEC_REDUCE_MUL_GLOBAL) | \
           (s.recv_opt.msg.operation == OPT_VEC_REDUCE_MUL_BASE_GLOBAL):
          s.send_to_ctrl_mem.msg @= \
              s.CgraPayloadType(CMD_GLOBAL_REDUCE_MUL,
                                DataType(s.reduce_add.out,
                                         s.recv_in[0].msg.predicate, 0, 0),
                                0,
                                s.recv_opt.msg,
                                0)

      if s.recv_opt.val & s.already_sent_to_controller:
        s.recv_from_ctrl_mem.rdy @= 1

    @update
    def update_predicate():
      s.send_out[0].msg.predicate @= 0
      if ((s.recv_opt.msg.operation == OPT_VEC_REDUCE_ADD) | \
          (s.recv_opt.msg.operation == OPT_VEC_REDUCE_MUL)):
        s.send_out[0].msg.predicate @= s.recv_in[0].msg.predicate
      elif ((s.recv_opt.msg.operation == OPT_VEC_REDUCE_ADD_BASE) | \
            (s.recv_opt.msg.operation == OPT_VEC_REDUCE_MUL_BASE)):
        s.send_out[0].msg.predicate @= s.recv_in[0].msg.predicate & \
                                       s.recv_in[1].msg.predicate
      elif ((s.recv_opt.msg.operation == OPT_VEC_REDUCE_ADD_BASE_GLOBAL) | \
            (s.recv_opt.msg.operation == OPT_VEC_REDUCE_MUL_BASE_GLOBAL)):
        s.send_out[0].msg.predicate @= s.recv_from_ctrl_mem.msg.data.predicate & \
                                       s.recv_in[1].msg.predicate

    @update_ff
    def update_already_sent_to_controller():
      if s.reset:
        s.already_sent_to_controller <<= 0
      else:
        if s.recv_opt.val & \
           ((s.recv_opt.msg.operation == OPT_VEC_REDUCE_ADD_GLOBAL) | \
            (s.recv_opt.msg.operation == OPT_VEC_REDUCE_ADD_BASE_GLOBAL) | \
            (s.recv_opt.msg.operation == OPT_VEC_REDUCE_MUL_GLOBAL) | \
            (s.recv_opt.msg.operation == OPT_VEC_REDUCE_MUL_BASE_GLOBAL)) & \
            ~s.already_sent_to_controller & \
            s.send_to_ctrl_mem.val & \
            s.send_to_ctrl_mem.rdy:
          s.already_sent_to_controller <<= 1
        # Recovers already_sent_to_controller once the ctrl proceeds to the next one.
        elif s.recv_opt.val & \
             ((s.recv_opt.msg.operation == OPT_VEC_REDUCE_ADD_GLOBAL) | \
              (s.recv_opt.msg.operation == OPT_VEC_REDUCE_ADD_BASE_GLOBAL) | \
              (s.recv_opt.msg.operation == OPT_VEC_REDUCE_MUL_GLOBAL) | \
              (s.recv_opt.msg.operation == OPT_VEC_REDUCE_MUL_BASE_GLOBAL)) & \
             s.already_sent_to_controller & \
             s.recv_opt.rdy:
          s.already_sent_to_controller <<= 0

    @update
    def update_mem():
      s.to_mem_waddr.val @= b1(0)
      s.to_mem_wdata.val @= b1(0)
      s.to_mem_wdata.msg @= s.const_zero
      s.to_mem_waddr.msg @= DataAddrType(0)
      s.to_mem_raddr.msg @= DataAddrType(0)
      s.to_mem_raddr.val @= b1(0)
      s.from_mem_rdata.rdy @= b1(0)

  def line_trace(s):
    return str(s.recv_in[0].msg) + OPT_SYMBOL_DICT[s.recv_opt.msg.operation] + " -> " + str(s.send_out[0].msg)

