"""
==========================================================================
CtrlMemDynamicRTL.py
==========================================================================
Control memory with dynamic reconfigurability (e.g., receiving control
signals, halt/terminate signals) for each CGRA tile.

Author : Cheng Tan
  Date : Dec 20, 2024
"""
from py_markdown_table.markdown_table import markdown_table
from pymtl3.stdlib.primitive import RegisterFile

from ...lib.basic.en_rdy.ifcs import SendIfcRTL
from ...lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL
from ...lib.basic.val_rdy.queues import NormalQueueRTL
from ...lib.cmd_type import *
from ...lib.opt_type import *
from ...lib.util.common import TILE_PORT_DIRECTION_DICT_SHORT_DESC


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
    s.recv_pkt = ValRdyRecvIfcRTL(CtrlPktType)

    # Component
    s.reg_file = RegisterFile(CtrlSignalType, ctrl_mem_size, 1, 1)
    # FIXME: valrdy normal queue RTL?
    s.recv_pkt_queue = NormalQueueRTL(CtrlPktType)
    s.times = Wire(TimeType)
    s.start_iterate_ctrl = Wire(b1)

    # Connections
    s.send_ctrl.msg //= s.reg_file.rdata[0]
    # s.recv_pkt.rdy //= s.recv_pkt_queue.enq_rdy
    s.recv_pkt //= s.recv_pkt_queue.recv

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
      for i in range(num_routing_outports):
        s.reg_file.wdata[0].routing_xbar_outport[i] @= 0
        s.reg_file.wdata[0].fu_xbar_outport[i] @= 0
      for i in range(num_tile_inports):
        s.reg_file.wdata[0].routing_predicate_in[i] @= 0

      if s.recv_pkt_queue.send.val & (s.recv_pkt_queue.send.msg.ctrl_action == CMD_CONFIG):
        s.reg_file.wen[0] @= 1 # s.recv_pkt_queue.deq_en
        s.reg_file.waddr[0] @= s.recv_pkt_queue.send.msg.ctrl_addr
        # Fills the fields of the control signal.
        s.reg_file.wdata[0].ctrl @= s.recv_pkt_queue.send.msg.ctrl_operation
        s.reg_file.wdata[0].predicate @= s.recv_pkt_queue.send.msg.ctrl_predicate
        for i in range(num_fu_inports):
          s.reg_file.wdata[0].fu_in[i] @= s.recv_pkt_queue.send.msg.ctrl_fu_in[i]
        for i in range(num_routing_outports):
          s.reg_file.wdata[0].routing_xbar_outport[i] @= s.recv_pkt_queue.send.msg.ctrl_routing_xbar_outport[i]
          s.reg_file.wdata[0].fu_xbar_outport[i] @= s.recv_pkt_queue.send.msg.ctrl_fu_xbar_outport[i]
        for i in range(num_tile_inports):
          s.reg_file.wdata[0].routing_predicate_in[i] @= s.recv_pkt_queue.send.msg.ctrl_routing_predicate_in[i]

      if (s.recv_pkt_queue.send.msg.ctrl_action == CMD_CONFIG) | \
         (s.recv_pkt_queue.send.msg.ctrl_action == CMD_LAUNCH) | \
         (s.recv_pkt_queue.send.msg.ctrl_action == CMD_TERMINATE) | \
         (s.recv_pkt_queue.send.msg.ctrl_action == CMD_PAUSE):
        s.recv_pkt_queue.send.rdy @= 1
      # TODO: Extend for the other commands. Maybe another queue to
      # handle complicated actions.
      # else:


    @update
    def update_send_out_signal():
      s.send_ctrl.en @= 0
      if s.start_iterate_ctrl == b1(1):
        if ((total_ctrl_steps > 0) & \
             (s.times == TimeType(total_ctrl_steps))) | \
           (s.reg_file.rdata[0].ctrl == OPT_START):
          s.send_ctrl.en @= b1(0)
        else:
          s.send_ctrl.en @= s.send_ctrl.rdy
      if s.recv_pkt_queue.send.val & \
         ((s.recv_pkt_queue.send.msg.ctrl_action == CMD_PAUSE) | \
          (s.recv_pkt_queue.send.msg.ctrl_action == CMD_TERMINATE)):
        s.send_ctrl.en @= b1(0)

    @update_ff
    def update_whether_we_can_iterate_ctrl():
      if s.recv_pkt_queue.send.val:
        # @yo96? data is still there, not released yet?
        if s.recv_pkt_queue.send.msg.ctrl_action == CMD_LAUNCH:
          s.start_iterate_ctrl <<= 1
        elif s.recv_pkt_queue.send.msg.ctrl_action == CMD_TERMINATE:
          s.start_iterate_ctrl <<= 0
        elif s.recv_pkt_queue.send.msg.ctrl_action == CMD_PAUSE:
          s.start_iterate_ctrl <<= 0
      # else:
      #   s.start_iterate_ctrl <<= 1

    @update_ff
    def update_raddr():
      if s.start_iterate_ctrl == b1(1):
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

  def line_trace(s, verbosity = 0):
    if verbosity == 0:
      config_mem_str  = "|".join([str(data) for data in s.reg_file.regs])
      return f'{s.recv_pkt.msg} || config_mem: [{config_mem_str}] || out: {s.send_ctrl.msg}'
    else:
      return s.verbose_trace(verbosity = verbosity)


  def verbose_trace_normal_processor(self, data_dict):
    if 'ctrl_operation' in data_dict:
      data_dict['ctrl_operation'] = OPT_SYMBOL_DICT[ data_dict['ctrl_operation'] ]
    if 'ctrl' in data_dict:
      data_dict['ctrl'] = OPT_SYMBOL_DICT[ data_dict['ctrl'] ]

  def verbose_trace_fu_in_processor(self, data_dict, sub_header, key_prefix = None):
    fu_in_key = 'fu_in'
    if key_prefix:
      fu_in_key = key_prefix + fu_in_key
    data_dict[fu_in_key] = [ int(fi) for fi in data_dict[fu_in_key] ]
    fu_in_header = []
    for idx, val in enumerate(data_dict[fu_in_key]):
      fu_in_header.append(idx)
    fu_in_header_str = "|".join([ f"{hd : ^3}" for hd in fu_in_header ])
    data_dict[fu_in_key] = "|".join([ f"{v : ^3}" for v in data_dict[fu_in_key] ])
    sub_header[fu_in_key] = fu_in_header_str

  # outport: fu_xbar_outport, routing_xbar_outport
  def verbose_trace_outport_processor(self, data_dict, sub_header, num_direction_ports, outport_key, key_prefix = None):
    if key_prefix:
      outport_key = key_prefix + outport_key
    if outport_key in data_dict:
      data_dict[outport_key] = [ int(op) for op in data_dict[outport_key] ]
      fu_reg_num = 1
      outport_sub_header = []
      for idx, val in enumerate(data_dict[outport_key]):
        # to directions
        if idx <= num_direction_ports - 1:
          hd = TILE_PORT_DIRECTION_DICT_SHORT_DESC[idx]
          outport_sub_header.append(f"{hd : ^{len(hd) + 2}}")
          data_dict[outport_key][idx] = f"{TILE_PORT_DIRECTION_DICT_SHORT_DESC[val - 1] if val != 0 else '-' : ^{len(hd) + 2}}"
        # to fu regs
        else:
          hd = f"fu_reg_{fu_reg_num}"
          outport_sub_header.append(f"{hd : ^{len(hd)}}")
          data_dict[outport_key][idx] = f"{TILE_PORT_DIRECTION_DICT_SHORT_DESC[val - 1] if val != 0 else '-' : ^{len(hd)}}"
          fu_reg_num += 1
      outport_sub_header_str = "|".join([ hd for hd in outport_sub_header ])
      data_dict[outport_key] = "|".join([ v for v in data_dict[outport_key] ])
      sub_header[outport_key] = outport_sub_header_str

  def verbose_trace_predicate_in_processor(self, data_dict, sub_header, num_direction_ports, key_prefix = None):
    predicate_in_key = 'routing_predicate_in'
    if key_prefix:
      predicate_in_key = key_prefix + predicate_in_key
    if predicate_in_key in data_dict:
      data_dict[predicate_in_key] = [ int(pi) for pi in data_dict[predicate_in_key] ]
      fu_out_num = 1
      predicate_in_sub_header = []
      for idx, val in enumerate(data_dict[predicate_in_key]):
        # from directions
        if idx <= num_direction_ports - 1:
          hd = TILE_PORT_DIRECTION_DICT_SHORT_DESC[idx]
          predicate_in_sub_header.append(f"{hd : ^{len(hd) + 2}}")
          data_dict[predicate_in_key][idx] = f"{val : ^{len(hd) + 2}}"
        # from fu
        else:
          hd = f"fu_out_{fu_out_num}"
          predicate_in_sub_header.append(f"{hd : ^{len(hd)}}")
          data_dict[predicate_in_key][idx] = f"{val : ^{len(hd)}}"
          fu_out_num += 1
      predicate_in_sub_header_str = "|".join([ hd for hd in predicate_in_sub_header ])
      data_dict[predicate_in_key] = "|".join([ v for v in data_dict[predicate_in_key] ])
      sub_header[predicate_in_key] = predicate_in_sub_header_str

  def verbose_trace_data_processor(self, data_dict, num_direction_ports, key_prefix = None):
    sub_header = {}
    for key in data_dict.keys():
      sub_header[key] = ''
    self.verbose_trace_normal_processor(data_dict)
    self.verbose_trace_fu_in_processor(data_dict, sub_header, key_prefix)
    self.verbose_trace_outport_processor(data_dict, sub_header, num_direction_ports, 'fu_xbar_outport', key_prefix)
    self.verbose_trace_outport_processor(data_dict, sub_header, num_direction_ports, 'routing_xbar_outport', key_prefix)
    self.verbose_trace_predicate_in_processor(data_dict, sub_header, num_direction_ports, key_prefix)
    return sub_header

  # verbose trace
  def verbose_trace(s, verbosity = 1):
    num_routing_outports = len(s.reg_file.wdata[0].routing_xbar_outport)
    num_fu_inports = len(s.reg_file.wdata[0].fu_in)
    num_tile_outports = num_routing_outports - num_fu_inports

    # recv_ctrl
    recv_pkt_msg_dict = dict(s.recv_pkt.msg.__dict__)
    recv_pkt_msg_header = s.verbose_trace_data_processor(recv_pkt_msg_dict, num_tile_outports, key_prefix = 'ctrl_')
    recv_pkt_msg_list = [recv_pkt_msg_header, recv_pkt_msg_dict]
    recv_pkt_msg_md = markdown_table(recv_pkt_msg_list).set_params(quote = False).get_markdown()

    # send_ctrl
    send_ctrl_msg_dict = dict(s.send_ctrl.msg.__dict__)
    send_ctrl_sub_header = s.verbose_trace_data_processor(send_ctrl_msg_dict, num_tile_outports)
    send_ctrl_msg_list = [send_ctrl_sub_header, send_ctrl_msg_dict]
    send_ctrl_msg_md = markdown_table(send_ctrl_msg_list).set_params(quote = False).get_markdown()

    if verbosity == 1:
      return (f'\n## class: {s.__class__.__name__}\n'
              f'- recv_pkt_msg:'
              f'{recv_pkt_msg_md}\n\n'
              f'- send_ctrl_msg:'
              f'{send_ctrl_msg_md}\n\n')
    else:
      # reg
      reg_dicts = [ dict(data.__dict__) for data in s.reg_file.regs ]
      reg_sub_header = {}
      for reg_dict in reg_dicts:
        reg_sub_header = s.verbose_trace_data_processor(reg_dict, num_tile_outports)
      reg_dicts.insert(0, reg_sub_header)
      reg_md = markdown_table(reg_dicts).set_params(quote=False).get_markdown()
      return (f'\n## class: {s.__class__.__name__}\n'
              f'- recv_pkt_msg:'
              f'{recv_pkt_msg_md}\n\n'
              f'- send_ctrl_msg:'
              f'{send_ctrl_msg_md}\n\n'
              f'- config_memory: {reg_md}\n')