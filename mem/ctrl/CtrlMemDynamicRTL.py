"""
==========================================================================
CtrlMemDynamicRTL.py
==========================================================================
Control memory with dynamic reconfigurability (e.g., receiving control
signals, halt/terminate signals) for each CGRA tile.

Author : Cheng Tan
  Date : Dec 20, 2024
"""

from pymtl3.stdlib.primitive import RegisterFile

from ...lib.basic.en_rdy.ifcs import SendIfcRTL
from ...lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ...lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ...lib.basic.val_rdy.queues import NormalQueueRTL
from ...lib.cmd_type import *
from ...lib.opt_type import *
from ...lib.util.common import *

class CtrlMemDynamicRTL(Component):

  def construct(s, CtrlPktType, CtrlSignalType, ctrl_mem_size,
                num_fu_inports, num_fu_outports, num_tile_inports,
                num_tile_outports, num_tiles,
                ctrl_count_per_iter = 4, total_ctrl_steps = 4):

    # The total_ctrl_steps indicates the number of steps the ctrl
    # signals should proceed. For example, if the number of ctrl
    # signals is 4 and they need to repeat 5 times, then the total
    # number of steps should be 4 * 5 = 20.
    # assert( ctrl_mem_size <= total_ctrl_steps )

    # Constant
    CtrlAddrType = mk_bits(clog2(max(ctrl_mem_size, ctrl_count_per_iter)))
    PCType = mk_bits(clog2(ctrl_mem_size + 1))
    TimeType = mk_bits(clog2(MAX_CTRL_COUNT))
    PrologueCountType = mk_bits(clog2(PROLOGUE_MAX_COUNT + 1))
    TileInPortType = mk_bits(clog2(num_tile_inports))
    FuOutPortType = mk_bits(clog2(num_fu_outports))
    num_routing_outports = num_tile_outports + num_fu_inports

    # Interface
    # Stores ctrl signals into the control memory/registers.
    s.send_ctrl = SendIfcRTL(CtrlSignalType)
    # Receives the ctrl packets from the controller.
    s.recv_pkt_from_controller = RecvIfcRTL(CtrlPktType)
    # Sends the ctrl packets towards the controller.
    s.send_pkt_to_controller = SendIfcRTL(CtrlPktType)

    s.tile_id = InPort(mk_bits(clog2(num_tiles + 1)))

    # Component
    s.reg_file = RegisterFile(CtrlSignalType, ctrl_mem_size, 1, 1)
    s.recv_pkt_queue = NormalQueueRTL(CtrlPktType)
    s.times = Wire(TimeType)
    s.start_iterate_ctrl = Wire(b1)
    s.sent_complete = Wire(b1)
    s.ctrl_count_per_iter_val = Wire(PCType)
    s.total_ctrl_steps_val = Wire(TimeType)

    s.prologue_count_reg_fu = [Wire(PrologueCountType) for _ in range(ctrl_mem_size)]
    s.prologue_count_outport_fu = OutPort(PrologueCountType)
    s.prologue_count_outport_fu_crossbar = \
        [OutPort(PrologueCountType) for _ in range(num_fu_outports)]
    s.prologue_count_outport_routing_crossbar = \
        [OutPort(PrologueCountType) for _ in range(num_tile_inports)]

    s.prologue_count_reg_fu_crossbar = \
        [Wire(PrologueCountType) for _ in range(num_fu_outports)]
    s.prologue_count_reg_routing_crossbar = \
        [Wire(PrologueCountType) for _ in range(num_tile_inports)]


    # Connections
    s.send_ctrl.msg //= s.reg_file.rdata[0]
    # s.recv_pkt.rdy //= s.recv_pkt_queue.enq_rdy
    s.recv_pkt_from_controller //= s.recv_pkt_queue.recv

    @update
    def update_msg():

      s.recv_pkt_queue.send.rdy @= 0
      s.reg_file.wen[0] @= 0
      s.reg_file.waddr[0] @= s.recv_pkt_queue.send.msg.ctrl_addr
      # Initializes the fields of the control signal.
      # s.reg_file.wdata[0] @= CtrlSignalType()
      s.reg_file.wdata[0].ctrl @= 0
      s.reg_file.wdata[0].predicate @= 0
      for i in range(num_fu_inports):
        s.reg_file.wdata[0].fu_in[i] @= 0
        s.reg_file.wdata[0].write_reg_from[i] @= s.recv_pkt_queue.send.msg.ctrl_write_reg_from[i]
        s.reg_file.wdata[0].write_reg_idx[i] @= s.recv_pkt_queue.send.msg.ctrl_write_reg_idx[i]
        s.reg_file.wdata[0].read_reg_from[i] @= s.recv_pkt_queue.send.msg.ctrl_read_reg_from[i]
        s.reg_file.wdata[0].read_reg_idx[i] @= s.recv_pkt_queue.send.msg.ctrl_read_reg_idx[i]
      for i in range(num_routing_outports):
        s.reg_file.wdata[0].routing_xbar_outport[i] @= 0
        s.reg_file.wdata[0].fu_xbar_outport[i] @= 0
      for i in range(num_tile_inports):
        s.reg_file.wdata[0].routing_predicate_in[i] @= 0
      s.reg_file.wdata[0].vector_factor_power @= s.recv_pkt_queue.send.msg.ctrl_vector_factor_power
      s.reg_file.wdata[0].is_last_ctrl @= 0

      if s.recv_pkt_queue.send.val & (s.recv_pkt_queue.send.msg.ctrl_action == CMD_CONFIG):
        s.reg_file.wen[0] @= 1 # s.recv_pkt_queue.deq_en
        s.reg_file.waddr[0] @= s.recv_pkt_queue.send.msg.ctrl_addr
        # Fills the fields of the control signal.
        s.reg_file.wdata[0].ctrl @= s.recv_pkt_queue.send.msg.ctrl_operation
        s.reg_file.wdata[0].predicate @= s.recv_pkt_queue.send.msg.ctrl_predicate
        for i in range(num_fu_inports):
          s.reg_file.wdata[0].fu_in[i] @= s.recv_pkt_queue.send.msg.ctrl_fu_in[i]
          s.reg_file.wdata[0].write_reg_from[i] @= s.recv_pkt_queue.send.msg.ctrl_write_reg_from[i]
          s.reg_file.wdata[0].write_reg_idx[i] @= s.recv_pkt_queue.send.msg.ctrl_write_reg_idx[i]
          s.reg_file.wdata[0].read_reg_from[i] @= s.recv_pkt_queue.send.msg.ctrl_read_reg_from[i]
          s.reg_file.wdata[0].read_reg_idx[i] @= s.recv_pkt_queue.send.msg.ctrl_read_reg_idx[i]
        for i in range(num_routing_outports):
          s.reg_file.wdata[0].routing_xbar_outport[i] @= s.recv_pkt_queue.send.msg.ctrl_routing_xbar_outport[i]
          s.reg_file.wdata[0].fu_xbar_outport[i] @= s.recv_pkt_queue.send.msg.ctrl_fu_xbar_outport[i]
        for i in range(num_tile_inports):
          s.reg_file.wdata[0].routing_predicate_in[i] @= s.recv_pkt_queue.send.msg.ctrl_routing_predicate_in[i]
        s.reg_file.wdata[0].vector_factor_power @= s.recv_pkt_queue.send.msg.ctrl_vector_factor_power
        s.reg_file.wdata[0].is_last_ctrl @= s.recv_pkt_queue.send.msg.ctrl_is_last_ctrl

      if (s.recv_pkt_queue.send.msg.ctrl_action == CMD_CONFIG) | \
         (s.recv_pkt_queue.send.msg.ctrl_action == CMD_CONFIG_PROLOGUE_FU) | \
         (s.recv_pkt_queue.send.msg.ctrl_action == CMD_CONFIG_PROLOGUE_FU_CROSSBAR) | \
         (s.recv_pkt_queue.send.msg.ctrl_action == CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR) | \
         (s.recv_pkt_queue.send.msg.ctrl_action == CMD_LAUNCH) | \
         (s.recv_pkt_queue.send.msg.ctrl_action == CMD_TERMINATE) | \
         (s.recv_pkt_queue.send.msg.ctrl_action == CMD_PAUSE) | \
         (s.recv_pkt_queue.send.msg.ctrl_action == CMD_CONFIG_TOTAL_CTRL_COUNT) | \
         (s.recv_pkt_queue.send.msg.ctrl_action == CMD_CONFIG_COUNT_PER_ITER):
        s.recv_pkt_queue.send.rdy @= 1
      # TODO: Extend for the other commands. Maybe another queue to
      # handle complicated actions.
      # else:


    @update
    def update_send_out_signal():
      s.send_ctrl.val @= 0
      s.send_pkt_to_controller.val @= 0
      s.send_pkt_to_controller.msg @= CtrlPktType(0, 0, num_tiles, 0, 0, CMD_COMPLETE, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
      if s.start_iterate_ctrl == b1(1):
        if ((s.total_ctrl_steps_val > 0) & (s.times == s.total_ctrl_steps_val)) | \
           (s.reg_file.rdata[0].ctrl == OPT_START):
          s.send_ctrl.val @= b1(0)
          # Sends COMPLETE signal to Controller when the last ctrl signal is done.
          if (s.sent_complete != 1) & (s.total_ctrl_steps_val > 0) & (s.times == s.total_ctrl_steps_val):
            #                             cgra_id, src,       dst, opaque, vc, ctrl_action
            s.send_pkt_to_controller.msg @= CtrlPktType(0, 0, num_tiles, 0, 0, CMD_COMPLETE, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
            s.send_pkt_to_controller.val @= 1
        else:
          s.send_ctrl.val @= 1
      if s.recv_pkt_queue.send.val & \
         ((s.recv_pkt_queue.send.msg.ctrl_action == CMD_PAUSE) | \
          (s.recv_pkt_queue.send.msg.ctrl_action == CMD_TERMINATE)):
        s.send_ctrl.val @= b1(0)

    @update_ff
    def update_whether_we_can_iterate_ctrl():
      if s.reset:
        s.start_iterate_ctrl <<= 0
      else:
        if s.recv_pkt_queue.send.val:
          if s.recv_pkt_queue.send.msg.ctrl_action == CMD_LAUNCH:
            s.start_iterate_ctrl <<= 1
          elif s.recv_pkt_queue.send.msg.ctrl_action == CMD_TERMINATE:
            s.start_iterate_ctrl <<= 0
          elif s.recv_pkt_queue.send.msg.ctrl_action == CMD_PAUSE:
            s.start_iterate_ctrl <<= 0
        # else:
        #   s.start_iterate_ctrl <<= 1

    @update_ff
    def issue_complete():
      if s.reset:
        s.sent_complete <<= 0
      else:
        # Once COMPLETE signal is sent, we shouldn't send another COMPLETE signal until the next ctrl signal is launched.
        if s.send_pkt_to_controller.val & s.send_pkt_to_controller.rdy:
          s.sent_complete <<= 1
        if s.recv_pkt_queue.send.msg.ctrl_action == CMD_LAUNCH:
          s.sent_complete <<= 0

    @update_ff
    def update_raddr_and_fu_prologue():
      if s.reset:
        s.times <<= 0
        s.reg_file.raddr[0] <<= 0
        for i in range(ctrl_mem_size):
          s.prologue_count_reg_fu[i] <<= 0
      else:
        if s.recv_pkt_queue.send.val & \
           (s.recv_pkt_queue.send.msg.ctrl_action == CMD_CONFIG_PROLOGUE_FU):
          s.prologue_count_reg_fu[s.recv_pkt_queue.send.msg.ctrl_addr] <<= \
              trunc(s.recv_pkt_queue.send.msg.data, PrologueCountType)

        if s.start_iterate_ctrl == b1(1):
          if (TimeType(s.total_ctrl_steps_val) == 0) | \
             (s.times < TimeType(s.total_ctrl_steps_val)):
            s.times <<= s.times + TimeType(1)

          # Reads the next ctrl signal only when the current one is done.
          if s.send_ctrl.rdy:
            if s.reg_file.raddr[0] == trunc(s.ctrl_count_per_iter_val - 1, CtrlAddrType):
              s.reg_file.raddr[0] <<= 0
            else:
              s.reg_file.raddr[0] <<= s.reg_file.raddr[0] + CtrlAddrType(1)
            if s.prologue_count_reg_fu[s.reg_file.raddr[0]] > 0:
              s.prologue_count_reg_fu[s.reg_file.raddr[0]] <<= s.prologue_count_reg_fu[s.reg_file.raddr[0]] - 1

    @update
    def update_prologue_outport():
      s.prologue_count_outport_fu @= s.prologue_count_reg_fu[s.reg_file.raddr[0]]
      for i in range(num_tile_inports):
        s.prologue_count_outport_routing_crossbar[i] @= \
            s.prologue_count_reg_routing_crossbar[i]
      for i in range(num_fu_outports):
        s.prologue_count_outport_fu_crossbar[i] @= \
            s.prologue_count_reg_fu_crossbar[i]

    @update_ff
    def update_prologue_reg():
      if s.reset:
        for i in range(num_tile_inports):
          s.prologue_count_reg_routing_crossbar[i] <<= 0
        for i in range(num_fu_outports):
          s.prologue_count_reg_fu_crossbar[i] <<= 0
      else:
        if s.recv_pkt_queue.send.val & \
           (s.recv_pkt_queue.send.msg.ctrl_action == CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR):
          temp_routing_crossbar_in = s.recv_pkt_queue.send.msg.ctrl_routing_xbar_outport[0]
          s.prologue_count_reg_routing_crossbar[trunc(temp_routing_crossbar_in, TileInPortType)] <<= trunc(s.recv_pkt_queue.send.msg.data, PrologueCountType)
        elif s.recv_pkt_queue.send.val & \
           (s.recv_pkt_queue.send.msg.ctrl_action == CMD_CONFIG_PROLOGUE_FU_CROSSBAR):
          temp_fu_crossbar_in = s.recv_pkt_queue.send.msg.ctrl_fu_xbar_outport[0]
          s.prologue_count_reg_fu_crossbar[trunc(temp_fu_crossbar_in, FuOutPortType)] <<= trunc(s.recv_pkt_queue.send.msg.data, PrologueCountType)

    @update_ff
    def update_ctrl_count_per_iter():
      if s.reset:
        s.ctrl_count_per_iter_val <<= PCType(ctrl_count_per_iter)
      elif s.recv_pkt_queue.send.val & (s.recv_pkt_queue.send.msg.ctrl_action == CMD_CONFIG_COUNT_PER_ITER):
        s.ctrl_count_per_iter_val <<= trunc(s.recv_pkt_queue.send.msg.data, PCType)

    @update_ff
    def update_total_ctrl_steps():
      if s.reset:
        s.total_ctrl_steps_val <<= TimeType(total_ctrl_steps)
      elif s.recv_pkt_queue.send.val & (s.recv_pkt_queue.send.msg.ctrl_action == CMD_CONFIG_TOTAL_CTRL_COUNT):
        s.total_ctrl_steps_val <<= trunc(s.recv_pkt_queue.send.msg.data, TimeType)

  def line_trace(s):
    config_mem_str  = "|".join([str(data) for data in s.reg_file.regs])
    return f'recv_pkt: {s.recv_pkt_from_controller.msg}.recv_rdy:{s.recv_pkt_from_controller.rdy} || control signal content: [{config_mem_str}] || ctrl_out: {s.send_ctrl.msg}, send_ctrl.val: {s.send_ctrl.val}, send_ctrl.rdy: {s.send_ctrl.rdy}, send_pkt.msg.ctrl_action: {s.send_pkt_to_controller.msg.ctrl_action}, send_pkt.val: {s.send_pkt_to_controller.val}'

