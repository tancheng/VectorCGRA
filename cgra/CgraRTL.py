"""
=========================================================================
CgraRTL.py
=========================================================================

Author : Cheng Tan
  Date : Dec 22, 2024
"""
from ..controller.ControllerRTL import ControllerRTL
from ..lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ..lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ..lib.basic.val_rdy.queues import BypassQueueRTL
from ..lib.opt_type import *
from ..lib.util.common import *
from ..mem.data.DataMemWithCrossbarRTL import DataMemWithCrossbarRTL
from ..noc.PyOCN.pymtl3_net.ocnlib.ifcs.positions import mk_ring_pos
from ..noc.PyOCN.pymtl3_net.ringnet.RingNetworkRTL import RingNetworkRTL
from ..tile.TileRTL import TileRTL
from ..cgra.DeSerializeRTL import DeSerializeRTL
from ..cgra.SerializeRTL import SerializeRTL
from ..tile.TileWrapperRTL import TileWrapperRTL

class CgraRTL(Component):

  def construct(s, DataType, PredicateType, CtrlPktType, CgraPayloadType,
                CtrlSignalType, NocPktType, CgraIdType, multi_cgra_rows,
                multi_cgra_columns, width, height,
                ctrl_mem_size, data_mem_size_global,
                data_mem_size_per_bank, num_banks_per_cgra,
                num_registers_per_reg_bank, num_ctrl,
                total_steps, FunctionUnit, FuList, cgra_topology,
                controller2addr_map, idTo2d_map, preload_data = None,
                is_multi_cgra = True):

    # Other topology can simply modify the tiles connections, or
    # leverage the template for modeling.
    assert(cgra_topology == "Mesh" or cgra_topology == "KingMesh")
    s.num_mesh_ports = 4
    if cgra_topology == "Mesh":
      s.num_mesh_ports = 4
    elif cgra_topology == "KingMesh":
      s.num_mesh_ports = 8

    s.num_tiles = width * height
    # The left and bottom tiles are connected to the data memory.
    data_mem_num_rd_tiles = height + width - 1
    data_mem_num_wr_tiles = height + width - 1

    num_cgras = multi_cgra_rows * multi_cgra_columns
    # An additional router for controller to receive CMD_COMPLETE signal from Ring to CPU.
    CtrlRingPos = mk_ring_pos(s.num_tiles + 1)
    CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
    DataAddrType = mk_bits(clog2(data_mem_size_global))
    assert(data_mem_size_per_bank * num_banks_per_cgra <= \
           data_mem_size_global)

    # Interfaces
    s.recv_from_cpu_pkt = RecvIfcRTL(CtrlPktType)
    # s.recv_from_inter_cgra_noc = RecvIfcRTL(NocPktType)
    # s.send_to_inter_cgra_noc = SendIfcRTL(NocPktType)
    s.send_to_cpu_pkt = SendIfcRTL(CtrlPktType)
    SingleBitType = mk_bits(1)
    s.send_to_cpu_pkt__last = OutPort(SingleBitType)

    s.cmd_e_count = Wire( mk_bits(clog2(width * height)) )
    s.cmd_e_valid = Wire( 1 )

    tile_count_sub = width * height - 1
    
    @update
    def comb_logic():
      # Extract cmd from your message structure
      cmd = s.send_to_cpu_pkt.msg.payload.cmd
      # Combined condition
      s.cmd_e_valid @= (cmd == 0xe) & s.send_to_cpu_pkt.val

      # Output assignment
      s.send_to_cpu_pkt__last @= s.cmd_e_valid & (s.cmd_e_count == tile_count_sub)

    @update_ff  
    def counter_logic():
      if s.reset:
        s.cmd_e_count <<= 0
      elif s.cmd_e_valid:
        if s.cmd_e_count == tile_count_sub:
          s.cmd_e_count <<= 0
        else:
          s.cmd_e_count <<= s.cmd_e_count + 1

    # Interfaces on the boundary of the CGRA.
    # s.recv_data_on_boundary_south = [RecvIfcRTL(DataType) for _ in range(width )]
    # s.send_data_on_boundary_south = [SendIfcRTL(DataType) for _ in range(width )]
    # s.recv_data_on_boundary_north = [RecvIfcRTL(DataType) for _ in range(width )]
    # s.send_data_on_boundary_north = [SendIfcRTL(DataType) for _ in range(width )]

    # s.recv_data_on_boundary_east  = [RecvIfcRTL(DataType) for _ in range(height)]
    # s.send_data_on_boundary_east  = [SendIfcRTL(DataType) for _ in range(height)]
    # s.recv_data_on_boundary_west  = [RecvIfcRTL(DataType) for _ in range(height)]
    # s.send_data_on_boundary_west  = [SendIfcRTL(DataType) for _ in range(height)]

    # Components
    # s.tile = [TileRTL(DataType, PredicateType, CtrlPktType,
    #                   CgraPayloadType, CtrlSignalType, ctrl_mem_size,
    #                   data_mem_size_global, num_ctrl,
    #                   total_steps, 4, 2, s.num_mesh_ports,
    #                   s.num_mesh_ports, num_cgras, s.num_tiles,
    #                   num_registers_per_reg_bank,
    #                   FuList = FuList)
    #           for i in range(s.num_tiles)]
    
    # s.cpu_to_controller_deserializer = DeSerializeRTL(CtrlPktType)
    # s.cpu_to_controller_serializer = SerializeRTL(CtrlPktType)
    s.data_mem = DataMemWithCrossbarRTL(NocPktType,
                                        CgraPayloadType,
                                        DataType,
                                        data_mem_size_global,
                                        data_mem_size_per_bank,
                                        num_banks_per_cgra,
                                        data_mem_num_rd_tiles,
                                        data_mem_num_wr_tiles,
                                        multi_cgra_rows,
                                        multi_cgra_columns,
                                        s.num_tiles,
                                        idTo2d_map,
                                        preload_data)
    s.controller = ControllerRTL(CgraIdType, CtrlPktType,
                                 NocPktType, DataType, DataAddrType,
                                 multi_cgra_rows, multi_cgra_columns,
                                 s.num_tiles, controller2addr_map, idTo2d_map)
    # An additional router for controller to receive CMD_COMPLETE signal from Ring to CPU.
    # The last argument of 1 is for the latency per hop.
    s.ctrl_ring = RingNetworkRTL(CtrlPktType, CtrlRingPos, s.num_tiles + 1, 1)
    s.cgra_id = 0

    # Address lower and upper bound.
    s.address_lower = 0
    s.address_upper = controller2addr_map[0][0]

    # Connections
    # Connects the controller id.
    s.controller.cgra_id //= s.cgra_id
    s.data_mem.cgra_id //= s.cgra_id

    # Connects the address lower and upper bound.
    s.data_mem.address_lower //= s.address_lower
    s.data_mem.address_upper //= s.address_upper

    # Connects cpu_to_controller_deserializer Unit with cpu packet
    s.recv_from_cpu_pkt //= s.controller.recv_from_cpu_pkt

    # Connects cpu_to_controller_serializer Unit with cpu packet
    s.controller.send_to_cpu_pkt  //= s.send_to_cpu_pkt

    # Connects data memory with controller.
    s.data_mem.recv_from_noc_load_request //= s.controller.send_to_mem_load_request
    s.data_mem.recv_from_noc_store_request //= s.controller.send_to_mem_store_request
    s.data_mem.recv_from_noc_load_response_pkt //= s.controller.send_to_tile_load_response
    s.data_mem.send_to_noc_load_request_pkt //= s.controller.recv_from_tile_load_request_pkt
    s.data_mem.send_to_noc_load_response_pkt //= s.controller.recv_from_tile_load_response_pkt
    s.data_mem.send_to_noc_store_pkt //= s.controller.recv_from_tile_store_request_pkt

    # if is_multi_cgra:
    #   s.recv_from_inter_cgra_noc //= s.controller.recv_from_inter_cgra_noc
    #   s.send_to_inter_cgra_noc //= s.controller.send_to_inter_cgra_noc
    if not is_multi_cgra:
      s.bypass_queue = BypassQueueRTL(NocPktType, 1)
      s.bypass_queue.send //= s.controller.recv_from_inter_cgra_noc
      s.bypass_queue.recv //= s.controller.send_to_inter_cgra_noc

    # Connects the ctrl interface between CPU and controller.
    # s.recv_from_cpu_pkt //= s.controller.recv_from_cpu_pkt
    # s.send_to_cpu_pkt //=  s.controller.send_to_cpu_pkt

    s.tiles = TileWrapperRTL(CgraIdType, DataType, PredicateType, CtrlPktType,
                      CgraPayloadType, CtrlSignalType, ctrl_mem_size,
                      data_mem_size_global, num_ctrl,
                      total_steps, 4, 2, s.num_mesh_ports,
                      s.num_mesh_ports, num_cgras, s.num_tiles,
                      num_registers_per_reg_bank, width, height, cgra_topology,
                      FuList = FuList)

    

    s.tiles.cgra_id //= s.cgra_id

    # Connects ring with each control memory.
    for i in range(s.num_tiles):
      s.ctrl_ring.send[i] //= s.tiles.tile_recv_from_controller_pkt[i]
    s.ctrl_ring.send[s.num_tiles] //= s.controller.recv_from_ctrl_ring_pkt

    for i in range(s.num_tiles):
      s.ctrl_ring.recv[i] //= s.tiles.tile_send_to_controller_pkt[i]
    s.ctrl_ring.recv[s.num_tiles] //= s.controller.send_to_ctrl_ring_pkt

    for i in range(s.num_tiles):
      if i % width == 0 or i // width == 0:
        s.tiles.tile_to_mem_raddr[i]   //= s.data_mem.recv_raddr[width + i // width - 1 if i >= width else i % width]
        s.tiles.tile_from_mem_rdata[i] //= s.data_mem.send_rdata[width + i // width - 1 if i >= width else i % width]
        s.tiles.tile_to_mem_waddr[i]   //= s.data_mem.recv_waddr[width + i // width - 1 if i >= width else i % width]
        s.tiles.tile_to_mem_wdata[i]   //= s.data_mem.recv_wdata[width + i // width - 1 if i >= width else i % width]

    @update
    def tie_off_boundary_recv_msgs():
      for tile_col in range(width):
        s.tiles.recv_data_on_boundary_north[tile_col].msg @= DataType()
        s.tiles.recv_data_on_boundary_south[tile_col].msg @= DataType()
      
      for tile_row in range(height):
        s.tiles.recv_data_on_boundary_west[tile_row].msg @= DataType()
        s.tiles.recv_data_on_boundary_east[tile_row].msg @= DataType()
    
    for tile_col in range(width):
      s.tiles.send_data_on_boundary_north[tile_col].rdy //= 0
      s.tiles.recv_data_on_boundary_north[tile_col].val //= 0
      s.tiles.send_data_on_boundary_south[tile_col].rdy //= 0
      s.tiles.recv_data_on_boundary_south[tile_col].val //= 0

    for tile_row in range(height):
      s.tiles.send_data_on_boundary_west[tile_row].rdy //= 0
      s.tiles.recv_data_on_boundary_west[tile_row].val //= 0
      s.tiles.send_data_on_boundary_east[tile_row].rdy //= 0
      s.tiles.recv_data_on_boundary_east[tile_row].val //= 0


  # Line trace
  def line_trace(s):
    res = "||\n".join([(("\n[cgra"+str(s.cgra_id)+"_tile"+str(i)+"]: ") + x.line_trace() + x.ctrl_mem.line_trace())
                       for (i,x) in enumerate(s.tile)])
    res += "\n :: [" + s.ctrl_ring.line_trace() + "]    \n"
    res += "\n :: [" + s.data_mem.line_trace() + "]    \n"
    return res
