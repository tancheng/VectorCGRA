"""
==========================================================================
CgraRTL_test.py
==========================================================================
Test cases for CGRA with crossbar-based data memory and ring-based control
memory of each tile.

Author : Cheng Tan
  Date : Dec 22, 2024
"""

from pymtl3.passes.backends.verilog import (VerilogVerilatorImportPass)
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)

from ..CgraRTL import CgraRTL
from ...fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from ...fu.single.AdderRTL import AdderRTL
from ...fu.single.BranchRTL import BranchRTL
from ...fu.single.CompRTL import CompRTL
from ...fu.single.LogicRTL import LogicRTL
from ...fu.single.MemUnitRTL import MemUnitRTL
from ...fu.single.MulRTL import MulRTL
from ...fu.single.PhiRTL import PhiRTL
from ...fu.single.RetRTL import RetRTL
from ...fu.single.SelRTL import SelRTL
from ...fu.single.ShifterRTL import ShifterRTL
from ...fu.vector.VectorAdderComboRTL import VectorAdderComboRTL
from ...fu.vector.VectorMulComboRTL import VectorMulComboRTL
from ...lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ...lib.basic.val_rdy.queues import BypassQueueRTL
from ...lib.cmd_type import *
from ...lib.messages import *
from ...lib.opt_type import *


#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, DUT, FunctionUnit, FuList, DataType, PredicateType,
                CtrlPktType, CtrlSignalType, NocPktType, CmdType,
                ControllerIdType, controller_id, width, height,
                ctrl_mem_size, data_mem_size_global,
                data_mem_size_per_bank, num_banks_per_cgra,
                num_registers_per_reg_bank,
                src_ctrl_pkt, ctrl_steps, topology, controller2addr_map,
                idTo2d_map, complete_signal_sink_out):

    s.num_tiles = width * height
    s.src_ctrl_pkt = TestSrcRTL(CtrlPktType, src_ctrl_pkt)
    s.dut = DUT(DataType, PredicateType, CtrlPktType, CtrlSignalType,
                NocPktType, CmdType, ControllerIdType,
                # CGRA terminals on x/y. Assume in total 4, though this
                # test is for single CGRA.
                1, 4,
                width, height, ctrl_mem_size,
                data_mem_size_global, data_mem_size_per_bank,
                num_banks_per_cgra, num_registers_per_reg_bank,
                ctrl_steps, ctrl_steps, FunctionUnit,
                FuList, topology, controller2addr_map, idTo2d_map)

    # Uses a bypass queue here to enable the verilator simulation.
    # Without bypass queue, the connection will not be translated and
    # recognized.
    s.bypass_queue = BypassQueueRTL(NocPktType, 1)
    s.complete_signal_sink_out = TestSinkRTL(CtrlPktType, complete_signal_sink_out)

    # Connections
    s.dut.controller_id //= controller_id
    # As we always first issue request pkt from CPU to NoC, 
    # when there is no NoC for single CGRA test, 
    # we have to connect from_noc and to_noc in testbench.
    s.src_ctrl_pkt.send //= s.dut.recv_from_cpu_pkt
    s.dut.send_to_noc //= s.bypass_queue.recv
    s.bypass_queue.send //= s.dut.recv_from_noc

    s.complete_signal_sink_out.recv //= s.dut.send_to_cpu_pkt

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

def init_param(topology, FuList = [MemUnitRTL, AdderRTL],
               x_tiles = 2, y_tiles = 2, data_bitwidth = 32):
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
  data_mem_size_global = 4096
  data_mem_size_per_bank = 32
  num_banks_per_cgra = 24
  num_terminals = 4
  num_commands = NUM_CMDS
  num_ctrl_operations = 64
  num_registers_per_reg_bank = 16
  TileInType = mk_bits(clog2(num_tile_inports + 1))
  FuInType = mk_bits(clog2(num_fu_inports + 1))
  FuOutType = mk_bits(clog2(num_fu_outports + 1))
  addr_nbits = clog2(data_mem_size_global)
  AddrType = mk_bits(addr_nbits)
  CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
  num_tiles = x_tiles * y_tiles
  DUT = CgraRTL
  FunctionUnit = FlexibleFuRTL
  DataType = mk_data(data_bitwidth, 1)
  PredicateType = mk_predicate(1, 1)
  
  CmdType = mk_bits(NUM_CMDS)
  ControllerIdType = mk_bits(clog2(num_terminals))
  controller_id = 1
  per_cgra_data_size = int(data_mem_size_global / num_terminals)
  controller2addr_map = {}
  # 0: [0,    1023]
  # 1: [1024, 2047]
  # 2: [2048, 3071]
  # 3: [3072, 4095]
  for i in range(num_terminals):
    controller2addr_map[i] = [i * per_cgra_data_size,
                              (i + 1) * per_cgra_data_size - 1]
  idTo2d_map = {
          0: [0, 0],
          1: [1, 0],
          2: [2, 0],
          3: [3, 0],
  }

  cgra_id_nbits = clog2(num_terminals)
  addr_nbits = clog2(data_mem_size_global)
  predicate_nbits = 1

  CtrlPktType = \
      mk_intra_cgra_pkt(num_tiles,
                        cgra_id_nbits,
                        num_commands,
                        ctrl_mem_size,
                        num_ctrl_operations,
                        num_fu_inports,
                        num_fu_outports,
                        num_tile_inports,
                        num_tile_outports,
                        num_registers_per_reg_bank,
                        addr_nbits,
                        data_bitwidth,
                        predicate_nbits)

  CtrlSignalType = \
      mk_separate_reg_ctrl(num_ctrl_operations,
                           num_fu_inports,
                           num_fu_outports,
                           num_tile_inports,
                           num_tile_outports,
                           num_registers_per_reg_bank)
  
  NocPktType = mk_multi_cgra_noc_pkt(ncols = num_terminals,
                                     nrows = 1,
                                     ntiles = num_tiles,
                                     addr_nbits = addr_nbits,
                                     data_nbits = data_bitwidth,
                                     predicate_nbits = 1,
                                     ctrl_actions = num_commands,
                                     ctrl_mem_size = ctrl_mem_size,
                                     ctrl_operations = num_ctrl_operations,
                                     ctrl_fu_inports = num_fu_inports,
                                     ctrl_fu_outports = num_fu_outports,
                                     ctrl_tile_inports = num_tile_inports,
                                     ctrl_tile_outports = num_tile_outports)

  pick_register = [FuInType(x + 1) for x in range(num_fu_inports)]
  tile_in_code = [TileInType(max(4 - x, 0)) for x in range(num_routing_outports)]
  fu_out_code  = [FuOutType(x % 2) for x in range(num_routing_outports)]
  src_opt_per_tile = [[
                # cgra_id src dst opaque vc  ctrl_action ctrl_addr ctrl_operation ctrl_predicate
      CtrlPktType(0,      0,  i,  0,     0,  CMD_CONFIG, 0,        OPT_INC,       0,
                  # ctrl_fu_in   routing_xbar  fu_xbar      
                  pick_register, tile_in_code, fu_out_code),

      CtrlPktType(0, 0,  i,  0,    0,  CMD_CONFIG, 1, OPT_INC, 0,
                  pick_register, tile_in_code, fu_out_code),
 
      CtrlPktType(0, 0,  i,  0,    0,  CMD_CONFIG, 2, OPT_ADD, 0,
                  pick_register, tile_in_code, fu_out_code),
 
      CtrlPktType(0, 0,  i,  0,    0,  CMD_CONFIG, 3, OPT_STR, 0,
                  pick_register, tile_in_code, fu_out_code),
 
      CtrlPktType(0, 0,  i,  0,    0,  CMD_CONFIG, 4, OPT_ADD, 0,
                  pick_register, tile_in_code, fu_out_code),
 
      CtrlPktType(0, 0,  i,  0,    0,  CMD_CONFIG, 5, OPT_ADD, 0,
                  pick_register, tile_in_code, fu_out_code),
 
      # This last one is for launching kernel.
      CtrlPktType(0, 0,  i,  0,    0,  CMD_LAUNCH, 0, OPT_ADD, 0,
                  pick_register, tile_in_code, fu_out_code)
      ] for i in range(num_tiles)]
  complete_signal_sink_out = [CtrlPktType(0, 0, 0, 0, 0, ctrl_action = CMD_COMPLETE)]
  
  src_ctrl_pkt = []
  for opt_per_tile in src_opt_per_tile:
    src_ctrl_pkt.extend(opt_per_tile)

  th = TestHarness(DUT, FunctionUnit, FuList, DataType, PredicateType,
                   CtrlPktType, CtrlSignalType, NocPktType, CmdType,
                   ControllerIdType, controller_id, x_tiles, y_tiles,
                   ctrl_mem_size, data_mem_size_global,
                   data_mem_size_per_bank, num_banks_per_cgra,
                   num_registers_per_reg_bank,
                   src_ctrl_pkt, ctrl_mem_size, topology,
                   controller2addr_map, idTo2d_map, complete_signal_sink_out)
  return th

def test_homogeneous_2x2(cmdline_opts):
  topology = "Mesh"
  FuList = [AdderRTL,
            MulRTL,
            LogicRTL,
            ShifterRTL,
            PhiRTL,
            CompRTL,
            BranchRTL,
            MemUnitRTL,
            SelRTL,
            RetRTL,
           ]
  th = init_param(topology, FuList)

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
  data_bitwidth = 64
  th = init_param(topology, FuList, data_bitwidth = data_bitwidth)
  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                      ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                       'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)

def test_vector_mesh_4x4(cmdline_opts):
  topology = "Mesh"
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
  data_bitwidth = 32
  th = init_param(topology, FuList, x_tiles = 4, y_tiles = 4,
                  data_bitwidth = data_bitwidth)
  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                      ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                       'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)
