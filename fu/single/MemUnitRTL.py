"""
==========================================================================
MemUnitRTL.py
==========================================================================
Scratchpad memory access unit for CGRA tiles.

Author : Cheng Tan
  Date : November 29, 2019
"""

from pymtl3 import *
from ..basic.Fu import Fu
from ...lib.basic.val_rdy.ifcs import ValRdySendIfcRTL, ValRdyRecvIfcRTL
from ...lib.opt_type import *

class MemUnitRTL(Component):

  def construct(s, DataType, PredicateType, CtrlType, num_inports,
                num_outports, data_mem_size, vector_factor_power = 0):

    # Constant
    num_entries = 2
    AddrType = mk_bits(clog2(data_mem_size))
    CountType = mk_bits(clog2(num_entries + 1))
    FuInType = mk_bits(clog2(num_inports + 1))
    # 3 indicates at most 7, i.e., 2^7 vectorization factor -> 128
    VectorFactorPowerType = mk_bits(3)
    VectorFactorType = mk_bits(8)

    # Interface
    s.recv_in = [ValRdyRecvIfcRTL(DataType) for _ in range(num_inports)]
    s.recv_predicate = ValRdyRecvIfcRTL(PredicateType)
    s.recv_const = ValRdyRecvIfcRTL(DataType)
    s.recv_opt = ValRdyRecvIfcRTL(CtrlType)
    s.send_out = [ValRdySendIfcRTL(DataType) for _ in range(num_outports)]

    # Interface to the data sram, need to interface them with
    # the data memory module in top level
    s.to_mem_raddr = ValRdySendIfcRTL(AddrType)
    s.from_mem_rdata = ValRdyRecvIfcRTL(DataType)
    s.to_mem_waddr = ValRdySendIfcRTL(AddrType)
    s.to_mem_wdata = ValRdySendIfcRTL(DataType)

    s.in0 = Wire(FuInType)
    s.in1 = Wire(FuInType)

    idx_nbits = clog2(num_inports)
    s.in0_idx = Wire(idx_nbits)
    s.in1_idx = Wire(idx_nbits)

    s.in0_idx //= s.in0[0:idx_nbits]
    s.in1_idx //= s.in1[0:idx_nbits]

    # Components
    s.recv_in_val_vector = Wire(num_inports)
    s.recv_all_val = Wire(1)
    s.vector_factor_power = Wire(VectorFactorPowerType)
    s.vector_factor_counter = Wire(VectorFactorType)
    s.reached_vector_factor = Wire(1)

    s.vector_factor_power //= vector_factor_power

    @update
    def comb_logic():

      s.recv_all_val @= 0
      # For pick input register
      s.in0 @= FuInType(0)
      s.in1 @= FuInType(0)
      for i in range(num_inports):
        s.recv_in[i].rdy @= b1(0)
      for i in range(num_outports):
        s.send_out[i].val @= 0
        s.send_out[i].msg @= DataType()

      s.recv_const.rdy @= 0
      s.recv_opt.rdy @= 0

      if s.recv_opt.val:
        if s.recv_opt.msg.fu_in[0] != 0:
          s.in0 @= zext(s.recv_opt.msg.fu_in[0] - 1, FuInType)
        if s.recv_opt.msg.fu_in[1] != 0:
          s.in1 @= zext(s.recv_opt.msg.fu_in[1] - 1, FuInType)

      s.to_mem_waddr.val @= 0
      s.to_mem_waddr.msg @= AddrType()
      s.to_mem_wdata.val @= 0
      s.to_mem_wdata.msg @= DataType()
      s.to_mem_raddr.val @= 0
      s.to_mem_raddr.msg @= AddrType()
      s.from_mem_rdata.rdy @= 0

      if s.recv_opt.val:
        if s.recv_opt.msg.operation == OPT_LD:
          s.recv_all_val @= s.recv_in[s.in0_idx].val
          # FIXME: to_mem_raddr shouldn't be ready if the existing request not yet returned.
          s.recv_in[s.in0_idx].rdy @= s.recv_all_val & s.to_mem_raddr.rdy
          s.to_mem_raddr.msg @= AddrType(s.recv_in[s.in0_idx].msg.payload[0:AddrType.nbits])
          s.to_mem_raddr.val @= s.recv_all_val
          s.from_mem_rdata.rdy @= s.send_out[0].rdy
          # FIXME: As the memory access might take more than one cycle,
          # the send_out valid no need to depend on recv_all_val.
          s.send_out[0].val @= s.from_mem_rdata.val
          s.send_out[0].msg @= s.from_mem_rdata.msg
          s.send_out[0].msg.predicate @= s.recv_in[s.in0_idx].msg.predicate & \
                                         s.from_mem_rdata.msg.predicate & \
                                         s.reached_vector_factor
          s.recv_opt.rdy @= s.send_out[0].rdy & s.from_mem_rdata.val

        # LD_CONST indicates the address is a const.
        elif s.recv_opt.msg.operation == OPT_LD_CONST:
          s.recv_all_val @= s.recv_const.val
          s.recv_const.rdy @= s.recv_all_val & s.to_mem_raddr.rdy
          s.to_mem_raddr.msg @= AddrType(s.recv_const.msg.payload[0:AddrType.nbits])
          s.to_mem_raddr.val @= s.recv_all_val
          s.from_mem_rdata.rdy @= s.send_out[0].rdy
          s.send_out[0].val @= s.from_mem_rdata.val
          s.send_out[0].msg @= s.from_mem_rdata.msg
          s.send_out[0].msg.predicate @= s.recv_const.msg.predicate & \
                                         s.from_mem_rdata.msg.predicate & \
                                         s.reached_vector_factor
          s.recv_opt.rdy @= s.send_out[0].rdy & s.from_mem_rdata.val

        elif s.recv_opt.msg.operation == OPT_STR:
          s.recv_all_val @= s.recv_in[s.in0_idx].val & \
                            s.recv_in[s.in1_idx].val
          s.recv_in[s.in0_idx].rdy @= s.recv_all_val & s.to_mem_waddr.rdy & s.to_mem_wdata.rdy
          s.recv_in[s.in1_idx].rdy @= s.recv_all_val & s.to_mem_waddr.rdy & s.to_mem_wdata.rdy
          s.to_mem_waddr.msg @= AddrType(s.recv_in[0].msg.payload[0:AddrType.nbits])
          s.to_mem_waddr.val @= s.recv_all_val
          s.to_mem_wdata.msg @= s.recv_in[s.in1_idx].msg
          s.to_mem_wdata.msg.predicate @= s.recv_in[s.in0_idx].msg.predicate & \
                                          s.recv_in[s.in1_idx].msg.predicate & \
                                          s.reached_vector_factor
          s.to_mem_wdata.val @= s.recv_all_val

          # `send_out` is meaningless for store operation.
          s.send_out[0].val @= b1(0)

          s.recv_opt.rdy @= s.recv_all_val & s.to_mem_waddr.rdy & s.to_mem_wdata.rdy

        # STR_CONST indicates the address is a const.
        elif s.recv_opt.msg.operation == OPT_STR_CONST:
          s.recv_all_val @= s.recv_in[s.in0_idx].val & s.recv_const.val
          s.recv_const.rdy @= s.recv_all_val & s.to_mem_waddr.rdy & s.to_mem_wdata.rdy
          # Only needs one input register to indicate the storing data.
          s.recv_in[s.in0_idx].rdy @= s.recv_all_val & s.to_mem_waddr.rdy & s.to_mem_wdata.rdy
          s.to_mem_waddr.msg @= AddrType(s.recv_const.msg.payload[0:AddrType.nbits])
          s.to_mem_waddr.val @= s.recv_all_val & \
                                s.recv_in[s.in0_idx].msg.predicate & \
                                s.recv_const.msg.predicate
          s.to_mem_wdata.msg @= s.recv_in[s.in0_idx].msg
          s.to_mem_wdata.msg.predicate @= s.recv_in[s.in0_idx].msg.predicate & \
                                          s.recv_const.msg.predicate & \
                                          s.reached_vector_factor
          s.to_mem_wdata.val @= s.recv_all_val & \
                                s.recv_in[s.in0_idx].msg.predicate & \
                                s.recv_const.msg.predicate

          # `send_out` is meaningless for store operation.
          s.send_out[0].val @= b1(0)

          s.recv_opt.rdy @= s.recv_all_val & s.to_mem_waddr.rdy & s.to_mem_wdata.rdy

        else:
          for j in range(num_outports):
            s.send_out[j].val @= b1(0)
          s.recv_opt.rdy @= 0
          s.recv_in[s.in0_idx].rdy @= 0
          s.recv_in[s.in1_idx].rdy @= 0

    @update
    def update_reached_vector_factor():
      s.reached_vector_factor @= 0
      if s.recv_opt.val & (s.vector_factor_counter + \
                           (VectorFactorType(1) << zext(s.vector_factor_power, VectorFactorType)) >= \
                           (VectorFactorType(1) << zext(s.recv_opt.msg.vector_factor_power, VectorFactorType))):
        s.reached_vector_factor @= 1

    @update_ff
    def update_vector_factor_counter():
      if s.reset:
        s.vector_factor_counter <<= 0
      else:
        if s.recv_opt.val:
          if s.recv_opt.msg.is_last_ctrl & \
             (s.vector_factor_counter + \
              (VectorFactorType(1) << zext(s.vector_factor_power, VectorFactorType)) < \
             (VectorFactorType(1) << zext(s.recv_opt.msg.vector_factor_power, VectorFactorType))):
            s.vector_factor_counter <<= s.vector_factor_counter + \
                                        (VectorFactorType(1) << zext(s.vector_factor_power, \
                                                                     VectorFactorType))
          elif s.recv_opt.msg.is_last_ctrl & s.reached_vector_factor:
            s.vector_factor_counter <<= 0

  def line_trace( s ):
    opt_str = " #"
    if s.recv_opt.val:
      opt_str = OPT_SYMBOL_DICT[s.recv_opt.msg.operation]
    out_str = ",".join([str(x.msg) for x in s.send_out])
    recv_str = ",".join([str(x.msg) for x in s.recv_in])
    return f'[recv: {recv_str}] {opt_str} (const: {s.recv_const.msg}) ] = [out: {out_str}] (s.recv_opt.rdy: {s.recv_opt.rdy}, {OPT_SYMBOL_DICT[s.recv_opt.msg.operation]}, send[0].val: {s.send_out[0].val}) <{s.recv_const.val}|{s.recv_const.msg}>'

