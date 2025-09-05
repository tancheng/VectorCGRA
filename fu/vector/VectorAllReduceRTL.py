"""
==========================================================================
VectorAllReduceRTL.py ==========================================================================
AllReduce functional unit.

Author : Cheng Tan
  Date : April 23, 2022
"""


from pymtl3 import *
from ..basic.SumUnit import SumUnit
from ..basic.ReduceMulUnit import ReduceMulUnit
from ...lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ...lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ...lib.opt_type import *

class VectorAllReduceRTL(Component):

  def construct(s, DataType, PredicateType, CtrlType,
                num_inports, num_outports, data_mem_size,
                vector_factor_power = 0,
                num_lanes = 4,
                data_bandwidth = 64):

    # Constants.
    assert(data_bandwidth % num_lanes == 0)
    # currently only support 4 due to the shift logic.
    assert(num_lanes % 4 == 0)
    num_entries = 4
    CountType = mk_bits(clog2(num_entries + 1))
    sub_bw = data_bandwidth // num_lanes
    s.const_zero = DataType(0, 0, 0, 0)

    # Interfaces.
    s.recv_in = [RecvIfcRTL(DataType) for _ in range(num_inports)]
    s.recv_const = RecvIfcRTL(DataType)
    s.recv_opt = RecvIfcRTL(CtrlType)
    s.send_out = [SendIfcRTL(DataType) for _ in range(num_outports)]
    s.send_to_controller = SendIfcRTL(DataType)
    TempDataType = mk_bits(data_bandwidth)
    s.temp_result = [Wire(TempDataType) for _ in range(num_lanes)]

    # Redundant interfaces for MemUnit.
    AddrType = mk_bits(clog2(data_mem_size))
    s.to_mem_raddr = SendIfcRTL(AddrType)
    s.from_mem_rdata = RecvIfcRTL(DataType)
    s.to_mem_waddr = SendIfcRTL(AddrType)
    s.to_mem_wdata = SendIfcRTL(DataType)

    # Reduction units.
    s.reduce_add = SumUnit(TempDataType, num_lanes)
    for i in range(num_lanes):
      s.reduce_add.in_[i] //= lambda: (s.temp_result[i]
          if (s.recv_opt.msg.operation == OPT_VEC_REDUCE_ADD) or \
             (s.recv_opt.msg.operation == OPT_VEC_REDUCE_ADD_BASE) else 0)

    s.reduce_mul = ReduceMulUnit(TempDataType, num_lanes)
    for i in range(num_lanes):
      s.reduce_mul.in_[i] //= lambda: (s.temp_result[i]
          if (s.recv_opt.msg.operation == OPT_VEC_REDUCE_MUL) or \
             (s.recv_opt.msg.operation == OPT_VEC_REDUCE_MUL_BASE) else 0)

    @update
    def update_result():
      # Connection: splits data into vectorized wires.
      s.send_out[0].msg.payload @= 0
      for i in range(num_lanes):
        s.temp_result[i] @= TempDataType(0)
        s.temp_result[i][0:sub_bw] @= s.recv_in[0].msg.payload[i*sub_bw:(i+1)*sub_bw]

      if s.recv_opt.msg.operation == OPT_VEC_REDUCE_ADD:
        s.send_out[0].msg.payload[0:data_bandwidth] @= s.reduce_add.out
      elif s.recv_opt.msg.operation == OPT_VEC_REDUCE_ADD_BASE:
        s.send_out[0].msg.payload[0:data_bandwidth] @= s.reduce_add.out + s.recv_in[1].msg.payload
      elif s.recv_opt.msg.operation == OPT_VEC_REDUCE_MUL:
        s.send_out[0].msg.payload[0:data_bandwidth] @= s.reduce_mul.out
      elif s.recv_opt.msg.operation == OPT_VEC_REDUCE_MUL_BASE:
        s.send_out[0].msg.payload[0:data_bandwidth] @= s.reduce_mul.out * s.recv_in[1].msg.payload

    @update
    def update_signal():
      for i in range(num_inports):
        s.recv_in[i].rdy @= b1(0)

      s.recv_in[0].rdy @= ((s.recv_opt.msg.operation == OPT_VEC_REDUCE_ADD) | \
                           (s.recv_opt.msg.operation == OPT_VEC_REDUCE_MUL) | \
                           (s.recv_opt.msg.operation == OPT_VEC_REDUCE_ADD_BASE) | \
                           (s.recv_opt.msg.operation == OPT_VEC_REDUCE_MUL_BASE)) & \
                          s.send_out[0].rdy
      s.recv_opt.rdy @= s.send_out[0].rdy
      s.recv_in[1].rdy @= ((s.recv_opt.msg.operation == OPT_VEC_REDUCE_ADD_BASE) | \
                           (s.recv_opt.msg.operation == OPT_VEC_REDUCE_MUL_BASE)) & \
                          s.send_out[0].rdy
      s.send_out[0].val @= s.recv_in[0].val & \
                           s.recv_opt.val & \
                           ((s.recv_opt.msg.operation == OPT_VEC_REDUCE_ADD) | \
                            (s.recv_opt.msg.operation == OPT_VEC_REDUCE_MUL) | \
                            (((s.recv_opt.msg.operation == OPT_VEC_REDUCE_ADD_BASE) | \
                              (s.recv_opt.msg.operation == OPT_VEC_REDUCE_MUL_BASE)) & \
                             (s.recv_in[1].val)))

      s.send_to_controller.val @= 0
      s.send_to_controller.msg @= DataType()

    @update
    def update_predicate():
      s.send_out[0].msg.predicate @= 0
      if ((s.recv_opt.msg.operation == OPT_VEC_REDUCE_ADD) | \
          (s.recv_opt.msg.operation == OPT_VEC_REDUCE_MUL)):
        s.send_out[0].msg.predicate @= s.recv_in[0].msg.predicate & s.recv_in[0].val
      elif ((s.recv_opt.msg.operation == OPT_VEC_REDUCE_ADD_BASE) | \
            (s.recv_opt.msg.operation == OPT_VEC_REDUCE_MUL_BASE)):
        s.send_out[0].msg.predicate @= s.recv_in[0].msg.predicate & \
                                       s.recv_in[0].val & \
                                       s.recv_in[1].msg.predicate & \
                                       s.recv_in[1].val

    @update
    def update_mem():
      s.to_mem_waddr.val @= b1(0)
      s.to_mem_wdata.val @= b1(0)
      s.to_mem_wdata.msg @= s.const_zero
      s.to_mem_waddr.msg @= AddrType(0)
      s.to_mem_raddr.msg @= AddrType(0)
      s.to_mem_raddr.val @= b1(0)
      s.from_mem_rdata.rdy @= b1(0)

  def line_trace(s):
    return str(s.recv_in[0].msg) + OPT_SYMBOL_DICT[s.recv_opt.msg.operation] + " -> " + str(s.send_out[0].msg)

