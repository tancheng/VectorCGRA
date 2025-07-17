"""
=========================================================================
CgraRTL.py
=========================================================================

Author : Cheng Tan
  Date : Dec 22, 2024
"""

from ..fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from ..fu.single.AdderRTL import AdderRTL
from ..fu.single.BranchRTL import BranchRTL
from ..fu.single.CompRTL import CompRTL
from ..fu.single.MemUnitRTL import MemUnitRTL
from ..fu.single.MulRTL import MulRTL
from ..fu.single.PhiRTL import PhiRTL
from ..lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ..lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ..lib.opt_type import *
from ..lib.util.common import *
from ..tile.TileRTL import TileRTL


class TileWrapperRTL(Component):

  def construct(s, DataType, PredicateType, CtrlPktType,
                      CgraPayloadType, CtrlSignalType, ctrl_mem_size,
                      data_mem_size_global, num_ctrl,
                      total_steps, num_fu_inports, num_fu_outports, num_tile_inports,
                      num_tile_outports, num_cgras, num_tiles,
                      num_registers_per_reg_bank, width, height, cgra_topology,
                      Fu = FlexibleFuRTL,
                      FuList = [PhiRTL, AdderRTL, CompRTL, MulRTL, BranchRTL, MemUnitRTL]):

    # Other topology can simply modify the tiles connections, or
    # leverage the template for modeling.
    s.num_tiles = num_tiles
    s.num_tile_inports = num_tile_inports
    s.num_tile_outports = num_tile_outports

    s.num_cgras = num_cgras
    # An additional router for controller to receive CMD_COMPLETE signal from Ring to CPU.
    global_addr_nbits = clog2(data_mem_size_global)
    AddrType = mk_bits(global_addr_nbits)

    s.tile_to_mem_raddr = [SendIfcRTL(AddrType) for _ in range(height + width - 1)]
    s.tile_from_mem_rdata = [RecvIfcRTL(DataType) for _ in range(height + width - 1)]
    s.tile_to_mem_waddr = [SendIfcRTL(AddrType) for _ in range(height + width - 1)]
    s.tile_to_mem_wdata = [SendIfcRTL(DataType) for _ in range(height + width - 1)]

    # Interfaces on the boundary of the CGRA.
    s.recv_data_on_boundary_south = [RecvIfcRTL(DataType) for _ in range(width )]
    s.send_data_on_boundary_south = [SendIfcRTL(DataType) for _ in range(width )]
    s.recv_data_on_boundary_north = [RecvIfcRTL(DataType) for _ in range(width )]
    s.send_data_on_boundary_north = [SendIfcRTL(DataType) for _ in range(width )]

    s.recv_data_on_boundary_east  = [RecvIfcRTL(DataType) for _ in range(height)]
    s.send_data_on_boundary_east  = [SendIfcRTL(DataType) for _ in range(height)]
    s.recv_data_on_boundary_west  = [RecvIfcRTL(DataType) for _ in range(height)]
    s.send_data_on_boundary_west  = [SendIfcRTL(DataType) for _ in range(height)]

    # Components
    s.tile = [TileRTL(DataType, PredicateType, CtrlPktType,
                      CgraPayloadType, CtrlSignalType, ctrl_mem_size,
                      data_mem_size_global, num_ctrl,
                      total_steps, num_fu_inports, num_fu_outports, s.num_tile_inports,
                      s.num_tile_outports, s.num_cgras, s.num_tiles,
                      num_registers_per_reg_bank,
                      FuList = FuList)
              for i in range(s.num_tiles)]

    for i in range(s.num_tiles):
      if i % width == 0 or i // width == 0:
        s.tile[i].to_mem_raddr   //= s.tile_to_mem_raddr[i]
        s.tile[i].from_mem_rdata //= s.tile_from_mem_rdata[i]
        s.tile[i].to_mem_waddr   //= s.tile_to_mem_waddr[i]
        s.tile[i].to_mem_wdata   //= s.tile_to_mem_wdata[i]
      else:
        s.tile[i].to_mem_raddr.rdy   //= 0
        s.tile[i].from_mem_rdata.val //= 0
        s.tile[i].from_mem_rdata.msg //= DataType(0, 0)
        s.tile[i].to_mem_waddr.rdy   //= 0
        s.tile[i].to_mem_wdata.rdy   //= 0

    for i in range(s.num_tiles):

      if i // width > 0:
        s.tile[i].send_data[PORT_SOUTH] //= s.tile[i-width].recv_data[PORT_NORTH]

      if i // width < height - 1:
        s.tile[i].send_data[PORT_NORTH] //= s.tile[i+width].recv_data[PORT_SOUTH]

      if i % width > 0:
        s.tile[i].send_data[PORT_WEST] //= s.tile[i-1].recv_data[PORT_EAST]

      if i % width < width - 1:
        s.tile[i].send_data[PORT_EAST] //= s.tile[i+1].recv_data[PORT_WEST]

      if cgra_topology == "KingMesh":
        if i % width > 0 and i // width < height - 1:
          s.tile[i].send_data[PORT_NORTHWEST] //= s.tile[i+width-1].recv_data[PORT_SOUTHEAST]
          s.tile[i+width-1].send_data[PORT_SOUTHEAST] //= s.tile[i].recv_data[PORT_NORTHWEST]

        if i % width < width - 1 and i // width < height - 1:
          s.tile[i].send_data[PORT_NORTHEAST] //= s.tile[i+width+1].recv_data[PORT_SOUTHWEST]
          s.tile[i+width+1].send_data[PORT_SOUTHWEST] //= s.tile[i].recv_data[PORT_NORTHEAST]

        if i // width == 0:
          s.tile[i].send_data[PORT_SOUTHWEST].rdy //= 0
          s.tile[i].recv_data[PORT_SOUTHWEST].val //= 0
          s.tile[i].recv_data[PORT_SOUTHWEST].msg //= DataType(0, 0)
          s.tile[i].send_data[PORT_SOUTHEAST].rdy //= 0
          s.tile[i].recv_data[PORT_SOUTHEAST].val //= 0
          s.tile[i].recv_data[PORT_SOUTHEAST].msg //= DataType(0, 0)

        if i // width == height - 1:
          s.tile[i].send_data[PORT_NORTHWEST].rdy //= 0
          s.tile[i].recv_data[PORT_NORTHWEST].val //= 0
          s.tile[i].recv_data[PORT_NORTHWEST].msg //= DataType(0, 0)
          s.tile[i].send_data[PORT_NORTHEAST].rdy //= 0
          s.tile[i].recv_data[PORT_NORTHEAST].val //= 0
          s.tile[i].recv_data[PORT_NORTHEAST].msg //= DataType(0, 0)

        if i % width == 0 and i // width > 0:
          s.tile[i].send_data[PORT_SOUTHWEST].rdy //= 0
          s.tile[i].recv_data[PORT_SOUTHWEST].val //= 0
          s.tile[i].recv_data[PORT_SOUTHWEST].msg //= DataType(0, 0)

        if i % width == 0 and i // width < height - 1:
          s.tile[i].send_data[PORT_NORTHWEST].rdy //= 0
          s.tile[i].recv_data[PORT_NORTHWEST].val //= 0
          s.tile[i].recv_data[PORT_NORTHWEST].msg //= DataType(0, 0)

        if i % width == width - 1 and i // width > 0:
          s.tile[i].send_data[PORT_SOUTHEAST].rdy //= 0
          s.tile[i].recv_data[PORT_SOUTHEAST].val //= 0
          s.tile[i].recv_data[PORT_SOUTHEAST].msg //= DataType(0, 0)

        if i % width == width - 1 and i // width < height - 1:
          s.tile[i].send_data[PORT_NORTHEAST].rdy //= 0
          s.tile[i].recv_data[PORT_NORTHEAST].val //= 0
          s.tile[i].recv_data[PORT_NORTHEAST].msg //= DataType(0, 0)


      if i // width == 0:
        s.tile[i].send_data[PORT_SOUTH] //= s.send_data_on_boundary_south[i % width]
        s.tile[i].recv_data[PORT_SOUTH] //= s.recv_data_on_boundary_south[i % width]

      if i // width == height - 1:
        s.tile[i].send_data[PORT_NORTH] //= s.send_data_on_boundary_north[i % width]
        s.tile[i].recv_data[PORT_NORTH] //= s.recv_data_on_boundary_north[i % width]

      if i % width == 0:
        s.tile[i].send_data[PORT_WEST] //= s.send_data_on_boundary_west[i // width]
        s.tile[i].recv_data[PORT_WEST] //= s.recv_data_on_boundary_west[i // width]

      if i % width == width - 1:
        s.tile[i].send_data[PORT_EAST] //= s.send_data_on_boundary_east[i // width]
        s.tile[i].recv_data[PORT_EAST] //= s.recv_data_on_boundary_east[i // width]


  # Line trace
  def line_trace(s):
    res = "||\n".join([(("\n[cgra"+str(s.cgra_id)+"_tile"+str(i)+"]: ") + x.line_trace() + x.ctrl_mem.line_trace())
                       for (i,x) in enumerate(s.tile)])
    res += "\n :: [" + s.ctrl_ring.line_trace() + "]    \n"
    res += "\n :: [" + s.data_mem.line_trace() + "]    \n"
    return res

