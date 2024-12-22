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
from ...lib.cmd_type import *
from ...lib.opt_type import *

class CtrlMemDynamicRTL(Component):

  def construct(s, CtrlPktType, CtrlSignalType, ctrl_mem_size,
                num_fu_inports, num_fu_outports, num_tile_inports,
                num_tile_outports, ctrl_count_per_iter = 4,
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
    num_routing_outports = num_tile_outports + num_fu_inports

    # Interface
    s.send_ctrl = SendIfcRTL(CtrlSignalType)
    s.recv_pkt = RecvIfcRTL(CtrlPktType)

    # Component
    s.reg_file = RegisterFile(CtrlSignalType, ctrl_mem_size, 1, 1)
    s.recv_pkt_queue = NormalQueue(CtrlPktType)
    s.times = Wire(TimeType)
    s.start_iterate_ctrl = Wire(b1)

    # Connections
    s.send_ctrl.msg //= s.reg_file.rdata[0]
    s.recv_pkt.rdy //= s.recv_pkt_queue.enq_rdy

    @update
    def update_msg():

      s.recv_pkt_queue.enq_en @= s.recv_pkt.en & s.recv_pkt_queue.enq_rdy
      s.recv_pkt_queue.enq_msg @= CtrlPktType()
      s.reg_file.wdata[0] @= CtrlSignalType()
      if s.recv_pkt.en:
        s.recv_pkt_queue.enq_msg @= s.recv_pkt.msg

      if s.recv_pkt_queue.deq_msg.ctrl_action == CMD_CONFIG:
        s.reg_file.wen[0] @= 1 # s.recv_pkt_queue.deq_en
        s.reg_file.waddr[0] @= s.recv_pkt_queue.deq_msg.ctrl_addr
        # Fills the fields of the control signal.
        s.reg_file.wdata[0].ctrl @= s.recv_pkt_queue.deq_msg.ctrl_operation
        s.reg_file.wdata[0].predicate @= s.recv_pkt_queue.deq_msg.ctrl_predicate
        for i in range(num_fu_inports):
          s.reg_file.wdata[0].fu_in[i] @= s.recv_pkt_queue.deq_msg.ctrl_fu_in[i]
        for i in range(num_routing_outports):
          s.reg_file.wdata[0].routing_xbar_outport[i] @= s.recv_pkt_queue.deq_msg.ctrl_routing_xbar_outport[i]
          s.reg_file.wdata[0].fu_xbar_outport[i] @= s.recv_pkt_queue.deq_msg.ctrl_fu_xbar_outport[i]
        for i in range(num_tile_inports):
          s.reg_file.wdata[0].routing_predicate_in[i] @= s.recv_pkt_queue.deq_msg.ctrl_routing_predicate_in[i]

      # @yo96? depending on data, causing combinational loop or not?
      if (s.recv_pkt_queue.deq_msg.ctrl_action == CMD_CONFIG) | \
         (s.recv_pkt_queue.deq_msg.ctrl_action == CMD_LAUNCH) | \
         (s.recv_pkt_queue.deq_msg.ctrl_action == CMD_TERMINATE) | \
         (s.recv_pkt_queue.deq_msg.ctrl_action == CMD_PAUSE):
        s.recv_pkt_queue.deq_en @= 1
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
      if s.recv_pkt_queue.deq_rdy & \
         ((s.recv_pkt_queue.deq_msg.ctrl_action == CMD_PAUSE) | \
          (s.recv_pkt_queue.deq_msg.ctrl_action == CMD_TERMINATE)):
        s.send_ctrl.en @= b1(0)

    @update_ff
    def update_whether_we_can_iterate_ctrl():
      if s.recv_pkt_queue.deq_rdy:
        # @yo96? data is still there, not released yet?
        if s.recv_pkt_queue.deq_msg.ctrl_action == CMD_LAUNCH:
          s.start_iterate_ctrl <<= 1
        elif s.recv_pkt_queue.deq_msg.ctrl_action == CMD_TERMINATE:
          s.start_iterate_ctrl <<= 0
        elif s.recv_pkt_queue.deq_msg.ctrl_action == CMD_PAUSE:
          s.start_iterate_ctrl <<= 0
      # else:
      #   s.start_iterate_ctrl <<= 1

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
            s.reg_file.raddr[0] <<= CtrlAddrType(0)
          else:
            s.reg_file.raddr[0] <<= s.reg_file.raddr[0] + CtrlAddrType(1)

  def line_trace(s):
    config_mem_str  = "|".join([str(data) for data in s.reg_file.regs])
    return f'{s.recv_pkt.msg} || config_mem: [{config_mem_str}] || out: {s.send_ctrl.msg}'

