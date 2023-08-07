"""
=========================================================================
CGRARTL.py
=========================================================================
Author : Cheng Tan
  Date : Dec 15, 2019
"""

from pymtl3                      import *
from ..lib.ifcs                  import SendIfcRTL, RecvIfcRTL
from ..noc.CrossbarRTL           import CrossbarRTL
from ..noc.ChannelRTL            import ChannelRTL
from ..tile.TileRTL              import TileRTL
from ..lib.opt_type              import *
from ..lib.common                import *
from ..mem.data.DataMemRTL       import DataMemRTL
from ..mem.data.DataMemCL        import DataMemCL
from ..fu.single.MemUnitRTL      import MemUnitRTL
from ..fu.single.AdderRTL        import AdderRTL
from ..fu.flexible.FlexibleFuRTL import FlexibleFuRTL

class CGRATemplateRTL( Component ):

  def construct( s, DataType, PredicateType, CtrlType, width, height,
                 ctrl_mem_size, data_mem_size, num_ctrl, total_steps,
                 FunctionUnit, FuList, TileList, LinkList, dataSPM,
                 preload_data = None, preload_const = None ):

    # s.num_tiles = width * height
    s.num_tiles = len( TileList )
    s.num_mesh_ports = 8
    AddrType = mk_bits( clog2( ctrl_mem_size ) )

    # Interfaces
    s.recv_waddr = [ RecvIfcRTL( AddrType )  for _ in range( s.num_tiles ) ]
    s.recv_wopt  = [ RecvIfcRTL( CtrlType )  for _ in range( s.num_tiles ) ]

    # Components
    if preload_const == None:
      # preload_const = [[DataType(0, 0)] for _ in range(width*height)]
      preload_const = [[DataType(0, 0)] for _ in range(s.num_tiles)]
    s.tile = [ TileRTL( DataType, PredicateType, CtrlType,
                        ctrl_mem_size, data_mem_size, num_ctrl,
                        total_steps, 4, 2, s.num_mesh_ports,
                        s.num_mesh_ports, FuList = FuList,
                        const_list = preload_const[i] )
                        for i in range( s.num_tiles ) ]
    s.data_mem = DataMemRTL( DataType, data_mem_size, dataSPM.getNumOfValidReadPorts(), dataSPM.getNumOfValidWritePorts(), preload_data )

    for link in LinkList:
      if link.isFromMem():
        memPort = link.getMemReadPort()
        dstTileIndex = link.dstTile.getIndex( TileList )
        s.data_mem.recv_raddr[memPort] //= s.tile[dstTileIndex].to_mem_raddr
        s.data_mem.send_rdata[memPort] //= s.tile[dstTileIndex].from_mem_rdata

      elif link.isToMem():
        memPort = link.getMemWritePort()
        srcTileIndex = link.srcTile.getIndex( TileList )
        s.tile[srcTileIndex].to_mem_waddr //= s.data_mem.recv_waddr[memPort]
        s.tile[srcTileIndex].to_mem_wdata //= s.data_mem.recv_wdata[memPort]

      else:
        srcTileIndex = link.srcTile.getIndex( TileList )
        dstTileIndex = link.dstTile.getIndex( TileList )
        s.tile[srcTileIndex].send_data[link.srcPort] //= s.tile[dstTileIndex].recv_data[link.dstPort]

    # Connections
    for i in range( s.num_tiles):
      s.recv_waddr[i] //= s.tile[i].recv_waddr
      s.recv_wopt[i]  //= s.tile[i].recv_wopt

      for invalidInPort in TileList[i].getInvalidInPorts():
        s.tile[i].recv_data[invalidInPort].en  //= 0
        s.tile[i].recv_data[invalidInPort].msg //= DataType( 0, 0 )

      for invalidOutPort in TileList[i].getInvalidOutPorts():
        s.tile[i].send_data[invalidOutPort].rdy //= 0

      if not TileList[i].hasFromMem():
        s.tile[i].to_mem_raddr.rdy //= 0
        s.tile[i].from_mem_rdata.en //= 0
        s.tile[i].from_mem_rdata.msg //= DataType(0, 0)

      if not TileList[i].hasToMem():
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
