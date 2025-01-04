"""
==========================================================================
Fu.py
==========================================================================
Simple generic functional unit for CGRA tile. This is the basic functional
unit that can be inherited by both the CL and RTL modules.

Author : Cheng Tan
  Date : August 6, 2023
"""


from pymtl3 import *
from ...lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ...lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ...lib.opt_type import *


class Fu( Component ):

  def construct( s, DataType, PredicateType, CtrlType,
                 num_inports, num_outports, data_mem_size = 4,
                 latency = 1 ):

    # Constant
    num_entries = 2
    AddrType = mk_bits(clog2(data_mem_size))
    s.const_zero = DataType(0, 0)
    CountType = mk_bits(clog2(num_entries + 1))
    FuInType = mk_bits(clog2(num_inports + 1))
    LatencyType = mk_bits(clog2(latency + 1))

    # Interface
    s.recv_in = [RecvIfcRTL(DataType) for _ in range(num_inports)]
    s.recv_predicate = RecvIfcRTL(PredicateType)
    s.recv_const = RecvIfcRTL(DataType)
    s.recv_opt = RecvIfcRTL(CtrlType)
    s.send_out = [SendIfcRTL(DataType) for _ in range(num_outports)]

    # Redundant interfaces for MemUnit
    s.to_mem_raddr = SendIfcRTL(AddrType)
    s.from_mem_rdata = RecvIfcRTL(DataType)
    s.to_mem_waddr = SendIfcRTL(AddrType)
    s.to_mem_wdata = SendIfcRTL(DataType)

    # Components
    s.latency = Wire(LatencyType)

    @update_ff
    def proceed_latency():
      if s.recv_opt.msg.ctrl == OPT_START:
        s.latency <<= LatencyType(0)
      elif s.latency == latency - 1:
        s.latency <<= LatencyType(0)
      else:
        s.latency <<= s.latency + LatencyType(1)

    # @update
    # def update_signal():
    #   for j in range(num_outports):
    #     s.send_rdy_vector[j] @= s.send_out[j].rdy
    #   s.recv_const.rdy @= reduce_and(s.send_rdy_vector) & (s.latency == latency - 1)
    #   # OPT_NAH doesn't require consuming any input.
    #   s.recv_opt.rdy @= ((s.recv_opt.msg.ctrl == OPT_NAH) | \
    #                       reduce_and(s.send_rdy_vector)) & \
    #                      (s.latency == latency - 1)

    @update
    def update_mem():
      s.to_mem_waddr.val @= b1(0)
      s.to_mem_wdata.val @= b1(0)
      s.to_mem_wdata.msg @= s.const_zero
      s.to_mem_waddr.msg @= AddrType(0)
      s.to_mem_raddr.msg @= AddrType(0)
      s.to_mem_raddr.val @= b1(0)
      s.from_mem_rdata.rdy @= b1(0)

  def line_trace( s ):
    opt_str = " #"
    if s.recv_opt.val:
      opt_str = OPT_SYMBOL_DICT[s.recv_opt.msg.ctrl]
    out_str = ",".join([str(x.msg) for x in s.send_out])
    recv_str = ",".join([str(x.msg) for x in s.recv_in])
    return f'[recv: {recv_str}] {opt_str}(opt_predicate:{s.recv_opt.msg.predicate}) (const_reg: {s.recv_const.msg}, predicate_reg: {s.recv_predicate.msg}) ] = [out: {out_str}] (s.recv_opt.rdy: {s.recv_opt.rdy}, {OPT_SYMBOL_DICT[s.recv_opt.msg.ctrl]}, recv_opt.val: {s.recv_opt.val}, send[0].val: {s.send_out[0].val}) '
