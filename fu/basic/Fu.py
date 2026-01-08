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
from ...lib.messages import *
from ...lib.opt_type import *

class Fu(Component):

  def construct(s, DataType, CtrlType,
                num_inports, num_outports,
                data_mem_size = 4, ctrl_mem_size = 4,
                latency = 1, vector_factor_power = 0,
                data_bitwidth = 32):

    PredicateType = DataType.get_field_type(kAttrPredicate)
    # Constants.
    num_entries = 2
    DataAddrType = mk_bits(clog2(data_mem_size))
    CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
    s.ctrl_addr_inport = InPort(CtrlAddrType)
    CountType = mk_bits(clog2(num_entries + 1))
    FuInType = mk_bits(clog2(num_inports + 1))
    LatencyType = mk_bits(clog2(latency + 1))
    s.const_zero = DataType(0, 0)
    # 3 indicates at most 7, i.e., 2^7 vectorization factor -> 128
    VectorFactorPowerType = mk_bits(3)
    VectorFactorType = mk_bits(8)
    s.CgraPayloadType = mk_cgra_payload(DataType,
                                        DataAddrType,
                                        CtrlType,
                                        CtrlAddrType)

    # Interfaces.
    s.recv_in = [RecvIfcRTL(DataType) for _ in range(num_inports)]
    s.recv_const = RecvIfcRTL(DataType)
    s.recv_opt = RecvIfcRTL(CtrlType)
    s.send_out = [SendIfcRTL(DataType) for _ in range(num_outports)]
    # Used for command delivery between functional unit and control memory, which is usually sent to (or received from) the controller.
    s.send_to_ctrl_mem = SendIfcRTL(s.CgraPayloadType)
    s.recv_from_ctrl_mem = RecvIfcRTL(s.CgraPayloadType)

    # Redundant interface, only used by PhiRTL.
    s.clear = InPort(b1)

    # Components.
    # Redundant interfaces for MemUnit
    s.to_mem_raddr = SendIfcRTL(DataAddrType)
    s.from_mem_rdata = RecvIfcRTL(DataType)
    s.to_mem_waddr = SendIfcRTL(DataAddrType)
    s.to_mem_wdata = SendIfcRTL(DataType)

    s.vector_factor_power = Wire(VectorFactorPowerType)
    s.vector_factor_counter = Wire(VectorFactorType)
    s.reached_vector_factor = Wire(1)
    s.latency = Wire(LatencyType)

    # Connections.
    s.vector_factor_power //= vector_factor_power

    @update
    def update_mem():
      s.to_mem_waddr.val @= b1(0)
      s.to_mem_wdata.val @= b1(0)
      s.to_mem_wdata.msg @= s.const_zero
      s.to_mem_waddr.msg @= DataAddrType(0)
      s.to_mem_raddr.msg @= DataAddrType(0)
      s.to_mem_raddr.val @= b1(0)
      s.from_mem_rdata.rdy @= b1(0)

    @update_ff
    def proceed_latency():
      if s.recv_opt.msg.operation == OPT_START:
        s.latency <<= LatencyType(0)
      elif s.latency == latency - 1:
        s.latency <<= LatencyType(0)
      else:
        s.latency <<= s.latency + LatencyType(1)

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

  def line_trace(s):
    opt_str = " #"
    if s.recv_opt.val:
      opt_str = OPT_SYMBOL_DICT[s.recv_opt.msg.operation]
    out_str = ",".join([str(x.msg) for x in s.send_out])
    recv_str = ",".join([str(x.msg) for x in s.recv_in])
    return f'[recv: {recv_str}] {opt_str} (const_reg: {s.recv_const.msg} ] = [out: {out_str}] (s.recv_opt.rdy: {s.recv_opt.rdy}, {OPT_SYMBOL_DICT[s.recv_opt.msg.operation]}, recv_opt.val: {s.recv_opt.val}, send[0].val: {s.send_out[0].val})'
