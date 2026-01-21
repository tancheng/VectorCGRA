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
from ...lib.util.data_struct_attr import *

class CtrlMemDynamicRTL(Component):

  def construct(s, IntraCgraPktType,
                ctrl_mem_size, num_fu_inports, num_fu_outports,
                num_tile_inports, num_tile_outports, num_cgras,
                num_tiles, ctrl_count_per_iter = 4,
                total_ctrl_steps = 4):

    CgraPayloadType = IntraCgraPktType.get_field_type(kAttrPayload)
    CtrlType = CgraPayloadType.get_field_type(kAttrCtrl)
    # The total_ctrl_steps indicates the number of steps the ctrl
    # signals should proceed. For example, if the number of ctrl
    # signals is 4 and they need to repeat 5 times, then the total
    # number of steps should be 4 * 5 = 20.
    # assert( ctrl_mem_size <= total_ctrl_steps )

    # Constants.
    CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
    PCType = mk_bits(clog2(ctrl_count_per_iter + 1))
    UpperBoundType = mk_bits(clog2(ctrl_mem_size + 1))
    TimeType = mk_bits(clog2(MAX_CTRL_COUNT + 1))
    PrologueCountType = mk_bits(clog2(PROLOGUE_MAX_COUNT + 1))
    TileInPortType = mk_bits(clog2(num_tile_inports))
    FuOutPortType = mk_bits(clog2(num_fu_outports))
    num_routing_outports = num_tile_outports + num_fu_inports

    # Interfaces.
    # Stores ctrl signals into the control memory/registers.
    s.send_ctrl = SendIfcRTL(CtrlType)
    # Receives the ctrl packets from the controller.
    s.recv_pkt_from_controller = RecvIfcRTL(IntraCgraPktType)
    # Sends the ctrl packets towards the controller.
    s.send_pkt_to_controller = SendIfcRTL(IntraCgraPktType)
    # Receives data/cmd from the functional unit, used for returning data to the controller/CPU.
    s.recv_from_element = RecvIfcRTL(CgraPayloadType)
    # Sends data/cmd to the functional unit, which is usually initialized by the controller/CPU.
    s.send_to_element = SendIfcRTL(CgraPayloadType)

    s.cgra_id = InPort(mk_bits(max(1, clog2(num_cgras))))
    s.tile_id = InPort(mk_bits(clog2(num_tiles + 1)))
    s.ctrl_addr_outport = OutPort(CtrlAddrType)

    # Components.
    s.reg_file = RegisterFile(CtrlType, ctrl_mem_size, 1, 1)
    s.recv_pkt_from_controller_queue = NormalQueueRTL(IntraCgraPktType)
    s.recv_from_element_queue = NormalQueueRTL(CgraPayloadType)
    s.times = Wire(TimeType)
    s.start_iterate_ctrl = Wire(b1)
    s.sent_complete = Wire(b1)
    s.ctrl_count_per_iter_val = Wire(PCType)
    s.ctrl_count_lower_bound = Wire(CtrlAddrType)
    s.ctrl_count_upper_bound = Wire(UpperBoundType)
    s.total_ctrl_steps_val = Wire(TimeType)

    s.prologue_count_reg_fu = [Wire(PrologueCountType) for _ in range(ctrl_mem_size)]
    s.prologue_count_outport_fu = OutPort(PrologueCountType)
    s.prologue_count_outport_fu_crossbar = \
        [[OutPort(PrologueCountType) for _ in range(num_fu_outports)] for _ in range(ctrl_mem_size)]
    s.prologue_count_outport_routing_crossbar = \
        [[OutPort(PrologueCountType) for _ in range(num_tile_inports)] for _ in range(ctrl_mem_size)]

    s.prologue_count_reg_fu_crossbar = \
        [[Wire(PrologueCountType) for _ in range(num_fu_outports)] for _ in range(ctrl_mem_size)]
    s.prologue_count_reg_routing_crossbar = \
        [[Wire(PrologueCountType) for _ in range(num_tile_inports)] for _ in range(ctrl_mem_size)]

    # Connections.
    s.send_ctrl.msg //= s.reg_file.rdata[0]
    s.recv_pkt_from_controller //= s.recv_pkt_from_controller_queue.recv
    s.recv_from_element //= s.recv_from_element_queue.recv

    @update
    def update_msg():
      s.recv_pkt_from_controller_queue.send.rdy @= 0
      s.send_to_element.msg @= CgraPayloadType(0, 0, 0, 0, 0)
      s.send_to_element.val @= 0
      s.reg_file.wen[0] @= 0
      s.reg_file.waddr[0] @= s.recv_pkt_from_controller_queue.send.msg.payload.ctrl_addr
      # Initializes the fields of the control signal.
      s.reg_file.wdata[0].operation @= 0
      for i in range(num_fu_inports):
        s.reg_file.wdata[0].fu_in[i] @= 0
        s.reg_file.wdata[0].write_reg_from[i] @= s.recv_pkt_from_controller_queue.send.msg.payload.ctrl.write_reg_from[i]
        s.reg_file.wdata[0].write_reg_idx[i] @= s.recv_pkt_from_controller_queue.send.msg.payload.ctrl.write_reg_idx[i]
        s.reg_file.wdata[0].read_reg_from[i] @= s.recv_pkt_from_controller_queue.send.msg.payload.ctrl.read_reg_from[i]
        s.reg_file.wdata[0].read_reg_idx[i] @= s.recv_pkt_from_controller_queue.send.msg.payload.ctrl.read_reg_idx[i]
      for i in range(num_routing_outports):
        s.reg_file.wdata[0].routing_xbar_outport[i] @= 0
        s.reg_file.wdata[0].fu_xbar_outport[i] @= 0
      s.reg_file.wdata[0].vector_factor_power @= s.recv_pkt_from_controller_queue.send.msg.payload.ctrl.vector_factor_power
      s.reg_file.wdata[0].is_last_ctrl @= 0

      if s.recv_pkt_from_controller_queue.send.val & (s.recv_pkt_from_controller_queue.send.msg.payload.cmd == CMD_CONFIG):
        s.reg_file.wen[0] @= 1
        s.reg_file.waddr[0] @= s.recv_pkt_from_controller_queue.send.msg.payload.ctrl_addr
        # Fills the fields of the control signal.
        s.reg_file.wdata[0].operation @= s.recv_pkt_from_controller_queue.send.msg.payload.ctrl.operation
        for i in range(num_fu_inports):
          s.reg_file.wdata[0].fu_in[i] @= s.recv_pkt_from_controller_queue.send.msg.payload.ctrl.fu_in[i]
          s.reg_file.wdata[0].write_reg_from[i] @= s.recv_pkt_from_controller_queue.send.msg.payload.ctrl.write_reg_from[i]
          s.reg_file.wdata[0].write_reg_idx[i] @= s.recv_pkt_from_controller_queue.send.msg.payload.ctrl.write_reg_idx[i]
          s.reg_file.wdata[0].read_reg_from[i] @= s.recv_pkt_from_controller_queue.send.msg.payload.ctrl.read_reg_from[i]
          s.reg_file.wdata[0].read_reg_idx[i] @= s.recv_pkt_from_controller_queue.send.msg.payload.ctrl.read_reg_idx[i]
        for i in range(num_routing_outports):
          s.reg_file.wdata[0].routing_xbar_outport[i] @= s.recv_pkt_from_controller_queue.send.msg.payload.ctrl.routing_xbar_outport[i]
          s.reg_file.wdata[0].fu_xbar_outport[i] @= s.recv_pkt_from_controller_queue.send.msg.payload.ctrl.fu_xbar_outport[i]
        s.reg_file.wdata[0].vector_factor_power @= s.recv_pkt_from_controller_queue.send.msg.payload.ctrl.vector_factor_power
        s.reg_file.wdata[0].is_last_ctrl @= s.recv_pkt_from_controller_queue.send.msg.payload.ctrl.is_last_ctrl
      elif s.recv_pkt_from_controller_queue.send.val & \
           ((s.recv_pkt_from_controller_queue.send.msg.payload.cmd == CMD_GLOBAL_REDUCE_ADD_RESPONSE) | \
            (s.recv_pkt_from_controller_queue.send.msg.payload.cmd == CMD_GLOBAL_REDUCE_MUL_RESPONSE)):
        s.send_to_element.msg @= s.recv_pkt_from_controller_queue.send.msg.payload
        s.send_to_element.val @= 1

      if (s.recv_pkt_from_controller_queue.send.msg.payload.cmd == CMD_CONFIG) | \
         (s.recv_pkt_from_controller_queue.send.msg.payload.cmd == CMD_CONFIG_PROLOGUE_FU) | \
         (s.recv_pkt_from_controller_queue.send.msg.payload.cmd == CMD_CONFIG_PROLOGUE_FU_CROSSBAR) | \
         (s.recv_pkt_from_controller_queue.send.msg.payload.cmd == CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR) | \
         (s.recv_pkt_from_controller_queue.send.msg.payload.cmd == CMD_LAUNCH) | \
         (s.recv_pkt_from_controller_queue.send.msg.payload.cmd == CMD_TERMINATE) | \
         (s.recv_pkt_from_controller_queue.send.msg.payload.cmd == CMD_PAUSE) | \
         (s.recv_pkt_from_controller_queue.send.msg.payload.cmd == CMD_PRESERVE) | \
         (s.recv_pkt_from_controller_queue.send.msg.payload.cmd == CMD_RESUME) | \
         (s.recv_pkt_from_controller_queue.send.msg.payload.cmd == CMD_CONFIG_TOTAL_CTRL_COUNT) | \
         (s.recv_pkt_from_controller_queue.send.msg.payload.cmd == CMD_CONFIG_COUNT_PER_ITER) | \
         (s.recv_pkt_from_controller_queue.send.msg.payload.cmd == CMD_CONFIG_CTRL_LOWER_BOUND) | \
         (s.recv_pkt_from_controller_queue.send.msg.payload.cmd == CMD_RECORD_PHI_ADDR) | \
         (s.recv_pkt_from_controller_queue.send.msg.payload.cmd == CMD_GLOBAL_REDUCE_ADD_RESPONSE) | \
         (s.recv_pkt_from_controller_queue.send.msg.payload.cmd == CMD_CONFIG_STREAMING_LD_START_ADDR) | \
         (s.recv_pkt_from_controller_queue.send.msg.payload.cmd == CMD_CONFIG_STREAMING_LD_STRIDE) | \
         (s.recv_pkt_from_controller_queue.send.msg.payload.cmd == CMD_CONFIG_STREAMING_LD_END_ADDR) | \
         (s.recv_pkt_from_controller_queue.send.msg.payload.cmd == CMD_GLOBAL_REDUCE_MUL_RESPONSE):
        s.recv_pkt_from_controller_queue.send.rdy @= 1
      # TODO: Extend for the other commands. Maybe another queue to
      # handle complicated actions.
      # else:

    @update
    def update_ctrl_addr_outport():
      s.ctrl_addr_outport @= s.reg_file.raddr[0]

    @update
    def update_send_pkt_to_controller():
      s.send_pkt_to_controller.val @= 0
      s.send_pkt_to_controller.msg @= IntraCgraPktType(0, num_tiles, 0, 0, 0, 0, 0, 0, 0, 0, CgraPayloadType(CMD_COMPLETE, 0, 0, 0, 0))
      s.recv_from_element_queue.send.rdy @= 0
      if s.start_iterate_ctrl == b1(1):
        if s.recv_from_element_queue.send.val & (~s.sent_complete):
          s.send_pkt_to_controller.msg @= \
              IntraCgraPktType(s.tile_id, num_tiles, 0, 0, 0, 0, 0, 0, 0, 0,
                               s.recv_from_element_queue.send.msg)
          s.send_pkt_to_controller.val @= 1
          s.recv_from_element_queue.send.rdy @= s.send_pkt_to_controller.rdy
        elif ((s.total_ctrl_steps_val > 0) & (s.times == s.total_ctrl_steps_val)) | \
           (s.reg_file.rdata[0].operation == OPT_START):
          # Sends COMPLETE signal to Controller when the last ctrl signal is done.
          if ~s.sent_complete & (s.total_ctrl_steps_val > 0) & (s.times == s.total_ctrl_steps_val) & s.start_iterate_ctrl:
            s.send_pkt_to_controller.msg @= \
                IntraCgraPktType(s.tile_id, num_tiles, 0, 0, 0, 0, 0, 0, 0, 0, CgraPayloadType(CMD_COMPLETE, 0, 0, 0, 0))
            s.send_pkt_to_controller.val @= 1

    @update
    def update_send_ctrl():
      s.send_ctrl.val @= 0
      if s.start_iterate_ctrl == b1(1):
        if s.sent_complete:
          s.send_ctrl.val @= 0
        elif ((s.total_ctrl_steps_val > 0) & (s.times == s.total_ctrl_steps_val)) | \
           (s.reg_file.rdata[0].operation == OPT_START):
          s.send_ctrl.val @= b1(0)
        else:
          s.send_ctrl.val @= 1
      if s.recv_pkt_from_controller_queue.send.val & \
          (s.recv_pkt_from_controller_queue.send.msg.payload.cmd == CMD_TERMINATE):
        s.send_ctrl.val @= b1(0)

    @update_ff
    def update_whether_we_can_iterate_ctrl():
      if s.reset:
        s.start_iterate_ctrl <<= 0
      else:
        if s.recv_pkt_from_controller_queue.send.val:
          if (s.recv_pkt_from_controller_queue.send.msg.payload.cmd == CMD_LAUNCH) | \
                  (s.recv_pkt_from_controller_queue.send.msg.payload.cmd == CMD_RESUME):
            s.start_iterate_ctrl <<= 1
    # TODO: issue #191, stop iterate ctrl after 10 cycels during pausing status, 
    # so as to clear channels safely.
          elif s.recv_pkt_from_controller_queue.send.msg.payload.cmd == CMD_TERMINATE:
            s.start_iterate_ctrl <<= 0

    @update_ff
    def issue_complete():
      if s.reset:
        s.sent_complete <<= 0
      else:
        if s.send_pkt_to_controller.val & \
           s.send_pkt_to_controller.rdy & \
           (s.send_pkt_to_controller.msg.payload.cmd == CMD_COMPLETE):
          s.sent_complete <<= 1
        elif s.recv_pkt_from_controller_queue.send.val & ( (s.recv_pkt_from_controller_queue.send.msg.payload.cmd == CMD_LAUNCH) | \
                (s.recv_pkt_from_controller_queue.send.msg.payload.cmd == CMD_RESUME) ):
          s.sent_complete <<= 0

    @update_ff
    def update_raddr_and_fu_prologue():
      if s.reset:
        s.times <<= 0
        s.reg_file.raddr[0] <<= 0
        for i in range(ctrl_mem_size):
          s.prologue_count_reg_fu[i] <<= 0
      elif s.recv_pkt_from_controller_queue.send.val & (s.recv_pkt_from_controller_queue.send.msg.payload.cmd == CMD_CONFIG_CTRL_LOWER_BOUND):
        s.reg_file.raddr[0] <<= trunc(s.recv_pkt_from_controller_queue.send.msg.payload.data.payload, CtrlAddrType)
      elif s.recv_pkt_from_controller_queue.send.val & (s.recv_pkt_from_controller_queue.send.msg.payload.cmd == CMD_TERMINATE):
        s.times <<= TimeType(0)
      else:
        if s.recv_pkt_from_controller_queue.send.val & \
           (s.recv_pkt_from_controller_queue.send.msg.payload.cmd == CMD_CONFIG_PROLOGUE_FU):
          s.prologue_count_reg_fu[s.recv_pkt_from_controller_queue.send.msg.payload.ctrl_addr] <<= \
              trunc(s.recv_pkt_from_controller_queue.send.msg.payload.data.payload, PrologueCountType)

        if s.start_iterate_ctrl == b1(1):
          if ((s.total_ctrl_steps_val == 0) | \
              (s.times < s.total_ctrl_steps_val)) & \
             s.send_ctrl.rdy & s.send_ctrl.val:
            s.times <<= s.times + TimeType(1)

          # Reads the next ctrl signal only when the current one is done.
          if s.send_ctrl.rdy & s.send_ctrl.val:
            if zext(s.reg_file.raddr[0], UpperBoundType) == s.ctrl_count_upper_bound - UpperBoundType(1):
              s.reg_file.raddr[0] <<= s.ctrl_count_lower_bound
            else:
              s.reg_file.raddr[0] <<= s.reg_file.raddr[0] + CtrlAddrType(1)
            if s.prologue_count_reg_fu[s.reg_file.raddr[0]] > 0:
              s.prologue_count_reg_fu[s.reg_file.raddr[0]] <<= s.prologue_count_reg_fu[s.reg_file.raddr[0]] - 1

    @update
    def update_prologue_outport():
      s.prologue_count_outport_fu @= s.prologue_count_reg_fu[s.reg_file.raddr[0]]
      for addr in range(ctrl_mem_size):
        for i in range(num_tile_inports):
          s.prologue_count_outport_routing_crossbar[addr][i] @= \
              s.prologue_count_reg_routing_crossbar[addr][i]
        for i in range(num_fu_outports):
          s.prologue_count_outport_fu_crossbar[addr][i] @= \
              s.prologue_count_reg_fu_crossbar[addr][i]

    @update_ff
    def update_prologue_reg():
      if s.reset:
        for addr in range(ctrl_mem_size):
          for i in range(num_tile_inports):
            s.prologue_count_reg_routing_crossbar[addr][i] <<= 0
          for i in range(num_fu_outports):
            s.prologue_count_reg_fu_crossbar[addr][i] <<= 0
      else:
        if s.recv_pkt_from_controller_queue.send.val & \
           (s.recv_pkt_from_controller_queue.send.msg.payload.cmd == CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR):
          temp_routing_crossbar_in = s.recv_pkt_from_controller_queue.send.msg.payload.ctrl.routing_xbar_outport[0]
          # Subtract 1 to convert from TileInType(1-8) to array index (0-7), consistent with normal crossbar routing
          if temp_routing_crossbar_in > 0:
            s.prologue_count_reg_routing_crossbar[s.recv_pkt_from_controller_queue.send.msg.payload.ctrl_addr][trunc(temp_routing_crossbar_in - 1, TileInPortType)] <<= trunc(s.recv_pkt_from_controller_queue.send.msg.payload.data.payload, PrologueCountType)
        elif s.recv_pkt_from_controller_queue.send.val & \
           (s.recv_pkt_from_controller_queue.send.msg.payload.cmd == CMD_CONFIG_PROLOGUE_FU_CROSSBAR):
          temp_fu_crossbar_in = s.recv_pkt_from_controller_queue.send.msg.payload.ctrl.fu_xbar_outport[0]
          s.prologue_count_reg_fu_crossbar[s.recv_pkt_from_controller_queue.send.msg.payload.ctrl_addr][trunc(temp_fu_crossbar_in, FuOutPortType)] <<= trunc(s.recv_pkt_from_controller_queue.send.msg.payload.data.payload, PrologueCountType)

    @update_ff
    def update_ctrl_count_per_iter():
      if s.reset:
        s.ctrl_count_per_iter_val <<= PCType(ctrl_count_per_iter)
      elif s.recv_pkt_from_controller_queue.send.val & (s.recv_pkt_from_controller_queue.send.msg.payload.cmd == CMD_CONFIG_COUNT_PER_ITER):
        s.ctrl_count_per_iter_val <<= trunc(s.recv_pkt_from_controller_queue.send.msg.payload.data.payload, PCType)

    @update_ff
    def update_lower_bound():
      if s.reset:
        s.ctrl_count_lower_bound <<= CtrlAddrType(0)
      elif s.recv_pkt_from_controller_queue.send.val & (s.recv_pkt_from_controller_queue.send.msg.payload.cmd == CMD_CONFIG_CTRL_LOWER_BOUND):
        s.ctrl_count_lower_bound <<= trunc(s.recv_pkt_from_controller_queue.send.msg.payload.data.payload, CtrlAddrType)

    @update
    def update_upper_bound():
      s.ctrl_count_upper_bound @= zext(s.ctrl_count_lower_bound, UpperBoundType) + zext(s.ctrl_count_per_iter_val, UpperBoundType)

    @update_ff
    def update_total_ctrl_steps():
      if s.reset:
        s.total_ctrl_steps_val <<= TimeType(total_ctrl_steps)
      elif s.recv_pkt_from_controller_queue.send.val & (s.recv_pkt_from_controller_queue.send.msg.payload.cmd == CMD_CONFIG_TOTAL_CTRL_COUNT):
        s.total_ctrl_steps_val <<= trunc(s.recv_pkt_from_controller_queue.send.msg.payload.data.payload, TimeType)

  def line_trace(s):
    config_mem_str  = "|".join([str(data) for data in s.reg_file.regs])
    return f'reg_file.raddr[0]: {s.reg_file.raddr[0]} || sent_complete: {s.sent_complete} || times: {s.times} || total_ctrl_steps_val: {s.total_ctrl_steps_val} || start_iterate_ctrl: {s.start_iterate_ctrl}|| recv_pkt: {s.recv_pkt_from_controller.msg}.recv_rdy:{s.recv_pkt_from_controller.rdy} || control signal content: [{config_mem_str}] || ctrl_out: {s.send_ctrl.msg}, send_ctrl.val: {s.send_ctrl.val}, send_ctrl.rdy: {s.send_ctrl.rdy}, send_pkt.msg.payload.cmd: {s.send_pkt_to_controller.msg.payload.cmd}, send_pkt.val: {s.send_pkt_to_controller.val}, ctrl_count_per_iter_val: {s.ctrl_count_per_iter_val}, ctrl_count_lower_bound: {s.ctrl_count_lower_bound}'

