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
                ControllerIdType, cgra_id, width, height,
                ctrl_mem_size, data_mem_size_global,
                data_mem_size_per_bank, num_banks_per_cgra,
                num_registers_per_reg_bank,
                src_ctrl_pkt, ctrl_steps, topology, controller2addr_map,
                idTo2d_map, complete_signal_sink_out):

    DataAddrType = mk_bits(clog2(data_mem_size_global))
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
    s.dut.controller_id //= cgra_id
    # As we always first issue request pkt from CPU to NoC, 
    # when there is no NoC for single CGRA test, 
    # we have to connect from_noc and to_noc in testbench.
    s.src_ctrl_pkt.send //= s.dut.recv_from_cpu_pkt
    s.dut.send_to_inter_cgra_noc //= s.bypass_queue.recv
    s.bypass_queue.send //= s.dut.recv_from_inter_cgra_noc

    s.complete_signal_sink_out.recv //= s.dut.send_to_cpu_pkt

    # Connects memory address upper and lower bound for each CGRA.
    s.dut.address_lower //= DataAddrType(controller2addr_map[cgra_id][0])
    s.dut.address_upper //= DataAddrType(controller2addr_map[cgra_id][1])

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
    return s.src_ctrl_pkt.done() and s.complete_signal_sink_out.done()

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
  # data_mem_size_global = 4096
  # data_mem_size_per_bank = 32
  # num_banks_per_cgra = 24
  data_mem_size_global = 128
  data_mem_size_per_bank = 16
  num_banks_per_cgra = 2
  num_cgras = 4
  num_ctrl_operations = 64
  num_registers_per_reg_bank = 16
  TileInType = mk_bits(clog2(num_tile_inports + 1))
  FuInType = mk_bits(clog2(num_fu_inports + 1))
  FuOutType = mk_bits(clog2(num_fu_outports + 1))
  addr_nbits = clog2(data_mem_size_global)
  AddrType = mk_bits(addr_nbits)
  CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
  RegIdxType = mk_bits(clog2(num_registers_per_reg_bank))
  num_tiles = x_tiles * y_tiles
  DUT = CgraRTL
  FunctionUnit = FlexibleFuRTL
  DataType = mk_data(data_bitwidth, 1)
  PredicateType = mk_predicate(1, 1)
  
  CmdType = mk_bits(NUM_CMDS)
  ControllerIdType = mk_bits(clog2(num_cgras))
  cgra_id = 0
  per_cgra_data_size = int(data_mem_size_global / num_cgras)
  controller2addr_map = {}
  # 0: [0,    1023]
  # 1: [1024, 2047]
  # 2: [2048, 3071]
  # 3: [3072, 4095]
  for i in range(num_cgras):
    controller2addr_map[i] = [i * per_cgra_data_size,
                              (i + 1) * per_cgra_data_size - 1]
  idTo2d_map = {
          0: [0, 0],
          1: [1, 0],
          2: [2, 0],
          3: [3, 0],
  }

  cgra_id_nbits = clog2(num_cgras)
  addr_nbits = clog2(data_mem_size_global)
  predicate_nbits = 1

  CtrlPktType = \
      mk_intra_cgra_pkt(num_tiles,
                        cgra_id_nbits,
                        NUM_CMDS,
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
  
  NocPktType = mk_multi_cgra_noc_pkt(ncols = num_cgras,
                                     nrows = 1,
                                     ntiles = num_tiles,
                                     addr_nbits = addr_nbits,
                                     data_nbits = data_bitwidth,
                                     predicate_nbits = 1,
                                     ctrl_actions = NUM_CMDS,
                                     ctrl_mem_size = ctrl_mem_size,
                                     ctrl_operations = num_ctrl_operations,
                                     ctrl_fu_inports = num_fu_inports,
                                     ctrl_fu_outports = num_fu_outports,
                                     ctrl_tile_inports = num_tile_inports,
                                     ctrl_tile_outports = num_tile_outports)

  tile_in_code = [TileInType(0) for _ in range(num_routing_outports)]
  fu_in_code = [FuInType(0) for _ in range(num_fu_inports)]
  fu_in_code[0] = FuInType(1)
  fu_out_code = [FuOutType(0) for _ in range(num_routing_outports)]
  fu_out_code[num_tile_inports] = FuOutType(1)
  read_reg_from_code = [b1(0) for _ in range(num_fu_inports)]
  read_reg_from_code[0] = b1(1)
  read_reg_idx_code = [RegIdxType(0) for _ in range(num_fu_inports)]
  read_reg_idx_code[0] = RegIdxType(2)

  '''
  Each tile performs independent INC, without waiting for data from
  neighbours, instead, consuming the data inside their own register
  cluster/file (i.e., `ctrl_read_reg_from`).
  '''
  src_opt_per_tile = [[
      # Pre-configure per-tile total config count. As we only have single `INC` operation,
      # we set it as one, which would trigger `COMPLETE` signal be sent back to CPU.
                # dst_cgra_id src dst opaque vc  ctrl_action ctrl_addr ctrl_operation ctrl_predicate
      CtrlPktType(cgra_id,    0,  i,  0,     0,  ctrl_action = CMD_CONFIG_TOTAL_CTRL_COUNT,
                  # Only execute one operation (i.e., store) is enough for this tile.
                  # If this is set more than 1, no `COMPLETE` signal would be set back
                  # to CPU/test_harness.
                  data = 1),
                # dst_cgra_id src dst opaque vc  ctrl_action ctrl_addr ctrl_operation ctrl_predicate
      CtrlPktType(cgra_id,    0,  i,  0,     0,  CMD_CONFIG, 0,        OPT_INC,       0,
                  # fu_in
                  fu_in_code,
                  # routing_xbar
                  tile_in_code,
                  # Needs a valid output for INC.
                  fu_out_code,
                  # Needs a valid input for INC.
                  ctrl_read_reg_from = read_reg_from_code,
                  ctrl_read_reg_idx = read_reg_idx_code
                  ),
                # dst_cgra_id src dst opaque vc  ctrl_action ctrl_addr ctrl_operation ctrl_predicate
      CtrlPktType(cgra_id,    0,  i,  0,     0,  CMD_LAUNCH, 0,        OPT_NAH,       0,
                  fu_in_code, tile_in_code, fu_out_code)
      ] for i in range(num_tiles)]

  # vc_id needs to be 1 due to the message might traverse across the date line via ring.
  #                                       dst_cgra_id, src, dst,       opq, vc, ctrl_action
  complete_signal_sink_out = [CtrlPktType(0,           0,   num_tiles, 0,   0,  ctrl_action = CMD_COMPLETE) for _ in range(num_tiles)]
  
  src_ctrl_pkt = []
  for opt_per_tile in src_opt_per_tile:
    src_ctrl_pkt.extend(opt_per_tile)

  th = TestHarness(DUT, FunctionUnit, FuList, DataType, PredicateType,
                   CtrlPktType, CtrlSignalType, NocPktType, CmdType,
                   ControllerIdType, cgra_id, x_tiles, y_tiles,
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
  th.set_param("top.dut.tile[1].construct", FuList=[ShifterRTL, AdderRTL])
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

