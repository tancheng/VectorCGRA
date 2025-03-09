"""
==========================================================================
RingMultiCgraRTL_test.py
==========================================================================
Test cases for multi-CGRA with ring NoC.

Author : Cheng Tan
  Date : Dec 23, 2024
"""

from pymtl3 import *
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)
from pymtl3.passes.backends.verilog import (VerilogTranslationPass,
                                            VerilogVerilatorImportPass)
from ..RingMultiCgraRTL import RingMultiCgraRTL
from ...fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from ...fu.single.AdderRTL import AdderRTL
from ...fu.single.MemUnitRTL import MemUnitRTL
from ...fu.single.ShifterRTL import ShifterRTL
from ...lib.messages import *
from ...lib.opt_type import *
from ...lib.cmd_type import *
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):
  def construct(s, DUT, FunctionUnit, FuList, DataType, PredicateType,
                CtrlPktType, CtrlSignalType, NocPktType, CmdType,
                cgra_rows, cgra_columns, width, height, ctrl_mem_size,
                data_mem_size_global, data_mem_size_per_bank,
                num_banks_per_cgra, num_registers_per_reg_bank,
                src_ctrl_pkt, ctrl_steps, controller2addr_map):

    s.num_terminals = cgra_rows * cgra_columns
    s.num_tiles = width * height

    s.src_ctrl_pkt = TestSrcRTL(CtrlPktType, src_ctrl_pkt)

    s.dut = DUT(DataType, PredicateType, CtrlPktType, CtrlSignalType,
                NocPktType, CmdType, cgra_rows, cgra_columns, height,
                width, ctrl_mem_size, data_mem_size_global,
                data_mem_size_per_bank, num_banks_per_cgra,
                num_registers_per_reg_bank, ctrl_steps, ctrl_steps,
                FunctionUnit, FuList, controller2addr_map)

    # Connections
    s.src_ctrl_pkt.send //= s.dut.recv_from_cpu_pkt

  def done(s):
    return s.src_ctrl_pkt.done()

  def line_trace(s):
    return s.dut.line_trace()

def test_homo_2x2(cmdline_opts):
  num_tile_inports  = 4
  num_tile_outports = 4
  num_fu_inports = 4
  num_fu_outports = 2
  num_routing_outports = num_tile_outports + num_fu_inports
  ctrl_mem_size = 6
  data_mem_size_global = 32
  data_mem_size_per_bank = 4
  num_banks_per_cgra = 2
  cgra_rows = 2
  cgra_columns = 2
  num_terminals = cgra_rows * cgra_columns
  width = 2
  height = 2
  num_commands = NUM_CMDS
  num_ctrl_operations = NUM_OPTS
  TileInType = mk_bits(clog2(num_tile_inports + 1))
  FuInType = mk_bits(clog2(num_fu_inports + 1))
  FuOutType = mk_bits(clog2(num_fu_outports + 1))
  ctrl_addr_nbits = clog2(ctrl_mem_size)
  # CtrlAddrType = mk_bits(ctrl_addr_nbits)
  data_addr_nbits = clog2(data_mem_size_global)
  DataAddrType = mk_bits(clog2(data_mem_size_global))
  num_tiles = width * height
  DUT = RingMultiCgraRTL
  FunctionUnit = FlexibleFuRTL
  FuList = [MemUnitRTL, AdderRTL]
  data_nbits = 32
  DataType = mk_data(data_nbits, 1)
  PredicateType = mk_predicate(1, 1)
  num_registers_per_reg_bank = 16
  CmdType = NUM_CMDS
  controller2addr_map = {
          0: [0, 7],
          1: [8, 15],
          2: [16, 23],
          3: [24, 31],
  }

  cgra_id_nbits = 2
  data_nbits = 32
  addr_nbits = clog2(data_mem_size_global)
  predicate_nbits = 1

  CtrlPktType = \
        mk_intra_cgra_pkt(width * height,
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
                        data_nbits,
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
                                     ntiles = width * height,
                                     addr_nbits = data_addr_nbits,
                                     data_nbits = 32,
                                     predicate_nbits = 1,
                                     ctrl_actions = num_commands,
                                     ctrl_mem_size = ctrl_mem_size,
                                     ctrl_operations = num_ctrl_operations,
                                     ctrl_fu_inports = num_fu_inports,
                                     ctrl_fu_outports = num_fu_outports,
                                     ctrl_tile_inports = num_tile_inports,
                                     ctrl_tile_outports = num_tile_outports)

  pickRegister = [FuInType(x + 1) for x in range(num_fu_inports)]

  src_opt_per_tile = [[
                # cgra_id src dst vc_id opq cmd_type    addr operation predicate
      CtrlPktType(i,      0,  0,  0,    0,  CMD_CONFIG, 0,   OPT_INC,  b1(0),
                       pickRegister,
                       [TileInType(4), TileInType(3), TileInType(2), TileInType(1),
                        # TODO: make below as TileInType(5) to double check.
                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],

                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                        FuOutType(1), FuOutType(1), FuOutType(1), FuOutType(1)]),
      CtrlPktType(i,      0,  0,  0,    0,  CMD_CONFIG, 1,   OPT_INC, b1(0),
                       pickRegister,
                       [TileInType(4), TileInType(3), TileInType(2), TileInType(1),
                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],

                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                        FuOutType(1), FuOutType(1), FuOutType(1), FuOutType(1)]),

      CtrlPktType(i,      0,  0,  0,    0,  CMD_CONFIG, 2,   OPT_ADD, b1(0),
                       pickRegister,
                       [TileInType(4), TileInType(3), TileInType(2), TileInType(1),
                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],

                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                        FuOutType(1), FuOutType(1), FuOutType(1), FuOutType(1)]),

      CtrlPktType(i,      0,  0,  0,    0,  CMD_CONFIG, 3,   OPT_STR, b1(0),
                       pickRegister,
                       [TileInType(4), TileInType(3), TileInType(2), TileInType(1),
                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],

                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                        FuOutType(1), FuOutType(1), FuOutType(1), FuOutType(1)]),

      CtrlPktType(i,      0,  0,  0,    0,  CMD_CONFIG, 4,   OPT_ADD, b1(0),
                       pickRegister,
                       [TileInType(4), TileInType(3), TileInType(2), TileInType(1),
                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],

                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                        FuOutType(1), FuOutType(1), FuOutType(1), FuOutType(1)]),

      CtrlPktType(i,      0,  0,  0,    0,  CMD_CONFIG, 5,   OPT_ADD, b1(0),
                       pickRegister,
                       [TileInType(4), TileInType(3), TileInType(2), TileInType(1),
                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],

                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                        FuOutType(1), FuOutType(1), FuOutType(1), FuOutType(1)]),

      # This last one is for launching kernel.
      CtrlPktType(i,      0,  0,  0,    0,  CMD_LAUNCH, 0,   OPT_ADD, b1(0),
                       pickRegister,
                       [TileInType(4), TileInType(3), TileInType(2), TileInType(1),
                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],

                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                        FuOutType(1), FuOutType(1), FuOutType(1), FuOutType(1)])
      ] for i in range(num_tiles)]


  src_ctrl_pkt = []
  for opt_per_tile in src_opt_per_tile:
    src_ctrl_pkt.extend(opt_per_tile)

  th = TestHarness(DUT, FunctionUnit, FuList, DataType, PredicateType, CtrlPktType,
                   CtrlSignalType, NocPktType, CmdType, cgra_rows, cgra_columns,
                   width, height, ctrl_mem_size, data_mem_size_global,
                   data_mem_size_per_bank, num_banks_per_cgra,
                   num_registers_per_reg_bank, src_ctrl_pkt,
                   ctrl_mem_size, controller2addr_map)
  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                      ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                       'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts=['max_cycles'], duts = ['dut'])
  run_sim(th)

