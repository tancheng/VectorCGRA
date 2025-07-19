"""
=========================================================================
TileSeparateCrossbarRTL.py
=========================================================================
The tile contains a list of functional units, a configuration memory, a
set of registers (e.g., channels), and two crossbars. One crossbar is for
routing the data to registers (i.e., the channels before FU and the
channels after the crossbar), and the other one is for passing the to the
next crossbar.

Detailed in: https://github.com/tancheng/VectorCGRA/issues/13 (Option 2).

Author : Cheng Tan
  Date : Nov 26, 2024
"""

from ..fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from ..fu.single.AdderRTL import AdderRTL
from ..fu.single.GrantRTL import GrantRTL
from ..fu.single.CompRTL import CompRTL
from ..fu.single.MemUnitRTL import MemUnitRTL
from ..fu.single.MulRTL import MulRTL
from ..fu.single.PhiRTL import PhiRTL
from ..lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ..lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ..lib.cmd_type import *
from ..lib.util.common import *
from ..mem.const.ConstQueueDynamicRTL import ConstQueueDynamicRTL
from ..mem.ctrl.CtrlMemDynamicRTL import CtrlMemDynamicRTL
from ..mem.register_cluster.RegisterClusterRTL import RegisterClusterRTL
from ..noc.CrossbarRTL import CrossbarRTL
from ..noc.LinkOrRTL import LinkOrRTL
from ..noc.PyOCN.pymtl3_net.channel.ChannelRTL import ChannelRTL
from ..rf.RegisterRTL import RegisterRTL


class TileRTL(Component):

  def construct(s, DataType, PredicateType, CtrlPktType, CgraPayloadType,
                CtrlSignalType, ctrl_mem_size, data_mem_size, num_ctrl,
                total_steps, num_fu_inports, num_fu_outports, num_tile_inports,
                num_tile_outports, num_cgras, num_tiles,
                num_registers_per_reg_bank = 16,
                Fu = FlexibleFuRTL,
                FuList = [PhiRTL, AdderRTL, CompRTL, MulRTL, GrantRTL, MemUnitRTL]):

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
    s.element = FlexibleFuRTL(DataType, PredicateType, CtrlSignalType,
                              num_fu_inports, num_fu_outports,
                              data_mem_size, num_tiles, FuList)
    s.const_mem = ConstQueueDynamicRTL(DataType, ctrl_mem_size)
    s.routing_crossbar = CrossbarRTL(DataType, PredicateType,
                                     CtrlSignalType,
                                     num_routing_xbar_inports,
                                     num_routing_xbar_outports,
                                     num_tiles,
                                     num_tile_outports)
    s.fu_crossbar = CrossbarRTL(DataType, PredicateType,
                                CtrlSignalType,
                                num_fu_xbar_inports,
                                num_fu_xbar_outports,
                                num_tiles,
                                num_tile_outports)
    s.register_cluster = \
        RegisterClusterRTL(DataType, CtrlSignalType, num_fu_inports,
                           num_registers_per_reg_bank)
    s.ctrl_mem = CtrlMemDynamicRTL(CtrlPktType,
                                   CgraPayloadType,
                                   CtrlSignalType,
                                   ctrl_mem_size,
                                   num_fu_inports,
                                   num_fu_outports,
                                   num_tile_inports,
                                   num_tile_outports,
                                   num_cgras,
                                   num_tiles,
                                   num_ctrl,
                                   total_steps)

    # The `tile_in_channel` indicates the outport channels that are
    # connected to the next tiles.
    s.tile_in_channel = [ChannelRTL(DataType, latency = 1)
                         for _ in range(num_tile_inports)]

    # The `tile_out_or_link` would "or" the outports of the
    # `tile_out_channel` and the FUs.
    s.tile_out_or_link = [LinkOrRTL(DataType)
                          for _ in range(num_tile_outports)]

    # Additional one register for partial predication
    s.reg_predicate = RegisterRTL(PredicateType)

    # Signals indicating whether certain modules already done their jobs.
    s.element_done = Wire(1)
    s.fu_crossbar_done = Wire(1)
    s.routing_crossbar_done = Wire(1)

    s.cgra_id = InPort(mk_bits(max(1, clog2(num_cgras))))
    s.tile_id = InPort(mk_bits(clog2(num_tiles + 1)))

    # Propagates tile id.
    s.element.tile_id //= s.tile_id
    s.ctrl_mem.cgra_id //= s.cgra_id
    s.ctrl_mem.tile_id //= s.tile_id
    s.fu_crossbar.tile_id //= s.tile_id
    s.routing_crossbar.tile_id //= s.tile_id

    # Assigns crossbar id.
    s.routing_crossbar.crossbar_id //= PORT_ROUTING_CROSSBAR
    s.fu_crossbar.crossbar_id //= PORT_FU_CROSSBAR

    # Constant queue.
    s.element.recv_const //= s.const_mem.send_const

    # Prologue port.
    s.element.prologue_count_inport //= s.ctrl_mem.prologue_count_outport_fu
    for i in range(num_routing_xbar_inports):
      s.routing_crossbar.prologue_count_inport[i] //= \
          s.ctrl_mem.prologue_count_outport_routing_crossbar[i]
    for i in range(num_fu_xbar_inports):
      s.fu_crossbar.prologue_count_inport[i] //= \
          s.ctrl_mem.prologue_count_outport_fu_crossbar[i]

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

    # One partial predication register for flow control.
    s.routing_crossbar.send_predicate //= s.reg_predicate.recv
    s.reg_predicate.send //= s.element.recv_predicate

    # Connections on the `fu_crossbar`.
    for i in range(num_fu_outports):
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
            (s.recv_from_controller_pkt.msg.payload.cmd == CMD_LAUNCH)):
            s.ctrl_mem.recv_pkt_from_controller.val @= 1
            s.ctrl_mem.recv_pkt_from_controller.msg @= s.recv_from_controller_pkt.msg
            s.recv_from_controller_pkt.rdy @= s.ctrl_mem.recv_pkt_from_controller.rdy
        elif s.recv_from_controller_pkt.val & (s.recv_from_controller_pkt.msg.payload.cmd == CMD_CONST):
            s.const_mem.recv_const.val @= 1
            s.const_mem.recv_const.msg @= s.recv_from_controller_pkt.msg.payload.data
            # s.const_mem.recv_const.msg.predicate @= 1
            s.recv_from_controller_pkt.rdy @= s.const_mem.recv_const.rdy

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

    # Updates the signals indicating whether certain modules already done their jobs.
    @update_ff
    def already_done():
      if s.reset | s.ctrl_mem.send_ctrl.rdy:
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
    out_str = "|".join(["(" + str(x.msg.payload) + ", predicate: " + str(x.msg.predicate) + ", val: " + str(x.val) + ", rdy: " + str(x.rdy) + ")" for x in s.send_data])
    ctrl_mem = s.ctrl_mem.line_trace()
    const_mem = s.const_mem.line_trace()
    return f"send_str: {send_str}, tile_inports: {recv_str} => [tile_in_channel: {tile_in_channel_str} || routing_crossbar: {s.routing_crossbar.recv_opt.msg} || fu_crossbar: {s.fu_crossbar.recv_opt.msg} || element: {s.element.line_trace()} || s.element_done: {s.element_done}, s.fu_crossbar_done: {s.fu_crossbar_done}, s.routing_crossbar_done: {s.routing_crossbar_done} ||  ctrl_mem: {ctrl_mem}, const_mem: {const_mem} ## "

