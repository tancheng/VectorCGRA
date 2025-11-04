"""
=========================================================================
CgraTemplateRTL.py
=========================================================================

Author : Cheng Tan
  Date : Dec 30, 2024
"""
from ..controller.ControllerRTL import ControllerRTL
from ..lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ..lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ..lib.basic.val_rdy.queues import BypassQueueRTL
from ..lib.opt_type import *
from ..lib.util.common import *
from ..mem.data.DataMemControllerRTL import DataMemControllerRTL
from ..noc.PyOCN.pymtl3_net.ocnlib.ifcs.positions import mk_ring_pos
from ..noc.PyOCN.pymtl3_net.ringnet.RingNetworkRTL import RingNetworkRTL
from ..tile.TileRTL import TileRTL
from ..lib.util.data_struct_attr import *
from ..lib.messages import *


class CgraTemplateRTL(Component):

  def construct(s, CgraPayloadType,
                multi_cgra_rows,
                multi_cgra_columns,
                per_cgra_rows, per_cgra_columns,
                ctrl_mem_size, data_mem_size_global,
                data_mem_size_per_bank, num_banks_per_cgra,
                num_registers_per_reg_bank, num_ctrl,
                total_steps, mem_access_is_combinational,
                FunctionUnit, FuList, TileList, LinkList,
                dataSPM, controller2addr_map, idTo2d_map,
                is_multi_cgra = True):

    DataType = CgraPayloadType.get_field_type(kAttrData)
    PredicateType = DataType.get_field_type(kAttrPredicate)
    CtrlSignalType = CgraPayloadType.get_field_type(kAttrCtrl)
    data_bitwidth = DataType.get_field_type(kAttrPayload).nbits

    CgraIdType = mk_cgra_id_type(multi_cgra_columns, multi_cgra_rows)

    # Reconstructs packet types.
    num_tiles = len(TileList)
    # Calculates num_rd_tiles from TileList (number of tiles with read ports).
    num_rd_tiles = dataSPM.getNumOfValidReadPorts()

    CtrlPktType = mk_intra_cgra_pkt(multi_cgra_columns, multi_cgra_rows,
                                    num_tiles, CgraPayloadType)

    NocPktType = mk_inter_cgra_pkt(multi_cgra_columns, multi_cgra_rows,
                                   num_tiles, num_rd_tiles,
                                   CgraPayloadType)

    s.num_mesh_ports = 8
    s.num_tiles = len(TileList)
    num_cgras = multi_cgra_rows * multi_cgra_columns
    # An additional router for controller to receive CMD_COMPLETE signal from Ring to CPU.
    CtrlRingPos = mk_ring_pos(s.num_tiles + 1)
    CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
    DataAddrType = mk_bits(clog2(data_mem_size_global))
    assert(data_mem_size_per_bank * num_banks_per_cgra <= \
           data_mem_size_global)

    # Interfaces
    s.recv_from_cpu_pkt = RecvIfcRTL(CtrlPktType)
    s.send_to_cpu_pkt = SendIfcRTL(CtrlPktType)
    s.recv_from_inter_cgra_noc = RecvIfcRTL(NocPktType)
    s.send_to_inter_cgra_noc = SendIfcRTL(NocPktType)

    if is_multi_cgra:
      s.recv_data_on_boundary_north = [RecvIfcRTL(DataType) for _ in range(per_cgra_columns)]
      s.send_data_on_boundary_north = [SendIfcRTL(DataType) for _ in range(per_cgra_columns)]
      s.recv_data_on_boundary_south = [RecvIfcRTL(DataType) for _ in range(per_cgra_columns)]
      s.send_data_on_boundary_south = [SendIfcRTL(DataType) for _ in range(per_cgra_columns)]
      s.recv_data_on_boundary_west  = [RecvIfcRTL(DataType) for _ in range(per_cgra_rows)]
      s.send_data_on_boundary_west  = [SendIfcRTL(DataType) for _ in range(per_cgra_rows)]
      s.recv_data_on_boundary_east  = [RecvIfcRTL(DataType) for _ in range(per_cgra_rows)]
      s.send_data_on_boundary_east  = [SendIfcRTL(DataType) for _ in range(per_cgra_rows)]

    # Components
    s.tile = [TileRTL(CtrlPktType,
                      ctrl_mem_size,
                      data_mem_size_global, num_ctrl,
                      total_steps, 4, 2, s.num_mesh_ports,
                      s.num_mesh_ports, num_cgras, s.num_tiles,
                      num_registers_per_reg_bank,
                      FuList = FuList)
              for i in range(s.num_tiles)]
    # FIXME: Need to enrish data-SPM-related user-controlled parameters, e.g., number of banks.
    s.data_mem = DataMemControllerRTL(NocPktType,
                                      data_mem_size_global,
                                      data_mem_size_per_bank,
                                      num_banks_per_cgra,
                                      dataSPM.getNumOfValidReadPorts(),
                                      dataSPM.getNumOfValidWritePorts(),
                                      multi_cgra_rows,
                                      multi_cgra_columns,
                                      s.num_tiles,
                                      mem_access_is_combinational,
                                      idTo2d_map)
    s.controller = ControllerRTL(NocPktType,
                                 multi_cgra_rows, multi_cgra_columns,
                                 s.num_tiles, controller2addr_map, idTo2d_map)
    # An additional router for controller to receive CMD_COMPLETE signal from Ring to CPU.
    # The last argument of 1 is for the latency per hop.
    s.ctrl_ring = RingNetworkRTL(CtrlPktType, CtrlRingPos, s.num_tiles + 1, 1)

    s.cgra_id = InPort(CgraIdType)

    # Address lower and upper bound.
    s.address_lower = InPort(DataAddrType)
    s.address_upper = InPort(DataAddrType)

    # Connections
    # Connects controller id.
    s.controller.cgra_id //= s.cgra_id
    s.data_mem.cgra_id //= s.cgra_id

    # Connects the address lower and upper bound.
    s.data_mem.address_lower //= s.address_lower
    s.data_mem.address_upper //= s.address_upper

    # Connects data memory with controller.
    s.data_mem.recv_from_noc_load_request //= s.controller.send_to_mem_load_request
    s.data_mem.recv_from_noc_store_request //= s.controller.send_to_mem_store_request
    s.data_mem.recv_from_noc_load_response_pkt //= s.controller.send_to_tile_load_response
    s.data_mem.send_to_noc_load_request_pkt //= s.controller.recv_from_tile_load_request_pkt
    s.data_mem.send_to_noc_load_response_pkt //= s.controller.recv_from_tile_load_response_pkt
    s.data_mem.send_to_noc_store_pkt //= s.controller.recv_from_tile_store_request_pkt

    if is_multi_cgra:
      s.recv_from_inter_cgra_noc //= s.controller.recv_from_inter_cgra_noc
      s.send_to_inter_cgra_noc //= s.controller.send_to_inter_cgra_noc
    else:
      s.bypass_queue = BypassQueueRTL(NocPktType, 1)
      s.bypass_queue.send //= s.controller.recv_from_inter_cgra_noc
      s.bypass_queue.recv //= s.controller.send_to_inter_cgra_noc

    # Connects the ctrl interface between CPU and controller.
    s.recv_from_cpu_pkt //= s.controller.recv_from_cpu_pkt
    s.send_to_cpu_pkt //= s.controller.send_to_cpu_pkt

    # Assigns tile id.
    for i in range(s.num_tiles):
      s.tile[i].cgra_id //= s.cgra_id
      s.tile[i].tile_id //= i

    # Connects ring with each control memory.
    for i in range(s.num_tiles):
      s.ctrl_ring.send[i] //= s.tile[i].recv_from_controller_pkt
    s.ctrl_ring.send[s.num_tiles] //= s.controller.recv_from_ctrl_ring_pkt

    for i in range(s.num_tiles):
      s.ctrl_ring.recv[i] //= s.tile[i].send_to_controller_pkt
    s.ctrl_ring.recv[s.num_tiles] //= s.controller.send_to_ctrl_ring_pkt

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

    if is_multi_cgra:
      for row in range(per_cgra_rows):
        for col in range(per_cgra_columns):
          tile_id = row * per_cgra_columns + col
          # Only connects if the port is valid
          if row == per_cgra_rows - 1:
            if PORT_NORTH not in TileList[tile_id].getInvalidOutPorts():
              s.tile[tile_id].send_data[PORT_NORTH] //= s.send_data_on_boundary_north[col]
            if PORT_NORTH not in TileList[tile_id].getInvalidInPorts():
              s.tile[tile_id].recv_data[PORT_NORTH] //= s.recv_data_on_boundary_north[col]

          if row == 0:
            if PORT_SOUTH not in TileList[tile_id].getInvalidOutPorts():
              s.tile[tile_id].send_data[PORT_SOUTH] //= s.send_data_on_boundary_south[col]
            if PORT_SOUTH not in TileList[tile_id].getInvalidInPorts():
              s.tile[tile_id].recv_data[PORT_SOUTH] //= s.recv_data_on_boundary_south[col]

          if col == 0:
            if PORT_WEST not in TileList[tile_id].getInvalidOutPorts():
              s.tile[tile_id].send_data[PORT_WEST] //= s.send_data_on_boundary_west[row]
            if PORT_WEST not in TileList[tile_id].getInvalidInPorts():
              s.tile[tile_id].recv_data[PORT_WEST] //= s.recv_data_on_boundary_west[row]

          if col == per_cgra_columns - 1:
            if PORT_EAST not in TileList[tile_id].getInvalidOutPorts():
              s.tile[tile_id].send_data[PORT_EAST] //= s.send_data_on_boundary_east[row]
            if PORT_EAST not in TileList[tile_id].getInvalidInPorts():
              s.tile[tile_id].recv_data[PORT_EAST] //= s.recv_data_on_boundary_east[row]

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

