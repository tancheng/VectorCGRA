"""
==========================================================================
MeshMultiCgraRTL.py
==========================================================================
Mesh connecting multiple CGRAs, each CGRA contains one controller.

Author : Cheng Tan
  Date : Jan 8, 2025
"""

from ..cgra.CgraRTL import CgraRTL
from ..lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ..lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ..lib.opt_type import *
from ..noc.PyOCN.pymtl3_net.meshnet.MeshNetworkRTL import MeshNetworkRTL
from ..noc.PyOCN.pymtl3_net.ocnlib.ifcs.positions import mk_mesh_pos
from ..lib.messages import *
from ..lib.util.data_struct_attr import *

class MeshMultiCgraRTL(Component):

  def construct(s, CgraPayloadType, cgra_rows, cgra_columns,
                tile_rows, tile_columns,
                ctrl_mem_size, data_mem_size_global,
                data_mem_size_per_bank, num_banks_per_cgra,
                num_registers_per_reg_bank,
                num_ctrl, total_steps, 
                mem_access_is_combinational,
                FunctionUnit, FuList, per_cgra_topology,
                controller2addr_map,
                simplified_modeling_for_synthesis = False):

    # Derives all types from CgraPayloadType.
    CgraDataType = CgraPayloadType.get_field_type(kAttrData)
    PredicateType = CgraDataType.get_field_type(kAttrPredicate)
    CtrlSignalType = CgraPayloadType.get_field_type(kAttrCtrl)
    data_nbits = CgraDataType.get_field_type(kAttrPayload).nbits
    
    # Reconstructs packet types.
    num_tiles = tile_rows * tile_columns
    num_rd_tiles = tile_rows + tile_columns - 1
    
    CtrlPktType = mk_intra_cgra_pkt(cgra_columns, cgra_rows,
                                    num_tiles, CgraPayloadType)
    
    NocPktType = mk_inter_cgra_pkt(cgra_columns, cgra_rows,
                                   num_tiles, num_rd_tiles,
                                   CgraPayloadType)
    # Constant
    s.num_cgras = cgra_rows * cgra_columns
    idTo2d_map = {}

    # Mesh position takes column as argument first.
    MeshPos = mk_mesh_pos(cgra_columns, cgra_rows)
    s.num_tiles = tile_rows * tile_columns
    CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
    DataAddrType = mk_bits(clog2(data_mem_size_global))
    ControllerIdType = mk_bits(max(1, clog2(s.num_cgras)))
    has_ctrl_ring = simplified_modeling_for_synthesis ? False : True

    # Interface
    # Request from/to CPU.
    s.recv_from_cpu_pkt = RecvIfcRTL(CtrlPktType)
    s.send_to_cpu_pkt = SendIfcRTL(CtrlPktType)

    # Components
    for cgra_row in range(cgra_rows):
      for cgra_col in range(cgra_columns):
        idTo2d_map[cgra_row * cgra_columns + cgra_col] = (cgra_col, cgra_row)

    s.cgra = [CgraRTL(CgraPayloadType, cgra_rows, cgra_columns,
                      tile_columns, tile_rows,
                      ctrl_mem_size, data_mem_size_global,
                      data_mem_size_per_bank, num_banks_per_cgra,
                      num_registers_per_reg_bank,
                      num_ctrl, total_steps,
                      mem_access_is_combinational,
                      FunctionUnit, FuList, per_cgra_topology,
                      controller2addr_map, idTo2d_map,
                      has_ctrl_ring = has_ctrl_ring)
              for cgra_id in range(s.num_cgras)]

    # Latency is 1.
    s.mesh = MeshNetworkRTL(NocPktType, MeshPos, cgra_columns, cgra_rows, 1)

    # Connections
    for i in range(s.num_cgras):
      s.mesh.send[i] //= s.cgra[i].recv_from_inter_cgra_noc
      s.mesh.recv[i] //= s.cgra[i].send_to_inter_cgra_noc

    # Connects controller id.
    for cgra_id in range(s.num_cgras):
      s.cgra[cgra_id].cgra_id //= cgra_id

    # Connects memory address upper and lower bound for each CGRA.
    for cgra_id in range(s.num_cgras):
      s.cgra[cgra_id].address_lower //= DataAddrType(controller2addr_map[cgra_id][0])
      s.cgra[cgra_id].address_upper //= DataAddrType(controller2addr_map[cgra_id][1])

    s.recv_from_cpu_pkt //= s.cgra[0].recv_from_cpu_pkt
    s.send_to_cpu_pkt //= s.cgra[0].send_to_cpu_pkt

    for i in range(1, s.num_cgras):
      s.cgra[i].recv_from_cpu_pkt.val //= 0
      s.cgra[i].recv_from_cpu_pkt.msg //= CtrlPktType()
      s.cgra[i].send_to_cpu_pkt.rdy //= 0

    # Connects the tiles on the boundary of each two adjacent CGRAs.
    for cgra_row in range(cgra_rows):
      for cgra_col in range(cgra_columns):
        if cgra_row != 0:
          for tile_col in range(tile_columns):
            s.cgra[cgra_row * cgra_columns + cgra_col].send_data_on_boundary_south[tile_col] //= \
                s.cgra[(cgra_row - 1) * cgra_columns + cgra_col].recv_data_on_boundary_north[tile_col]
            s.cgra[cgra_row * cgra_columns + cgra_col].recv_data_on_boundary_south[tile_col] //= \
                s.cgra[(cgra_row - 1) * cgra_columns + cgra_col].send_data_on_boundary_north[tile_col]
        else:
          for tile_col in range(tile_columns):
            s.cgra[cgra_row * cgra_columns + cgra_col].send_data_on_boundary_south[tile_col].rdy //= 0
            s.cgra[cgra_row * cgra_columns + cgra_col].recv_data_on_boundary_south[tile_col].val //= 0
            s.cgra[cgra_row * cgra_columns + cgra_col].recv_data_on_boundary_south[tile_col].msg //= CgraDataType()

        if cgra_row == cgra_rows - 1:
          for tile_col in range(tile_columns):
            s.cgra[cgra_row * cgra_columns + cgra_col].send_data_on_boundary_north[tile_col].rdy //= 0
            s.cgra[cgra_row * cgra_columns + cgra_col].recv_data_on_boundary_north[tile_col].val //= 0
            s.cgra[cgra_row * cgra_columns + cgra_col].recv_data_on_boundary_north[tile_col].msg //= CgraDataType()

        if cgra_col != 0:
          for tile_row in range(tile_rows):
            s.cgra[cgra_row * cgra_columns + cgra_col].send_data_on_boundary_west[tile_row] //= \
                s.cgra[cgra_row * cgra_columns + cgra_col - 1].recv_data_on_boundary_east[tile_row]
            s.cgra[cgra_row * cgra_columns + cgra_col].recv_data_on_boundary_west[tile_row] //= \
                s.cgra[cgra_row * cgra_columns + cgra_col - 1].send_data_on_boundary_east[tile_row]
        else:
          for tile_row in range(tile_rows):
            s.cgra[cgra_row * cgra_columns + cgra_col].send_data_on_boundary_west[tile_row].rdy //= 0
            s.cgra[cgra_row * cgra_columns + cgra_col].recv_data_on_boundary_west[tile_row].val //= 0
            s.cgra[cgra_row * cgra_columns + cgra_col].recv_data_on_boundary_west[tile_row].msg //= CgraDataType()

        if cgra_col == cgra_columns - 1:
          for tile_row in range(tile_rows):
            s.cgra[cgra_row * cgra_columns + cgra_col].send_data_on_boundary_east[tile_row].rdy //= 0
            s.cgra[cgra_row * cgra_columns + cgra_col].recv_data_on_boundary_east[tile_row].val //= 0
            s.cgra[cgra_row * cgra_columns + cgra_col].recv_data_on_boundary_east[tile_row].msg //= CgraDataType()

  def line_trace(s):
    res = "||\n".join([(("\n\n[cgra_"+str(i)+": ") + x.line_trace())
                       for (i,x) in enumerate(s.cgra)])
    res += " ## mesh: " + s.mesh.line_trace()
    return res

