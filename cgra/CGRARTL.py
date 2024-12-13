"""
=========================================================================
CGRARTL.py
=========================================================================
Author : Cheng Tan
  Date : Dec 15, 2019
"""

from pymtl3 import *
from ..fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from ..fu.single.MemUnitRTL import MemUnitRTL
from ..fu.single.AdderRTL import AdderRTL
from ..lib.basic.en_rdy.ifcs import SendIfcRTL, RecvIfcRTL
from ..lib.opt_type import *
from ..lib.util.common import *
from ..mem.data.DataMemRTL import DataMemRTL
from ..mem.data.DataMemCL import DataMemCL
from ..noc.ChannelRTL import ChannelRTL
from ..noc.CrossbarRTL import CrossbarRTL
from ..tile.TileRTL import TileRTL


class CGRARTL( Component ):

  def construct( s, DataType, PredicateType, CtrlType, width, height,
                 ctrl_mem_size, data_mem_size, num_ctrl, total_steps,
                 FunctionUnit, FuList, preload_data = None,
                 preload_const = None ):

    s.num_tiles = width * height
    s.num_mesh_ports = 4
    AddrType = mk_bits( clog2( ctrl_mem_size ) )

    # Interfaces
    s.recv_waddr = [ RecvIfcRTL( AddrType )  for _ in range( s.num_tiles ) ]
    s.recv_wopt  = [ RecvIfcRTL( CtrlType )  for _ in range( s.num_tiles ) ]

    # Components
    if preload_const == None:
      preload_const = [[DataType(0, 0)] for _ in range(width*height)]
    s.tile = [ TileRTL( DataType, PredicateType, CtrlType,
                        ctrl_mem_size, data_mem_size, num_ctrl,
                        total_steps, 4, 2, s.num_mesh_ports,
                        s.num_mesh_ports,
                        Fu = FunctionUnit,
                        FuList = FuList,
                        const_list = preload_const[i] )
                        for i in range( s.num_tiles ) ]
    s.data_mem = DataMemRTL( DataType, data_mem_size, height, height, preload_data )

    # Connections
    for i in range( s.num_tiles):
      s.recv_waddr[i] //= s.tile[i].recv_waddr
      s.recv_wopt[i]  //= s.tile[i].recv_wopt

      if i // width > 0:
        s.tile[i].send_data[PORT_SOUTH] //= s.tile[i-width].recv_data[PORT_NORTH]

      if i // width < height - 1:
        s.tile[i].send_data[PORT_NORTH] //= s.tile[i+width].recv_data[PORT_SOUTH]

      if i % width > 0:
        s.tile[i].send_data[PORT_WEST] //= s.tile[i-1].recv_data[PORT_EAST]

      if i % width < width - 1:
        s.tile[i].send_data[PORT_EAST] //= s.tile[i+1].recv_data[PORT_WEST]

      if i // width == 0:
        s.tile[i].send_data[PORT_SOUTH].rdy //= 0
        s.tile[i].recv_data[PORT_SOUTH].en  //= 0
        s.tile[i].recv_data[PORT_SOUTH].msg //= DataType( 0, 0 )

      if i // width == height - 1:
        s.tile[i].send_data[PORT_NORTH].rdy  //= 0
        s.tile[i].recv_data[PORT_NORTH].en   //= 0
        s.tile[i].recv_data[PORT_NORTH].msg  //= DataType( 0, 0 )

      if i % width == 0:
        s.tile[i].send_data[PORT_WEST].rdy  //= 0
        s.tile[i].recv_data[PORT_WEST].en   //= 0
        s.tile[i].recv_data[PORT_WEST].msg  //= DataType( 0, 0 )

      if i % width == width - 1:
        s.tile[i].send_data[PORT_EAST].rdy  //= 0
        s.tile[i].recv_data[PORT_EAST].en   //= 0
        s.tile[i].recv_data[PORT_EAST].msg  //= DataType( 0, 0 )

      if i % width == 0:
        s.tile[i].to_mem_raddr   //= s.data_mem.recv_raddr[i//width]
        s.tile[i].from_mem_rdata //= s.data_mem.send_rdata[i//width]
        s.tile[i].to_mem_waddr   //= s.data_mem.recv_waddr[i//width]
        s.tile[i].to_mem_wdata   //= s.data_mem.recv_wdata[i//width]
      else:
        s.tile[i].to_mem_raddr.rdy //= 0
        s.tile[i].from_mem_rdata.en //= 0
        s.tile[i].from_mem_rdata.msg //= DataType(0, 0)
        s.tile[i].to_mem_waddr.rdy //= 0
        s.tile[i].to_mem_wdata.rdy //= 0

  # Line trace
  def line_trace( s ):
    # str = "||".join([ x.element.line_trace() for x in s.tile ])
    # str += " :: [" + s.data_mem.line_trace() + "]"
    res = "||\n".join([ (("[tile"+str(i)+"]: ") + x.line_trace() + x.ctrl_mem.line_trace())
                              for (i,x) in enumerate(s.tile) ])
    res += "\n :: [" + s.data_mem.line_trace() + "]    \n"
    return res
