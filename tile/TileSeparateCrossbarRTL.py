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
from py_markdown_table.markdown_table import markdown_table
from pymtl3 import *

from .TileRTL_constant import tile_port_direction_dict
from ..lib.opt_type import OPT_SYMBOL_DICT
from ..fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from ..fu.single.AdderRTL import AdderRTL
from ..fu.single.BranchRTL import BranchRTL
from ..fu.single.PhiRTL import PhiRTL
from ..fu.single.CompRTL import CompRTL
from ..fu.single.MemUnitRTL import MemUnitRTL
from ..fu.single.MulRTL import MulRTL
from ..lib.basic.en_rdy.ifcs import SendIfcRTL, RecvIfcRTL
from ..lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL
from ..mem.const.ConstQueueRTL import ConstQueueRTL
from ..mem.ctrl.CtrlMemDynamicRTL import CtrlMemDynamicRTL
from ..noc.CrossbarSeparateRTL import CrossbarSeparateRTL
from ..noc.ChannelNormalRTL import ChannelNormalRTL
from ..noc.LinkOrRTL import LinkOrRTL
from ..rf.RegisterRTL import RegisterRTL
# from ..noc.BypassChannelRTL      import BypassChannelRTL

class TileSeparateCrossbarRTL(Component):

  def construct(s, DataType, PredicateType, CtrlPktType, CtrlSignalType,
                ctrl_mem_size, data_mem_size, num_ctrl, total_steps,
                num_fu_inports, num_fu_outports, num_tile_inports,
                num_tile_outports, Fu = FlexibleFuRTL,
                FuList = [PhiRTL, AdderRTL, CompRTL, MulRTL, BranchRTL,
                          MemUnitRTL], const_list = None):

    # Constants.
    num_routing_xbar_inports = num_tile_inports
    num_routing_xbar_outports = num_fu_inports + num_tile_outports

    num_fu_xbar_inports = num_fu_outports
    num_fu_xbar_outports = num_fu_inports + num_tile_outports

    CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
    DataAddrType = mk_bits(clog2(data_mem_size))

    # Interfaces.
    s.recv_data = [RecvIfcRTL(DataType) for _ in range (
        num_tile_inports)]
    s.send_data = [SendIfcRTL(DataType) for _ in range (
        num_tile_outports)]

    # Ctrl.
    # s.recv_waddr = RecvIfcRTL(CtrlAddrType)
    # s.recv_wopt = RecvIfcRTL(CtrlSignalType)
    s.recv_ctrl_pkt = ValRdyRecvIfcRTL(CtrlPktType)

    # Data.
    s.to_mem_raddr = SendIfcRTL(DataAddrType)
    s.from_mem_rdata = RecvIfcRTL(DataType)
    s.to_mem_waddr = SendIfcRTL(DataAddrType)
    s.to_mem_wdata = SendIfcRTL(DataType)

    # Components.
    s.element = FlexibleFuRTL(DataType, PredicateType, CtrlSignalType,
                              num_fu_inports, num_fu_outports,
                              data_mem_size, FuList)
    s.const_queue = ConstQueueRTL(DataType, const_list if const_list != None else [DataType(0)])
    s.routing_crossbar = CrossbarSeparateRTL(DataType, PredicateType, CtrlSignalType,
                                             num_routing_xbar_inports,
                                             num_routing_xbar_outports)
    s.fu_crossbar = CrossbarSeparateRTL(DataType, PredicateType, CtrlSignalType,
                                        num_fu_xbar_inports,
                                        num_fu_xbar_outports)
    s.ctrl_mem = CtrlMemDynamicRTL(CtrlPktType, CtrlSignalType, ctrl_mem_size,
                                   num_fu_inports, num_fu_outports,
                                   num_tile_inports, num_tile_outports,
                                   num_ctrl, total_steps)
    # The `tile_out_channel` indicates the outport channels that are
    # connected to the next tiles.
    s.tile_out_channel = [ChannelNormalRTL(DataType) for _ in range(
        num_tile_outports)]
    # The `fu_in_channel` indicates the inport channels that are
    # connected to the FUs.
    s.fu_in_channel = [ChannelNormalRTL(DataType) for _ in range(
        num_fu_inports)]
    # The `tile_out_or_link` would "or" the outports of the
    # `tile_out_channel` and the FUs.
    s.tile_out_or_link = [LinkOrRTL(DataType) for _ in range(
        num_tile_outports)]
    # The `fu_in_or_link` would "or" the inports of the `fu_in_channel'
    # and the outports of the fu_crossbar.
    s.fu_in_or_link = [LinkOrRTL(DataType) for _ in range(num_fu_inports)]
    # # Added to break the combinational loops
    # s.bypass_channel = [ BypassChannelRTL( DataType ) for _ in range( num_fu_outports ) ]

    # Additional one register for partial predication
    s.reg_predicate = RegisterRTL(PredicateType)

    # Connections.
    # Ctrl.
    # s.ctrl_mem.recv_waddr //= s.recv_waddr
    # s.ctrl_mem.recv_ctrl //= s.recv_wopt
    s.ctrl_mem.recv_pkt //= s.recv_ctrl_pkt

    # Constant queue.
    s.element.recv_const //= s.const_queue.send_const

    for i in range(len(FuList)):
      if FuList[i] == MemUnitRTL:
        s.to_mem_raddr //= s.element.to_mem_raddr[i]
        s.from_mem_rdata //= s.element.from_mem_rdata[i]
        s.to_mem_waddr //= s.element.to_mem_waddr[i]
        s.to_mem_wdata //= s.element.to_mem_wdata[i]
      else:
        s.element.to_mem_raddr[i].rdy //= 0
        s.element.from_mem_rdata[i].en //= 0
        s.element.from_mem_rdata[i].msg //= DataType()
        s.element.to_mem_waddr[i].rdy //= 0
        s.element.to_mem_wdata[i].rdy //= 0

    # Connections on the `routing_crossbar`.
    # The data from other tiles should be connected to the
    # `routing_crossbar`.
    for i in range(num_tile_inports):
      s.recv_data[i] //= s.routing_crossbar.recv_data[i]

    # # Connects specific xbar control signals to the corresponding crossbar.
    for i in range(num_routing_xbar_outports):
      s.routing_crossbar.crossbar_outport[i] //= s.ctrl_mem.send_ctrl.msg.routing_xbar_outport[i]
      s.fu_crossbar.crossbar_outport[i] //= s.ctrl_mem.send_ctrl.msg.fu_xbar_outport[i]


    # The data going out to the other tiles should be from
    # the `routing_crossbar`. Note that there are also data
    # being fed into the FUs via the `routing_crossbar`, which
    # are filtered out by `num_tile_outports` below.
    for i in range(num_tile_outports):
      s.routing_crossbar.send_data[i] //= s.tile_out_channel[i].recv

    # for i in range(num_fu_inports):
    #   s.routing_crossbar.send_data[num_tile_outports + i] //= s.fu_in_channel[i].recv

    # One partial predication register for flow control.
    s.routing_crossbar.send_predicate //= s.reg_predicate.recv
    s.reg_predicate.send //= s.element.recv_predicate

    # Connects the FU's inport channels with the corresponding FU.
    for i in range(num_fu_inports):
      s.fu_in_channel[i].send //= s.element.recv_in[i]
      s.fu_in_channel[i].count //= s.element.recv_in_count[i]

    # Connections on the `fu_crossbar`.
    for i in range(num_fu_outports):
      s.element.send_out[i] //= s.fu_crossbar.recv_data[i]

    # Links "or" the outports of the FUs (via `fu_crossbar`) with the
    # outports of the `routing_crossbar` through the corresponding channels.
    for i in range(num_tile_outports):
      s.fu_crossbar.send_data[i] //= s.tile_out_or_link[i].recv_fu
      s.tile_out_channel[i].send //= s.tile_out_or_link[i].recv_xbar
      s.tile_out_or_link[i].send //= s.send_data[i]

    # Links "or" the inports of the FUs (from the `routing_crossbar`)
    # with the outports of the FUs (via the `fu_crossbar`).
    for i in range(num_fu_inports):
      s.fu_crossbar.send_data[num_tile_outports + i] //= s.fu_in_or_link[i].recv_fu
      s.routing_crossbar.send_data[num_tile_outports + i] //= s.fu_in_or_link[i].recv_xbar
      s.fu_in_or_link[i].send //= s.fu_in_channel[i].recv


    # Updates the configuration memory related signals.
    @update
    def update_opt():

      s.element.recv_opt.msg @= s.ctrl_mem.send_ctrl.msg
      s.routing_crossbar.recv_opt.msg @= s.ctrl_mem.send_ctrl.msg
      s.fu_crossbar.recv_opt.msg @= s.ctrl_mem.send_ctrl.msg

      s.element.recv_opt.en @= s.ctrl_mem.send_ctrl.en
      s.routing_crossbar.recv_opt.en @= s.ctrl_mem.send_ctrl.en
      s.fu_crossbar.recv_opt.en @= s.ctrl_mem.send_ctrl.en

      s.ctrl_mem.send_ctrl.rdy @= s.element.recv_opt.rdy & \
                                  s.routing_crossbar.recv_opt.rdy & \
                                  s.fu_crossbar.recv_opt.rdy

  # verbose trace
  def verbose_trace( s, verbosity = 1 ):
      recv_data = [ x.msg.__dict__ for x in s.recv_data ]
      recv_list = []
      for idx, data in enumerate(recv_data):
          port_direction = tile_port_direction_dict[idx]
          dict_with_direction = {"inport_direction": port_direction}
          dict_with_direction.update(data)
          recv_list.append(dict_with_direction)
      recv_md = markdown_table(recv_list).set_params(quote=False).get_markdown()

      routing_crossbar_dict = dict(s.routing_crossbar.recv_opt.msg.__dict__)
      routing_crossbar_dict['ctrl'] = OPT_SYMBOL_DICT[routing_crossbar_dict['ctrl']]
      routing_crossbar_dict['predicate'] = int(routing_crossbar_dict['predicate'])
      routing_crossbar_dict['fu_in'] = [int(fi) for fi in routing_crossbar_dict['fu_in']]
      routing_crossbar_dict['fu_xbar_outport'] = [int(fxop) for fxop in routing_crossbar_dict['fu_xbar_outport']]
      routing_crossbar_dict['routing_predicate_in'] = [int(rpi) for rpi in
                                                       routing_crossbar_dict['routing_predicate_in']]
      routing_crossbar_dict['routing_xbar_outport'] = [int(rxop) for rxop in
                                                       routing_crossbar_dict['routing_xbar_outport']]
      routing_crossbar_str = "\n".join([(key + ": " + str(value)) for key, value in routing_crossbar_dict.items()])

      fu_crossbar_dict = dict(s.fu_crossbar.recv_opt.msg.__dict__)
      fu_crossbar_dict['ctrl'] = OPT_SYMBOL_DICT[fu_crossbar_dict['ctrl']]
      fu_crossbar_dict['predicate'] = int(fu_crossbar_dict['predicate'])
      fu_crossbar_dict['fu_in'] = [int(fi) for fi in fu_crossbar_dict['fu_in']]
      fu_crossbar_dict['fu_xbar_outport'] = [int(fxop) for fxop in fu_crossbar_dict['fu_xbar_outport']]
      fu_crossbar_dict['routing_predicate_in'] = [int(rpi) for rpi in fu_crossbar_dict['routing_predicate_in']]
      fu_crossbar_dict['routing_xbar_outport'] = [int(rxop) for rxop in fu_crossbar_dict['routing_xbar_outport']]
      fu_crossbar_str = "\n".join([(key + ": " + str(value)) for key, value in fu_crossbar_dict.items()])

      tile_out_channel_recv_data = [x.recv.msg.__dict__ for x in s.tile_out_channel]
      tile_out_channel_recv_data_list = []
      for idx, data in enumerate(tile_out_channel_recv_data):
          port_direction = tile_port_direction_dict[idx]
          dict_with_direction = {"inport_direction": port_direction}
          dict_with_direction.update(data)
          tile_out_channel_recv_data_list.append(dict_with_direction)
      tile_out_channel_recv_md = markdown_table(tile_out_channel_recv_data_list).set_params(quote=False).get_markdown()

      tile_out_channel_send_data = [x.send.msg.__dict__ for x in s.tile_out_channel]
      tile_out_channel_send_data_list = []
      for idx, data in enumerate(tile_out_channel_send_data):
          port_direction = tile_port_direction_dict[idx]
          dict_with_direction = {"outport_direction": port_direction}
          dict_with_direction.update(data)
          tile_out_channel_send_data_list.append(dict_with_direction)
      tile_out_channel_send_md = markdown_table(tile_out_channel_send_data_list).set_params(quote=False).get_markdown()

      fu_in_channel_recv_data = [x.recv.msg.__dict__ for x in s.fu_in_channel]
      fu_in_channel_recv_data_list = []
      for idx, data in enumerate(fu_in_channel_recv_data):
          port_direction = tile_port_direction_dict[idx]
          dict_with_direction = {"inport_direction": port_direction}
          dict_with_direction.update(data)
          fu_in_channel_recv_data_list.append(dict_with_direction)
      fu_in_channel_recv_md = markdown_table(fu_in_channel_recv_data_list).set_params(quote=False).get_markdown()

      fu_in_channel_send_data = [x.send.msg.__dict__ for x in s.fu_in_channel]
      fu_in_channel_send_data_list = []
      for idx, data in enumerate(fu_in_channel_send_data):
          port_direction = tile_port_direction_dict[idx]
          dict_with_direction = {"outport_direction": port_direction}
          dict_with_direction.update(data)
          fu_in_channel_send_data_list.append(dict_with_direction)
      fu_in_channel_send_md = markdown_table(fu_in_channel_send_data_list).set_params(quote=False).get_markdown()

      tile_outports_data = [x.msg.__dict__ for x in s.send_data]
      tile_outports_data_list = []
      for idx, data in enumerate(tile_outports_data):
          port_direction = tile_port_direction_dict[idx]
          dict_with_direction = {"outport_direction": port_direction}
          dict_with_direction.update(data)
          tile_outports_data_list.append(dict_with_direction)
      tile_outports_md = markdown_table(tile_outports_data_list).set_params(quote=False).get_markdown()

      return (f'\n## class: {s.__class__.__name__}\n'
              f'- tile_inports:\n'
              f'{recv_md}\n'
              f'===>\n'
              f'- routing_crossbar:\n'
              f'{routing_crossbar_str}\n'
              f'- fu_crossbar:\n'
              f'{fu_crossbar_str}\n'
              f'- element:\n'
              f'{s.element.line_trace()}\n'
              f'- tile_out_channels_recv:\n'
              f'{tile_out_channel_recv_md}\n'
              f'===>\n'
              f'- tile_out_channel_send:\n'
              f'{tile_out_channel_send_md}\n'
              f'- fu_in_channels_recv:\n'
              f'{fu_in_channel_recv_md}\n'
              f'===>\n'
              f'- fu_in_channels_send:\n'
              f'{fu_in_channel_send_md}\n'
              f'===>\n'
              f'- tile_outports:\n'
              f'{tile_outports_md}\n')
  # Line trace
  def line_trace( s ):
    recv_str = "|".join([str(x.msg) for x in s.recv_data])
    tile_out_channel_recv_str = "|".join([str(x.recv.msg) for x in s.tile_out_channel])
    tile_out_channel_send_str = "|".join([str(x.send.msg) for x in s.tile_out_channel])
    fu_in_channel_recv_str = "|".join([str(x.recv.msg) for x in s.fu_in_channel])
    fu_in_channel_send_str = "|".join([str(x.send.msg) for x in s.fu_in_channel])
    out_str = "|".join(["(" + str(x.msg.payload) + "," + str(x.msg.predicate) + ")" for x in s.send_data])
    return f"tile_inports: {recv_str} => [routing_crossbar: {s.routing_crossbar.recv_opt.msg} || fu_crossbar: {s.fu_crossbar.recv_opt.msg} || element: {s.element.line_trace()} || tile_out_channels: {tile_out_channel_recv_str} => {tile_out_channel_send_str} || fu_in_channels: {fu_in_channel_recv_str} => {fu_in_channel_send_str}]  => tile_outports: {out_str} ## "
    # return f"{recv_str} => [{s.crossbar.recv_opt.msg}] ({s.element.line_trace()}) => {channel_recv_str} => {channel_send_str} => {out_str}"
