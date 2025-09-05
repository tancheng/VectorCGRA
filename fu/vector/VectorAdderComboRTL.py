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
from ...lib.opt_type import *

class VectorAdderComboRTL(Component):

  def construct(s, DataType, PredicateType, CtrlType,
                num_inports, num_outports, data_mem_size,
                vector_factor_power = 0,
                num_lanes = 4, data_bandwidth = 64):

    # Constants
    assert(data_bandwidth % num_lanes == 0)
    num_entries = 2
    s.const_zero = DataType()
    sub_bw = data_bandwidth // num_lanes
    CountType = mk_bits(clog2(num_entries + 1))

    # Interface
    s.recv_in = [RecvIfcRTL(DataType) for _ in range(num_inports)]
    s.recv_const = RecvIfcRTL(DataType)
    s.recv_opt = RecvIfcRTL(CtrlType)
    s.send_out = [SendIfcRTL(DataType) for _ in range(num_outports)]
    s.send_to_controller = SendIfcRTL(DataType)

    # Components
    s.Fu = [VectorAdderRTL(sub_bw, CtrlType, 4, 2, data_mem_size)
            for _ in range(num_lanes)]

    # Connection: for carry-in/out
    s.Fu[0].carry_in //= 0
    for i in range(1, num_lanes):
      s.Fu[i].carry_in //= s.Fu[i-1].carry_out

    for i in range(num_lanes):
      # Connection: split into vectorized FUs.
      # TODO: Make the operand idx be dynamically picked: https://github.com/tancheng/VectorCGRA/issues/180.
      s.recv_in[0].msg.payload[i*sub_bw:(i+1)*sub_bw] //= s.Fu[i].recv_in[0].msg[0:sub_bw]
      s.recv_in[1].msg.payload[i*sub_bw:(i+1)*sub_bw] //= s.Fu[i].recv_in[1].msg[0:sub_bw]
      s.recv_const.msg.payload[i*sub_bw:(i+1)*sub_bw] //= s.Fu[i].recv_const.msg[0:sub_bw]

      # Connection: aggregate into combo out
      s.Fu[i].send_out[0].msg[0:sub_bw] //= s.send_out[0].msg.payload[i*sub_bw:(i+1)*sub_bw]

    # Redundant interfaces for MemUnit
    AddrType = mk_bits(clog2(data_mem_size))
    s.to_mem_raddr = SendIfcRTL(AddrType)
    s.from_mem_rdata = RecvIfcRTL(DataType)
    s.to_mem_waddr = SendIfcRTL(AddrType)
    s.to_mem_wdata = SendIfcRTL(DataType)

    @update
    def update_signal():
      s.recv_in[0].rdy @= s.Fu[0].recv_in[0].rdy
      s.recv_in[1].rdy @= s.Fu[0].recv_in[1].rdy

      for i in range(num_lanes):
        s.Fu[i].recv_opt.val @= s.recv_opt.val

        for j in range(num_outports):
          s.Fu[i].send_out[j].rdy @= s.send_out[j].rdy

        s.Fu[i].recv_in[0].val @= s.recv_in[0].val
        s.Fu[i].recv_in[1].val @= s.recv_in[1].val
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
        s.send_out[0].msg.predicate @= s.recv_in[0].msg.predicate & s.recv_in[1].msg.predicate

      elif ( s.recv_opt.msg.operation == OPT_VEC_SUB ) | \
           ( s.recv_opt.msg.operation == OPT_VEC_SUB_COMBINED ):
        for i in range(num_lanes):
          s.Fu[i].recv_opt.msg.operation @= OPT_SUB
          s.Fu[i].combine_adder @= (s.recv_opt.msg.operation == OPT_VEC_SUB_COMBINED)
        s.send_out[0].msg.predicate @= s.recv_in[0].msg.predicate & s.recv_in[1].msg.predicate

      # elif ( s.recv_opt.msg.operation == OPT_VEC_ADD_CONST ) | \
      #      ( s.recv_opt.msg.operation == OPT_ADD_CONST ):
      elif (s.recv_opt.msg.operation == OPT_VEC_ADD_CONST) | \
           (s.recv_opt.msg.operation == OPT_VEC_ADD_CONST_COMBINED):
        for i in range(num_lanes):
          s.Fu[i].recv_opt.msg.operation @= OPT_ADD_CONST
          s.Fu[i].combine_adder @= (s.recv_opt.msg.operation == OPT_VEC_ADD_COMBINED)
        s.send_out[0].msg.predicate @= s.recv_in[0].msg.predicate

      elif (s.recv_opt.msg.operation == OPT_VEC_SUB_CONST ) | \
           (s.recv_opt.msg.operation == OPT_VEC_SUB_CONST_COMBINED ):
        for i in range(num_lanes):
          s.Fu[i].recv_opt.msg.operation @= OPT_SUB_CONST
          s.Fu[i].combine_adder @= (s.recv_opt.msg.operation == OPT_VEC_SUB_CONST_COMBINED)
        s.send_out[0].msg.predicate @= s.recv_in[0].msg.predicate

      else:
        for j in range(num_outports):
          s.send_out[j].val @= b1(0)

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

