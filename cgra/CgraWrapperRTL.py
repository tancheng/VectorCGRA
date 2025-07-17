"""
=========================================================================
CgraRTL.py
=========================================================================

Author : Cheng Tan
  Date : Dec 22, 2024
"""
from ..cgra.CgraRTL import CgraRTL
from ..lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ..lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ..lib.basic.val_rdy.queues import BypassQueueRTL
from ..lib.opt_type import *
from ..lib.util.common import *
from ..mem.data.DataMemWithCrossbarRTL import DataMemWithCrossbarRTL
from ..noc.PyOCN.pymtl3_net.ocnlib.ifcs.positions import mk_ring_pos
from ..noc.PyOCN.pymtl3_net.ringnet.RingNetworkRTL import RingNetworkRTL
from ..tile.TileRTL import TileRTL


class CgraWrapperRTL(Component):

  def construct(s, DataType, PredicateType, CtrlPktType, CgraPayloadType,
                CtrlSignalType, NocPktType, CgraIdType, multi_cgra_rows,
                multi_cgra_columns, width, height,
                ctrl_mem_size, data_mem_size_global,
                data_mem_size_per_bank, num_banks_per_cgra,
                num_registers_per_reg_bank, num_ctrl,
                total_steps, FunctionUnit, FuList, cgra_topology,
                controller2addr_map, idTo2d_map, preload_data = None,
                is_multi_cgra = True):
    
    DataAddrType = mk_bits(clog2(data_mem_size_global))

    # An additional router for controller to receive CMD_COMPLETE signal from Ring to CPU.
    # The last argument of 1 is for the latency per hop.

    s.cgra = CgraRTL(DataType, PredicateType, CtrlPktType, CgraPayloadType,
                CtrlSignalType, NocPktType, CgraIdType,
                # CGRA terminals on x/y. Assume in total 4, though this
                # test is for single CGRA.
                multi_cgra_rows, multi_cgra_columns,
                width, height, ctrl_mem_size,
                data_mem_size_global, data_mem_size_per_bank,
                num_banks_per_cgra, num_registers_per_reg_bank,
                num_ctrl, total_steps, FunctionUnit,
                FuList, cgra_topology, controller2addr_map, idTo2d_map, preload_data,
                is_multi_cgra)
    
    s.recv_from_cpu_pkt = RecvIfcRTL(CtrlPktType)
    s.recv_from_inter_cgra_noc = RecvIfcRTL(NocPktType)
    s.send_to_inter_cgra_noc = SendIfcRTL(NocPktType)
    s.send_to_cpu_pkt = SendIfcRTL(CtrlPktType)

    if not is_multi_cgra:
      s.cgra.bypass_queue.send //= s.cgra.controller.recv_from_inter_cgra_noc
      s.cgra.bypass_queue.recv //= s.cgra.controller.send_to_inter_cgra_noc

    # s.cgra.recv_from_cpu_pkt //= s.recv_from_cpu_pkt
    # s.cgra.recv_from_inter_cgra_noc //= s.recv_from_inter_cgra_noc
    # s.cgra.send_to_inter_cgra_noc //= s.send_to_inter_cgra_noc
    # s.cgra.send_to_cpu_pkt //= s.send_to_cpu_pkt

    # Address lower and upper bound.
    s.address_lower = InPort(DataAddrType)
    s.address_upper = InPort(DataAddrType)
    # Connects the address lower and upper bound.
    s.cgra.data_mem.address_lower //= s.address_lower
    s.cgra.data_mem.address_upper //= s.address_upper

    # Connects the address lower and upper bound.
    s.cgra.data_mem.address_lower //= s.address_lower
    s.cgra.data_mem.address_upper //= s.address_upper

    if is_multi_cgra:
      s.recv_from_inter_cgra_noc //= s.cgra.controller.recv_from_inter_cgra_noc
      s.send_to_inter_cgra_noc //= s.cgra.controller.send_to_inter_cgra_noc

    # Connects the ctrl interface between CPU and controller.
    s.recv_from_cpu_pkt //= s.cgra.controller.recv_from_cpu_pkt
    s.send_to_cpu_pkt //=  s.cgra.controller.send_to_cpu_pkt

    # TestHarness from CgraRTL_test.py
    for tile_col in range(width):
      s.cgra.send_data_on_boundary_north[tile_col].rdy //= 0
      s.cgra.recv_data_on_boundary_north[tile_col].val //= 0
      s.cgra.recv_data_on_boundary_north[tile_col].msg //= DataType()

      s.cgra.send_data_on_boundary_south[tile_col].rdy //= 0
      s.cgra.recv_data_on_boundary_south[tile_col].val //= 0
      s.cgra.recv_data_on_boundary_south[tile_col].msg //= DataType()

    for tile_row in range(height):
      s.cgra.send_data_on_boundary_west[tile_row].rdy //= 0
      s.cgra.recv_data_on_boundary_west[tile_row].val //= 0
      s.cgra.recv_data_on_boundary_west[tile_row].msg //= DataType()

      s.cgra.send_data_on_boundary_east[tile_row].rdy //= 0
      s.cgra.recv_data_on_boundary_east[tile_row].val //= 0
      s.cgra.recv_data_on_boundary_east[tile_row].msg //= DataType()

  # Line trace
  def line_trace(s):
    res = "||\n".join([(("\n[cgra"+str(s.cgra_id)+"_tile"+str(i)+"]: ") + x.line_trace() + x.ctrl_mem.line_trace())
                       for (i,x) in enumerate(s.tile)])
    res += "\n :: [" + s.ctrl_ring.line_trace() + "]    \n"
    res += "\n :: [" + s.data_mem.line_trace() + "]    \n"
    return res