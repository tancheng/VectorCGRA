"""
==========================================================================
MeshMultiCgraRTL.py
==========================================================================
Mesh connecting multiple CGRAs, each CGRA contains one controller.

Author : Cheng Tan
  Date : Jan 8, 2025
"""

from pymtl3 import *
from pymtl3.stdlib.primitive import RegisterFile
from ..cgra.CgraRTL import CgraRTL
from ..lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ..lib.opt_type import *
from ..lib.util.common import *
from ..noc.PyOCN.pymtl3_net.ocnlib.ifcs.positions import mk_mesh_pos
from ..noc.PyOCN.pymtl3_net.meshnet.MeshNetworkRTL import MeshNetworkRTL

class MeshMultiCgraRTL(Component):
  def construct(s, CGRADataType, PredicateType, CtrlPktType,
                CtrlSignalType, NocPktType, CmdType, cgra_rows,
                cgra_columns, tile_rows, tile_columns, ctrl_mem_size,
                data_mem_size_global, data_mem_size_per_bank,
                num_banks_per_cgra, num_ctrl, total_steps, FunctionUnit,
                FuList, controller2addr_map, preload_data = None,
                preload_const = None):

    # Constant
    s.num_terminals = cgra_rows * cgra_columns
    idTo2d_map = {}

    # Mesh position takes column as argument first.
    MeshPos = mk_mesh_pos(cgra_columns, cgra_rows)
    s.num_tiles = tile_rows * tile_columns
    CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
    ControllerIdType = mk_bits(clog2(s.num_terminals))

    # Interface
    # Request from/to CPU.
    s.recv_from_cpu_pkt = RecvIfcRTL(CtrlPktType)

    # Components
    for cgra_row in range(cgra_rows):
      for cgra_col in range(cgra_columns):
        idTo2d_map[cgra_row * cgra_columns + cgra_col] = (cgra_col, cgra_row)

    s.cgra = [CgraRTL(CGRADataType, PredicateType, CtrlPktType,
                      CtrlSignalType, NocPktType, CmdType,
                      ControllerIdType, cgra_rows, cgra_columns,
                      terminal_id, tile_columns, tile_rows,
                      ctrl_mem_size, data_mem_size_global,
                      data_mem_size_per_bank, num_banks_per_cgra,
                      num_ctrl, total_steps, FunctionUnit, FuList,
                      "Mesh", controller2addr_map, idTo2d_map,
                      preload_data = None, preload_const = None)
              for terminal_id in range(s.num_terminals)]
    # Latency is 1.
    s.mesh = MeshNetworkRTL(NocPktType, MeshPos, cgra_columns, cgra_rows, 1)

    # Connections
    s.recv_from_cpu_pkt //= s.cgra[0].recv_from_cpu_pkt
    for i in range(s.num_terminals):
      s.mesh.send[i] //= s.cgra[i].recv_from_noc
      s.mesh.recv[i] //= s.cgra[i].send_to_noc

    for i in range(1, s.num_terminals):
      s.cgra[i].recv_from_cpu_pkt.val //= 0
      s.cgra[i].recv_from_cpu_pkt.msg //= CtrlPktType()

    # Connects the tiles on the boundary of each two ajacent CGRAs.
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
            s.cgra[cgra_row * cgra_columns + cgra_col].recv_data_on_boundary_south[tile_col].msg //= CGRADataType()

        if cgra_row == cgra_rows - 1:
          for tile_col in range(tile_columns):
            s.cgra[cgra_row * cgra_columns + cgra_col].send_data_on_boundary_north[tile_col].rdy //= 0
            s.cgra[cgra_row * cgra_columns + cgra_col].recv_data_on_boundary_north[tile_col].val //= 0
            s.cgra[cgra_row * cgra_columns + cgra_col].recv_data_on_boundary_north[tile_col].msg //= CGRADataType()

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
            s.cgra[cgra_row * cgra_columns + cgra_col].recv_data_on_boundary_west[tile_row].msg //= CGRADataType()

        if cgra_col == cgra_columns - 1:
          for tile_row in range(tile_rows):
            s.cgra[cgra_row * cgra_columns + cgra_col].send_data_on_boundary_east[tile_row].rdy //= 0
            s.cgra[cgra_row * cgra_columns + cgra_col].recv_data_on_boundary_east[tile_row].val //= 0
            s.cgra[cgra_row * cgra_columns + cgra_col].recv_data_on_boundary_east[tile_row].msg //= CGRADataType()

  def line_trace(s):
    res = "||\n".join([(("[cgra["+str(i)+"]: ") + x.line_trace())
                       for (i,x) in enumerate(s.cgra)])
    res += " ## mesh: " + s.mesh.line_trace()
    return res

