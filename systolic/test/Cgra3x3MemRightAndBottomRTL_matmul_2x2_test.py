"""
==========================================================================
Cgra3x3MemRightAndBottomRTL_matmul_2x2_test.py
==========================================================================
Simulation/translation for 3x3 CGRA. The provided test is only used for a
2x2 matmul, but is extendable/scalable to larger test.

Author : Cheng Tan
  Date : Nov 19, 2024
"""

from pymtl3 import *
from pymtl3.passes.backends.verilog import VerilogTranslationPass
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)
from ..CgraSystolicArrayRTL import CgraSystolicArrayRTL
from ...fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from ...fu.single.AdderRTL import AdderRTL
from ...fu.single.BranchRTL import BranchRTL
from ...fu.single.CompRTL import CompRTL
from ...fu.single.LogicRTL import LogicRTL
from ...fu.single.MemUnitRTL import MemUnitRTL
from ...fu.single.MulRTL import MulRTL
from ...fu.single.PhiRTL import PhiRTL
from ...fu.single.SelRTL import SelRTL
from ...fu.double.SeqMulAdderRTL import SeqMulAdderRTL
from ...fu.single.ShifterRTL import ShifterRTL
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ...lib.cmd_type import *
from ...lib.messages import *
from ...lib.opt_type import *

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

kMaxCycles = 100

class TestHarness(Component):
  def construct(s, DUT, FunctionUnit, FuList, DataType, PredicateType,
                CtrlPktType, CtrlSignalType, NocPktType, CmdType,
                ControllerIdType, controller_id, width, height,
                ctrl_mem_size, data_mem_size_global,
                data_mem_size_per_bank, num_banks_per_cgra,
                num_registers_per_reg_bank,
                src_ctrl_pkt, ctrl_steps, controller2addr_map,
                preload_data, preload_const, expected_out):

    s.DataType = DataType
    s.num_tiles = width * height
    s.src_ctrl_pkt = TestSrcRTL(CtrlPktType, src_ctrl_pkt)
    s.expected_out = expected_out

    s.dut = DUT(DataType, PredicateType, CtrlPktType, CtrlSignalType,
                NocPktType, CmdType, ControllerIdType, controller_id,
                width, height, ctrl_mem_size, data_mem_size_global,
                data_mem_size_per_bank, num_banks_per_cgra,
                num_registers_per_reg_bank,
                1, kMaxCycles, FunctionUnit, FuList,
                controller2addr_map, preload_data, preload_const)

    # Connections.
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

  # Checks the output parity.
  def check_parity(s):
    for i in range(len(s.expected_out)):
      for j in range(len(s.expected_out[i])):
        # Outputs are stored in bank 2 and bank 3.
        if s.dut.data_mem.reg_file[2+i].regs[j] != s.expected_out[i][j]:
          return False
    return True

  def done(s):
    return s.check_parity()

  def line_trace(s):
    return s.dut.line_trace()

def run_sim(test_harness, enable_verification_pymtl,
            max_cycles = kMaxCycles):
  # test_harness.elaborate()
  test_harness.apply(DefaultPassGroup())
  # Reset is essential for most simulation, which would initialize
  # many signals. For example, the credit-based virtual channel
  # needs to be initialized with number of supported credits.
  test_harness.sim_reset()

  # Run simulation
  ncycles = 0
  print()
  print("{}:{}".format( ncycles, test_harness.line_trace()))
  if enable_verification_pymtl:
    while not test_harness.done() and ncycles < kMaxCycles:
      test_harness.sim_tick()
      ncycles += 1
      print("----------------------------------------------------")
      print("{}:{}".format( ncycles, test_harness.line_trace()))

    # Checks the output parity.
    assert test_harness.check_parity()

    # Checks timeout.
    assert ncycles < max_cycles
  else:
    while ncycles < max_cycles:
      test_harness.sim_tick()
      ncycles += 1
      print("----------------------------------------------------")
      print("{}:{}".format( ncycles, test_harness.line_trace()))

  test_harness.sim_tick()
  test_harness.sim_tick()
  test_harness.sim_tick()

def test_CGRA_systolic(cmdline_opts):

  tile_ports = 4
  num_tile_inports  = tile_ports
  num_tile_outports = tile_ports
  num_fu_inports = 4
  num_fu_outports = 2
  num_routing_outports = num_tile_outports + num_fu_inports
  # FIXME: Needs to be more than number of ctrl signals.
  # Maybe simplied as max(all_ctrl_across_all_tiles).
  ctrl_mem_size = 8
  data_mem_size_global = 32
  data_mem_size_per_bank = 4
  num_banks_per_cgra = 4
  width = 3
  height = 3
  num_terminals = 1
  num_ctrl_actions = 6
  num_ctrl_operations = 64
  num_registers_per_reg_bank = 16
  TileInType = mk_bits(clog2(num_tile_inports + 1))
  FuInType = mk_bits(clog2(num_fu_inports + 1))
  FuOutType = mk_bits(clog2(num_fu_outports + 1))
  addr_nbits = clog2(data_mem_size_global)
  AddrType = mk_bits(addr_nbits)
  CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
  num_tiles = width * height
  DUT = CgraSystolicArrayRTL
  FunctionUnit = FlexibleFuRTL
  DataType = mk_data(32, 1)
  PredicateType = mk_predicate(1, 1)
  FuList = [SeqMulAdderRTL, AdderRTL, MulRTL, LogicRTL, ShifterRTL, PhiRTL, CompRTL, BranchRTL, MemUnitRTL]

  CmdType = mk_bits(4)
  ControllerIdType = mk_bits(max(clog2(num_terminals), 1))
  controller_id = 0
  controller2addr_map = {
          0: [0,  15],
          1: [16, 31],
  }

  data_nbits = 64
  CtrlPktType = \
      mk_intra_cgra_pkt(width * height,
                        num_ctrl_actions,
                        ctrl_mem_size,
                        num_ctrl_operations,
                        num_fu_inports,
                        num_fu_outports,
                        num_tile_inports,
                        num_tile_outports,
                        num_registers_per_reg_bank,
                        data_nbits)
  CtrlSignalType = \
      mk_separate_reg_ctrl(num_ctrl_operations,
                           num_fu_inports,
                           num_fu_outports,
                           num_tile_inports,
                           num_tile_outports,
                           num_registers_per_reg_bank)

  NocPktType = mk_multi_cgra_noc_pkt(ncols = 1,
                                     nrows = 1,
                                     addr_nbits = addr_nbits,
                                     data_nbits = 32,
                                     predicate_nbits = 1)
  pick_register = [FuInType(x + 1) for x in range(num_fu_inports)]

  src_opt_per_tile = [
      # On tile 0 ([0, 0]).
                 # src dst vc_id opq cmd_type    addr operation     predicate
      [
       CtrlPktType(0,  0,  0,    0,  CMD_CONFIG, 0,   OPT_LD_CONST, b1(0),    pick_register,
                   [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                    TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                   [FuOutType (1), FuOutType (0), FuOutType (0), FuOutType (0),
                    FuOutType (0), FuOutType (0), FuOutType (0), FuOutType (0)]),
       CtrlPktType(0,  0,  0,    0,  CMD_LAUNCH, 0,   OPT_NAH, b1(0),    pick_register,
                   [TileInType(2), TileInType(0), TileInType(0), TileInType(0),
                    TileInType(2), TileInType(0), TileInType(0), TileInType(0)],
                   [FuOutType (0), FuOutType (0), FuOutType (0), FuOutType (0),
                    FuOutType (0), FuOutType (0), FuOutType (0), FuOutType (0)])],

      # On tile 1 ([0, 1]).
                 # src dst vc_id opq cmd_type    addr operation     predicate
      [
       CtrlPktType(0,  1,  0,    0,  CMD_CONFIG, 0,   OPT_LD_CONST, b1(0), pick_register,
                   [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                    TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                   [FuOutType (1), FuOutType (0), FuOutType (0), FuOutType (0),
                    FuOutType (0), FuOutType (0), FuOutType (0), FuOutType (0)]),
       CtrlPktType(0,  1,  0,    0,  CMD_LAUNCH, 0,   OPT_NAH, b1(0),    pick_register,
                   [TileInType(2), TileInType(0), TileInType(0), TileInType(0),
                    TileInType(2), TileInType(0), TileInType(0), TileInType(0)],
                   [FuOutType (0), FuOutType (0), FuOutType (0), FuOutType (0),
                    FuOutType (0), FuOutType (0), FuOutType (0), FuOutType (0)])],

      # On tile 2 ([0, 2]).
      [CtrlPktType(0,  2,  0,    0,  CMD_CONFIG, 0,   OPT_NAH, b1(0), pick_register,
                   [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                    TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                   [FuOutType (0), FuOutType (0), FuOutType (0), FuOutType (0),
                    FuOutType (0), FuOutType (0), FuOutType (0), FuOutType (0)]),
       CtrlPktType(0,  2,  0,    0,  CMD_LAUNCH, 0,   OPT_NAH, b1(0),    pick_register,
                   [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                    TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                   [FuOutType (0), FuOutType (0), FuOutType (0), FuOutType (0),
                    FuOutType (0), FuOutType (0), FuOutType (0), FuOutType (0)])],

      # On tile 3 ([1, 0]).
      [CtrlPktType(0,  3,  0,    0,  CMD_CONFIG, 0,   OPT_MUL_CONST, b1(0), pick_register,
                   [TileInType(2), TileInType(0), TileInType(0), TileInType(0),
                    TileInType(2), TileInType(0), TileInType(0), TileInType(0)],
                   [FuOutType (0), FuOutType (0), FuOutType (0), FuOutType (1),
                    FuOutType (0), FuOutType (0), FuOutType (0), FuOutType (0)]),
       CtrlPktType(0,  3,  0,    0,  CMD_LAUNCH, 0,   OPT_NAH, b1(0),    pick_register,
                   [TileInType(2), TileInType(0), TileInType(0), TileInType(0),
                    TileInType(2), TileInType(0), TileInType(0), TileInType(0)],
                   [FuOutType (0), FuOutType (0), FuOutType (0), FuOutType (0),
                    FuOutType (0), FuOutType (0), FuOutType (0), FuOutType (0)])],

      # On tile 4 ([1, 1]).
      [
       CtrlPktType(0,  4,  0,    0,  CMD_CONFIG, 0,   OPT_MUL_CONST_ADD, b1(0), pick_register,
                   [TileInType(2), TileInType(0), TileInType(0), TileInType(0),
                    TileInType(2), TileInType(0), TileInType(3), TileInType(0)],
                   [FuOutType (0), FuOutType (0), FuOutType (0), FuOutType (1),
                    FuOutType (0), FuOutType (0), FuOutType (0), FuOutType (0)]),
       CtrlPktType(0,  4,  0,    0,  CMD_LAUNCH, 0,   OPT_NAH, b1(0),    pick_register,
                   [TileInType(2), TileInType(0), TileInType(0), TileInType(0),
                    TileInType(2), TileInType(0), TileInType(0), TileInType(0)],
                   [FuOutType (0), FuOutType (0), FuOutType (0), FuOutType (0),
                    FuOutType (0), FuOutType (0), FuOutType (0), FuOutType (0)])],

      # On tile 5 ([1, 2]).
      [
       CtrlPktType(0,  5,  0,    0,  CMD_CONFIG, 0,   OPT_STR_CONST, b1(0), pick_register,
                   [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                    TileInType(3), TileInType(0), TileInType(0), TileInType(0)],
                   [FuOutType (0), FuOutType (0), FuOutType (0), FuOutType (0),
                    FuOutType (0), FuOutType (0), FuOutType (0), FuOutType (0)]),
       CtrlPktType(0,  5,  0,    0,  CMD_LAUNCH, 0,   OPT_NAH, b1(0),    pick_register,
                   [TileInType(2), TileInType(0), TileInType(0), TileInType(0),
                    TileInType(2), TileInType(0), TileInType(0), TileInType(0)],
                   [FuOutType (0), FuOutType (0), FuOutType (0), FuOutType (0),
                    FuOutType (0), FuOutType (0), FuOutType (0), FuOutType (0)])],

      # On tile 6 ([2, 0]).
      [
       CtrlPktType(0,  6,  0,    0,  CMD_CONFIG, 0,   OPT_MUL_CONST, b1(0), pick_register,
                   [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                    TileInType(2), TileInType(0), TileInType(0), TileInType(0)],
                   [FuOutType (0), FuOutType (0), FuOutType (0), FuOutType (1),
                    FuOutType (0), FuOutType (0), FuOutType (0), FuOutType (0)]),
       CtrlPktType(0,  6,  0,    0,  CMD_LAUNCH, 0,   OPT_NAH, b1(0),    pick_register,
                   [TileInType(2), TileInType(0), TileInType(0), TileInType(0),
                    TileInType(2), TileInType(0), TileInType(0), TileInType(0)],
                   [FuOutType (0), FuOutType (0), FuOutType (0), FuOutType (0),
                    FuOutType (0), FuOutType (0), FuOutType (0), FuOutType (0)])],

      # On tile 7 ([2, 1]).
      [
       CtrlPktType(0,  7,  0,    0,  CMD_CONFIG, 0,   OPT_MUL_CONST_ADD, b1(0), pick_register,
                   [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                    TileInType(2), TileInType(0), TileInType(3), TileInType(0)],
                   [FuOutType (0), FuOutType (0), FuOutType (0), FuOutType (1),
                    FuOutType (0), FuOutType (0), FuOutType (0), FuOutType (0)]),
       CtrlPktType(0,  7,  0,    0,  CMD_LAUNCH, 0,   OPT_NAH, b1(0),    pick_register,
                   [TileInType(2), TileInType(0), TileInType(0), TileInType(0),
                    TileInType(2), TileInType(0), TileInType(0), TileInType(0)],
                   [FuOutType (0), FuOutType (0), FuOutType (0), FuOutType (0),
                    FuOutType (0), FuOutType (0), FuOutType (0), FuOutType (0)])],

      # On tile 8 ([2, 2]).
      [
       CtrlPktType(0,  8,  0,    0,  CMD_CONFIG, 0,   OPT_STR_CONST, b1(0), pick_register,
                   [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                    TileInType(3), TileInType(0), TileInType(0), TileInType(0)],
                   [FuOutType (0), FuOutType (0), FuOutType (0), FuOutType (0),
                    FuOutType (0), FuOutType (0), FuOutType (0), FuOutType (0)]),
       CtrlPktType(0,  8,  0,    0,  CMD_LAUNCH, 0,   OPT_NAH, b1(0),    pick_register,
                   [TileInType(2), TileInType(0), TileInType(0), TileInType(0),
                    TileInType(2), TileInType(0), TileInType(0), TileInType(0)],
                   [FuOutType (0), FuOutType (0), FuOutType (0), FuOutType (0),
                    FuOutType (0), FuOutType (0), FuOutType (0), FuOutType (0)])]]
  
  src_ctrl_pkt = []
  for opt_per_tile in src_opt_per_tile:
    src_ctrl_pkt.extend(opt_per_tile)

  test_meta_data = [
     # addr:  0    1    2    3
           [0x1, 0x2, 0x0, 0x0],
     # addr:  4    5    6    7
           [0x3, 0x4, 0x0, 0x0],
     # addr:  8    9   10   11
           [0x0, 0x0, 0x0, 0x0],
     # addr: 12   13   14   15
           [0x0, 0x0, 0x0, 0x0]]

  preload_data_per_bank = [[DataType(test_meta_data[j][i], 1)
                            for i in range(data_mem_size_per_bank)]
                           for j in range(num_banks_per_cgra)]

  preload_const = [
                   # The offset address used for loading input activation.
                   # We use a shared data memory here, indicating global address
                   # space. Users can make each tile has its own address space.

                   # The last one is not useful for the first colum, which is just
                   # to make the length aligned.
                   [DataType(0, 1), DataType(1, 1), DataType(0, 0)],
                   # The first one is not useful for the second colum, which is just
                   # to make the length aligned.
                   # [DataType(0, 0), DataType(4, 1), DataType(5, 1)],
                   [DataType(4, 1), DataType(5, 1), DataType(0, 0)],
                   # The third column is not actually necessary to perform activation
                   # loading nor storing parameters.
                   [DataType(0, 0), DataType(0, 0), DataType(0, 0)],

                   # Preloads weights. 3 items to align with the above const length.
                   # Duplication exists as the iter of the const queue automatically
                   # increment.
                   [DataType(2, 1), DataType(2, 1), DataType(2, 1)],
                   [DataType(4, 1), DataType(4, 1), DataType(4, 1)],
                   # The third column (except the bottom one) is used to store the
                   # accumulated results.
                   [DataType(8, 1), DataType(9, 1), DataType(0, 0)],

                   [DataType(6, 1), DataType(6, 1), DataType(6, 1)],
                   [DataType(8, 1), DataType(8, 1), DataType(8, 1)],
                   # The third column (except the bottom one) is used to store the
                   # accumulated results.
                   [DataType(12, 1), DataType(13, 1), DataType(0, 0)]]

  """
  1 3      2 6     14 20
       x        =
  2 4      4 8     30 44
  """
  expected_out = [[DataType(14, 1), DataType(20, 1)],
                  [DataType(30, 1), DataType(44, 1)]]

  # When the max iterations are larger than the number of control signals,
  # enough ctrl_waddr needs to be provided to make execution (i.e., ctrl
  # read) continue.
  th = TestHarness(DUT, FunctionUnit, FuList, DataType, PredicateType,
                   CtrlPktType, CtrlSignalType, NocPktType, CmdType,
                   ControllerIdType, controller_id, width, height,
                   ctrl_mem_size, data_mem_size_global,
                   data_mem_size_per_bank, num_banks_per_cgra,
                   num_registers_per_reg_bank,
                   src_ctrl_pkt, ctrl_mem_size,
                   controller2addr_map, preload_data_per_bank,
                   preload_const, expected_out)

  th.elaborate()
  th.dut.set_metadata(VerilogTranslationPass.explicit_module_name,
                      f'CgraSystolicArrayRTL')
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])

  enable_verification_pymtl = not (cmdline_opts['test_verilog'] or \
                                   cmdline_opts['dump_vcd'] or \
                                   cmdline_opts['dump_vtb'])
  run_sim(th, enable_verification_pymtl)
