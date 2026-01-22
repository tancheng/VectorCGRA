"""
==========================================================================
StreamingMemUnitRTL.py
==========================================================================
Scratchpad memory streaming load unit for CGRA tiles.

Author : Yufei Yang
  Date : Jan 21, 2026
"""

from pymtl3 import *
from ..basic.Fu import Fu
from ...lib.basic.val_rdy.ifcs import ValRdySendIfcRTL, ValRdyRecvIfcRTL
from ...lib.messages import *
from ...lib.opt_type import *

class StreamingMemUnitRTL(Component):

  def construct(s, DataType, CtrlType, num_inports,
                num_outports, data_mem_size, ctrl_mem_size = 4,
                vector_factor_power = 0,
                data_bitwidth = 32):

    PredicateType = DataType.get_field_type(kAttrPredicate)
    # Constant
    num_entries = 2
    AddrType = mk_bits(clog2(data_mem_size))
    CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
    s.ctrl_addr_inport = InPort(CtrlAddrType)
    CountType = mk_bits(clog2(num_entries + 1))
    FuInType = mk_bits(clog2(num_inports + 1))
    # 3 indicates at most 7, i.e., 2^7 vectorization factor -> 128
    VectorFactorPowerType = mk_bits(3)
    VectorFactorType = mk_bits(8)
    s.CgraPayloadType = mk_cgra_payload(DataType,
                                        AddrType,
                                        CtrlType,
                                        CtrlAddrType)

    # Interfaces.
    s.recv_in = [ValRdyRecvIfcRTL(DataType) for _ in range(num_inports)]
    s.recv_const = ValRdyRecvIfcRTL(DataType)
    s.recv_opt = ValRdyRecvIfcRTL(CtrlType)
    s.send_out = [ValRdySendIfcRTL(DataType) for _ in range(num_outports)]
    s.send_to_ctrl_mem = ValRdySendIfcRTL(s.CgraPayloadType)
    s.recv_from_ctrl_mem = ValRdyRecvIfcRTL(s.CgraPayloadType)

    # Interfaces to the data sram, need to interface them with
    # the data memory module in top level.
    s.to_mem_raddr = ValRdySendIfcRTL(AddrType)
    s.from_mem_rdata = ValRdyRecvIfcRTL(DataType)
    s.to_mem_waddr = ValRdySendIfcRTL(AddrType)
    s.to_mem_wdata = ValRdySendIfcRTL(DataType)

    # Interfaces for streaming LD.
    s.streaming_start_raddr = InPort(AddrType)
    s.streaming_stride = InPort(AddrType)
    s.streaming_end_raddr = InPort(AddrType)
    # This is for blocking fu_crossbar and routing_crossbar
    # when performing streaming LD operation.
    s.streaming_done = OutPort(b1)

    # Redundant interface, only used by PhiRTL.
    s.clear = InPort(b1)

    s.in0 = Wire(FuInType)
    s.in1 = Wire(FuInType)

    idx_nbits = clog2(num_inports)
    s.in0_idx = Wire(idx_nbits)
    s.in1_idx = Wire(idx_nbits)

    s.in0_idx //= s.in0[0:idx_nbits]
    s.in1_idx //= s.in1[0:idx_nbits]

    # Components.
    s.recv_in_val_vector = Wire(num_inports)
    s.recv_all_val = Wire(1)
    # Indicates whether the raddr has been sent to memory as request,
    # to avoid repeatly sending the same request when the response has not
    # yet returned.
    s.already_sent_raddr = Wire(1)
    s.vector_factor_power = Wire(VectorFactorPowerType)
    s.vector_factor_counter = Wire(VectorFactorType)
    s.reached_vector_factor = Wire(1)

    # One streaming LD will issue multiple single LD request.
    # Indicates the raddr of each request.
    s.single_request_addr = Wire(AddrType)
    # Indicates the request that each response is corresponding to.
    s.single_response_of_which_request_addr = Wire(AddrType)

    # Registers for when to enter streaming status.
    s.ctrl_addr_reg = Wire(CtrlAddrType)
    s.streaming_status = Wire(1)

    # Connections.
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

      s.send_to_ctrl_mem.val @= 0
      s.send_to_ctrl_mem.msg @= s.CgraPayloadType(0, 0, 0, 0, 0)
      s.recv_from_ctrl_mem.rdy @= 0

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
        if s.recv_opt.msg.operation == OPT_STREAM_LD:
          # Streaming LD does not consume any operands.
          s.recv_in[s.in0_idx].rdy @= 0
          s.to_mem_raddr.val @= s.streaming_status & (s.single_request_addr <= s.streaming_end_raddr)
          s.to_mem_raddr.msg @= s.single_request_addr
          s.from_mem_rdata.rdy @= s.send_out[0].rdy
          s.send_out[0].val @= s.from_mem_rdata.val
          s.send_out[0].msg @= s.from_mem_rdata.msg
          s.send_out[0].msg.predicate @= s.from_mem_rdata.msg.predicate & \
                                           s.reached_vector_factor
          # Current operation blocks until streaming finishes.
          s.recv_opt.rdy @= s.send_out[0].rdy & s.streaming_done
        
        else:
          for j in range(num_outports):
            s.send_out[j].val @= b1(0)
          s.recv_opt.rdy @= 0
          s.recv_in[s.in0_idx].rdy @= 0
          s.recv_in[s.in1_idx].rdy @= 0

    @update
    def update_streaming_done():
      if s.recv_opt.val:
        if s.recv_opt.msg.operation == OPT_STREAM_LD:
          # Streaming LD is done when the last streaming result is consumed.
          s.streaming_done @= (s.single_response_of_which_request_addr == s.streaming_end_raddr) &\
                  s.from_mem_rdata.val & s.from_mem_rdata.rdy
        else:
          s.streaming_done @= 1
      else:
        s.streaming_done @= 1

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

    @update_ff
    def update_already_sent_raddr():
      if s.reset:
        s.already_sent_raddr <<= 0
      else:
        if ~s.recv_opt.val:
          s.already_sent_raddr <<= 0
        elif s.from_mem_rdata.val & s.from_mem_rdata.rdy:
          # Clears the flag when the data has returned (s.from_mem_rdata.val)
          # and successfully delivered to the destination (s.from_mem_rdata.rdy).
          s.already_sent_raddr <<= 0
        elif s.to_mem_raddr.val & \
             s.to_mem_raddr.rdy & \
             ~s.already_sent_raddr:
          s.already_sent_raddr <<= 1
        else:
          s.already_sent_raddr <<= s.already_sent_raddr

    @update_ff
    def update_single_request_addr():
      if (s.recv_opt.msg.operation == OPT_STREAM_LD) & (s.ctrl_addr_reg != s.ctrl_addr_inport):
        # Initializes when detecting operation changes to OPT_STREAM_LD, 
        s.single_request_addr <<= s.streaming_start_raddr
      elif s.streaming_done:
        # Resets when streaming done.
        s.single_request_addr <<= 0
      elif s.to_mem_raddr.val & s.to_mem_raddr.rdy:
        # Updates everytime issuing a single request within the same streaming LD.
        s.single_request_addr <<= s.single_request_addr + s.streaming_stride
      else:
        s.single_request_addr <<= s.single_request_addr

    @update_ff
    def update_single_response_of_which_request_addr():
      if (s.recv_opt.msg.operation == OPT_STREAM_LD) & (s.ctrl_addr_reg != s.ctrl_addr_inport):
        # Initializes when detecting operation changes to OPT_STREAM_LD, 
        s.single_response_of_which_request_addr <<= s.streaming_start_raddr
      elif s.streaming_done:
        # Resets when streaming done.
        s.single_response_of_which_request_addr <<= 0
      elif s.from_mem_rdata.val & s.from_mem_rdata.rdy:
        # Updates everytime receives a response and is consumed.
        s.single_response_of_which_request_addr <<= s.single_response_of_which_request_addr + s.streaming_stride
      else:
        s.single_response_of_which_request_addr <<= s.single_response_of_which_request_addr

    @update_ff
    def update_streaming_status():
      if (s.recv_opt.msg.operation == OPT_STREAM_LD) & (s.ctrl_addr_reg != s.ctrl_addr_inport):
        # Starts streaming at next cycle when detecting operation changes to OPT_STREAM_LD.
        s.streaming_status <<= 1
      elif s.streaming_done:
        # Stops streaming when address reach to the end.
        s.streaming_status <<= 0
      else:
        s.streaming_status <<= s.streaming_status

    @update_ff
    def update_ctrl_addr_reg():
      s.ctrl_addr_reg <<= s.ctrl_addr_inport

  def line_trace(s):
    opt_str = " #"
    if s.recv_opt.val:
      opt_str = OPT_SYMBOL_DICT[s.recv_opt.msg.operation]
    out_str = ",".join([str(x.msg) for x in s.send_out])
    recv_str = ",".join([str(x.msg) for x in s.recv_in])
    return f'[recv: {recv_str}] {opt_str} (const: {s.recv_const.msg}) ] = [out: {out_str}] (s.recv_opt.rdy: {s.recv_opt.rdy}, {OPT_SYMBOL_DICT[s.recv_opt.msg.operation]}, send[0].val: {s.send_out[0].val}) <{s.recv_const.val}|{s.recv_const.msg}>'

