"""
=========================================================================
CgraRTL.py
=========================================================================

Author : Cheng Tan
  Date : Dec 22, 2024
"""

from pymtl3 import *
from ..controller.ControllerRTL import ControllerRTL
from ..fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from ..fu.single.MemUnitRTL import MemUnitRTL
from ..fu.single.AdderRTL import AdderRTL
from ..lib.util.common import *
from ..lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ..lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ..lib.opt_type import *
from ..mem.data.DataMemWithCrossbarRTL import DataMemWithCrossbarRTL
from ..noc.PyOCN.pymtl3_net.ocnlib.ifcs.positions import mk_ring_pos
from ..noc.PyOCN.pymtl3_net.ringnet.RingNetworkRTL import RingNetworkRTL
from ..tile.TileRTL import TileRTL

class CgraRTL(Component):

  def construct(s, DataType, PredicateType, CtrlPktType, CtrlSignalType,
                NocPktType, CmdType, ControllerIdType, multi_cgra_rows,
                multi_cgra_columns, width, height,
                ctrl_mem_size, data_mem_size_global,
                data_mem_size_per_bank, num_banks_per_cgra,
                num_registers_per_reg_bank, num_ctrl,
                total_steps, FunctionUnit, FuList, cgra_topology,
                controller2addr_map, idTo2d_map, preload_data = None):

    # Other topology can simply modify the tiles connections, or
    # leverage the template for modeling.
    assert(cgra_topology == "Mesh" or cgra_topology == "KingMesh")
    s.num_mesh_ports = 4
    if cgra_topology == "Mesh":
      s.num_mesh_ports = 4
    elif cgra_topology == "KingMesh":
      s.num_mesh_ports = 8

    s.num_tiles = width * height
    CtrlRingPos = mk_ring_pos(s.num_tiles)
    CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
    DataAddrType = mk_bits(clog2(data_mem_size_global))
    assert(data_mem_size_per_bank * num_banks_per_cgra <= \
           data_mem_size_global)

    # Interfaces
    s.recv_from_cpu_pkt = RecvIfcRTL(CtrlPktType)
    s.recv_from_noc = RecvIfcRTL(NocPktType)
    s.send_to_noc = SendIfcRTL(NocPktType)

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
                      CtrlSignalType, ctrl_mem_size,
                      data_mem_size_global, num_ctrl,
                      total_steps, 4, 2, s.num_mesh_ports,
                      s.num_mesh_ports, num_registers_per_reg_bank,
                      FuList = FuList)
              for i in range(s.num_tiles)]
    s.data_mem = DataMemWithCrossbarRTL(NocPktType, DataType,
                                        data_mem_size_global,
                                        data_mem_size_per_bank,
                                        num_banks_per_cgra,
                                        height, height,
                                        preload_data)
    s.controller = ControllerRTL(ControllerIdType, CmdType, CtrlPktType,
                                 NocPktType, DataType, DataAddrType,
                                 multi_cgra_rows, multi_cgra_columns,
                                 controller2addr_map, idTo2d_map)
    s.ctrl_ring = RingNetworkRTL(CtrlPktType, CtrlRingPos, s.num_tiles, 1)
    s.controller_id = InPort(ControllerIdType)

    # Connections
    # Connects the controller id.
    s.controller.controller_id //= s.controller_id

    # Connects data memory with controller.
    s.data_mem.recv_raddr[height] //= s.controller.send_to_tile_load_request_addr
    s.data_mem.recv_waddr[height] //= s.controller.send_to_tile_store_request_addr
    s.data_mem.recv_wdata[height] //= s.controller.send_to_tile_store_request_data
    s.data_mem.recv_from_noc_rdata //= s.controller.send_to_tile_load_response_data
    s.data_mem.send_to_noc_load_request_pkt //= s.controller.recv_from_tile_load_request_pkt
    s.data_mem.send_to_noc_load_response_pkt //= s.controller.recv_from_tile_load_response_pkt
    s.data_mem.send_to_noc_store_pkt //= s.controller.recv_from_tile_store_request_pkt

    s.recv_from_noc //= s.controller.recv_from_noc
    s.send_to_noc //= s.controller.send_to_noc

    # Connects the ctrl interface between CPU and controller.
    s.recv_from_cpu_pkt //= s.controller.recv_from_cpu_pkt

    # Connects ring with each control memory.
    for i in range(s.num_tiles):
      s.ctrl_ring.send[i] //= s.tile[i].recv_ctrl_pkt

    s.ctrl_ring.recv[0] //= s.controller.send_to_ctrl_ring_ctrl_pkt
    for i in range(1, s.num_tiles + 1):
      s.ctrl_ring.recv[i].val //= s.tile[i-1].send_pkt.val
      s.ctrl_ring.recv[i].msg //= s.tile[i-1].send_pkt.msg

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
          s.tile[i].recv_data[PORT_SOUTHWEST].msg //= DataType( 0, 0 )
          s.tile[i].send_data[PORT_SOUTHEAST].rdy //= 0
          s.tile[i].recv_data[PORT_SOUTHEAST].val //= 0
          s.tile[i].recv_data[PORT_SOUTHEAST].msg //= DataType( 0, 0 )

        if i // width == height - 1:
          s.tile[i].send_data[PORT_NORTHWEST].rdy //= 0
          s.tile[i].recv_data[PORT_NORTHWEST].val //= 0
          s.tile[i].recv_data[PORT_NORTHWEST].msg //= DataType( 0, 0 )
          s.tile[i].send_data[PORT_NORTHEAST].rdy //= 0
          s.tile[i].recv_data[PORT_NORTHEAST].val //= 0
          s.tile[i].recv_data[PORT_NORTHEAST].msg //= DataType( 0, 0 )

        if i % width == 0 and i // width > 0:
          s.tile[i].send_data[PORT_SOUTHWEST].rdy //= 0
          s.tile[i].recv_data[PORT_SOUTHWEST].val //= 0
          s.tile[i].recv_data[PORT_SOUTHWEST].msg //= DataType( 0, 0 )

        if i % width == 0 and i // width < height - 1:
          s.tile[i].send_data[PORT_NORTHWEST].rdy //= 0
          s.tile[i].recv_data[PORT_NORTHWEST].val //= 0
          s.tile[i].recv_data[PORT_NORTHWEST].msg //= DataType( 0, 0 )

        if i % width == width - 1 and i // width > 0:
          s.tile[i].send_data[PORT_SOUTHEAST].rdy //= 0
          s.tile[i].recv_data[PORT_SOUTHEAST].val //= 0
          s.tile[i].recv_data[PORT_SOUTHEAST].msg //= DataType( 0, 0 )

        if i % width == width - 1 and i // width < height - 1:
          s.tile[i].send_data[PORT_NORTHEAST].rdy //= 0
          s.tile[i].recv_data[PORT_NORTHEAST].val //= 0
          s.tile[i].recv_data[PORT_NORTHEAST].msg //= DataType( 0, 0 )


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

      if i % width == 0:
        s.tile[i].to_mem_raddr   //= s.data_mem.recv_raddr[i//width]
        s.tile[i].from_mem_rdata //= s.data_mem.send_rdata[i//width]
        s.tile[i].to_mem_waddr   //= s.data_mem.recv_waddr[i//width]
        s.tile[i].to_mem_wdata   //= s.data_mem.recv_wdata[i//width]
      else:
        s.tile[i].to_mem_raddr.rdy   //= 0
        s.tile[i].from_mem_rdata.val //= 0
        s.tile[i].from_mem_rdata.msg //= DataType(0, 0)
        s.tile[i].to_mem_waddr.rdy   //= 0
        s.tile[i].to_mem_wdata.rdy   //= 0

  # Line trace
  def line_trace(s):
    res = "||\n".join([(("[tile"+str(i)+"]: ") + x.line_trace() + x.ctrl_mem.line_trace())
                       for (i,x) in enumerate(s.tile)])
    res += "\n :: [" + s.ctrl_ring.line_trace() + "]    \n"
    res += "\n :: [" + s.data_mem.line_trace() + "]    \n"
    return res

