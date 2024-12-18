"""
=========================================================================
CGRAWithCrossbarDataMemRTL.py
=========================================================================

Author : Cheng Tan
  Date : Dec 13, 2024
"""

from pymtl3 import *
from ..fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from ..fu.single.MemUnitRTL import MemUnitRTL
from ..fu.single.AdderRTL import AdderRTL
from ..lib.util.common import *
from ..lib.basic.en_rdy.ifcs import SendIfcRTL, RecvIfcRTL
from ..lib.basic.val_rdy.ifcs import ValRdySendIfcRTL
from ..lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL
from ..lib.opt_type import *
from ..mem.data.DataMemWithCrossbarRTL import DataMemWithCrossbarRTL
from ..noc.ChannelNormalRTL import ChannelNormalRTL
from ..noc.CrossbarSeparateRTL import CrossbarSeparateRTL
from ..tile.TileSeparateCrossbarRTL import TileSeparateCrossbarRTL
from ..controller.ControllerRTL import ControllerRTL


class CGRAWithCrossbarDataMemRTL(Component):

  def construct(s, DataType, PredicateType, CtrlType, NocPktType,
                CmdType, ControllerIdType, controller_id,
                width, height, ctrl_mem_size, data_mem_size_global,
                data_mem_size_per_bank, num_banks_per_cgra, num_ctrl,
                total_steps, FunctionUnit, FuList, controller2addr_map,
                preload_data = None, preload_const = None):

    s.num_tiles = width * height
    s.num_mesh_ports = 4
    CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
    DataAddrType = mk_bits(clog2(data_mem_size_global))
    assert(data_mem_size_per_bank * num_banks_per_cgra <= \
           data_mem_size_global)

    # Interfaces
    s.recv_waddr = [RecvIfcRTL(CtrlAddrType) for _ in range(s.num_tiles)]
    s.recv_wopt = [RecvIfcRTL(CtrlType) for _ in range(s.num_tiles)]

    # Explicitly provides the ValRdyRecvIfcRTL in the library, as the
    # translation pass sometimes not able to distinguish the
    # EnRdyRecvIfcRTL from it.
    s.recv_from_noc = ValRdyRecvIfcRTL(NocPktType)
    s.send_to_noc = ValRdySendIfcRTL(NocPktType)

    # s.recv_towards_controller = RecvIfcRTL(DataType)
    # s.send_from_controller = SendIfcRTL(DataType)


    # Components
    if preload_const == None:
      preload_const = [[DataType(0, 0)] for _ in range(width*height)]
    s.tile = [TileSeparateCrossbarRTL(DataType, PredicateType, CtrlType,
                                      ctrl_mem_size, data_mem_size_global,
                                      num_ctrl, total_steps, 4, 2, s.num_mesh_ports,
                                      s.num_mesh_ports, const_list = preload_const[i])
                                      for i in range( s.num_tiles)]
    s.data_mem = DataMemWithCrossbarRTL(NocPktType, DataType,
                                        data_mem_size_global,
                                        data_mem_size_per_bank,
                                        num_banks_per_cgra, height, height,
                                        preload_data)
    s.controller = ControllerRTL(ControllerIdType, CmdType, NocPktType,
                                 DataType, DataAddrType, controller_id,
                                 controller2addr_map)

    # Connections

    # Connects data memory with controller.
    # s.data_mem.recv_from_noc //= s.controller.send_to_master
    # s.data_mem.send_to_noc //= s.controller.recv_from_master

    # The last `recv_raddr` is reserved to connect the controller.
    s.data_mem.recv_raddr[height] //= s.controller.send_to_master_load_request_addr
    s.data_mem.recv_waddr[height] //= s.controller.send_to_master_store_request_addr
    s.data_mem.recv_wdata[height] //= s.controller.send_to_master_store_request_data
    # Reserved ...
    s.data_mem.recv_from_noc_rdata //= s.controller.send_to_master_load_response_data
    # Reserved ...
    s.data_mem.send_to_noc_load_request_pkt //= s.controller.recv_from_master_load_request_pkt
    s.data_mem.send_to_noc_load_response_pkt //= s.controller.recv_from_master_load_response_pkt
    s.data_mem.send_to_noc_store_pkt //= s.controller.recv_from_master_store_request_pkt

    s.recv_from_noc //= s.controller.recv_from_noc
    s.send_to_noc //= s.controller.send_to_noc

    # s.recv_towards_controller //= s.controller.recv_from_master
    # s.send_from_controller //= s.controller.send_to_master

    for i in range(s.num_tiles):
      s.recv_waddr[i] //= s.tile[i].recv_waddr
      s.recv_wopt[i] //= s.tile[i].recv_wopt

      if i // width > 0:
        s.tile[i].send_data[PORT_SOUTH] //= s.tile[i-width].recv_data[PORT_NORTH]

      if i // width < height - 1:
        s.tile[i].send_data[PORT_NORTH] //= s.tile[i+width].recv_data[PORT_SOUTH]

      if i % width > 0:
        s.tile[i].send_data[PORT_WEST] //= s.tile[i-1].recv_data[PORT_EAST]

      if i % width < width - 1:
        s.tile[i].send_data[PORT_EAST] //= s.tile[i+1].recv_data[PORT_WEST]

      if i // width == 0:
        s.tile[i].send_data[PORT_SOUTH].rdy //= 0
        s.tile[i].recv_data[PORT_SOUTH].en //= 0
        s.tile[i].recv_data[PORT_SOUTH].msg //= DataType(0, 0)

      if i // width == height - 1:
        s.tile[i].send_data[PORT_NORTH].rdy //= 0
        s.tile[i].recv_data[PORT_NORTH].en //= 0
        s.tile[i].recv_data[PORT_NORTH].msg //= DataType(0, 0)

      if i % width == 0:
        s.tile[i].send_data[PORT_WEST].rdy //= 0
        s.tile[i].recv_data[PORT_WEST].en //= 0
        s.tile[i].recv_data[PORT_WEST].msg //= DataType(0, 0)

      if i % width == width - 1:
        s.tile[i].send_data[PORT_EAST].rdy //= 0
        s.tile[i].recv_data[PORT_EAST].en //= 0
        s.tile[i].recv_data[PORT_EAST].msg //= DataType(0, 0)

      if i % width == 0:
        s.tile[i].to_mem_raddr //= s.data_mem.recv_raddr[i//width]
        s.tile[i].from_mem_rdata //= s.data_mem.send_rdata[i//width]
        s.tile[i].to_mem_waddr //= s.data_mem.recv_waddr[i//width]
        s.tile[i].to_mem_wdata //= s.data_mem.recv_wdata[i//width]
      else:
        s.tile[i].to_mem_raddr.rdy //= 0
        s.tile[i].from_mem_rdata.en //= 0
        s.tile[i].from_mem_rdata.msg //= DataType(0, 0)
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
