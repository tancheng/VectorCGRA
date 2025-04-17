"""
==========================================================================
MeshMultiCgraRTL_test.py
==========================================================================
Test cases for multi-CGRA with mesh NoC.

Author : Cheng Tan
  Date : Jan 8, 2024
"""

from re import sub
from pymtl3.passes.backends.verilog import (
  VerilogVerilatorImportPass,
  VerilogPlaceholderPass,
)
from pymtl3.passes.backends.verilog.translation.VerilogTranslationPass import VerilogTranslationPass
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)

from ..MeshMultiCgraRTL import MeshMultiCgraRTL
from ...fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from ...fu.double.SeqMulAdderRTL import SeqMulAdderRTL
from ...fu.double.PrlMulAdderRTL import PrlMulAdderRTL
from ...fu.float.FpAddRTL import FpAddRTL
from ...fu.float.FpMulRTL import FpMulRTL
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
                IntraCgraPktType, CgraPayloadType, CtrlSignalType, NocPktType,
                cgra_rows, cgra_columns, width, height, ctrl_mem_size,
                data_mem_size_global, data_mem_size_per_bank,
                num_banks_per_cgra, num_registers_per_reg_bank,
                src_ctrl_pkt, src_query_pkt, ctrl_steps,
                controller2addr_map, expected_sink_out_pkt):

    s.num_terminals = cgra_rows * cgra_columns
    s.num_tiles = width * height

    s.src_ctrl_pkt = TestSrcRTL(IntraCgraPktType, src_ctrl_pkt)
    s.src_query_pkt = TestSrcRTL(IntraCgraPktType, src_query_pkt)

    cmp_fn = lambda a, b : a.payload.data == b.payload.data and a.payload.cmd == b.payload.cmd
    s.expected_sink_out = TestSinkRTL(IntraCgraPktType, expected_sink_out_pkt, cmp_fn = cmp_fn)

    s.dut = DUT(DataType, PredicateType, IntraCgraPktType, CgraPayloadType,
                CtrlSignalType, NocPktType, cgra_rows, cgra_columns,
                height, width, ctrl_mem_size, data_mem_size_global,
                data_mem_size_per_bank, num_banks_per_cgra,
                num_registers_per_reg_bank, ctrl_steps, ctrl_steps,
                FunctionUnit, FuList, controller2addr_map)

    # Connections
    s.expected_sink_out.recv //= s.dut.send_to_cpu_pkt

    complete_count_value = \
            sum(1 for pkt in expected_sink_out_pkt \
                if pkt.payload.cmd == CMD_COMPLETE)

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
        if s.expected_sink_out.recv.val & s.expected_sink_out.recv.rdy & \
           (s.complete_count < complete_count_value):
          s.complete_count <<= s.complete_count + CompleteCountType(1)
      print(f"complete_count: {s.complete_count}")

  def done(s):
    return s.src_ctrl_pkt.done() and s.src_query_pkt.done() and \
           s.expected_sink_out.done()

  def line_trace(s):
    return s.dut.line_trace()

def run_sim(test_harness, max_cycles = 200):
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

def initialize_test_harness(cmdline_opts,
                            num_cgra_rows = 2,
                            num_cgra_columns = 2,
                            num_x_tiles_per_cgra = 2,
                            num_y_tiles_per_cgra = 2,
                            num_banks_per_cgra = 2,
                            data_mem_size_per_bank = 16):
  num_tile_inports = 4
  num_tile_outports = 4
  num_fu_inports = 4
  num_fu_outports = 2
  num_routing_outports = num_tile_outports + num_fu_inports
  ctrl_mem_size = 16
  num_cgras = num_cgra_rows * num_cgra_columns
  data_mem_size_global = data_mem_size_per_bank * num_banks_per_cgra * num_cgras
  num_tiles = num_x_tiles_per_cgra * num_y_tiles_per_cgra
  TileInType = mk_bits(clog2(num_tile_inports + 1))
  FuInType = mk_bits(clog2(num_fu_inports + 1))
  FuOutType = mk_bits(clog2(num_fu_outports + 1))
  ctrl_addr_nbits = clog2(ctrl_mem_size)
  data_addr_nbits = clog2(data_mem_size_global)
  data_nbits = 32
  DataType = mk_data(data_nbits, 1)
  DataAddrType = mk_bits(clog2(data_mem_size_global))
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
            FpAddRTL,
            FpMulRTL,
            SeqMulAdderRTL,
            # PrlMulAdderRTL, FIXME: https://github.com/tancheng/VectorCGRA/issues/123
            VectorMulComboRTL,
            VectorAdderComboRTL]
  predicate_nbits = 1
  PredicateType = mk_predicate(1, 1)
  num_registers_per_reg_bank = 16
  per_cgra_data_size = int(data_mem_size_global / num_cgras)
  controller2addr_map = {}
  for i in range(num_cgras):
    controller2addr_map[i] = [i * per_cgra_data_size,
                              (i + 1) * per_cgra_data_size - 1]
  print("[LOG] controller2addr_map: ", controller2addr_map)

  RegIdxType = mk_bits(clog2(num_registers_per_reg_bank))

  cgra_id_nbits = clog2(num_cgras)

  CtrlType = mk_ctrl(num_fu_inports,
                     num_fu_outports,
                     num_tile_inports,
                     num_tile_outports,
                     num_registers_per_reg_bank)

  CtrlAddrType = mk_bits(clog2(ctrl_mem_size))

  CgraPayloadType = mk_cgra_payload(DataType,
                                    DataAddrType,
                                    CtrlType,
                                    CtrlAddrType)

  InterCgraPktType = mk_inter_cgra_pkt(num_cgra_columns,
                                       num_cgra_rows,
                                       num_tiles,
                                       CgraPayloadType)

  IntraCgraPktType = mk_intra_cgra_pkt(num_cgra_columns,
                                       num_cgra_rows,
                                       num_tiles,
                                       CgraPayloadType)

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
       IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(254, 1), data_addr = 34)),
       # Tile 0.
       # Indicates the load address of 2.    dst_cgra_y
       IntraCgraPktType(0, 0, 0, 2, 0, 0, 0, 1, payload = CgraPayloadType(CMD_CONST, data = DataType(34, 1))),
                      # src dst src_cgra dst_cgra
       IntraCgraPktType(0,  0,  0,       2,       0, 0, 0, 1,
                        payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                  ctrl = CtrlType(OPT_LD_CONST, 0,
                                                                  [FuInType(0), FuInType(0), FuInType(0), FuInType(0)],
                                                                  [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                   TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                  [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                   # Note that we still need to set FU xbar.
                                                                   FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                  # 2 indicates the FU xbar port (instead of const queue or routing xbar port).
                                                                  write_reg_from = [b2(2), b2(0), b2(0), b2(0)],
                                                                  write_reg_idx = [RegIdxType(7), RegIdxType(0), RegIdxType(0), RegIdxType(0)]))),
       IntraCgraPktType(0,  0,  0,       2,       0, 0, 0, 1,
                        payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                  ctrl = CtrlType(OPT_INC, 0,
                                                                  [FuInType(1), FuInType(0), FuInType(0), FuInType(0)],
                                                                  [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                   TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                  [FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                   FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                  read_reg_from = [b1(1), b1(0), b1(0), b1(0)],
                                                                  read_reg_idx = [RegIdxType(7), RegIdxType(0), RegIdxType(0), RegIdxType(0)]))),

       # Tile 2. Note that tile 0 and tile 2 can access the memory, as they are on
       # the first column.
       # Indicates the store address of 3.
       IntraCgraPktType(0, 2, 0, 2, 0, 0, 0, 1, payload = CgraPayloadType(CMD_CONST, data = DataType(3, 1))),
                      # src dst src_cgra dst_cgra
       IntraCgraPktType(0,  2,  0,       2,       0, 0, 0, 1,
                        payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                  ctrl = CtrlType(OPT_STR_CONST, 0,
                                                                  [FuInType(1), FuInType(0), FuInType(0), FuInType(0)],
                                                                  [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                   TileInType(2), TileInType(0), TileInType(0), TileInType(0)],
                                                                  [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                   FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),
       # Pre-configure per-tile total config count.
       # Only execute one operation (i.e., store) is enough for this tile.
       # If this is set more than 1, no `COMPLETE` signal would be set back
       # to CPU/test_harness.
       IntraCgraPktType(0, 2, 0, 2, 0, 0, 0, 1, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(1))),

       # For launching the two tiles.
       IntraCgraPktType(0, 0, 0, 2, 0, 0, 0, 1, payload = CgraPayloadType(CMD_LAUNCH)),
       IntraCgraPktType(0, 2, 0, 2, 0, 0, 0, 1, payload = CgraPayloadType(CMD_LAUNCH)),
      ]

  src_query_pkt = \
      [
       IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = 34)),
       IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = 3)),
      ]

  # vc_id needs to be 1 due to the message might traverse across the date line via ring.
  expected_sink_out_pkt = \
      [
                      # src  dst        src/dst cgra x/y
       IntraCgraPktType(0,   num_tiles, 2, 0, 0, 1, 0, 0, payload = CgraPayloadType(CMD_COMPLETE)),
       IntraCgraPktType(2,   num_tiles, 2, 0, 0, 1, 0, 0, payload = CgraPayloadType(CMD_COMPLETE)),
                                                                                                                     # Expected updated value.
       IntraCgraPktType(0,   num_tiles, 0, 0, 0, 0, 0, 0, payload = CgraPayloadType(CMD_LOAD_RESPONSE, data = DataType(0xff, 1), data_addr = 3)),
       IntraCgraPktType(0,   num_tiles, 1, 0, 1, 0, 0, 0, payload = CgraPayloadType(CMD_LOAD_RESPONSE, data = DataType(0xfe, 1), data_addr = 34)),
      ]

  # We only needs 2 steps to finish this test.
  ctrl_steps = 2

  th = TestHarness(DUT, FunctionUnit, FuList, DataType, PredicateType, IntraCgraPktType,
                   CgraPayloadType, CtrlType, InterCgraPktType, num_cgra_rows, num_cgra_columns,
                   num_x_tiles_per_cgra, num_y_tiles_per_cgra, ctrl_mem_size, data_mem_size_global,
                   data_mem_size_per_bank, num_banks_per_cgra,
                   num_registers_per_reg_bank, src_ctrl_pkt, src_query_pkt,
                   ctrl_steps, controller2addr_map, expected_sink_out_pkt)
  return th

def test_sim_homo_2x2_2x2(cmdline_opts):
  th = initialize_test_harness(cmdline_opts,
                               num_cgra_rows = 2,
                               num_cgra_columns = 2,
                               num_x_tiles_per_cgra = 2,
                               num_y_tiles_per_cgra = 2,
                               num_banks_per_cgra = 2,
                               data_mem_size_per_bank = 16)
  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                      ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                       'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)

def _enable_translate_recursively(m):
  m.set_metadata(VerilogTranslationPass.enable, True)
  for child in m.get_child_components(repr):
    _enable_translate_recursively( child )

def translate_model(top, submodules_to_translate):
  top.elaborate()
  top.apply(VerilogPlaceholderPass())
  if not submodules_to_translate:
    _enable_translate_recursively(top)
  else:
    for submodule in submodules_to_translate:
      m = getattr(top, submodule)
      _enable_translate_recursively(m)
  top.apply(VerilogTranslationPass())

def test_verilog_homo_2x2_4x4(cmdline_opts):
  th = initialize_test_harness(cmdline_opts,
                               num_cgra_rows = 2,
                               num_cgra_columns = 2,
                               num_x_tiles_per_cgra = 4,
                               num_y_tiles_per_cgra = 4,
                               num_banks_per_cgra = 8,
                               data_mem_size_per_bank = 256)
  translate_model(th, ['dut'])
def test_multi_CGRA_systolic_2x2_2x2(cmdline_opts,
                                     num_cgra_rows = 2,
                                     num_cgra_columns = 2,
                                     num_x_tiles_per_cgra = 2,
                                     num_y_tiles_per_cgra = 2,
                                     num_banks_per_cgra = 2,
                                     data_mem_size_per_bank = 16):
  num_tile_inports = 4
  num_tile_outports = 4
  num_fu_inports = 4
  num_fu_outports = 2
  num_routing_outports = num_tile_outports + num_fu_inports
  ctrl_mem_size = 16
  num_cgras = num_cgra_rows * num_cgra_columns
  data_mem_size_global = data_mem_size_per_bank * num_banks_per_cgra * num_cgras
  num_tiles = num_x_tiles_per_cgra * num_y_tiles_per_cgra
  TileInType = mk_bits(clog2(num_tile_inports + 1))
  FuInType = mk_bits(clog2(num_fu_inports + 1))
  FuOutType = mk_bits(clog2(num_fu_outports + 1))
  ctrl_addr_nbits = clog2(ctrl_mem_size)
  data_addr_nbits = clog2(data_mem_size_global)
  data_nbits = 32
  DataType = mk_data(data_nbits, 1)
  DataAddrType = mk_bits(clog2(data_mem_size_global))
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
            SeqMulAdderRTL,
            VectorMulComboRTL,
            VectorAdderComboRTL]
  predicate_nbits = 1
  PredicateType = mk_predicate(1, 1)
  num_registers_per_reg_bank = 16
  per_cgra_data_size = int(data_mem_size_global / num_cgras)
  controller2addr_map = {}
  for i in range(num_cgras):
    controller2addr_map[i] = [i * per_cgra_data_size,
                              (i + 1) * per_cgra_data_size - 1]
  print("[LOG] controller2addr_map: ", controller2addr_map)

  RegIdxType = mk_bits(clog2(num_registers_per_reg_bank))

  cgra_id_nbits = clog2(num_cgras)

  CtrlType = mk_ctrl(num_fu_inports,
                     num_fu_outports,
                     num_tile_inports,
                     num_tile_outports,
                     num_registers_per_reg_bank)

  CtrlAddrType = mk_bits(clog2(ctrl_mem_size))

  CgraPayloadType = mk_cgra_payload(DataType,
                                    DataAddrType,
                                    CtrlType,
                                    CtrlAddrType)

  InterCgraPktType = mk_inter_cgra_pkt(num_cgra_columns,
                                       num_cgra_rows,
                                       num_tiles,
                                       CgraPayloadType)

  IntraCgraPktType = mk_intra_cgra_pkt(num_cgra_columns,
                                       num_cgra_rows,
                                       num_tiles,
                                       CgraPayloadType)


  updated_ctrl_steps = 3

  fu_in_code = [FuInType(x + 1) for x in range(num_fu_inports)]

  activation_tensor_preload_data = [
      [
          # CGRA 2, tile 2: [1, 2, 3]
          IntraCgraPktType(0, 2, 0, 2, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(1, 1), data_addr = 64)),
          IntraCgraPktType(0, 2, 0, 2, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(2, 1), data_addr = 65)),
          IntraCgraPktType(0, 2, 0, 2, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(3, 1), data_addr = 66)),

          # CGRA 2, tile 0: [4, 5, 6]
          IntraCgraPktType(0, 0, 0, 2, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(4, 1), data_addr = 67)),
          IntraCgraPktType(0, 0, 0, 2, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(5, 1), data_addr = 68)),
          IntraCgraPktType(0, 0, 0, 2, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(6, 1), data_addr = 69)),

          # CGRA 0, tile 2: [7, 8, 9]
          IntraCgraPktType(0, 2, 0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(7, 1), data_addr = 0)),
          IntraCgraPktType(0, 2, 0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(8, 1), data_addr = 1)),
          IntraCgraPktType(0, 2, 0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(9, 1), data_addr = 2)),
      ]
  ]

  src_opt_pkt = [
      # CGRA 2, tile 2.
      [
          IntraCgraPktType(0, 2, 0, 2, payload = CgraPayloadType(CMD_CONST, data = DataType(64, 1))),
          IntraCgraPktType(0, 2, 0, 2, payload = CgraPayloadType(CMD_CONST, data = DataType(65, 1))),
          IntraCgraPktType(0, 2, 0, 2, payload = CgraPayloadType(CMD_CONST, data = DataType(66, 1))),

          # Pre-configure per-tile config count per iter.
          IntraCgraPktType(0, 2, 0, 2,       0, 0, 0, 0, 0, 0,
                           CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(1, 1))),

          # Pre-configure per-tile total config count.
          IntraCgraPktType(0, 2, 0, 2,       0, 0, 0, 0, 0, 0,
                           CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(updated_ctrl_steps, 1))),

          # LD_CONST indicates the address is a const.
          IntraCgraPktType(0, 2, 0, 2,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                     ctrl = CtrlType(OPT_LD_CONST, 0,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     # Sends to east tiles: [(CGRA 2, tile 3), (CGRA 3, tile 2), (CGRA 3, tile 3)].
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(1),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

          IntraCgraPktType(0, 2, 0, 2, payload = CgraPayloadType(CMD_LAUNCH))
      ],

      # CGRA 2, tile 0.
      [
          IntraCgraPktType(0, 0, 0, 2, payload = CgraPayloadType(CMD_CONST, data = DataType(67, 1))),
          IntraCgraPktType(0, 0, 0, 2, payload = CgraPayloadType(CMD_CONST, data = DataType(68, 1))),
          IntraCgraPktType(0, 0, 0, 2, payload = CgraPayloadType(CMD_CONST, data = DataType(69, 1))),

          # Pre-configure per-tile config count per iter.
          # Set config_mem data as 1.
          # Set 1, read the 1st always
          # Set 2, read 1, 2 repeatedly
          IntraCgraPktType(0, 0, 0, 2,       0, 0, 0, 0, 0, 0,
                           CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(1, 1))),

          # Pre-configure per-tile total config count.
          # Total run 3 times.
          IntraCgraPktType(0, 0, 0, 2,       0, 0, 0, 0, 0, 0,
                           CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(updated_ctrl_steps, 1))),

          # LD_CONST indicates the address is a const.
          IntraCgraPktType(0, 0, 0, 2,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                     ctrl = CtrlType(OPT_LD_CONST, 0,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     # Sends to east tiles: [(CGRA 2, tile 1), (CGRA 3, tile 0), (CGRA 3, tile 1)]
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(1),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

          # IntraCgraPktType(0, 2, 0, 2, payload = CgraPayloadType(CMD_LAUNCH)),
          IntraCgraPktType(0, 0, 0, 2, payload = CgraPayloadType(CMD_LAUNCH))
      ],

      # CGRA 0, tile 2.
      [
          IntraCgraPktType(0, 2, 0, 0, payload = CgraPayloadType(CMD_CONST, data = DataType(0, 1))),
          IntraCgraPktType(0, 2, 0, 0, payload = CgraPayloadType(CMD_CONST, data = DataType(1, 1))),
          IntraCgraPktType(0, 2, 0, 0, payload = CgraPayloadType(CMD_CONST, data = DataType(2, 1))),

          # Pre-configure per-tile config count per iter.
          IntraCgraPktType(0, 2, 0, 0,       0, 0, 0, 0, 0, 0,
                           CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(1, 1))),

          # Pre-configure per-tile total config count.
          IntraCgraPktType(0, 2, 0, 0,       0, 0, 0, 0, 0, 0,
                           CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(updated_ctrl_steps, 1))),

          # LD_CONST indicates the address is a const.
          IntraCgraPktType(0, 2, 0, 0,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                     ctrl = CtrlType(OPT_LD_CONST, 0,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     # Sends to east tiles: [(CGRA 0, tile 3), (CGRA 1, tile 2), (CGRA 1, tile 3)]
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(1),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

          # IntraCgraPktType(0, 2, 0, 2, payload = CgraPayloadType(CMD_LAUNCH)),
          # IntraCgraPktType(0, 0, 0, 2, payload = CgraPayloadType(CMD_LAUNCH)),
          IntraCgraPktType(0, 2, 0, 0, payload = CgraPayloadType(CMD_LAUNCH))
      ],

      # CGRA 2, tile 3.
      [
          IntraCgraPktType(0, 3, 0, 2, payload = CgraPayloadType(CMD_CONST, data = DataType(2, 1))),

          # Pre-configure per-tile config count per iter.
          IntraCgraPktType(0, 3, 0, 2,       0, 0, 0, 0, 0, 0,
                           CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(1, 1))),

          # Pre-configure per-tile total config count.
          IntraCgraPktType(0, 3, 0, 2,       0, 0, 0, 0, 0, 0,
                           CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(updated_ctrl_steps, 1))),

          IntraCgraPktType(0, 3, 0, 2,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                     ctrl = CtrlType(OPT_MUL_CONST, 0,
                                                                     fu_in_code,
                                                                     # Forward data from west(CGRA 2, tile 2) to east (CGRA 3, tile 2).
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(3),
                                                                      # Put data from west(CGRA 2, tile 2) to first inport of FU, to do OPT_MUL_CONST.
                                                                      TileInType(3), TileInType(0), TileInType(0), TileInType(0)],
                                                                     #              Sends mul to south tile(CGRA 2, tile1).
                                                                     [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

          IntraCgraPktType(0, 3, 0, 2, payload = CgraPayloadType(CMD_LAUNCH))
      ],

      # CGRA 2, tile 1.
      [
          IntraCgraPktType(0, 1, 0, 2, payload = CgraPayloadType(CMD_CONST, data = DataType(4, 1))),

          # Pre-configure per-tile config count per iter.
          IntraCgraPktType(0, 1, 0, 2,       0, 0, 0, 0, 0, 0,
                           CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(1, 1))),

          # Pre-configure per-tile total config count.
          IntraCgraPktType(0, 1, 0, 2,       0, 0, 0, 0, 0, 0,
                           CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(updated_ctrl_steps, 1))),
          # load request ---> to return response, return to whom(who issue the request)
          # tile (!, ?), cgra (1, ?) ? according to address, ! according to code(infer by code(0 -> n-1)) or cpu (num_tiles)
          IntraCgraPktType(0, 1, 0, 2,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                     ctrl = CtrlType(OPT_MUL_CONST_ADD, 0,
                                                                     fu_in_code,
                                                                     # Forward data from west(CGRA 2, tile 0) to east (CGRA 3, tile 0).
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(3),
                                                                      # Put data from west(CGRA 2, tile 0) to first inport of FU, to do MUL_CONST (const 4).
                                                                      # Put data from north(CGRA 2, tile 3) to third inport to do ADD.
                                                                      TileInType(3), TileInType(0), TileInType(1), TileInType(0)],
                                                                     #              Sends mul_add to south tile(CGRA 0, tile 3).
                                                                     [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

          # IntraCgraPktType(0, 3, 0, 2, payload = CgraPayloadType(CMD_LAUNCH)),
          IntraCgraPktType(0, 1, 0, 2, payload = CgraPayloadType(CMD_LAUNCH))
      ],

      # CGRA 0, tile 3.
      [
          IntraCgraPktType(0, 3, 0, 0, payload = CgraPayloadType(CMD_CONST, data = DataType(6, 1))),

          # Pre-configure per-tile config count per iter.
          IntraCgraPktType(0, 3, 0, 0,       0, 0, 0, 0, 0, 0,
                           CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(1, 1))),

          # Pre-configure per-tile total config count.
          IntraCgraPktType(0, 3, 0, 0,       0, 0, 0, 0, 0, 0,
                           CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(updated_ctrl_steps, 1))),

          IntraCgraPktType(0, 3, 0, 0,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                     ctrl = CtrlType(OPT_MUL_CONST_ADD, 0,
                                                                     fu_in_code,
                                                                     # Forward data from west(CGRA 0, tile 2) to east (CGRA 1, tile 2).
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(3),
                                                                      # Put data from west(CGRA 0, tile 2) to first inport of FU, to do MUL_CONST (const 6).
                                                                      # Put data from north(CGRA 2, tile 1) to third inport to do ADD.
                                                                      TileInType(3), TileInType(0), TileInType(1), TileInType(0)],
                                                                     #              Sends mul_add to south tile(CGRA 0, tile 1).
                                                                     [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

          # IntraCgraPktType(0, 3, 0, 2, payload = CgraPayloadType(CMD_LAUNCH)),
          # IntraCgraPktType(0, 1, 0, 2, payload = CgraPayloadType(CMD_LAUNCH)),
          IntraCgraPktType(0, 3, 0, 0, payload = CgraPayloadType(CMD_LAUNCH))
      ],

      # CGRA 0, tile 1.
      [
          # Const
          IntraCgraPktType(0, 1, 0, 0, payload = CgraPayloadType(CMD_CONST, data = DataType(3, 1))), # 60
          IntraCgraPktType(0, 1, 0, 0, payload = CgraPayloadType(CMD_CONST, data = DataType(4, 1))), # 72
          IntraCgraPktType(0, 1, 0, 0, payload = CgraPayloadType(CMD_CONST, data = DataType(5, 1))), # 84

          # Pre-configure per-tile config count per iter.
          IntraCgraPktType(0, 1, 0, 0,       0, 0, 0, 0, 0, 0,
                           CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(1, 1))),

          # Pre-configure per-tile total config count.
          IntraCgraPktType(0, 1, 0, 0,       0, 0, 0, 0, 0, 0,
                           CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(updated_ctrl_steps, 1))),

          IntraCgraPktType(0, 1, 0, 0,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                     ctrl = CtrlType(OPT_STR_CONST, 0,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      # Stores data from north(CGRA 0, tile 3).
                                                                      TileInType(1), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

          IntraCgraPktType(0, 1, 0, 0, payload = CgraPayloadType(CMD_LAUNCH))
      ],

      # CGRA 3, tile 2.
      [
          IntraCgraPktType(0, 2, 0, 3, payload = CgraPayloadType(CMD_CONST, data = DataType(8, 1))),

          # Pre-configure per-tile config count per iter.
          IntraCgraPktType(0, 2, 0, 3,       0, 0, 0, 0, 0, 0,
                           CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(1, 1))),

          # Pre-configure per-tile total config count.
          IntraCgraPktType(0, 2, 0, 3,       0, 0, 0, 0, 0, 0,
                           CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(updated_ctrl_steps, 1))),

          IntraCgraPktType(0, 2, 0, 3,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                     ctrl = CtrlType(OPT_MUL_CONST, 0,
                                                                     fu_in_code,
                                                                     # Forward data from west(CGRA 2, tile 3) to east (CGRA 3, tile 3).
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(3),
                                                                      # Put data from west(CGRA 2, tile 3) to first inport of FU, to do OPT_MUL_CONST.
                                                                      TileInType(3), TileInType(0), TileInType(0), TileInType(0)],
                                                                     #              Sends mul to south tile(CGRA 3, tile 0).
                                                                     [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

          IntraCgraPktType(0, 2, 0, 3, payload = CgraPayloadType(CMD_LAUNCH))
      ],

      # CGRA 3, tile 0.
      [
          IntraCgraPktType(0, 0, 0, 3, payload = CgraPayloadType(CMD_CONST, data = DataType(10, 1))),

          # Pre-configure per-tile config count per iter.
          IntraCgraPktType(0, 0, 0, 3,       0, 0, 0, 0, 0, 0,
                           CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(1, 1))),

          # Pre-configure per-tile total config count.
          IntraCgraPktType(0, 0, 0, 3,       0, 0, 0, 0, 0, 0,
                           CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(updated_ctrl_steps, 1))),

          IntraCgraPktType(0, 0, 0, 3,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                     ctrl = CtrlType(OPT_MUL_CONST_ADD, 0,
                                                                     fu_in_code,
                                                                     # Forward data from west(CGRA 2, tile 1) to east (CGRA 3, tile 1).
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(3),
                                                                      # Put data from west(CGRA 2, tile 1) to first inport of FU, to do MUL_CONST (const 10).
                                                                      # Put data from north(CGRA 3, tile 2) to third inport to do ADD.
                                                                      TileInType(3), TileInType(0), TileInType(1), TileInType(0)],
                                                                      #             Sends mul_add to south tile(CGRA 1, tile 2).
                                                                     [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

          IntraCgraPktType(0, 0, 0, 3, payload = CgraPayloadType(CMD_LAUNCH))
      ],

      # CGRA 1, tile 2.
      [
          IntraCgraPktType(0, 2, 0, 1, payload = CgraPayloadType(CMD_CONST, data = DataType(12, 1))),

          # Pre-configure per-tile config count per iter.
          IntraCgraPktType(0, 2, 0, 1,       0, 0, 0, 0, 0, 0,
                           CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(1, 1))),

          # Pre-configure per-tile total config count.
          IntraCgraPktType(0, 2, 0, 1,       0, 0, 0, 0, 0, 0,
                           CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(updated_ctrl_steps, 1))),

          IntraCgraPktType(0, 2, 0, 1,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                     ctrl = CtrlType(OPT_MUL_CONST_ADD, 0,
                                                                     fu_in_code,
                                                                     # Forward data from west(CGRA 0, tile 3) to east (CGRA 1, tile 3).
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(3),
                                                                      # Put data from west(CGRA 0, tile 3) to first inport of FU, to do MUL_CONST (const 12).
                                                                      # Put data from north(CGRA 3, tile 0) to third inport to do ADD.
                                                                      TileInType(3), TileInType(0), TileInType(1), TileInType(0)],
                                                                      #             Sends mul_add to south tile(CGRA 1, tile 0).
                                                                     [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

          IntraCgraPktType(0, 2, 0, 1, payload = CgraPayloadType(CMD_LAUNCH))
      ],

      # CGRA 1, tile 0.
      [
          # Const
          IntraCgraPktType(0, 0, 0, 1, payload = CgraPayloadType(CMD_CONST, data = DataType(32, 1))), # 132
          IntraCgraPktType(0, 0, 0, 1, payload = CgraPayloadType(CMD_CONST, data = DataType(33, 1))), # 162
          IntraCgraPktType(0, 0, 0, 1, payload = CgraPayloadType(CMD_CONST, data = DataType(34, 1))), # 192

          # Pre-configure per-tile config count per iter.
          IntraCgraPktType(0, 0, 0, 1,       0, 0, 0, 0, 0, 0,
                           CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(1, 1))),

          # Pre-configure per-tile total config count.
          IntraCgraPktType(0, 0, 0, 1,       0, 0, 0, 0, 0, 0,
                           CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(updated_ctrl_steps, 1))),

          IntraCgraPktType(0, 0, 0, 1,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                     ctrl = CtrlType(OPT_STR_CONST, 0,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      # Stores data from north(CGRA 1, tile 2).
                                                                      TileInType(1), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

          IntraCgraPktType(0, 0, 0, 1, payload = CgraPayloadType(CMD_LAUNCH))
      ],

      # CGRA 3, tile 3.
      [
          IntraCgraPktType(0, 3, 0, 3, payload = CgraPayloadType(CMD_CONST, data = DataType(14, 1))),

          # Pre-configure per-tile config count per iter.
          IntraCgraPktType(0, 3, 0, 3,       0, 0, 0, 0, 0, 0,
                           CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(1, 1))),

          # Pre-configure per-tile total config count.
          IntraCgraPktType(0, 3, 0, 3,       0, 0, 0, 0, 0, 0,
                           CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(updated_ctrl_steps, 1))),

          IntraCgraPktType(0, 3, 0, 3,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                     ctrl = CtrlType(OPT_MUL_CONST, 0,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      # Put data from west(CGRA 3, tile 2) to first inport of FU, to do OPT_MUL_CONST.
                                                                      TileInType(3), TileInType(0), TileInType(0), TileInType(0)],
                                                                      #             Sends mul to south tile(CGRA 3, tile 1).
                                                                     [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

          IntraCgraPktType(0, 3, 0, 3, payload = CgraPayloadType(CMD_LAUNCH))
      ],

      # CGRA 3, tile 1.
      [
          IntraCgraPktType(0, 1, 0, 3, payload = CgraPayloadType(CMD_CONST, data = DataType(16, 1))),

          # Pre-configure per-tile config count per iter.
          IntraCgraPktType(0, 1, 0, 3,       0, 0, 0, 0, 0, 0,
                           CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(1, 1))),

          # Pre-configure per-tile total config count.
          IntraCgraPktType(0, 1, 0, 3,       0, 0, 0, 0, 0, 0,
                           CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(updated_ctrl_steps, 1))),

          IntraCgraPktType(0, 1, 0, 3,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                     ctrl = CtrlType(OPT_MUL_CONST_ADD, 0,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      # Put data from west(CGRA 3, tile 0) to first inport of FU, to do MUL_CONST (const 16).
                                                                      # Put data from north(CGRA 3, tile 3) to third inport to do ADD.
                                                                      TileInType(3), TileInType(0), TileInType(1), TileInType(0)],
                                                                      #             Sends mul_add to south tile(CGRA 1, tile 3).
                                                                     [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

          IntraCgraPktType(0, 1, 0, 3, payload = CgraPayloadType(CMD_LAUNCH))
      ],

      # CGRA 1, tile 3.
      [
          IntraCgraPktType(0, 3, 0, 1, payload = CgraPayloadType(CMD_CONST, data = DataType(18, 1))),

          # Pre-configure per-tile config count per iter.
          IntraCgraPktType(0, 3, 0, 1,       0, 0, 0, 0, 0, 0,
                           CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(1, 1))),

          # Pre-configure per-tile total config count.
          IntraCgraPktType(0, 3, 0, 1,       0, 0, 0, 0, 0, 0,
                           CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(updated_ctrl_steps, 1))),

          IntraCgraPktType(0, 3, 0, 1,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                     ctrl = CtrlType(OPT_MUL_CONST_ADD, 0,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      # Put data from west(CGRA 1, tile 2) to first inport of FU, to do MUL_CONST (const 18).
                                                                      # Put data from north(CGRA 3, tile 1) to third inport to do ADD.
                                                                      TileInType(3), TileInType(0), TileInType(1), TileInType(0)],
                                                                      #             Sends mul_add to south tile(CGRA 1, tile 1).
                                                                     [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

          IntraCgraPktType(0, 3, 0, 1, payload = CgraPayloadType(CMD_LAUNCH))
      ],

      # CGRA 1, tile 1.
      [
          # Const
          IntraCgraPktType(0, 1, 0, 1, payload = CgraPayloadType(CMD_CONST, data = DataType(35, 1))), # 204
          IntraCgraPktType(0, 1, 0, 1, payload = CgraPayloadType(CMD_CONST, data = DataType(36, 1))), # 252
          IntraCgraPktType(0, 1, 0, 1, payload = CgraPayloadType(CMD_CONST, data = DataType(37, 1))), # 300

          # Pre-configure per-tile config count per iter.
          IntraCgraPktType(0, 1, 0, 1,       0, 0, 0, 0, 0, 0,
                           CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(1, 1))),

          # Pre-configure per-tile total config count.
          IntraCgraPktType(0, 1, 0, 1,       0, 0, 0, 0, 0, 0,
                           CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(updated_ctrl_steps, 1))),

          IntraCgraPktType(0, 1, 0, 1,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                     ctrl = CtrlType(OPT_STR_CONST, 0,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      # Stores data from north(CGRA 1, tile 3).
                                                                      TileInType(1), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

          IntraCgraPktType(0, 1, 0, 1, payload = CgraPayloadType(CMD_LAUNCH))
      ]
  ]

  src_query_pkt = \
      [
          IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = 3)),
          IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = 4)),
          IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = 5)),

          IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = 32)),
          IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = 33)),
          IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = 34)),

          IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = 35)),
          IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = 36)),
          IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = 37))
      ]

  # vc_id needs to be 1 due to the message might traverse across the date line via ring.
  expected_complete_sink_out_pkg = [IntraCgraPktType(payload = CgraPayloadType(CMD_COMPLETE)) for _ in range(15)]
  expected_mem_sink_out_pkt = \
      [
          # cgra 0
          IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_RESPONSE, data = DataType(0x3c, 1), data_addr = 3)),
          IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_RESPONSE, data = DataType(0x48, 1), data_addr = 4)),
          IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_RESPONSE, data = DataType(0x54, 1), data_addr = 5)),

          # cgra 1
          IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_RESPONSE, data = DataType(0x84, 1), data_addr = 32)),
          IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_RESPONSE, data = DataType(0xa2, 1), data_addr = 33)),
          IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_RESPONSE, data = DataType(0xc0, 1), data_addr = 34)),

          IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_RESPONSE, data = DataType(0xcc, 1), data_addr = 35)),
          IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_RESPONSE, data = DataType(0xfc, 1), data_addr = 36)),
          IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_RESPONSE, data = DataType(0x12c, 1), data_addr = 37))
      ]

  src_ctrl_pkt = []
  for activation in activation_tensor_preload_data:
      src_ctrl_pkt.extend(activation)
  for src_opt in src_opt_pkt:
      src_ctrl_pkt.extend(src_opt)

  expected_sink_out_pkt = []
  expected_sink_out_pkt.extend(expected_complete_sink_out_pkg)
  expected_sink_out_pkt.extend(expected_mem_sink_out_pkt)

  # We only needs 3 steps to finish this test.
  ctrl_steps = 3

  th = TestHarness(DUT, FunctionUnit, FuList, DataType, PredicateType, IntraCgraPktType,
                   CgraPayloadType, CtrlType, InterCgraPktType, num_cgra_rows, num_cgra_columns,
                   num_x_tiles_per_cgra, num_y_tiles_per_cgra, ctrl_mem_size, data_mem_size_global,
                   data_mem_size_per_bank, num_banks_per_cgra,
                   num_registers_per_reg_bank, src_ctrl_pkt, src_query_pkt,
                   ctrl_steps, controller2addr_map, expected_sink_out_pkt)

  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                      ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                       'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)
