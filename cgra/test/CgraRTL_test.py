"""
==========================================================================
CgraRTL_test.py
==========================================================================
Test cases for CGRA with crossbar-based data memory and ring-based control
memory of each tile.

Author : Cheng Tan
  Date : Dec 22, 2024
"""

from pymtl3 import *
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)
from pymtl3.passes.backends.verilog import (VerilogTranslationPass,
                                            VerilogVerilatorImportPass)
from ..CgraRTL import CgraRTL
from ...fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from ...fu.single.AdderRTL import AdderRTL
from ...fu.single.BranchRTL import BranchRTL
from ...fu.single.CompRTL import CompRTL
from ...fu.single.LogicRTL import LogicRTL
from ...fu.single.MemUnitRTL import MemUnitRTL
from ...fu.single.MulRTL import MulRTL
from ...fu.single.PhiRTL import PhiRTL
from ...fu.single.SelRTL import SelRTL
from ...fu.single.ShifterRTL import ShifterRTL
from ...fu.vector.VectorMulComboRTL import VectorMulComboRTL
from ...fu.vector.VectorAdderComboRTL import VectorAdderComboRTL
from ...lib.messages import *
from ...lib.cmd_type import *
from ...lib.opt_type import *
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, DUT, FunctionUnit, FuList, DataType, PredicateType,
                CtrlPktType, CtrlSignalType, NocPktType, CmdType,
                ControllerIdType, controller_id, width, height,
                ctrl_mem_size, data_mem_size_global,
                data_mem_size_per_bank, num_banks_per_cgra,
                src_ctrl_pkt, ctrl_steps, topology, controller2addr_map):

    s.num_tiles = width * height
    s.src_ctrl_pkt = TestSrcRTL(CtrlPktType, src_ctrl_pkt)
    s.dut = DUT(DataType, PredicateType, CtrlPktType, CtrlSignalType,
                NocPktType, CmdType, ControllerIdType, controller_id,
                width, height, ctrl_mem_size, data_mem_size_global,
                data_mem_size_per_bank, num_banks_per_cgra,
                ctrl_steps, ctrl_steps, FunctionUnit, FuList,
                topology, controller2addr_map)

    # Connections
    s.src_ctrl_pkt.send //= s.dut.recv_from_cpu_ctrl_pkt

    s.dut.send_to_noc.rdy //= 0
    s.dut.recv_from_noc.val //= 0
    s.dut.recv_from_noc.msg //= NocPktType(0, 0, 0, 0, 0, 0)

    for tile_col in range(width):
      s.dut.send_data_on_boundary_north[tile_col].rdy //= 0
      s.dut.recv_data_on_boundary_north[tile_col].val //= 0
      s.dut.recv_data_on_boundary_north[tile_col].msg //= DataType()

      s.dut.send_data_on_boundary_south[tile_col].rdy //= 0
      s.dut.recv_data_on_boundary_south[tile_col].val //= 0
      s.dut.recv_data_on_boundary_south[tile_col].msg //= DataType()

    for tile_row in range(height):
      s.dut.send_data_on_boundary_west[tile_row].rdy //= 0
      s.dut.recv_data_on_boundary_west[tile_row].val //= 0
      s.dut.recv_data_on_boundary_west[tile_row].msg //= DataType()

      s.dut.send_data_on_boundary_east[tile_row].rdy //= 0
      s.dut.recv_data_on_boundary_east[tile_row].val //= 0
      s.dut.recv_data_on_boundary_east[tile_row].msg //= DataType()

  def done(s):
    return s.src_ctrl_pkt.done()

  def line_trace(s):
    return s.dut.line_trace()

def init_param(topology, FuList = [MemUnitRTL, AdderRTL]):
  tile_ports = 4
  assert(topology == "Mesh" or topology == "KingMesh")
  if topology == "Mesh":
    tile_ports = 4
  elif topology == "KingMesh":
    tile_ports = 8
  num_tile_inports  = tile_ports
  num_tile_outports = tile_ports
  num_fu_inports = 4
  num_fu_outports = 2
  num_routing_outports = num_tile_outports + num_fu_inports
  ctrl_mem_size = 6
  data_mem_size_global = 512
  data_mem_size_per_bank = 32
  num_banks_per_cgra = 2
  width = 2
  height = 2
  num_terminals = 4
  num_ctrl_actions = 6
  num_ctrl_operations = 64
  TileInType = mk_bits(clog2(num_tile_inports + 1))
  FuInType = mk_bits(clog2(num_fu_inports + 1))
  FuOutType = mk_bits(clog2(num_fu_outports + 1))
  addr_nbits = clog2(data_mem_size_global)
  AddrType = mk_bits(addr_nbits)
  CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
  num_tiles = width * height
  DUT = CgraRTL
  FunctionUnit = FlexibleFuRTL
  DataType = mk_data(32, 1)
  PredicateType = mk_predicate(1, 1)
  
  CmdType = mk_bits(4)
  ControllerIdType = mk_bits(clog2(num_terminals))
  controller_id = 1
  controller2addr_map = {
          0: [0, 3],
          1: [4, 7],
          2: [8, 11],
          3: [12, 15],
  }
  
  CtrlPktType = \
      mk_ring_across_tiles_pkt(width * height,
                               num_ctrl_actions,
                               ctrl_mem_size,
                               num_ctrl_operations,
                               num_fu_inports,
                               num_fu_outports,
                               num_tile_inports,
                               num_tile_outports)
  CtrlSignalType = \
      mk_separate_ctrl(num_ctrl_operations,
                       num_fu_inports,
                       num_fu_outports,
                       num_tile_inports,
                       num_tile_outports)
  
  NocPktType = mk_ring_multi_cgra_pkt(nrouters = num_terminals,
                                      addr_nbits = addr_nbits,
                                      data_nbits = 32,
                                      predicate_nbits = 1)
  pick_register = [FuInType(x + 1) for x in range(num_fu_inports)]
  tile_in_code = [TileInType(max(4 - x, 0)) for x in range(num_routing_outports)]
  fu_out_code  = [FuOutType(x % 2) for x in range(num_routing_outports)]
  src_opt_per_tile = [[
                # src dst vc_id opq cmd_type    addr operation predicate
      CtrlPktType(0,  i,  0,    0,  CMD_CONFIG, 0,   OPT_INC,  b1(0),
                  pick_register, tile_in_code, fu_out_code),
                  # [TileInType(4), TileInType(3), TileInType(2), TileInType(1),
                  #  # TODO: make below as TileInType(5) to double check.
                  #  TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
  
                  # [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                  #  FuOutType(1), FuOutType(1), FuOutType(1), FuOutType(1)]),
      CtrlPktType(0,  i,  0,    0,  CMD_CONFIG, 1,   OPT_INC, b1(0),
                  pick_register, tile_in_code, fu_out_code),
 
      CtrlPktType(0,  i,  0,    0,  CMD_CONFIG, 2,   OPT_ADD, b1(0),
                  pick_register, tile_in_code, fu_out_code),
 
      CtrlPktType(0,  i,  0,    0,  CMD_CONFIG, 3,   OPT_STR, b1(0),
                  pick_register, tile_in_code, fu_out_code),
 
      CtrlPktType(0,  i,  0,    0,  CMD_CONFIG, 4,   OPT_ADD, b1(0),
                  pick_register, tile_in_code, fu_out_code),
 
      CtrlPktType(0,  i,  0,    0,  CMD_CONFIG, 5,   OPT_ADD, b1(0),
                  pick_register, tile_in_code, fu_out_code),
 
      # This last one is for launching kernel.
      CtrlPktType(0,  i,  0,    0,  CMD_LAUNCH, 0,   OPT_ADD, b1(0),
                  pick_register, tile_in_code, fu_out_code)
      ] for i in range(num_tiles)]
  
  src_ctrl_pkt = []
  for opt_per_tile in src_opt_per_tile:
    src_ctrl_pkt.extend(opt_per_tile)

  th = TestHarness(DUT, FunctionUnit, FuList, DataType, PredicateType,
                   CtrlPktType, CtrlSignalType, NocPktType, CmdType,
                   ControllerIdType, controller_id, width, height,
                   ctrl_mem_size, data_mem_size_global,
                   data_mem_size_per_bank, num_banks_per_cgra,
                   src_ctrl_pkt, ctrl_mem_size, topology,
                   controller2addr_map)
  return th

def test_homogeneous_2x2(cmdline_opts):
  topology = "Mesh"
  th = init_param(topology)
  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                      ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                       'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)

def test_heterogeneous_king_mesh_2x2(cmdline_opts):
  topology = "KingMesh"
  th = init_param(topology)
  th.set_param("top.dut.tile[1].construct", FuList=[ShifterRTL])
  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                      ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                       'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)

def test_vector_king_mesh_2x2(cmdline_opts):
  topology = "KingMesh"
  FuList = [AdderRTL,
            MulRTL,
            LogicRTL,
            ShifterRTL,
            PhiRTL,
            CompRTL,
            BranchRTL,
            MemUnitRTL,
            SelRTL,
            VectorMulComboRTL,
            VectorAdderComboRTL]
  th = init_param(topology, FuList)
  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                      ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                       'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)

