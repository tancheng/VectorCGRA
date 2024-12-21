"""
==========================================================================
CtrlMemDynamicRTL.py
==========================================================================
Control memory with dynamic reconfigurability (e.g., receiving control
signals, halt/terminate signals) for each CGRA tile.

Author : Cheng Tan
  Date : Dec 20, 2024
"""

from pymtl3 import *
from pymtl3.stdlib.dstruct.queues import NormalQueue
from pymtl3.stdlib.primitive import RegisterFile
from ...lib.basic.en_rdy.ifcs import SendIfcRTL, RecvIfcRTL
from ...lib.opt_type import *

class CtrlMemDynamicRTL(Component):

  def construct(s, CtrlPktType, CtrlActionType, CtrlSignalType,
                ctrl_mem_size, ctrl_count_per_iter = 4,
                total_ctrl_steps = 4):

    # The total_ctrl_steps indicates the number of steps the ctrl
    # signals should proceed. For example, if the number of ctrl
    # signals is 4 and they need to repeat 5 times, then the total
    # number of steps should be 4 * 5 = 20.
    # assert( ctrl_mem_size <= total_ctrl_steps )

    # Constant
    CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
    PCType = mk_bits(clog2(ctrl_count_per_iter + 1))
    TimeType = mk_bits(clog2(total_ctrl_steps + 1))

    # Interface
    s.send_ctrl = SendIfcRTL(CtrlType)
    # s.recv_waddr = RecvIfcRTL(AddrType)
    # s.recv_ctrl = RecvIfcRTL(CtrlType)

    s.recv_pkt = RecvIfcRTL(CtrPktType)

    # Component
    s.reg_file = RegisterFile(CtrlType, ctrl_mem_size, 1, 1)
    s.recv_pkt_queue = NormalQueue(CtrPktType)
    s.times = Wire(TimeType)
    s.start_iterate_ctrl = Wire(b1)

    # Connections
    s.send_ctrl.msg //= s.reg_file.rdata[0]
    s.recv_pkt_queue.recv //= s.recv_pkt.recv
    # s.reg_file.waddr[0] //= s.recv_waddr.msg
    # s.reg_file.wdata[0] //= s.recv_ctrl.msg
    # s.reg_file.wen[0] //= lambda: s.recv_ctrl.en & s.recv_waddr.en

    @update
    def update_msg():
      if s.recv_pkt_queue.send.msg.ctrl_action == CMD_CONFIG:
        s.reg_file.waddr[0] //= s.recv_pkt_queue.send.msg.ctrl_addr
        s.reg_file.wdata[0] //= s.recv_pkt_queue.send.msg.ctrl_data
        s.reg_file.wen[0] //= s.recv_pkt_queue.send.en

      # @yo96? depending on data, causing combinational loop or not?
      if s.recv_pkt_queue.send.msg.ctrl_action == CMD_CONFIG | \
         s.recv_pkt_queue.send.msg.ctrl_action == CMD_LAUNCH | \
         s.recv_pkt_queue.send.msg.ctrl_action == CMD_TERMINATE | \
         s.recv_pkt_queue.send.msg.ctrl_action == CMD_HALT:
        s.recv_pkt_queue.send.rdy @= 1
      # TODO: Extend for the other commands. Maybe another queue to
      # handle complicated actions.
      # else:


    @update
    def update_send_out_signal():
      if s.start_iterate_ctrl == b1(1):
        if ((total_ctrl_steps > 0) & \
             (s.times == TimeType(total_ctrl_steps))) | \
           (s.reg_file.rdata[0].ctrl == OPT_START):
          s.send_ctrl.en @= b1(0)
        else:
          s.send_ctrl.en @= s.send_ctrl.rdy
      # @yo96? What would happen if we overwrite? ok?
      if s.recv_pkt_queue.send.msg.ctrl_action == CMD_LAUNCH | \
         s.recv_pkt_queue.send.msg.ctrl_action == CMD_TERMINATE:
        s.send_ctrl.en @= b1(0)

    # @update
    # def update_signal():
    #   if ((total_ctrl_steps > 0) & \
    #        (s.times == TimeType(total_ctrl_steps))) | \
    #      (s.reg_file.rdata[0].ctrl == OPT_START):
    #     s.send_ctrl.en @= b1(0)
    #   else:
    #     s.send_ctrl.en @= s.send_ctrl.rdy # s.recv_raddr[i].rdy
      # s.recv_waddr.rdy @= b1(1)
      # s.recv_ctrl.rdy @= b1(1)
      # s.recv_pkt.rdy @= recv_pkt_queue.recv.rdy

    @update_ff
    def update_whether_we_can_iterate_ctrl():
      # if s.reg_file.rdata[0].ctrl != OPT_START:
      # @yo96? data is still there, not released yet?
      if s.recv_pkt_queue.send.msg.ctrl_action == CMD_LAUNCH:
        s.start_iterate_ctrl <<= 1
      elif s.recv_pkt_queue.send.msg.ctrl_action == CMD_TERMINATE:
        s.start_iterate_ctrl <<= 0
      else:
        s.start_iterate_ctrl <<= 1

    @update_ff
    def update_raddr():
      # if s.reg_file.rdata[0].ctrl != OPT_START:
      if s.start_iterate_ctrl == b1(1):
        # @yo96? There is no else, what would happen on the s.times and raddr[0]?
        if (total_ctrl_steps == 0) | \
           (s.times < TimeType(total_ctrl_steps)):
          s.times <<= s.times + TimeType(1)
        # Reads the next ctrl signal only when the current one is done.
        if s.send_ctrl.rdy:
          if zext(s.reg_file.raddr[0] + 1, PCType) == \
             PCType(ctrl_count_per_iter):
            s.reg_file.raddr[0] <<= AddrType(0)
          else:
            s.reg_file.raddr[0] <<= s.reg_file.raddr[0] + AddrType(1)

  def line_trace(s):
    out_str  = "||".join([str(data) for data in s.reg_file.regs])
    return f'{s.recv_ctrl.msg} : [{out_str}] : {s.send_ctrl.msg}'

