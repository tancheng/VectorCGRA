"""
==========================================================================
MeshMultiCgraRTL_test.py
==========================================================================
Test cases for multi-CGRA with mesh NoC.

Author : Cheng Tan
  Date : Jan 8, 2024
"""

from pymtl3.passes.backends.verilog import (VerilogVerilatorImportPass)
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)

from ..MeshMultiCgraRTL import MeshMultiCgraRTL
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
from ...fu.vector.VectorAdderComboRTL import VectorAdderComboRTL
from ...fu.vector.VectorMulComboRTL import VectorMulComboRTL
from ...lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ...lib.cmd_type import *
from ...lib.messages import *
from ...lib.opt_type import *


#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):
  def construct(s, DUT, FunctionUnit, FuList, DataType, PredicateType,
                CtrlPktType, CtrlSignalType, NocPktType, CmdType,
                cgra_rows, cgra_columns, width, height, ctrl_mem_size,
                data_mem_size_global, data_mem_size_per_bank,
                num_banks_per_cgra, num_registers_per_reg_bank,
                src_ctrl_pkt, src_query_pkt, ctrl_steps,
                controller2addr_map, expected_sink_out_pkt):

    s.num_terminals = cgra_rows * cgra_columns
    s.num_tiles = width * height

    s.src_ctrl_pkt = TestSrcRTL(CtrlPktType, src_ctrl_pkt)
    s.src_query_pkt = TestSrcRTL(CtrlPktType, src_query_pkt)
    s.expected_sink_out = TestSinkRTL(CtrlPktType, expected_sink_out_pkt)

    s.dut = DUT(DataType, PredicateType, CtrlPktType, CtrlSignalType,
                NocPktType, CmdType, cgra_rows, cgra_columns,
                height, width, ctrl_mem_size, data_mem_size_global,
                data_mem_size_per_bank, num_banks_per_cgra,
                num_registers_per_reg_bank, ctrl_steps, ctrl_steps,
                FunctionUnit, FuList, controller2addr_map)

    # Connections
    s.expected_sink_out.recv //= s.dut.send_to_cpu_pkt

    complete_count_value = \
            sum(1 for pkt in expected_sink_out_pkt \
                if pkt.ctrl_action == CMD_COMPLETE)

    CompleteCountType = mk_bits(clog2(complete_count_value + 1))
    s.complete_count = Wire(CompleteCountType)

    @update
    def conditional_issue_ctrl_or_query():
      s.dut.recv_from_cpu_pkt.val @= s.src_ctrl_pkt.send.val
      s.dut.recv_from_cpu_pkt.msg @= s.src_ctrl_pkt.send.msg
      s.src_ctrl_pkt.send.rdy @= 0
      s.src_query_pkt.send.rdy @= 0
      if (s.complete_count >= complete_count_value) & \
         ~s.src_ctrl_pkt.send.val:
        s.dut.recv_from_cpu_pkt.val @= s.src_query_pkt.send.val
        s.dut.recv_from_cpu_pkt.msg @= s.src_query_pkt.send.msg
        s.src_query_pkt.send.rdy @= s.dut.recv_from_cpu_pkt.rdy
      else:
        s.src_ctrl_pkt.send.rdy @= s.dut.recv_from_cpu_pkt.rdy
  
    @update_ff
    def update_complete_count():
      if s.reset:
        s.complete_count <<= 0
      else:
        if s.expected_sink_out.recv.val & s.expected_sink_out.recv.rdy:
          s.complete_count <<= s.complete_count + CompleteCountType(1)

  def done(s):
    return s.src_ctrl_pkt.done() and s.src_query_pkt.done() and \
           s.expected_sink_out.done()

  def line_trace(s):
    return s.dut.line_trace()

def run_sim(test_harness, max_cycles = 100):
  test_harness.apply(DefaultPassGroup())
  test_harness.sim_reset()

  # Run simulation

  ncycles = 0
  print()
  print("cycle {}:{}".format(ncycles, test_harness.line_trace()))
  while not test_harness.done() and ncycles < max_cycles:
    test_harness.sim_tick()
    ncycles += 1
    print("cycle {}:{}".format(ncycles, test_harness.line_trace()))

  # Check timeout
  assert ncycles < max_cycles

  test_harness.sim_tick()
  test_harness.sim_tick()
  test_harness.sim_tick()

def initialize_test_harness(cmdline_opts):
  num_tile_inports  = 4
  num_tile_outports = 4
  num_fu_inports = 4
  num_fu_outports = 2
  num_routing_outports = num_tile_outports + num_fu_inports
  ctrl_mem_size = 16
  data_mem_size_global = 128
  cgra_rows = 2
  cgra_columns = 2
  num_terminals = cgra_rows * cgra_columns
  num_banks_per_cgra = 2
  data_mem_size_per_bank = data_mem_size_global // num_terminals // num_banks_per_cgra
  x_tiles = 2
  y_tiles = 2
  TileInType = mk_bits(clog2(num_tile_inports + 1))
  FuInType = mk_bits(clog2(num_fu_inports + 1))
  FuOutType = mk_bits(clog2(num_fu_outports + 1))
  ctrl_addr_nbits = clog2(ctrl_mem_size)
  data_addr_nbits = clog2(data_mem_size_global)
  DataAddrType = mk_bits(clog2(data_mem_size_global))
  num_tiles = x_tiles * y_tiles
  DUT = MeshMultiCgraRTL
  FunctionUnit = FlexibleFuRTL
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
  data_nbits = 32
  predicate_nbits = 1
  DataType = mk_data(data_nbits, 1)
  PredicateType = mk_predicate(1, 1)
  cmd_nbits = clog2(NUM_CMDS)
  num_registers_per_reg_bank = 16
  CmdType = mk_bits(cmd_nbits)
  per_cgra_data_size = int(data_mem_size_global / num_terminals)
  controller2addr_map = {}
  for i in range(num_terminals):
    controller2addr_map[i] = [i * per_cgra_data_size,
                              (i + 1) * per_cgra_data_size - 1]
  print("[LOG] controller2addr_map: ", controller2addr_map)

  cmd_nbits = clog2(NUM_CMDS)
  RegIdxType = mk_bits(clog2(num_registers_per_reg_bank))
  CmdType = mk_bits(cmd_nbits)

  cgra_id_nbits = clog2(num_terminals)
  addr_nbits = clog2(data_mem_size_global)
  pickRegister = [FuInType(x + 1) for x in range(num_fu_inports)]
  CtrlPktType = \
        mk_intra_cgra_pkt(num_tiles,
                          cgra_id_nbits,
                          NUM_CMDS,
                          ctrl_mem_size,
                          NUM_OPTS,
                          num_fu_inports,
                          num_fu_outports,
                          num_tile_inports,
                          num_tile_outports,
                          num_registers_per_reg_bank,
                          addr_nbits,
                          data_nbits,
                          predicate_nbits)
  CtrlSignalType = \
      mk_separate_reg_ctrl(NUM_OPTS,
                           num_fu_inports,
                           num_fu_outports,
                           num_tile_inports,
                           num_tile_outports,
                           num_registers_per_reg_bank)
  NocPktType = mk_multi_cgra_noc_pkt(ncols = cgra_columns,
                                     nrows = cgra_rows,
                                     ntiles = num_tiles,
                                     addr_nbits = data_addr_nbits,
                                     data_nbits = data_nbits,
                                     predicate_nbits = predicate_nbits,
                                     ctrl_actions = NUM_CMDS,
                                     ctrl_mem_size = ctrl_mem_size,
                                     ctrl_operations = NUM_OPTS,
                                     ctrl_fu_inports = num_fu_inports,
                                     ctrl_fu_outports = num_fu_outports,
                                     ctrl_tile_inports = num_tile_inports,
                                     ctrl_tile_outports = num_tile_outports)

  '''
  Creates test performing load -> inc -> store on cgra 2. Specifically,
  cgra 2 tile 0 performs `load` on memory address 34, and stores the result (0xfe) in register 7.
  cgra 2 tile 0 read data from register 7 and performs `inc` (0xfe -> 0xff), and sends result to tile 2.
  cgra 2 tile 2 waits for the data from tile 0, and performs stores (0xff) to memory address 3.
  Note that address 34 is in cgra 1's sram bank 0, while address 3 is in cgra 0's sram bank 0,
  therefore, all the memory addresses from cgra 2 are remote.
  '''
  src_ctrl_pkt = \
      [
       # Preloads data.                                            address 34 belongs to cgra 1 (not cgra 0)
       CtrlPktType(2, 0, 0, 0, 0, ctrl_action = CMD_STORE_REQUEST, addr = 34, data = 254, data_predicate = 1),
       # Tile 0.
       # Indicates the load address of 2.
       CtrlPktType(2,      0,  0,  0,    0, ctrl_action = CMD_CONST, data = 34),

                 # cgra_id src dst vc_id opq cmd_type    addr operation predicate
       CtrlPktType(2,      0,  0,  0,    0,  CMD_CONFIG, 0,   OPT_LD_CONST,  b1(0),
                   [FuInType(0), FuInType(0), FuInType(0), FuInType(0)],
                   [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                    TileInType(0), TileInType(0), TileInType(0), TileInType(0)],

                   [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                    # Note that we still need to set FU xbar.
                    FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                   # 2 indicates the FU xbar port (instead of const queue or routing xbar port).
                   ctrl_write_reg_from = [b2(2), b2(0), b2(0), b2(0)],
                   ctrl_write_reg_idx = [RegIdxType(7), RegIdxType(0), RegIdxType(0), RegIdxType(0)]
                  ),

       CtrlPktType(2,      0,  0,  0,    0,  CMD_CONFIG, 1,   OPT_INC,  b1(0),
                   [FuInType(1), FuInType(0), FuInType(0), FuInType(0)],
                   [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                    TileInType(0), TileInType(0), TileInType(0), TileInType(0)],

                   [FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0),
                    FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                   ctrl_read_reg_from = [b1(1), b1(0), b1(0), b1(0)],
                   ctrl_read_reg_idx = [RegIdxType(7), RegIdxType(0), RegIdxType(0), RegIdxType(0)]
                  ),

       # Tile 2. Note that tile 0 and tile 2 can access the memory, as they are on
       # the first column.
       # Indicates the store address of 3.
       CtrlPktType(2,      0,  2,  0,    0, ctrl_action = CMD_CONST, data = 3),

                 # cgra_id src dst vc_id opq cmd_type    addr operation predicate
       CtrlPktType(2,      0,  2,  0,    0,  CMD_CONFIG, 0,   OPT_STR_CONST,  b1(0),
                   [FuInType(1), FuInType(0), FuInType(0), FuInType(0)],
                   [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                    TileInType(2), TileInType(0), TileInType(0), TileInType(0)],

                   [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                    FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)], 0, 0, 0, 0, 0),

       # Pre-configure per-tile total config count.
       CtrlPktType(2,      0,  2,  0,    0,
                   ctrl_action = CMD_CONFIG_TOTAL_CTRL_COUNT,
                   # Only execute one operation (i.e., store) is enough for this tile.
                   # If this is set more than 1, no `COMPLETE` signal would be set back
                   # to CPU/test_harness.
                   data = 1),

       # For launching the two tiles.
       CtrlPktType(2,      0,  0,  0,    0,  CMD_LAUNCH, 0,   OPT_NAH, b1(0),
                   pickRegister,
                   [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                    TileInType(0), TileInType(0), TileInType(0), TileInType(0)],

                   [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                    FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)], 0, 0, 0, 0, 0),
       CtrlPktType(2,      0,  2,  0,    0,  CMD_LAUNCH, 0,   OPT_NAH, b1(0),
                   pickRegister,
                   [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                    TileInType(0), TileInType(0), TileInType(0), TileInType(0)],

                   [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                    FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)], 0, 0, 0, 0, 0),
      ]

  src_query_pkt = \
      [
       CtrlPktType(0, 0, 0, 0, 0, ctrl_action = CMD_LOAD_REQUEST, addr = 34),
       CtrlPktType(0, 0, 0, 0, 0, ctrl_action = CMD_LOAD_REQUEST, addr = 3),
      ]

  # vc_id needs to be 1 due to the message might traverse across the date line via ring.
  expected_sink_out_pkt = \
      [
                 # dst_cgra, src, dst_tile,  opq, vc_id ctrl_action
       CtrlPktType(0,        0,   num_tiles, 0,   0,    ctrl_action = CMD_COMPLETE),
       CtrlPktType(0,        0,   num_tiles, 0,   0,    ctrl_action = CMD_COMPLETE),
                                                                                                         # Expected updated value.
       CtrlPktType(0,        0,   num_tiles, 0,   0,    ctrl_action = CMD_LOAD_RESPONSE, addr = 3,  data = 0xff, data_predicate = 1),
       CtrlPktType(0,        0,   num_tiles, 0,   0,    ctrl_action = CMD_LOAD_RESPONSE, addr = 34, data = 0xfe, data_predicate = 1),
      ]

  # We only needs 2 steps to finish this test.
  ctrl_steps = 2

  th = TestHarness(DUT, FunctionUnit, FuList, DataType, PredicateType, CtrlPktType,
                   CtrlSignalType, NocPktType, CmdType, cgra_rows, cgra_columns,
                   x_tiles, y_tiles, ctrl_mem_size, data_mem_size_global,
                   data_mem_size_per_bank, num_banks_per_cgra,
                   num_registers_per_reg_bank, src_ctrl_pkt, src_query_pkt,
                   ctrl_steps, controller2addr_map, expected_sink_out_pkt)
  return th

def test_sim_homo_2x2_2x2(cmdline_opts):
  th = initialize_test_harness(cmdline_opts)
  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                      ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                       'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)

def test_verilog_homo_2x2_2x2(cmdline_opts):
  th = initialize_test_harness(cmdline_opts)
  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                      ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                       'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  th.apply(DefaultPassGroup())
