"""
=========================================================================
TileRTL.py
=========================================================================

Author : Cheng Tan
  Date : Dec 11, 2019
"""
from py_markdown_table.markdown_table import markdown_table
from pymtl3 import *

from ..fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from ..fu.single.AdderRTL import AdderRTL
from ..fu.single.BranchRTL import BranchRTL
from ..fu.single.CompRTL import CompRTL
from ..fu.single.MemUnitRTL import MemUnitRTL
from ..fu.single.MulRTL import MulRTL
from ..fu.single.PhiRTL import PhiRTL
from ..lib.basic.en_rdy.ifcs import SendIfcRTL, RecvIfcRTL
from ..lib.util.common import TILE_PORT_DIRECTION_DICT_DESC
from ..mem.const.ConstQueueRTL import ConstQueueRTL
from ..mem.ctrl.CtrlMemRTL import CtrlMemRTL
from ..noc.ChannelRTL import ChannelRTL
from ..noc.CrossbarRTL import CrossbarRTL
from ..rf.RegisterRTL import RegisterRTL


# from ..noc.BypassChannelRTL      import BypassChannelRTL

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
      recv_str = "|".join([str(x.msg) for x in s.recv_data])
      channel_recv_str = "|".join([str(x.recv.msg) for x in s.channel])
      channel_send_str = "|".join([str(x.send.msg) for x in s.channel])
      out_str = "|".join(["(" + str(x.msg.payload) + "," + str(x.msg.predicate) + ")" for x in s.send_data])
      return f"{recv_str} => [{s.crossbar.recv_opt.msg}] ({s.element.line_trace()}) => {channel_recv_str} => {channel_send_str} => {out_str}"


  def verbose_trace_md_formatter(self, data_type, data):
      assert data_type in [ "recv", "send" ]
      data_list = [ x for x in data ]
      result_list = []
      for idx, port_data in enumerate(data_list):
          msg_dict = port_data.msg.__dict__
          if data_type is "recv":
            tile_port_dict = { "tile_inport_direction": TILE_PORT_DIRECTION_DICT_DESC[idx], "rdy": port_data.rdy }
          else:
            tile_port_dict = { "tile_outport_direction": TILE_PORT_DIRECTION_DICT_DESC[idx], "en": port_data.en }
          tile_port_dict.update(msg_dict)
          result_list.append(tile_port_dict)
      result_md = markdown_table(result_list).set_params(quote = False).get_markdown()
      return result_md

  # verbose trace
  def verbose_trace(s, verbosity = 1):
      # recv:
      #   1. rdy (if ready to receive data), if en and rdy: then data has been transferred (val, rdy are new type(protocol))
      #   2. data
      #   [3. opt will show in FU trace]
      # FU:
      #   FlexibleFuRTL.py
      # tile out:
      #   1. en (is data transferred)
      recv_md = s.verbose_trace_md_formatter("recv", s.recv_data)
      send_md = s.verbose_trace_md_formatter("send", s.send_data)
      return (f"\n## class[{s.__class__.__name__}]:\n"
              f"- Tile recv:"
              f"{recv_md}\n\n"
              f"- FU element:\n"
              f"{s.element.verbose_trace(verbosity=verbosity)}\n"
              f"===>\n"
              f"- Tile out:"
              f"{send_md}\n")
