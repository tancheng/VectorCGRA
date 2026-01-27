"""
=========================================================================
TileWithContextSwitchRTL.py
=========================================================================
Integrates tile with the context switch module and clearable channels

Author : Yufei Yang
  Date : Sep 24, 2025
"""

from ..fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from ..fu.single.AdderRTL import AdderRTL
from ..fu.single.GrantRTL import GrantRTL
from ..fu.single.CompRTL import CompRTL
from ..fu.single.MemUnitRTL import MemUnitRTL
from ..fu.single.MulRTL import MulRTL
from ..fu.single.PhiRTL import PhiRTL
from ..fu.single.RetRTL import RetRTL
from ..lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ..lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ..lib.cmd_type import *
from ..lib.util.common import *
from ..mem.const.ConstQueueDynamicRTL import ConstQueueDynamicRTL
from ..mem.ctrl.CtrlMemDynamicRTL import CtrlMemDynamicRTL
from ..mem.ctrl.ContextSwitchRTL import ContextSwitchRTL
from ..mem.register_cluster.RegisterClusterRTL import RegisterClusterRTL
from ..noc.CrossbarRTL import CrossbarRTL
from ..noc.LinkOrRTL import LinkOrRTL
from ..noc.ChannelWithClearRTL import ChannelWithClearRTL
from ..rf.RegisterRTL import RegisterRTL
from ..lib.util.data_struct_attr import *


class TileWithContextSwitchRTL(Component):

  def construct(s, IntraCgraPktType,
                ctrl_mem_size, data_mem_size, num_ctrl,
                total_steps, num_fu_inports, num_fu_outports, num_tile_inports,
                num_tile_outports, num_cgras, num_tiles,
                num_registers_per_reg_bank = 16,
                Fu = FlexibleFuRTL,
                FuList = [PhiRTL, AdderRTL, CompRTL, MulRTL, GrantRTL, MemUnitRTL]):

    # Derives types from CgraPayloadType.
    CgraPayloadType = IntraCgraPktType.get_field_type(kAttrPayload)
    CtrlPktType = IntraCgraPktType
    DataType = CgraPayloadType.get_field_type(kAttrData)
    PredicateType = DataType.get_field_type(kAttrPredicate)
    CtrlSignalType = CgraPayloadType.get_field_type(kAttrCtrl)
    data_bitwidth = DataType.get_field_type(kAttrPayload).nbits

    # Constants.
    num_routing_xbar_inports = num_tile_inports
    num_routing_xbar_outports = num_fu_inports + num_tile_outports

    num_fu_xbar_inports = num_fu_outports
    num_fu_xbar_outports = num_fu_inports + num_tile_outports

    CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
    DataAddrType = mk_bits(clog2(data_mem_size))

    # Interfaces.
    s.recv_data = [RecvIfcRTL(DataType)
                   for _ in range (num_tile_inports)]
    s.send_data = [SendIfcRTL(DataType)
                   for _ in range (num_tile_outports)]

    # Ctrl.
    s.recv_from_controller_pkt = RecvIfcRTL(CtrlPktType)
    # Sends the ctrl packets to ctrl ring.
    s.send_to_controller_pkt = SendIfcRTL(CtrlPktType)

    # Data.
    s.to_mem_raddr = SendIfcRTL(DataAddrType)
    s.from_mem_rdata = RecvIfcRTL(DataType)
    s.to_mem_waddr = SendIfcRTL(DataAddrType)
    s.to_mem_wdata = SendIfcRTL(DataType)

    # Components.
    s.element = FlexibleFuRTL(CtrlPktType, DataType, CtrlSignalType,
                              num_fu_inports, num_fu_outports,
                              data_mem_size, ctrl_mem_size,
                              num_tiles, FuList)
    # We use many CMD_CONST to simulate runtime commands in TileWithContextSwitchRTL_test,
    # so here we increase the size of const_mem to avoid deadlock.
    s.const_mem = ConstQueueDynamicRTL(DataType, ctrl_mem_size+10)
    s.routing_crossbar = CrossbarRTL(DataType,
                                     CtrlSignalType,
                                     num_routing_xbar_inports,
                                     num_routing_xbar_outports,
                                     num_cgras,
                                     num_tiles,
                                     ctrl_mem_size,
                                     num_tile_outports)
    s.fu_crossbar = CrossbarRTL(DataType,
                                CtrlSignalType,
                                num_fu_xbar_inports,
                                num_fu_xbar_outports,
                                num_cgras,
                                num_tiles,
                                ctrl_mem_size,
                                num_tile_outports)
    s.register_cluster = \
        RegisterClusterRTL(DataType, CtrlSignalType, num_fu_inports,
                           num_registers_per_reg_bank)
    s.ctrl_mem = CtrlMemDynamicRTL(CtrlPktType,
                                   ctrl_mem_size,
                                   num_fu_inports,
                                   num_fu_outports,
                                   num_tile_inports,
                                   num_tile_outports,
                                   num_cgras,
                                   num_tiles,
                                   num_ctrl,
                                   total_steps)
    s.context_switch = ContextSwitchRTL(data_bitwidth, clog2(ctrl_mem_size))

    # The `tile_in_channel` indicates the outport channels that are
    # connected to the next tiles.
    s.tile_in_channel = [ChannelWithClearRTL(DataType, latency = 1)
                         for _ in range(num_tile_inports)]

    # The `tile_out_or_link` would "or" the outports of the
    # `tile_out_channel` and the FUs.
    s.tile_out_or_link = [LinkOrRTL(DataType)
                          for _ in range(num_tile_outports)]

    # Signals indicating whether certain modules already done their jobs.
    s.element_done = Wire(1)
    s.fu_crossbar_done = Wire(1)
    s.routing_crossbar_done = Wire(1)

    # Used for:
    # Clearing the 'first' signal in PhiRTL to correctly resume the progress.
    # Clearing the 'prologue_counter' signal in CrossbarRTL to correctly resume the progress.
    s.clear = Wire(1)

    s.cgra_id = InPort(mk_bits(max(1, clog2(num_cgras))))
    s.tile_id = InPort(mk_bits(clog2(num_tiles + 1)))

    # Propagates tile id.
    s.element.tile_id //= s.tile_id
    s.ctrl_mem.cgra_id //= s.cgra_id
    s.ctrl_mem.tile_id //= s.tile_id
    s.fu_crossbar.cgra_id //= s.cgra_id
    s.fu_crossbar.tile_id //= s.tile_id
    s.routing_crossbar.cgra_id //= s.cgra_id
    s.routing_crossbar.tile_id //= s.tile_id

    # Assigns crossbar id.
    s.routing_crossbar.crossbar_id //= PORT_ROUTING_CROSSBAR
    s.fu_crossbar.crossbar_id //= PORT_FU_CROSSBAR

    # Constant queue.
    s.element.recv_const //= s.const_mem.send_const

    # Fu data <-> ctrl memory (eventually towards/from CPU via controller).
    s.element.send_to_ctrl_mem //= s.ctrl_mem.recv_from_element
    s.element.recv_from_ctrl_mem //= s.ctrl_mem.send_to_element

    # Ctrl address port.
    s.routing_crossbar.ctrl_addr_inport //= s.ctrl_mem.ctrl_addr_outport
    s.fu_crossbar.ctrl_addr_inport //= s.ctrl_mem.ctrl_addr_outport

    # Connects context switch module
    s.context_switch.recv_cmd //= s.recv_from_controller_pkt.msg.payload.cmd
    s.context_switch.recv_cmd_vld //= s.recv_from_controller_pkt.val
    s.context_switch.recv_opt //= s.ctrl_mem.send_ctrl.msg.operation
    s.context_switch.progress_in //= s.element.send_out[0].msg
    s.context_switch.progress_in_val //= s.element.send_out[0].val
    s.context_switch.phi_addr //= s.recv_from_controller_pkt.msg.payload.ctrl_addr
    s.context_switch.ctrl_mem_rd_addr //= s.ctrl_mem.ctrl_addr_outport

    # Prologue port.
    s.element.prologue_count_inport //= s.ctrl_mem.prologue_count_outport_fu
    for addr in range(ctrl_mem_size):
      for i in range(num_routing_xbar_inports):
        s.routing_crossbar.prologue_count_inport[addr][i] //= \
            s.ctrl_mem.prologue_count_outport_routing_crossbar[addr][i]
      for i in range(num_fu_xbar_inports):
        s.fu_crossbar.prologue_count_inport[addr][i] //= \
            s.ctrl_mem.prologue_count_outport_fu_crossbar[addr][i]

    for i in range(len(FuList)):
      if FuList[i] == MemUnitRTL:
        s.to_mem_raddr //= s.element.to_mem_raddr[i]
        s.from_mem_rdata //= s.element.from_mem_rdata[i]
        s.to_mem_waddr //= s.element.to_mem_waddr[i]
        s.to_mem_wdata //= s.element.to_mem_wdata[i]
      else:
        s.element.to_mem_raddr[i].rdy //= 0
        s.element.from_mem_rdata[i].val //= 0
        s.element.from_mem_rdata[i].msg //= DataType()
        s.element.to_mem_waddr[i].rdy //= 0
        s.element.to_mem_wdata[i].rdy //= 0

    # Feed clear signal to PhiRTL and CrossbarRTL to correctly resume the progress.
    for i in range(len(FuList)):
      if (FuList[i] == PhiRTL) | (FuList[i] == RetRTL):
        s.element.clear[i] //= s.clear
      else:
        s.element.clear[i] //= 0
    s.fu_crossbar.clear //= s.clear
    s.routing_crossbar.clear //= s.clear
    s.const_mem.clear //= s.clear

    # Connections on the `routing_crossbar`.
    # The data from other tiles should be connected to the
    # `routing_crossbar`.
    for i in range(num_tile_inports):
      s.recv_data[i] //= s.tile_in_channel[i].recv
      s.tile_in_channel[i].send //= s.routing_crossbar.recv_data[i]

    # Connects specific xbar control signals to the corresponding crossbar.
    for i in range(num_routing_xbar_outports):
      s.routing_crossbar.crossbar_outport[i] //= \
          s.ctrl_mem.send_ctrl.msg.routing_xbar_outport[i]
      s.fu_crossbar.crossbar_outport[i] //= \
          s.ctrl_mem.send_ctrl.msg.fu_xbar_outport[i]

    # Connections on the `fu_crossbar`.
    # Leaves the recv_data[0] to resume the progress.
    for i in range(1, num_fu_outports):
      s.element.send_out[i] //= s.fu_crossbar.recv_data[i]

    # The data going out to the other tiles should be from the
    # `routing_crossbar`. Note that there are also data being fed into
    # the FUs via the `routing_crossbar`, which are filtered out by
    # `num_tile_outports` below. In addition, we "or" the outports of
    # the FUs (via `fu_crossbar`) with the outports of the
    # `routing_crossbar` through the corresponding channels.
    for i in range(num_tile_outports):
      s.fu_crossbar.send_data[i] //= s.tile_out_or_link[i].recv_fu
      s.routing_crossbar.send_data[i] //= s.tile_out_or_link[i].recv_xbar
      s.tile_out_or_link[i].send //= s.send_data[i]

    # Crossbars outputs are integrated with the "register_cluster".
    # Whether the required operands for FU are from the "routing_crossbar"
    # or from the "register_cluster" depends on the control signals.
    for i in range(num_fu_inports):
      s.routing_crossbar.send_data[num_tile_outports + i] //= \
          s.register_cluster.recv_data_from_routing_crossbar[i]
      s.fu_crossbar.send_data[num_tile_outports + i] //= \
          s.register_cluster.recv_data_from_fu_crossbar[i]

      s.register_cluster.recv_data_from_const[i].msg //= DataType()
      s.register_cluster.recv_data_from_const[i].val //= 0

      s.register_cluster.send_data_to_fu[i] //= \
          s.element.recv_in[i]
      s.register_cluster.inport_opt //= s.ctrl_mem.send_ctrl.msg

    @update
    def feed_pkt():
        s.ctrl_mem.recv_pkt_from_controller.msg @= CtrlPktType(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0) # , 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        s.const_mem.recv_const.msg @= DataType(0, 0, 0, 0)
        s.ctrl_mem.recv_pkt_from_controller.val @= 0
        s.const_mem.recv_const.val @= 0
        s.recv_from_controller_pkt.rdy @= 0

        if s.recv_from_controller_pkt.val & \
           ((s.recv_from_controller_pkt.msg.payload.cmd == CMD_CONFIG) | \
            (s.recv_from_controller_pkt.msg.payload.cmd == CMD_CONFIG_PROLOGUE_FU) | \
            (s.recv_from_controller_pkt.msg.payload.cmd == CMD_CONFIG_PROLOGUE_FU_CROSSBAR) | \
            (s.recv_from_controller_pkt.msg.payload.cmd == CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR) | \
            (s.recv_from_controller_pkt.msg.payload.cmd == CMD_CONFIG_TOTAL_CTRL_COUNT) | \
            (s.recv_from_controller_pkt.msg.payload.cmd == CMD_CONFIG_COUNT_PER_ITER) | \
            (s.recv_from_controller_pkt.msg.payload.cmd == CMD_CONFIG_CTRL_LOWER_BOUND) | \
            (s.recv_from_controller_pkt.msg.payload.cmd == CMD_GLOBAL_REDUCE_ADD_RESPONSE) | \
            (s.recv_from_controller_pkt.msg.payload.cmd == CMD_GLOBAL_REDUCE_MUL_RESPONSE) | \
            (s.recv_from_controller_pkt.msg.payload.cmd == CMD_CONFIG_STREAMING_LD_START_ADDR) | \
            (s.recv_from_controller_pkt.msg.payload.cmd == CMD_CONFIG_STREAMING_LD_STRIDE) | \
            (s.recv_from_controller_pkt.msg.payload.cmd == CMD_CONFIG_STREAMING_LD_END_ADDR) | \
            (s.recv_from_controller_pkt.msg.payload.cmd == CMD_RECORD_PHI_ADDR) | \
            (s.recv_from_controller_pkt.msg.payload.cmd == CMD_LAUNCH) | \
            (s.recv_from_controller_pkt.msg.payload.cmd == CMD_PAUSE) | \
            (s.recv_from_controller_pkt.msg.payload.cmd == CMD_PRESERVE) | \
            (s.recv_from_controller_pkt.msg.payload.cmd == CMD_RESUME)):
            s.ctrl_mem.recv_pkt_from_controller.val @= 1
            s.ctrl_mem.recv_pkt_from_controller.msg @= s.recv_from_controller_pkt.msg
            s.recv_from_controller_pkt.rdy @= s.ctrl_mem.recv_pkt_from_controller.rdy
        elif s.recv_from_controller_pkt.val & (s.recv_from_controller_pkt.msg.payload.cmd == CMD_CONST):
            s.const_mem.recv_const.val @= 1
            s.const_mem.recv_const.msg @= s.recv_from_controller_pkt.msg.payload.data
            s.recv_from_controller_pkt.rdy @= s.const_mem.recv_const.rdy

        if s.recv_from_controller_pkt.val & (s.recv_from_controller_pkt.msg.payload.cmd == CMD_TERMINATE):
            s.ctrl_mem.recv_pkt_from_controller.val @= 1
            s.ctrl_mem.recv_pkt_from_controller.msg @= s.recv_from_controller_pkt.msg
            s.recv_from_controller_pkt.rdy @= s.ctrl_mem.recv_pkt_from_controller.rdy
            s.clear @= 1
            for i in range(num_tile_inports):
              s.tile_in_channel[i].clear @= 1
        else:
            s.clear @= 0
            for i in range(num_tile_inports):
              s.tile_in_channel[i].clear @= 0

    @update
    def update_send_out_signal():
        s.send_to_controller_pkt.val @= 0
        s.send_to_controller_pkt.msg @= CtrlPktType(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0) # , 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        if s.ctrl_mem.send_pkt_to_controller.val:
            s.send_to_controller_pkt.val @= 1
            s.send_to_controller_pkt.msg @= s.ctrl_mem.send_pkt_to_controller.msg
        s.ctrl_mem.send_pkt_to_controller.rdy @= s.send_to_controller_pkt.rdy

    # Updates the configuration memory related signals.
    @update
    def update_opt():
      s.element.recv_opt.msg @= s.ctrl_mem.send_ctrl.msg
      s.routing_crossbar.recv_opt.msg @= s.ctrl_mem.send_ctrl.msg
      s.fu_crossbar.recv_opt.msg @= s.ctrl_mem.send_ctrl.msg

      # FIXME: Do we still need separate element and routing_xbar?
      # FIXME: Do we need to consider reg bank here?
      s.element.recv_opt.val @= s.ctrl_mem.send_ctrl.val & ~s.element_done
      s.routing_crossbar.recv_opt.val @= s.ctrl_mem.send_ctrl.val & ~s.routing_crossbar_done
      s.fu_crossbar.recv_opt.val @= s.ctrl_mem.send_ctrl.val & ~s.fu_crossbar_done

      # FIXME: yo96, rename ctrl.rdy to ctrl.proceed or sth similar.
      # Allows either the FU-related go out first or routing-xbar go out first. And only
      # allows the ctrl signal proceed till all the sub-modules done their own job (once).
      s.ctrl_mem.send_ctrl.rdy @= (s.element.recv_opt.rdy | s.element_done) & \
                                  (s.routing_crossbar.recv_opt.rdy | s.routing_crossbar_done) & \
                                  (s.fu_crossbar.recv_opt.rdy | s.fu_crossbar_done)

    # TODO: https://github.com/tancheng/VectorCGRA/issues/127
    @update
    def notify_const_mem():
      s.const_mem.ctrl_proceed @= s.ctrl_mem.send_ctrl.rdy & s.ctrl_mem.send_ctrl.val
    
    @update
    def overwrite_fu_outport():
      s.element.send_out[0].rdy @= s.fu_crossbar.recv_data[0].rdy
      if s.context_switch.overwrite_fu_outport.val == 1:
        s.fu_crossbar.recv_data[0].val @= 1
        s.fu_crossbar.recv_data[0].msg @= s.context_switch.overwrite_fu_outport.msg
      else:
        s.fu_crossbar.recv_data[0].val @= s.element.send_out[0].val
        s.fu_crossbar.recv_data[0].msg @= s.element.send_out[0].msg
    
    # Updates the signals indicating whether certain modules already done their jobs.
    @update_ff
    def already_done():
      if s.reset | s.ctrl_mem.send_ctrl.rdy | s.clear:
        s.element_done <<= 0
        s.fu_crossbar_done <<= 0
        s.routing_crossbar_done <<= 0
      else:
        if s.element.recv_opt.rdy:
          s.element_done <<= 1
        if s.fu_crossbar.recv_opt.rdy:
          s.fu_crossbar_done <<= 1
        if s.routing_crossbar.recv_opt.rdy:
          s.routing_crossbar_done <<= 1

    @update
    def notify_crossbars_compute_status():
      s.routing_crossbar.compute_done @= s.element_done
      s.fu_crossbar.compute_done @= s.element_done

  # Line trace
  def line_trace(s):
    recv_str = "|".join(["(" + str(x.msg) + ", val: " + str(x.val) + ", rdy: " + str(x.rdy) + ")" for x in s.recv_data])
    send_str = "|".join([str(x.msg) for x in s.send_data])
    tile_in_channel_recv_str = "|".join([str(x.recv.msg) for x in s.tile_in_channel])
    tile_in_channel_send_str = "|".join([str(x.send.msg) for x in s.tile_in_channel])
    tile_in_channel_str = "|".join([str(x.line_trace()) for x in s.tile_in_channel])
    out_str = "|".join(["(" + str(x.msg.payload) + ", val: " + str(x.val) + ", rdy: " + str(x.rdy) + ")" for x in s.send_data])
    ctrl_mem = s.ctrl_mem.line_trace()
    const_mem = s.const_mem.line_trace()
    context_switch = s.context_switch.line_trace()
    return f"send_str: {send_str}, tile_inports: {recv_str} => [tile_in_channel: {tile_in_channel_str} || routing_crossbar: {s.routing_crossbar.recv_opt.msg} || fu_crossbar: {s.fu_crossbar.recv_opt.msg} || element: {s.element.line_trace()} || s.element_done: {s.element_done}, s.fu_crossbar_done: {s.fu_crossbar_done}, s.routing_crossbar_done: {s.routing_crossbar_done} ||  ctrl_mem: {ctrl_mem}, const_mem: {const_mem} || context_switch: {context_switch}## "

