"""
==========================================================================
VectorAdderCombRTL.py
==========================================================================
Multiple parallelly combined adders to enable vectorization.
The result is same for both multi-FU and combo. The vectorized
addition is still useful for a[0:3]++ (i.e., vec_add_inc) and
a[0:3]+b (i.e., vec_add_const) at different vectorization
granularities.

Author : Cheng Tan
  Date : March 28, 2022
"""

from pymtl3 import *
from .VectorAdderRTL import VectorAdderRTL
from ...lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ...lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ...lib.messages import *
from ...lib.opt_type import *

class VectorAdderComboRTL(Component):

  def construct(s, CtrlPktType,
                num_inports, num_outports,
                vector_factor_power = 0,
                num_lanes = 4, data_bitwidth = 64):

    # Constants
    assert(data_bitwidth % num_lanes == 0)
    num_entries   = 2
    s.DataType = CtrlPktType.get_field_type(kAttrPayload).get_field_type(kAttrData)
    s.DataAddrType = CtrlPktType.get_field_type(kAttrPayload).get_field_type(kAttrDataAddr)
    s.CtrlType = CtrlPktType.get_field_type(kAttrPayload).get_field_type(kAttrCtrl)
    s.CtrlAddrType = CtrlPktType.get_field_type(kAttrPayload).get_field_type(kAttrCtrlAddr)
    s.CgraPayloadType = CtrlPktType.get_field_type(kAttrPayload)
    s.const_zero = s.DataType()
    data_bitwidth = s.DataType.get_field_type(kAttrPayload).nbits
    sub_bw = data_bitwidth // num_lanes
    CountType = mk_bits(clog2(num_entries + 1))
    FuInType = mk_bits(clog2(num_inports + 1))
    idx_nbits = clog2(num_inports)
    s.ctrl_addr_inport = InPort(s.CtrlAddrType)

    # Interface
    s.recv_in = [RecvIfcRTL(s.DataType) for _ in range(num_inports)]
    s.recv_const = RecvIfcRTL(s.DataType)
    s.recv_opt = RecvIfcRTL(s.CtrlType)
    s.send_out = [SendIfcRTL(s.DataType) for _ in range(num_outports)]
    s.send_to_ctrl_mem = SendIfcRTL(s.CgraPayloadType)
    s.recv_from_ctrl_mem = RecvIfcRTL(s.CgraPayloadType)
    
    # Redundant interface, only used by PhiRTL.
    s.clear = InPort(b1)

    # Components
    s.Fu = [VectorAdderRTL(sub_bw, CtrlPktType, 4, 2)
            for _ in range(num_lanes)]
    s.in0 = Wire(FuInType)
    s.in1 = Wire(FuInType)
    s.in0_idx = Wire(idx_nbits)
    s.in1_idx = Wire(idx_nbits)
    s.in0_msg = Wire(s.DataType)
    s.in1_msg = Wire(s.DataType)

    # Connections.
    s.in0_idx //= s.in0[0:idx_nbits]
    s.in1_idx //= s.in1[0:idx_nbits]

    # Connection: for carry-in/out
    s.Fu[0].carry_in //= 0
    for i in range(1, num_lanes):
      s.Fu[i].carry_in //= s.Fu[i-1].carry_out

    for i in range(num_lanes):
      # Connection: split into vectorized FUs.
      s.in0_msg.payload[i*sub_bw:(i+1)*sub_bw] //= s.Fu[i].recv_in[0].msg[0:sub_bw]
      s.in1_msg.payload[i*sub_bw:(i+1)*sub_bw] //= s.Fu[i].recv_in[1].msg[0:sub_bw]
      s.recv_const.msg.payload[i*sub_bw:(i+1)*sub_bw] //= s.Fu[i].recv_const.msg[0:sub_bw]

      # Connection: aggregate into combo out
      s.Fu[i].send_out[0].msg[0:sub_bw] //= s.send_out[0].msg.payload[i*sub_bw:(i+1)*sub_bw]

    # Redundant interfaces for MemUnit
    s.to_mem_raddr = SendIfcRTL(s.DataAddrType)
    s.from_mem_rdata = RecvIfcRTL(s.DataType)
    s.to_mem_waddr = SendIfcRTL(s.DataAddrType)
    s.to_mem_wdata = SendIfcRTL(s.DataType)

    @update
    def update_operand_idx():
      # For pick input register
      s.in0 @= 0
      s.in1 @= 0
      if s.recv_opt.val:
        if s.recv_opt.msg.fu_in[0] != FuInType(0):
          s.in0 @= s.recv_opt.msg.fu_in[0] - FuInType(1)
        if s.recv_opt.msg.fu_in[1] != FuInType(0):
          s.in1 @= s.recv_opt.msg.fu_in[1] - FuInType(1)

    @update
    def update_signal():
      s.in0_msg @= s.recv_in[s.in0_idx].msg
      s.in1_msg @= s.recv_in[s.in1_idx].msg

      for i in range(num_inports):
        s.recv_in[i].rdy @= b1(0)
      if s.Fu[0].recv_in[0].rdy:
        s.recv_in[s.in0_idx].rdy @= b1(1)
      if s.Fu[0].recv_in[1].rdy:
        s.recv_in[s.in1_idx].rdy @= b1(1)

      s.send_to_ctrl_mem.val @= 0
      s.send_to_ctrl_mem.msg @= s.CgraPayloadType(0, 0, 0, 0, 0, 0)

      s.recv_from_ctrl_mem.rdy @= 0

      for i in range(num_lanes):
        s.Fu[i].recv_opt.val @= s.recv_opt.val

        for j in range(num_outports):
          s.Fu[i].send_out[j].rdy @= s.send_out[j].rdy

        s.Fu[i].recv_in[0].val @= s.recv_in[s.in0_idx].val
        s.Fu[i].recv_in[1].val @= s.recv_in[s.in1_idx].val
        s.Fu[i].recv_const.val @= s.recv_const.val

        # Note that the predication for a combined FU should be identical/shareable,
        # which means the computation in different basic block cannot be combined.
        # s.Fu[i].recv_opt.msg.predicate = s.recv_opt.msg.predicate
      s.recv_const.rdy @= s.Fu[0].recv_const.rdy
      s.recv_opt.rdy @= s.Fu[0].recv_opt.rdy

    @update
    def update_opt():

      for j in range( num_outports ):
        s.send_out[j].val @= b1(0)
        s.send_out[j].msg.predicate @= b1(0)

      s.send_out[0].val @= s.Fu[0].send_out[0].val & \
                           s.recv_opt.val

      for i in range(num_lanes):
        s.Fu[i].recv_opt.msg.fu_in[0] @= 1
        s.Fu[i].recv_opt.msg.fu_in[1] @= 2
        s.Fu[i].recv_opt.msg.operation @= OPT_NAH
        s.Fu[i].combine_adder @= 0

      if ( s.recv_opt.msg.operation == OPT_VEC_ADD ) | \
         ( s.recv_opt.msg.operation == OPT_VEC_ADD_COMBINED ):
        for i in range(num_lanes):
          s.Fu[i].recv_opt.msg.operation @= OPT_ADD
          s.Fu[i].combine_adder @= (s.recv_opt.msg.operation == OPT_VEC_ADD_COMBINED)
        s.send_out[0].msg.predicate @= s.in0_msg.predicate & s.in1_msg.predicate

      elif ( s.recv_opt.msg.operation == OPT_VEC_SUB ) | \
           ( s.recv_opt.msg.operation == OPT_VEC_SUB_COMBINED ):
        for i in range(num_lanes):
          s.Fu[i].recv_opt.msg.operation @= OPT_SUB
          s.Fu[i].combine_adder @= (s.recv_opt.msg.operation == OPT_VEC_SUB_COMBINED)
        s.send_out[0].msg.predicate @= s.in0_msg.predicate & s.in1_msg.predicate

      # elif ( s.recv_opt.msg.operation == OPT_VEC_ADD_CONST ) | \
      #      ( s.recv_opt.msg.operation == OPT_ADD_CONST ):
      elif (s.recv_opt.msg.operation == OPT_VEC_ADD_CONST) | \
           (s.recv_opt.msg.operation == OPT_VEC_ADD_CONST_COMBINED):
        for i in range(num_lanes):
          s.Fu[i].recv_opt.msg.operation @= OPT_ADD_CONST
          s.Fu[i].combine_adder @= (s.recv_opt.msg.operation == OPT_VEC_ADD_COMBINED)
        s.send_out[0].msg.predicate @= s.in0_msg.predicate

      elif (s.recv_opt.msg.operation == OPT_VEC_SUB_CONST ) | \
           (s.recv_opt.msg.operation == OPT_VEC_SUB_CONST_COMBINED ):
        for i in range(num_lanes):
          s.Fu[i].recv_opt.msg.operation @= OPT_SUB_CONST
          s.Fu[i].combine_adder @= (s.recv_opt.msg.operation == OPT_VEC_SUB_CONST_COMBINED)
        s.send_out[0].msg.predicate @= s.in0_msg.predicate

      else:
        for j in range(num_outports):
          s.send_out[j].val @= b1(0)

    @update
    def update_mem():
      s.to_mem_waddr.val @= b1(0)
      s.to_mem_wdata.val @= b1(0)
      s.to_mem_wdata.msg @= s.const_zero
      s.to_mem_waddr.msg @= s.DataAddrType(0)
      s.to_mem_raddr.msg @= s.DataAddrType(0)
      s.to_mem_raddr.val @= b1(0)
      s.from_mem_rdata.rdy @= b1(0)

  def line_trace(s):
    return str(s.in0_msg) + OPT_SYMBOL_DICT[s.recv_opt.msg.operation] + str(s.in1_msg) + " -> " + str(s.send_out[0].msg)

