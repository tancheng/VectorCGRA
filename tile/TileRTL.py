"""
=========================================================================
TileRTL.py
=========================================================================

Author : Cheng Tan
  Date : Dec 11, 2019
"""
import json


from pymtl3 import *

from ..fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from ..fu.single.AdderRTL import AdderRTL
from ..fu.single.BranchRTL import BranchRTL
from ..fu.single.CompRTL import CompRTL
from ..fu.single.MemUnitRTL import MemUnitRTL
from ..fu.single.MulRTL import MulRTL
from ..fu.single.PhiRTL import PhiRTL
from ..lib.basic.en_rdy.ifcs import SendIfcRTL, RecvIfcRTL
from ..mem.const.ConstQueueRTL import ConstQueueRTL
from ..mem.ctrl.CtrlMemRTL import CtrlMemRTL
from ..noc.CrossbarRTL import CrossbarRTL
from ..noc.ChannelRTL import ChannelRTL
from ..rf.RegisterRTL import RegisterRTL
# from ..noc.BypassChannelRTL      import BypassChannelRTL
from py_markdown_table.markdown_table import markdown_table

tile_port_direction_dict = {0: "NORTH", 1: "SOUTH", 2: "WEST", 3: "EAST", 4: "NORTHWEST", 5: "NORTHEAST",
                              6: "SOUTHEAST", 7: "SOUTHWEST"}

class TileRTL( Component ):

  def construct( s, DataType, PredicateType, CtrlType,
                 ctrl_mem_size, data_mem_size, num_ctrl,
                 total_steps, num_fu_inports, num_fu_outports,
                 num_connect_inports, num_connect_outports,
                 Fu=FlexibleFuRTL,
                 FuList=[PhiRTL,AdderRTL,CompRTL,MulRTL,BranchRTL,MemUnitRTL],
                 const_list = None ):

    # Constant
    num_xbar_inports  = num_fu_outports + num_connect_inports
    num_xbar_outports = num_fu_inports + num_connect_outports

    CtrlAddrType = mk_bits( clog2( ctrl_mem_size ) )
    DataAddrType = mk_bits( clog2( data_mem_size ) )

    # Interfaces
    s.recv_data = [ RecvIfcRTL( DataType ) for _ in range ( num_connect_inports ) ]
    s.send_data = [ SendIfcRTL( DataType ) for _ in range ( num_connect_outports ) ]

    # Ctrl
    s.recv_waddr = RecvIfcRTL( CtrlAddrType )
    s.recv_wopt  = RecvIfcRTL( CtrlType )

    # Data
    s.to_mem_raddr   = SendIfcRTL( DataAddrType )
    s.from_mem_rdata = RecvIfcRTL( DataType )
    s.to_mem_waddr   = SendIfcRTL( DataAddrType )
    s.to_mem_wdata   = SendIfcRTL( DataType )

    # Components
    s.element  = FlexibleFuRTL( DataType, PredicateType, CtrlType,
                                num_fu_inports, num_fu_outports,
                                data_mem_size, FuList )
    s.const_queue = ConstQueueRTL( DataType, const_list if const_list != None else [DataType(0)])
    s.crossbar = CrossbarRTL( DataType, PredicateType, CtrlType,
                              num_xbar_inports, num_xbar_outports )
    s.ctrl_mem = CtrlMemRTL( CtrlType, ctrl_mem_size, num_ctrl, total_steps )
    s.channel  = [ ChannelRTL( DataType ) for _ in range( num_xbar_outports ) ]
    # # Added to break the combinational loops
    # s.bypass_channel = [ BypassChannelRTL( DataType ) for _ in range( num_fu_outports ) ]

    # Additional one register for partial predication
    s.reg_predicate = RegisterRTL( PredicateType )

    # Connections

    # Ctrl
    s.ctrl_mem.recv_waddr //= s.recv_waddr
    s.ctrl_mem.recv_ctrl  //= s.recv_wopt

    # Data
    s.element.recv_const //= s.const_queue.send_const

    for i in range( len( FuList ) ):
      if FuList[i] == MemUnitRTL:
        s.to_mem_raddr   //= s.element.to_mem_raddr[i]
        s.from_mem_rdata //= s.element.from_mem_rdata[i]
        s.to_mem_waddr   //= s.element.to_mem_waddr[i]
        s.to_mem_wdata   //= s.element.to_mem_wdata[i]
      else:
        s.element.to_mem_raddr[i].rdy   //= 0
        s.element.from_mem_rdata[i].en  //= 0
        s.element.from_mem_rdata[i].msg //= DataType()
        s.element.to_mem_waddr[i].rdy   //= 0
        s.element.to_mem_wdata[i].rdy   //= 0

    for i in range( num_connect_inports ):
      s.recv_data[i] //= s.crossbar.recv_data[i]

    for i in range( num_xbar_outports ):
      s.crossbar.send_data[i] //= s.channel[i].recv

    # One partial predication register for flow control.
    s.crossbar.send_predicate //= s.reg_predicate.recv
    s.reg_predicate.send //= s.element.recv_predicate

    for i in range( num_connect_outports ):
      s.channel[i].send //= s.send_data[i]

    for i in range( num_fu_inports ):
      s.channel[num_connect_inports+i].send //= s.element.recv_in[i]
      s.channel[num_connect_inports+i].count //= s.element.recv_in_count[i]

    for i in range( num_fu_outports ):
      s.element.send_out[i] //= s.crossbar.recv_data[num_connect_outports+i]
      # s.element.send_out[i]    //= s.bypass_channel[i].recv
      # s.bypass_channel[i].send //= s.crossbar.recv_data[num_connect_outports+i]

    @update
    def update_opt():
      s.element.recv_opt.msg   @= s.ctrl_mem.send_ctrl.msg
      s.crossbar.recv_opt.msg  @= s.ctrl_mem.send_ctrl.msg
      s.element.recv_opt.en    @= s.ctrl_mem.send_ctrl.en
      s.crossbar.recv_opt.en   @= s.ctrl_mem.send_ctrl.en
      s.ctrl_mem.send_ctrl.rdy @= s.element.recv_opt.rdy & s.crossbar.recv_opt.rdy


  # Line trace
  def line_trace( s ):
    # recv_str    = f'[{", ".join([ str(x.msg.__dict__) for x in s.recv_data ])}]'
    recv_data = [ x.msg.__dict__ for x in s.recv_data ]
    recv_list = []
    for idx, data in enumerate(recv_data):
      port_direction = tile_port_direction_dict[idx]
      dict_with_direction = {"port_direction": port_direction}
      dict_with_direction.update(data)
      recv_list.append(dict_with_direction)
    recv_md = markdown_table(recv_list).set_params(quote=False).get_markdown()
    recv_opt_msg_dict = s.crossbar.recv_opt.msg.__dict__
    # todo
    # E   AttributeError: 'str' object has no attribute 'clone'
    # print(f"s.crossbar.recv_opt.msg: {s.crossbar.recv_opt.msg}")
    # recv_opt_msg_dict['ctrl'] = OPT_SYMBOL_DICT[s.crossbar.recv_opt.msg.ctrl]
    recv_opt_msg = "\n".join([(key + ": " + str(value)) for key, value in recv_opt_msg_dict.items()])

    channel_recv_md = markdown_table([ x.recv.msg.__dict__ for x in s.channel ]).set_params(quote=False).get_markdown()
    channel_send_md = markdown_table([ x.send.msg.__dict__ for x in s.channel ]).set_params(quote=False).get_markdown()
    out_md  = markdown_table([ dict(send_msg_payload=x.msg.payload, send_msg_predicate=x.msg.predicate) for x in s.send_data ]).set_params(quote=False).get_markdown()
    return (f"\n## class[{s.__class__.__name__}]:\n"
            f"- recv:"
            f"{recv_md}\n"
            f"===>\n"
            f"- recv_opt_msg:\n"
            f"{recv_opt_msg}\n"
            f"- element:\n"
            f"{s.element.line_trace()}\n"
            f"===>\n"
            f"- channel_recv:\n"
            f"{channel_recv_md}\n"
            f"===>\n"
            f"- channel_send:"
            f"{channel_send_md}\n"
            f"===>\n"
            f"- out:"
            f"{out_md}\n")

