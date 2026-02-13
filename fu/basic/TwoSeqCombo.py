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

  def construct(s, CtrlPktType,
                Fu0, Fu1,
                num_inports, num_outports):

    # Constant
    num_entries   = 2
    s.DataType = CtrlPktType.get_field_type(kAttrPayload).get_field_type(kAttrData)
    s.AddrType = CtrlPktType.get_field_type(kAttrPayload).get_field_type(kAttrDataAddr)
    s.CtrlType = CtrlPktType.get_field_type(kAttrPayload).get_field_type(kAttrCtrl)
    s.CtrlAddrType = CtrlPktType.get_field_type(kAttrPayload).get_field_type(kAttrCtrlAddr)
    s.CgraPayloadType = CtrlPktType.get_field_type(kAttrPayload)
    s.ctrl_addr_inport = InPort(s.CtrlAddrType)
    s.const_zero  = s.DataType(0, 0)
    CountType     = mk_bits(clog2(num_entries + 1))

    # Interface
    s.recv_in        = [RecvIfcRTL(s.DataType) for _ in range(num_inports)]
    s.recv_const     = RecvIfcRTL(s.DataType)
    s.recv_opt       = RecvIfcRTL(s.CtrlType)
    s.send_out       = [SendIfcRTL(s.DataType) for _ in range(num_outports)]
    s.send_to_ctrl_mem = SendIfcRTL(s.CgraPayloadType)
    s.recv_from_ctrl_mem = RecvIfcRTL(s.CgraPayloadType)

    # Redundant interface, only used by PhiRTL.
    s.clear = InPort(b1)

    # Redundant interfaces for MemUnit
    s.to_mem_raddr   = SendIfcRTL(s.AddrType)
    s.from_mem_rdata = RecvIfcRTL(s.DataType)
    s.to_mem_waddr   = SendIfcRTL(s.AddrType)
    s.to_mem_wdata   = SendIfcRTL(s.DataType)

    # Components
    s.Fu0 = Fu0(CtrlPktType, 4, 2)
    s.Fu1 = Fu1(CtrlPktType, 4, 2)

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
      s.to_mem_waddr.msg   @= s.AddrType(0)
      s.to_mem_raddr.msg   @= s.AddrType(0)
      s.to_mem_raddr.val   @= b1(0)
      s.from_mem_rdata.rdy @= b1(0)

    @update
    def update_send_to_controller():
      s.send_to_ctrl_mem.val @= 0
      s.send_to_ctrl_mem.msg @= s.CgraPayloadType(0, 0, 0, 0, 0)
      s.recv_from_ctrl_mem.rdy @= 0

  def line_trace(s):
    return s.Fu0.line_trace() + " ; " + s.Fu1.line_trace()

