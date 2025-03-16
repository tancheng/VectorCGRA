"""
=========================================================================
CgraTemplateRTL.py
=========================================================================

Author : Cheng Tan
  Date : Dec 30, 2024
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

class CgraTemplateRTL(Component):

  def construct(s, DataType, PredicateType, CtrlPktType, CtrlSignalType,
                NocPktType, CmdType, ControllerIdType, multi_cgra_rows,
                multi_cgra_columns, ctrl_mem_size, data_mem_size_global,
                data_mem_size_per_bank, num_banks_per_cgra,
                num_registers_per_reg_bank, num_ctrl,
                total_steps, FunctionUnit, FuList, TileList, LinkList,
                dataSPM, controller2addr_map, idTo2d_map,
                preload_data = None):

    s.num_mesh_ports = 8
    s.num_tiles = len(TileList)
    CtrlRingPos = mk_ring_pos(s.num_tiles)
    CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
    DataAddrType = mk_bits(clog2(data_mem_size_global))
    assert(data_mem_size_per_bank * num_banks_per_cgra <= \
           data_mem_size_global)

    # Interfaces
    s.recv_from_cpu_pkt = RecvIfcRTL(CtrlPktType)
    s.recv_from_noc = RecvIfcRTL(NocPktType)
    s.send_to_noc = SendIfcRTL(NocPktType)

    # FIXME: Think about how to handle the boundary for the case of
    # multi-cgra modeling.
    # # Interfaces on the boundary of the CGRA.
    # s.recv_data_on_boundary_south = [RecvIfcRTL(DataType) for _ in range(width )]
    # s.send_data_on_boundary_south = [SendIfcRTL(DataType) for _ in range(width )]
    # s.recv_data_on_boundary_north = [RecvIfcRTL(DataType) for _ in range(width )]
    # s.send_data_on_boundary_north = [SendIfcRTL(DataType) for _ in range(width )]

    # s.recv_data_on_boundary_east  = [RecvIfcRTL(DataType) for _ in range(height)]
    # s.send_data_on_boundary_east  = [SendIfcRTL(DataType) for _ in range(height)]
    # s.recv_data_on_boundary_west  = [RecvIfcRTL(DataType) for _ in range(height)]
    # s.send_data_on_boundary_west  = [SendIfcRTL(DataType) for _ in range(height)]

    # Components
    s.tile = [TileRTL(DataType, PredicateType, CtrlPktType,
                      CtrlSignalType, ctrl_mem_size,
                      data_mem_size_global, num_ctrl,
                      total_steps, 4, 2, s.num_mesh_ports,
                      s.num_mesh_ports,
                      num_registers_per_reg_bank,
                      FuList = FuList)
              for i in range(s.num_tiles)]
    # FIXME: Need to enrish data-SPM-related user-controlled parameters, e.g., number of banks.
    s.data_mem = DataMemWithCrossbarRTL(NocPktType, DataType,
                                        data_mem_size_global,
                                        data_mem_size_per_bank,
                                        num_banks_per_cgra,
                                        dataSPM.getNumOfValidReadPorts(),
                                        dataSPM.getNumOfValidWritePorts(),
                                        preload_data)
    s.controller = ControllerRTL(ControllerIdType, CmdType, CtrlPktType,
                                 NocPktType, DataType, DataAddrType,
                                 multi_cgra_rows, multi_cgra_columns,
                                 controller2addr_map, idTo2d_map)
    s.ctrl_ring = RingNetworkRTL(CtrlPktType, CtrlRingPos, s.num_tiles, 1)

    s.controller_id = InPort(ControllerIdType)

    # Connections
    # Connects controller id.
    s.controller.controller_id //= s.controller_id

    # Connects data memory with controller.
    s.data_mem.recv_raddr[dataSPM.getNumOfValidReadPorts()] //= s.controller.send_to_tile_load_request_addr
    s.data_mem.recv_waddr[dataSPM.getNumOfValidWritePorts()] //= s.controller.send_to_tile_store_request_addr
    s.data_mem.recv_wdata[dataSPM.getNumOfValidWritePorts()] //= s.controller.send_to_tile_store_request_data
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
    for i in range(1, s.num_tiles):
      s.ctrl_ring.recv[i].val //= 0
      s.ctrl_ring.recv[i].msg //= CtrlPktType()

    for link in LinkList:

      if link.isFromMem():
        memPort = link.getMemReadPort()
        dstTileIndex = link.dstTile.getIndex(TileList)
        s.data_mem.recv_raddr[memPort] //= s.tile[dstTileIndex].to_mem_raddr
        s.data_mem.send_rdata[memPort] //= s.tile[dstTileIndex].from_mem_rdata

      elif link.isToMem():
        memPort = link.getMemWritePort()
        srcTileIndex = link.srcTile.getIndex(TileList)
        s.tile[srcTileIndex].to_mem_waddr //= s.data_mem.recv_waddr[memPort]
        s.tile[srcTileIndex].to_mem_wdata //= s.data_mem.recv_wdata[memPort]

      else:
        srcTileIndex = link.srcTile.getIndex(TileList)
        dstTileIndex = link.dstTile.getIndex(TileList)
        s.tile[srcTileIndex].send_data[link.srcPort] //= s.tile[dstTileIndex].recv_data[link.dstPort]

    for i in range(s.num_tiles):

      for invalidInPort in TileList[i].getInvalidInPorts():
        s.tile[i].recv_data[invalidInPort].val //= 0
        s.tile[i].recv_data[invalidInPort].msg //= DataType(0, 0)

      for invalidOutPort in TileList[i].getInvalidOutPorts():
        s.tile[i].send_data[invalidOutPort].rdy //= 0

      if not TileList[i].hasFromMem():
        s.tile[i].to_mem_raddr.rdy   //= 0
        s.tile[i].from_mem_rdata.val //= 0
        s.tile[i].from_mem_rdata.msg //= DataType(0, 0)

      if not TileList[i].hasToMem():
        s.tile[i].to_mem_waddr.rdy //= 0
        s.tile[i].to_mem_wdata.rdy //= 0

  # Line trace
  def line_trace(s):
    res = "||\n".join([(("[tile"+str(i)+"]: ") + x.line_trace() + x.ctrl_mem.line_trace())
                       for (i,x) in enumerate(s.tile)])
    res += "\n :: [" + s.data_mem.line_trace() + "]    \n"
    return res

