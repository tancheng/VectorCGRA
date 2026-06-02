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

from ..fu.single.PhiRTL import PhiRTL
from ..fu.single.AdderRTL import AdderRTL
from ..fu.single.ShifterRTL import ShifterRTL
from ..fu.single.MemUnitRTL import MemUnitRTL
from ..fu.single.SelRTL import SelRTL
from ..fu.single.CompRTL import CompRTL
from ..fu.double.SeqMulAdderRTL import SeqMulAdderRTL
from ..fu.single.RetRTL import RetRTL
from ..fu.single.MulRTL import MulRTL
from ..fu.single.ExclusiveDivRTL import ExclusiveDivRTL
from ..fu.single.LogicRTL import LogicRTL
from ..fu.single.GrantRTL import GrantRTL
from ..fu.single.LoopControlRTL import LoopControlRTL
from ..fu.single.ConstRTL import ConstRTL
from ..fu.float.FpAddRTL import FpAddRTL
from ..fu.float.FpMulRTL import FpMulRTL

fu_map = {
  "add": AdderRTL,
  "mul": MulRTL,
  "div": ExclusiveDivRTL,
  "fadd": FpAddRTL,
  "fmul": FpMulRTL,
  "fdiv": None,
  "logic": LogicRTL,
  "cmp": CompRTL,
  "sel": SelRTL,
  "type_conv": None,
  "vfmul": None,
  "fadd_fadd": None,
  "fmul_fadd": None,
  "grant": GrantRTL,
  "loop_control": LoopControlRTL,
  "phi": PhiRTL,
  "constant": ConstRTL,
  "mem": MemUnitRTL,
  "return": RetRTL,
  "mem_indexed": MemUnitRTL,
  "alloca": None,
  "shift": ShifterRTL,
}

def map_fu2rtl(fu_type: list[str]):
  fuRTL = list({fu_map[fu] for fu in fu_type})
  fuRTL_new = [fu for fu in fuRTL if fu is not None]
  return fuRTL_new


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
                is_multi_cgra = True, cgra_id = 0,
                provided_max_per_cgra_rows = None,
                provided_max_per_cgra_cols = None,
                provided_max_num_rd_tiles = None,
                provided_max_num_wr_tiles = None,
                has_dma_ports = False):
    """
    provided_max_per_cgra_rows: the row number of the largest cgra in the multi heterogeneous cgra architecture. None for single cgra arch or Homogeneous multi-cgra arch.
    provided_max_per_cgra_cols: the column number of the largest cgra in the multi heterogeneous cgra architecture. None for single cgra arch or Homogeneous multi-cgra arch.
    provided_max_num_rd_tiles: the number of read ports of the largest cgra in the multi heterogeneous cgra architecture. None for single cgra arch or Homogeneous multi-cgra arch.
    provided_max_num_wr_tiles: the number of write ports of the largest cgra in the multi heterogeneous cgra architecture. None for single cgra arch or Homogeneous multi-cgra arch.
    """

    DataType = CgraPayloadType.get_field_type(kAttrData)
    PredicateType = DataType.get_field_type(kAttrPredicate)
    CtrlSignalType = CgraPayloadType.get_field_type(kAttrCtrl)
    data_bitwidth = DataType.get_field_type(kAttrPayload).nbits

    CgraIdType = mk_cgra_id_type(multi_cgra_columns, multi_cgra_rows)

    # Reconstructs packet types.
    # In the case of heterogeneous multi-cgra, `max_num_tiles` means the tile number of the largest cgra.
    # In the case of single cgra, it is the tile number of the current cgra.
    max_per_cgra_rows = provided_max_per_cgra_rows if provided_max_per_cgra_rows is not None else per_cgra_rows
    max_per_cgra_cols = provided_max_per_cgra_cols if provided_max_per_cgra_cols is not None else per_cgra_columns
    max_num_tiles = max_per_cgra_rows * max_per_cgra_cols
    # In the case of heterogeneous multi-cgra, `max_num_rd_tiles` means the number of read ports of the largest cgra.
    # In the case of single cgra, it is the number of read ports of the current cgra.
    max_num_rd_tiles = provided_max_num_rd_tiles if provided_max_num_rd_tiles is not None else dataSPM.getNumOfValidReadPorts()
    max_num_wr_tiles = provided_max_num_wr_tiles if provided_max_num_wr_tiles is not None else dataSPM.getNumOfValidWritePorts()
    

    # Use largest CGRA shape(max_num_tiles) to set CtrlPktType/NocPktType for compatibility.
    CtrlPktType = mk_intra_cgra_pkt(multi_cgra_columns, multi_cgra_rows,
                                    max_num_tiles, CgraPayloadType)

    NocPktType = mk_inter_cgra_pkt(multi_cgra_columns, multi_cgra_rows,
                                   max_num_tiles, max_num_rd_tiles,
                                   CgraPayloadType)

    s.num_mesh_ports = 8
    # tile number of the current cgra.
    s.num_tiles = len(TileList)
    num_cgras = multi_cgra_rows * multi_cgra_columns
    # An additional router for controller to receive CMD_COMPLETE signal from Ring to CPU.
    CtrlRingPos = mk_ring_pos(max_num_tiles + 1)
    CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
    DataAddrType = mk_bits(clog2(data_mem_size_global))
    DmaDataType = DataType.get_field_type(kAttrPayload)
    DmaMaskType = mk_bits(max(1, DmaDataType.nbits // 8))
    assert(data_mem_size_per_bank * num_banks_per_cgra <= \
           data_mem_size_global)

    # Interfaces
    s.recv_from_cpu_pkt = RecvIfcRTL(CtrlPktType)
    s.send_to_cpu_pkt = SendIfcRTL(CtrlPktType)
    s.recv_from_inter_cgra_noc = RecvIfcRTL(NocPktType)
    s.send_to_inter_cgra_noc = SendIfcRTL(NocPktType)

    # Optional DMA interface ports. These are exposed at the template level
    # to allow a top-level wrapper (like CgraDmaRTL) to connect a DMA engine
    # directly to the internal DataMemController.
    if has_dma_ports:
      s.spm_dma_wval  = InPort()
      s.spm_dma_wrdy  = OutPort()
      s.spm_dma_waddr = InPort(DataAddrType)
      s.spm_dma_wdata = InPort(DmaDataType)
      s.spm_dma_wmask = InPort(DmaMaskType)

      s.spm_dma_rval       = InPort()
      s.spm_dma_rrdy       = OutPort()
      s.spm_dma_raddr      = InPort(DataAddrType)
      s.spm_dma_rresp_val  = OutPort()
      s.spm_dma_rresp_rdy  = InPort()
      s.spm_dma_rresp_data = OutPort(DmaDataType)

    if is_multi_cgra:
      # Use the largest CGRA shape to set the boundary ports for compatibility in the case of heterogeneous multi-cgra.
      # Remember to ground the remaining boundary ports of the current CGRA when the current CGRA has fewer rows or columns than the largest CGRA.
      # See also: 
      s.recv_data_on_boundary_north = [RecvIfcRTL(DataType) for _ in range(max_per_cgra_cols)]
      s.send_data_on_boundary_north = [SendIfcRTL(DataType) for _ in range(max_per_cgra_cols)]
      s.recv_data_on_boundary_south = [RecvIfcRTL(DataType) for _ in range(max_per_cgra_cols)]
      s.send_data_on_boundary_south = [SendIfcRTL(DataType) for _ in range(max_per_cgra_cols)]
      s.recv_data_on_boundary_west  = [RecvIfcRTL(DataType) for _ in range(max_per_cgra_rows)]
      s.send_data_on_boundary_west  = [SendIfcRTL(DataType) for _ in range(max_per_cgra_rows)]
      s.recv_data_on_boundary_east  = [RecvIfcRTL(DataType) for _ in range(max_per_cgra_rows)]
      s.send_data_on_boundary_east  = [SendIfcRTL(DataType) for _ in range(max_per_cgra_rows)]

    # Components
    s.tile = [TileRTL(CtrlPktType,
                      ctrl_mem_size,
                      data_mem_size_global, num_ctrl,
                      total_steps, 4, 2, s.num_mesh_ports,
                      s.num_mesh_ports, num_cgras, s.num_tiles,
                      num_registers_per_reg_bank,
                      FuList = map_fu2rtl(TileList[i].getAllValidFuTypes()))
              for i in range(s.num_tiles)]
    # FIXME: Need to enrish data-SPM-related user-controlled parameters, e.g., number of banks.
    s.data_mem = DataMemControllerRTL(NocPktType,
                                      data_mem_size_global,
                                      data_mem_size_per_bank,
                                      num_banks_per_cgra,
                                      max_num_rd_tiles,
                                      max_num_wr_tiles,
                                      multi_cgra_rows,
                                      multi_cgra_columns,
                                      max_num_tiles,
                                      mem_access_is_combinational,
                                      idTo2d_map,
                                      has_dma_ports)
    s.cgra_id = InPort(CgraIdType)
    s.controller = ControllerRTL(NocPktType,
                                  multi_cgra_rows, multi_cgra_columns,
                                  max_num_tiles, controller2addr_map, idTo2d_map)
    # Connects controller id.
    s.controller.cgra_id //= s.cgra_id
    # An additional router for controller to receive CMD_COMPLETE signal from Ring to CPU.
    # The last argument of 1 is for the latency per hop.
    s.ctrl_ring = RingNetworkRTL(CtrlPktType, CtrlRingPos, max_num_tiles + 1, 1)

    # Address lower and upper bound.
    s.address_lower = InPort(DataAddrType)
    s.address_upper = InPort(DataAddrType)

    # Connections data mem cgra ID.
    s.data_mem.cgra_id //= s.cgra_id

    # Connects the address lower and upper bound.
    s.data_mem.address_lower //= s.address_lower
    s.data_mem.address_upper //= s.address_upper

    if has_dma_ports:
      # DMA_MVIN: dram -> dma -> spm
      s.data_mem.spm_dma_wval  //= s.spm_dma_wval
      s.data_mem.spm_dma_wrdy  //= s.spm_dma_wrdy
      s.data_mem.spm_dma_waddr //= s.spm_dma_waddr
      s.data_mem.spm_dma_wdata //= s.spm_dma_wdata
      s.data_mem.spm_dma_wmask //= s.spm_dma_wmask

      # DMA_MVOUT: spm -> dma -> dram
      s.data_mem.spm_dma_rval       //= s.spm_dma_rval
      s.data_mem.spm_dma_rrdy       //= s.spm_dma_rrdy
      s.data_mem.spm_dma_raddr      //= s.spm_dma_raddr
      s.data_mem.spm_dma_rresp_val  //= s.spm_dma_rresp_val
      s.data_mem.spm_dma_rresp_rdy  //= s.spm_dma_rresp_rdy
      s.data_mem.spm_dma_rresp_data //= s.spm_dma_rresp_data

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
      s.ctrl_ring.recv[i] //= s.tile[i].send_to_controller_pkt

    s.ctrl_ring.recv[s.num_tiles] //= s.controller.send_to_ctrl_ring_pkt
    s.ctrl_ring.send[s.num_tiles] //= s.controller.recv_from_ctrl_ring_pkt

    # Grounds the remaining ports of the ring.
    for i in range(s.num_tiles + 1, max_num_tiles + 1):
      s.ctrl_ring.send[i].rdy //= 0
      s.ctrl_ring.recv[i].val //= 0
      s.ctrl_ring.recv[i].msg //= CtrlPktType()

    # Records the tile indices and ports that have been grounded for from_mem and to_mem,
    # to avoid PyMTL3 MultiWriterError.
    recv_data_grounded_for_from_mem = set()
    send_data_rdy_grounded_for_to_mem = set()

    for link in LinkList:

      if link.isFromMem():
        memPort = link.getMemReadPort()
        dstTileIndex = link.dstTile.getIndex(TileList)
        if not link.disabled:
          s.data_mem.recv_raddr[memPort] //= s.tile[dstTileIndex].to_mem_raddr
          s.data_mem.send_rdata[memPort] //= s.tile[dstTileIndex].from_mem_rdata

        # Grounds the generic routing port since it is unused for memory links when in single-CGRA mode.
        # NOTE `recv_data` is used to receive data between multiple CGRAs.
        if not link.disabled and not is_multi_cgra:
            s.tile[dstTileIndex].recv_data[link.dstPort].val //= 0
            s.tile[dstTileIndex].recv_data[link.dstPort].msg //= DataType(0, 0)
            # Records the tile indices and ports that have been grounded.
            recv_data_grounded_for_from_mem.add((dstTileIndex, link.dstPort))

      elif link.isToMem():
        memPort = link.getMemWritePort()
        srcTileIndex = link.srcTile.getIndex(TileList)
        if not link.disabled:
          s.tile[srcTileIndex].to_mem_waddr //= s.data_mem.recv_waddr[memPort]
          s.tile[srcTileIndex].to_mem_wdata //= s.data_mem.recv_wdata[memPort]

        # Grounds the generic routing port ready signal when in single-CGRA mode.
        # NOTE `send_data` is used to send data between multiple CGRAs.
        if not link.disabled and not is_multi_cgra:
            s.tile[srcTileIndex].send_data[link.srcPort].rdy //= 0
            # Records the tile indices and ports that have been grounded.
            send_data_rdy_grounded_for_to_mem.add((srcTileIndex, link.srcPort))

      else:
        srcTileIndex = link.srcTile.getIndex(TileList)
        dstTileIndex = link.dstTile.getIndex(TileList)
        if not link.disabled:
          s.tile[srcTileIndex].send_data[link.srcPort] //= s.tile[dstTileIndex].recv_data[link.dstPort]

    # (cgra_idx_x, cgra_idx_y) is the coordinate of the current cgra in multi-cgra(Cartesian coordinate system).
    """
    ^ y
    |
    |  cgra2   cgra3
    |  cgra0   cgra1
    +---------------> x
    See also https://github.com/tancheng/VectorCGRA/blob/master/doc/figures/multi_cgra_coordinate_and_storage_way.png

    """
    cgra_idx_x = cgra_id % multi_cgra_columns
    cgra_idx_y = cgra_id // multi_cgra_columns

    """
    y   ^
        | tile12  tile13 tile14   tile15
        | tile8   tile9  tile10   tile11
        | tile4   tile5  tile6    tile7
        | tile0   tile1  tile2    tile3
        |--------------------------> x
    
    See also https://github.com/tancheng/VectorCGRA/blob/master/doc/figures/multi_cgra_coordinate_and_storage_way.png  
    """
    if is_multi_cgra:
      for tile_idx_y in range(per_cgra_rows):
        for tile_idx_x in range(per_cgra_columns):
          tile_id = tile_idx_y * per_cgra_columns + tile_idx_x
          # Only connects if the port is valid
          if tile_idx_y == per_cgra_rows - 1:
            if PORT_INDEX_NORTH not in TileList[tile_id].getInvalidOutPorts():
              s.tile[tile_id].send_data[PORT_INDEX_NORTH] //= s.send_data_on_boundary_north[tile_idx_x]
            if PORT_INDEX_NORTH not in TileList[tile_id].getInvalidInPorts():
              s.tile[tile_id].recv_data[PORT_INDEX_NORTH] //= s.recv_data_on_boundary_north[tile_idx_x]

          if tile_idx_y == 0:
            # Corner case: In multi-cgra, for each row of CGRAs except the bottom row,
            # the south port of the bottom row tiles must be connected to the adjacent/south cgra.
            if cgra_idx_y > 0:
              s.tile[tile_id].send_data[PORT_INDEX_SOUTH] //= s.send_data_on_boundary_south[tile_idx_x]
              s.tile[tile_id].recv_data[PORT_INDEX_SOUTH] //= s.recv_data_on_boundary_south[tile_idx_x]
            else: #cgra_idx_y == 0
              # In multi-cgra, for the bottom row CGRAs, the south ports of the bottom row tiles should be grounded.
              s.tile[tile_id].send_data[PORT_INDEX_SOUTH].rdy //= 0
              s.tile[tile_id].recv_data[PORT_INDEX_SOUTH].val //= 0
              s.tile[tile_id].recv_data[PORT_INDEX_SOUTH].msg //= DataType(0, 0)

          if tile_idx_x == 0:
            # Corner case: In multi-cgra, for each column of CGRAs except the first column,
            # the west port of the first column tiles must be connected to the adjacent/west cgra.
            if cgra_idx_x > 0:
              s.tile[tile_id].send_data[PORT_INDEX_WEST] //= s.send_data_on_boundary_west[tile_idx_y]
              s.tile[tile_id].recv_data[PORT_INDEX_WEST] //= s.recv_data_on_boundary_west[tile_idx_y]
            else: #cgra_idx_x == 0
              # In multi-cgra, for the first column CGRAs, the west ports of the first column tiles should be grounded.
              s.tile[tile_id].send_data[PORT_INDEX_WEST].rdy //= 0
              s.tile[tile_id].recv_data[PORT_INDEX_WEST].val //= 0
              s.tile[tile_id].recv_data[PORT_INDEX_WEST].msg //= DataType(0, 0)

          if tile_idx_x == per_cgra_columns - 1:
            if PORT_INDEX_EAST not in TileList[tile_id].getInvalidOutPorts():
              s.tile[tile_id].send_data[PORT_INDEX_EAST] //= s.send_data_on_boundary_east[tile_idx_y]
            if PORT_INDEX_EAST not in TileList[tile_id].getInvalidInPorts():
              s.tile[tile_id].recv_data[PORT_INDEX_EAST] //= s.recv_data_on_boundary_east[tile_idx_y]

    for tile_idx_y in range(per_cgra_rows):
      for tile_idx_x in range(per_cgra_columns):
        i = tile_idx_y * per_cgra_columns + tile_idx_x

        for invalidInPort in TileList[i].getInvalidInPorts():
          """
            Corner case 1:
              When the links between the dataSPM and the leftmost tiles are disabled, the PORT_INDEX_WEST status becomes invalid.
              In this case, if the current CGRA needs to connect to the CGRA on its left, then the recv_data/send_data signals must not be tied to ground.

            Corner case 2:
              When the links between the dataSPM and the bottom tiles are disabled, the PORT_INDEX_SOUTH status becomes invalid.
              In this case, if the current CGRA needs to connect to the CGRA below it, then the recv_data/send_data signals must not be tied to ground.
          """
          skip_multi = (is_multi_cgra and tile_idx_x == 0 and invalidInPort == PORT_INDEX_WEST) or \
              (is_multi_cgra and tile_idx_y == 0 and invalidInPort == PORT_INDEX_SOUTH)
          skip_from_mem_dup = (not is_multi_cgra) and ((i, invalidInPort) in recv_data_grounded_for_from_mem)
          if not skip_multi and not skip_from_mem_dup:
            s.tile[i].recv_data[invalidInPort].val //= 0
            s.tile[i].recv_data[invalidInPort].msg //= DataType(0, 0)

        for invalidOutPort in TileList[i].getInvalidOutPorts():
          skip_multi = (is_multi_cgra and tile_idx_x == 0 and invalidOutPort == PORT_INDEX_WEST) or \
              (is_multi_cgra and tile_idx_y == 0 and invalidOutPort == PORT_INDEX_SOUTH)
          skip_to_mem_dup = (not is_multi_cgra) and ((i, invalidOutPort) in send_data_rdy_grounded_for_to_mem)
          if not skip_multi and not skip_to_mem_dup:
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


