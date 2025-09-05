"""
==========================================================================
VectorMulCombRTL.py
==========================================================================
Multiple parallelly combined multipliers to enable vectorization.
The result is same for both multi-FU and combo.
The vectorized Mul works at different vectorization granularities.

Author : Cheng Tan
  Date : April 17, 2022
"""

from pymtl3 import *
from .VectorMulRTL import VectorMulRTL
from ..basic.SumUnit import SumUnit
from ...lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ...lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ...lib.opt_type import *

class VectorMulComboRTL(Component):

  def construct(s, DataType, PredicateType, CtrlType,
                num_inports, num_outports, data_mem_size,
                vector_factor_power = 0,
                num_lanes = 4, data_bitwidth = 64):

    # Constants
    assert(data_bitwidth % num_lanes == 0)
    # currently only support 4 due to the shift logic
    assert(num_lanes % 4 == 0)
    num_entries = 2
    s.const_zero = DataType(0, 0)
    CountType = mk_bits(clog2(num_entries + 1))
    # By default 16-bit indicates both input and output. For a Mul,
    # if output is no longer than 16-bit, it means the
    # input is no longer than 8-bit. Here, the sub_bw is by default
    # 4, which will be times by 2 to make it 8-bit to compensate
    # the longer output in the subFU.
    sub_bw = data_bitwidth // num_lanes
    sub_bw_2 = 2 * data_bitwidth // num_lanes
    sub_bw_3 = 3 * data_bitwidth // num_lanes
    sub_bw_4 = 4 * data_bitwidth // num_lanes

    # Interface
    s.recv_in = [RecvIfcRTL(DataType) for _ in range(num_inports)]
    s.recv_const = RecvIfcRTL(DataType)
    s.recv_opt = RecvIfcRTL(CtrlType)
    s.send_out = [SendIfcRTL(DataType) for _ in range(num_outports)]
    s.send_to_controller = SendIfcRTL(DataType)
    TempDataType = mk_bits(data_bitwidth)
    FuDataType = mk_bits(sub_bw)
    s.temp_result = [Wire(TempDataType) for _ in range(num_lanes)]

    # Components
    s.Fu = [VectorMulRTL(sub_bw, CtrlType, 4, 2, data_mem_size)
            for _ in range(num_lanes)]

    # Redundant interfaces for MemUnit
    AddrType = mk_bits(clog2(data_mem_size))
    s.to_mem_raddr = SendIfcRTL(AddrType)
    s.from_mem_rdata = RecvIfcRTL(DataType)
    s.to_mem_waddr = SendIfcRTL(AddrType)
    s.to_mem_wdata = SendIfcRTL(DataType)

    @update
    def update_input_output():

      # Initialization to avoid latches
      for j in range(num_outports):
        s.send_out[j].val @= b1(0)

      s.send_out[0].val @= s.Fu[0].send_out[0].val & \
                           s.recv_opt.val
      s.send_out[0].msg.payload @= 0

      s.send_to_controller.val @= 0
      s.send_to_controller.msg @= DataType()

      for i in range(num_lanes):
        s.temp_result[i] @= TempDataType(0)
        s.Fu[i].recv_in[0].msg[0:sub_bw] @= FuDataType()
        s.Fu[i].recv_in[1].msg[0:sub_bw] @= FuDataType()

      if s.recv_opt.msg.operation == OPT_VEC_MUL:
        # Connection: split into vectorized FUs
        s.Fu[0].recv_in[0].msg[0:sub_bw] @= s.recv_in[0].msg.payload[0:sub_bw]
        s.Fu[0].recv_in[1].msg[0:sub_bw] @= s.recv_in[1].msg.payload[0:sub_bw]
        s.Fu[1].recv_in[0].msg[0:sub_bw] @= s.recv_in[0].msg.payload[sub_bw:sub_bw_2]
        s.Fu[1].recv_in[1].msg[0:sub_bw] @= s.recv_in[1].msg.payload[sub_bw:sub_bw_2]
        s.Fu[2].recv_in[0].msg[0:sub_bw] @= s.recv_in[0].msg.payload[sub_bw_2:sub_bw_3]
        s.Fu[2].recv_in[1].msg[0:sub_bw] @= s.recv_in[1].msg.payload[sub_bw_2:sub_bw_3]
        s.Fu[3].recv_in[0].msg[0:sub_bw] @= s.recv_in[0].msg.payload[sub_bw_3:sub_bw_4]
        s.Fu[3].recv_in[1].msg[0:sub_bw] @= s.recv_in[1].msg.payload[sub_bw_3:sub_bw_4]

        for i in range(num_lanes):
          s.temp_result[i] @= TempDataType(0)
          s.temp_result[i][0:sub_bw_2] @= s.Fu[i].send_out[0].msg[0:sub_bw_2]

        s.send_out[0].msg.payload[0:data_bitwidth] @= \
          (s.temp_result[3] << (sub_bw * 3)) + \
          (s.temp_result[2] << (sub_bw * 2)) + \
          (s.temp_result[1] << sub_bw) + \
          s.temp_result[0]

      elif s.recv_opt.msg.operation == OPT_VEC_MUL_COMBINED: # with highest precision
        s.Fu[0].recv_in[0].msg[0:sub_bw] @= s.recv_in[0].msg.payload[0:sub_bw]
        s.Fu[0].recv_in[1].msg[0:sub_bw] @= s.recv_in[1].msg.payload[0:sub_bw]
        s.Fu[1].recv_in[0].msg[0:sub_bw] @= s.recv_in[0].msg.payload[0:sub_bw]
        s.Fu[1].recv_in[1].msg[0:sub_bw] @= s.recv_in[1].msg.payload[sub_bw:sub_bw_2]
        s.Fu[2].recv_in[0].msg[0:sub_bw] @= s.recv_in[0].msg.payload[sub_bw:sub_bw_2]
        s.Fu[2].recv_in[1].msg[0:sub_bw] @= s.recv_in[1].msg.payload[0:sub_bw]
        s.Fu[3].recv_in[0].msg[0:sub_bw] @= s.recv_in[0].msg.payload[sub_bw:sub_bw_2]
        s.Fu[3].recv_in[1].msg[0:sub_bw] @= s.recv_in[1].msg.payload[sub_bw:sub_bw_2]

        for i in range(num_lanes):
          s.temp_result[i] @= TempDataType(0)
          s.temp_result[i][0:sub_bw_2] @= s.Fu[i].send_out[0].msg[0:sub_bw_2]

        s.send_out[0].msg.payload[0:data_bitwidth] @= \
            s.temp_result[0] + \
            (s.temp_result[1] << sub_bw) + \
            (s.temp_result[2] << sub_bw) + \
            (s.temp_result[3] << (sub_bw * 2))

      else:
        for j in range(num_outports):
          s.send_out[j].val @= b1(0)

    @update
    def update_signal():
      s.recv_in[0].rdy @= s.Fu[0].recv_in[0].rdy
      s.recv_in[1].rdy @= s.Fu[0].recv_in[1].rdy

      for i in range(num_lanes):
        s.Fu[i].recv_opt.val @= s.recv_opt.val

        # Note that the predication for a combined FU should be identical/shareable,
        # which means the computation in different basic block cannot be combined.
        # s.Fu[i].recv_opt.msg.predicate = s.recv_opt.msg.predicate

        s.Fu[i].recv_in[0].val @= s.recv_in[0].val
        s.Fu[i].recv_in[1].val @= s.recv_in[1].val
        s.Fu[i].recv_const.val @= s.recv_const.val

        for j in range(num_outports):
          s.Fu[i].send_out[j].rdy @= s.send_out[j].rdy

      s.recv_const.rdy @= s.Fu[0].recv_const.rdy
      s.recv_opt.rdy @= s.send_out[0].rdy

    @update
    def update_opt():
      s.send_out[0].msg.predicate @= b1(0)

      for i in range(num_lanes):
        s.Fu[i].recv_opt.msg.fu_in[0] @= 1
        s.Fu[i].recv_opt.msg.fu_in[1] @= 2
        s.Fu[i].recv_opt.msg.operation @= OPT_NAH

      if (s.recv_opt.msg.operation == OPT_VEC_MUL) | \
         (s.recv_opt.msg.operation == OPT_VEC_MUL_COMBINED):
        for i in range(num_lanes):
          s.Fu[i].recv_opt.msg.operation @= OPT_MUL
        s.send_out[0].msg.predicate @= s.recv_in[0].msg.predicate & s.recv_in[1].msg.predicate

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
    return str(s.recv_in[0].msg) + OPT_SYMBOL_DICT[s.recv_opt.msg.operation] + str(s.recv_in[1].msg) + " -> " + str(s.send_out[0].msg)

