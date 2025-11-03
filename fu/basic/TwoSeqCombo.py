"""
==========================================================================
TwoSeqComb.py
==========================================================================
Simple generic two sequentially combined functional units for CGRA tile.

Author : Cheng Tan
  Date : November 28, 2019
"""

from pymtl3 import *
from ...lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ...lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ...lib.messages import *
from ...lib.opt_type import *

class TwoSeqCombo(Component):

  def construct(s, DataType, CtrlType,
                Fu0, Fu1,
                num_inports, num_outports,
                data_mem_size, ctrl_mem_size,
                data_bitwidth = 32):

    PredicateType = DataType.get_field_type(kAttrPredicate)
    # Constant
    num_entries   = 2
    AddrType      = mk_bits(clog2(data_mem_size))
    CtrlAddrType  = mk_bits(clog2(ctrl_mem_size))
    s.const_zero  = DataType(0, 0)
    CountType     = mk_bits(clog2(num_entries + 1))
    s.CgraPayloadType = mk_cgra_payload(DataType,
                                        AddrType,
                                        CtrlType,
                                        CtrlAddrType)

    # Interface
    s.recv_in        = [RecvIfcRTL(DataType) for _ in range(num_inports)]
    s.recv_const     = RecvIfcRTL(DataType)
    s.recv_opt       = RecvIfcRTL(CtrlType)
    s.send_out       = [SendIfcRTL(DataType) for _ in range(num_outports)]
    s.send_to_ctrl_mem = SendIfcRTL(s.CgraPayloadType)
    s.recv_from_ctrl_mem = RecvIfcRTL(s.CgraPayloadType)

    # Redundant interface, only used by PhiRTL.
    s.clear = InPort(b1)

    # Redundant interfaces for MemUnit
    s.to_mem_raddr   = SendIfcRTL(AddrType)
    s.from_mem_rdata = RecvIfcRTL(DataType)
    s.to_mem_waddr   = SendIfcRTL(AddrType)
    s.to_mem_wdata   = SendIfcRTL(DataType)

    # Components
    s.Fu0 = Fu0(DataType, CtrlType, 4, 2, data_mem_size, ctrl_mem_size)
    s.Fu1 = Fu1(DataType, CtrlType, 4, 2, data_mem_size, ctrl_mem_size)

    # Connections
    s.recv_in[0].msg //= s.Fu0.recv_in[0].msg
    s.recv_in[1].msg //= s.Fu0.recv_in[1].msg
    s.recv_in[2].msg //= s.Fu1.recv_in[1].msg

    s.Fu0.send_out[0].msg //= s.Fu1.recv_in[0].msg
    s.Fu1.send_out[0].msg //= s.send_out[0].msg

    s.Fu0.recv_const //= s.recv_const

    @update
    def update_signal():

      s.recv_in[0].rdy  @= s.Fu0.recv_in[0].rdy
      s.recv_in[1].rdy  @= s.Fu0.recv_in[1].rdy
      s.recv_in[2].rdy  @= s.Fu1.recv_in[1].rdy

      s.Fu0.recv_in[0].val @= s.recv_in[0].val
      s.Fu0.recv_in[1].val @= s.recv_in[1].val
      s.Fu1.recv_in[0].val @= s.Fu0.send_out[0].val
      s.Fu1.recv_in[1].val @= s.recv_in[2].val

      s.Fu0.recv_opt.val @= s.recv_opt.val
      s.Fu1.recv_opt.val @= s.recv_opt.val

      s.recv_opt.rdy @= s.Fu0.recv_opt.rdy & s.Fu1.recv_opt.rdy

      s.send_out[0].val @= s.Fu1.send_out[0].val

      s.Fu0.send_out[0].rdy @= s.Fu1.recv_in[0].rdy
      s.Fu1.send_out[0].rdy @= s.send_out[0].rdy

    @update
    def update_mem():
      s.to_mem_waddr.val   @= b1(0)
      s.to_mem_wdata.val   @= b1(0)
      s.to_mem_wdata.msg   @= s.const_zero
      s.to_mem_waddr.msg   @= AddrType(0)
      s.to_mem_raddr.msg   @= AddrType(0)
      s.to_mem_raddr.val   @= b1(0)
      s.from_mem_rdata.rdy @= b1(0)

    @update
    def update_send_to_controller():
      s.send_to_ctrl_mem.val @= 0
      s.send_to_ctrl_mem.msg @= s.CgraPayloadType(0, 0, 0, 0, 0)
      s.recv_from_ctrl_mem.rdy @= 0

  def line_trace(s):
    return s.Fu0.line_trace() + " ; " + s.Fu1.line_trace()

