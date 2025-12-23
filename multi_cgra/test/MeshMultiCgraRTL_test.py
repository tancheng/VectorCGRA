"""
==========================================================================
MeshMultiCgraRTL_test.py
==========================================================================
Test cases for multi-CGRA with mesh NoC.

Author : Cheng Tan
  Date : Jan 8, 2024
"""

from pymtl3.passes.backends.verilog import (
    VerilogVerilatorImportPass,
    VerilogPlaceholderPass,
)
from pymtl3.passes.backends.verilog.translation.VerilogTranslationPass import VerilogTranslationPass
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)

from ..MeshMultiCgraRTL import MeshMultiCgraRTL
from ...fu.double.SeqMulAdderRTL import SeqMulAdderRTL
from ...fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from ...fu.float.FpAddRTL import FpAddRTL
from ...fu.float.FpMulRTL import FpMulRTL
from ...fu.single.AdderRTL import AdderRTL
from ...fu.single.GrantRTL import GrantRTL
from ...fu.single.CompRTL import CompRTL
from ...fu.single.LogicRTL import LogicRTL
from ...fu.single.MemUnitRTL import MemUnitRTL
from ...fu.single.MulRTL import MulRTL
from ...fu.single.PhiRTL import PhiRTL
from ...fu.single.RetRTL import RetRTL
from ...fu.single.SelRTL import SelRTL
from ...fu.single.ShifterRTL import ShifterRTL
from ...fu.vector.VectorAllReduceRTL import VectorAllReduceRTL
from ...fu.vector.VectorAdderComboRTL import VectorAdderComboRTL
from ...fu.vector.VectorMulComboRTL import VectorMulComboRTL
from ...lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ...lib.messages import *
from ...lib.opt_type import *


#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):
  def construct(s, DUT, FunctionUnit, FuList,
                IntraCgraPktType,
                cgra_rows, cgra_columns, width, height, ctrl_mem_size,
                data_mem_size_global, data_mem_size_per_bank,
                num_banks_per_cgra, num_registers_per_reg_bank,
                src_ctrl_pkt, src_query_pkt,
                ctrl_steps_per_iter,
                ctrl_steps_total,
                mem_access_is_combinational,
                controller2addr_map, expected_sink_out_pkt,
                cmp_func):

    CgraPayloadType = IntraCgraPktType.get_field_type(kAttrPayload)
    s.num_terminals = cgra_rows * cgra_columns
    s.num_tiles = width * height

    s.src_ctrl_pkt = TestSrcRTL(IntraCgraPktType, src_ctrl_pkt)
    s.src_query_pkt = TestSrcRTL(IntraCgraPktType, src_query_pkt)

    s.expected_sink_out = TestSinkRTL(IntraCgraPktType, expected_sink_out_pkt, cmp_fn = cmp_func)

    s.dut = DUT(CgraPayloadType, cgra_rows, cgra_columns,
                height, width, ctrl_mem_size, data_mem_size_global,
                data_mem_size_per_bank, num_banks_per_cgra,
                num_registers_per_reg_bank,
                ctrl_steps_per_iter, ctrl_steps_total,
                mem_access_is_combinational,
                FunctionUnit, FuList, "Mesh", controller2addr_map)

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

  def done(s):
    return s.src_ctrl_pkt.done() and s.src_query_pkt.done() and \
           s.expected_sink_out.done()

  def line_trace(s):
    return s.dut.line_trace()

def run_sim(test_harness, max_cycles = 200):
  test_harness.apply(DefaultPassGroup())
  test_harness.sim_reset()

  # Runs simulation.
  ncycles = 0
  print("cycle {}:{}".format(ncycles, test_harness.line_trace()))
  while not test_harness.done() and ncycles < max_cycles:
    test_harness.sim_tick()
    ncycles += 1
    print("cycle {}:{}".format(ncycles, test_harness.line_trace()))

  # Checks timeout.
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
                            data_mem_size_per_bank = 16,
                            mem_access_is_combinational = True,
                            test_name = "test_homo"):
  num_tile_inports = 4
  num_tile_outports = 4
  num_fu_inports = 4
  num_fu_outports = 2
  num_routing_outports = num_tile_outports + num_fu_inports
  ctrl_mem_size = 16
  num_cgras = num_cgra_rows * num_cgra_columns
  data_mem_size_global = data_mem_size_per_bank * num_banks_per_cgra * num_cgras
  num_tiles = num_x_tiles_per_cgra * num_y_tiles_per_cgra
  num_rd_tiles = num_x_tiles_per_cgra + num_y_tiles_per_cgra - 1
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
            GrantRTL,
            MemUnitRTL,
            SelRTL,
            RetRTL,
            # FpAddRTL,
            # FpMulRTL,
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
                                       num_rd_tiles,
                                       CgraPayloadType)

  IntraCgraPktType = mk_intra_cgra_pkt(num_cgra_columns,
                                       num_cgra_rows,
                                       num_tiles,
                                       CgraPayloadType)

  src_ctrl_pkt = []
  expected_sink_out_pkt = []
  src_query_pkt = []
  ctrl_steps_per_iter = 0
  ctrl_steps_global = 0

  cmp_func = lambda a, b : a.payload.data == b.payload.data and a.payload.cmd == b.payload.cmd

  if test_name == 'test_homo':
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
                                                      ctrl = CtrlType(OPT_LD_CONST,
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
                                                      ctrl = CtrlType(OPT_INC,
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
                                                      ctrl = CtrlType(OPT_STR_CONST,
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
      ctrl_steps_per_iter = 2
      ctrl_steps_total = 2

  elif test_name == 'test_systolic':
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
                                                         ctrl = CtrlType(OPT_LD_CONST,
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
              IntraCgraPktType(0, 0, 0, 2,       0, 0, 0, 0, 0, 0,
                               CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(1, 1))),

              # Pre-configure per-tile total config count.
              IntraCgraPktType(0, 0, 0, 2,       0, 0, 0, 0, 0, 0,
                               CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(updated_ctrl_steps, 1))),

              # LD_CONST indicates the address is a const.
              IntraCgraPktType(0, 0, 0, 2,
                               payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                         ctrl = CtrlType(OPT_LD_CONST,
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
                                                         ctrl = CtrlType(OPT_LD_CONST,
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
                                                         ctrl = CtrlType(OPT_MUL_CONST,
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

              IntraCgraPktType(0, 1, 0, 2,
                               payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                         ctrl = CtrlType(OPT_MUL_CONST_ADD,
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
                                                         ctrl = CtrlType(OPT_MUL_CONST_ADD,
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
                                                         ctrl = CtrlType(OPT_STR_CONST,
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
                                                         ctrl = CtrlType(OPT_MUL_CONST,
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
                                                         ctrl = CtrlType(OPT_MUL_CONST_ADD,
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
                                                         ctrl = CtrlType(OPT_MUL_CONST_ADD,
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
                                                         ctrl = CtrlType(OPT_STR_CONST,
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
                                                         ctrl = CtrlType(OPT_MUL_CONST,
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
                                                         ctrl = CtrlType(OPT_MUL_CONST_ADD,
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
                                                         ctrl = CtrlType(OPT_MUL_CONST_ADD,
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
                                                         ctrl = CtrlType(OPT_STR_CONST,
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

      # Figure to illustrate details: https://github.com/tancheng/VectorCGRA/blob/master/doc/figures/multi_cgra_weight_stationary_systolic_array.png
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

      for activation in activation_tensor_preload_data:
          src_ctrl_pkt.extend(activation)
      for src_opt in src_opt_pkt:
          src_ctrl_pkt.extend(src_opt)

      expected_sink_out_pkt.extend(expected_complete_sink_out_pkg)
      expected_sink_out_pkt.extend(expected_mem_sink_out_pkt)

      # We only needs 3 steps to finish this test.
      ctrl_steps_per_iter = 3
      ctrl_steps_total = 3

  elif test_name == 'test_fir_scalar':
    routing_xbar_code = [TileInType(0) for _ in range(num_routing_outports)]
    fu_xbar_code = [FuOutType(0) for _ in range(num_routing_outports)]
    write_reg_from_code = [b2(0) for _ in range(num_fu_inports)]
    # 2 indicates the FU xbar port (instead of const queue or routing xbar port).
    write_reg_from_code[0] = b2(2)
    read_reg_from_code = [b1(0) for _ in range(num_fu_inports)]
    read_reg_from_code[0] = b1(1)
    read_reg_idx_code = [RegIdxType(0) for _ in range(num_fu_inports)]

    fu_in_code = [FuInType(x + 1) for x in range(num_fu_inports)]
    src_ctrl_pkt = []
    src_query_pkt = []
    expected_sink_out_pkt = []
    # Expects all the fields on the output is exactly same as provided golden reference.
    cmp_func = lambda a, b : a.payload.data == b.payload.data and \
                             a.payload.cmd == b.payload.cmd and \
                             a.payload.ctrl.operation == b.payload.ctrl.operation and \
                             a.src == b.src and \
                             a.dst == b.dst and \
                             a.src_cgra_id == b.src_cgra_id and \
                             a.dst_cgra_id == b.dst_cgra_id and \
                             a.src_cgra_x == b.src_cgra_x and \
                             a.src_cgra_y == b.src_cgra_y and \
                             a.dst_cgra_x == b.dst_cgra_x and \
                             a.dst_cgra_y == b.dst_cgra_y

    preload_data = [
        [
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(10, 1), data_addr = 0)),
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(11, 1), data_addr = 1)),
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(12, 1), data_addr = 2)),
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(13, 1), data_addr = 3)),
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(14, 1), data_addr = 4)),
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(15, 1), data_addr = 5)),
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(16, 1), data_addr = 6)),
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(17, 1), data_addr = 7)),
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(18, 1), data_addr = 8)),
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(19, 1), data_addr = 9)),
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(20, 1), data_addr = 10)),
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(21, 1), data_addr = 11)),
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(22, 1), data_addr = 12)),
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(23, 1), data_addr = 13)),
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(24, 1), data_addr = 14)),
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(25, 1), data_addr = 15)),
        ]
    ]

    # kernel specific parameters.
    kStoreAddress = 16 # We no longer need this for storing the result, as we can directly return it to CPU.
    kInputBaseAddress = 0
    kCoefficientBaseAddress = 2
    kSumInitValue = 3
    kLoopLowerBound = 2
    kLoopIncrement = 1
    kLoopUpperBound = 10
    kCtrlCountPerIter = 4
    ctrl_steps_per_iter = kCtrlCountPerIter
    # Though kTotalCtrlSteps is way more than required loop iteration count,
    # the stored result should still be correct thanks to the grant predicate.
    kTotalCtrlSteps = kCtrlCountPerIter * \
                      (kLoopUpperBound - kLoopLowerBound) + \
                      100
    ctrl_steps_total = kTotalCtrlSteps
    kExpectedOutput = 2215

    # Corresponding DFG:
    #
    #              0(phi_const) <---------┐
    #             /      |      \         |
    #           2(+)    4(+)    8(+)      |
    #          /       /       /  |       |
    #        3(ld) 5(ld)   9(cmp) |       |
    #          \    /        | \  |       |
    #           6(x)    12(not) 10(grant_predicate)
    #             |          |
    #      ┌--> 7(+)         |
    #      |    /   \        |
    #  1(phi_const)  11(grant_predicate)
    #                        |
    #                     13(ret)
    #
    # Corresponding mapping:
    '''
        ↑ Y
    (0,5)|         🔳
    (0,4)|        .
    (0,3)|      .
    (0,2)|    .
    (0,1)| 🔳
    (0,0)+-------------→ X
        (1,0)(2,0)(3,0)

    ===================================================
    cycle 0:
    [    🔳            🔳            🔳            🔳 ]

    [ 0(phi_const) →   🔳            🔳            🔳 ]
        ↓ ↺
    [    🔳            🔳            🔳            🔳 ]

    [   7(+)    ───→   🔳            🔳            🔳 ]
          ↺
    ---------------------------------------------------
    cycle 1:
    [    🔳            🔳            🔳            🔳 ]

    [ 2(+ const)     8(+ const)      🔳            🔳 ]
          ↺            ↓ ↺
    [ 4(+ const)       🔳            🔳            🔳 ]
          ↺
    [ 1(phi_const)  11(grant_pred)   🔳            🔳 ]
          ↺             ↺
    ---------------------------------------------------
    cycle 2:
    [    🔳            🔳            🔳            🔳 ]

    [   3(ld)          🔳            🔳            🔳 ]
          ↓             ↑
    [   5(ld)        9(cmp)          🔳            🔳 ]
          ↺             ↺
    [    🔳         13(ret)          🔳            🔳 ]

    ---------------------------------------------------
    cycle 3:
    [    🔳            🔳            🔳            🔳 ]

    [    🔳   ← 10(grant_predicate)  🔳            🔳 ]

    [   6(x)        12(not)          🔳            🔳 ]
          ↓             ↓
    [    🔳            🔳            🔳            🔳 ]

    ---------------------------------------------------
    '''

    src_opt_pkt = [
        # tile 0
        [
            # Const for PHI_CONST.
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONST, data = DataType(kSumInitValue, 1))),

            # # Store address.
            # IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONST, data = DataType(kStoreAddress, 1))),

            # Pre-configure per-tile config count per iter.
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter, 1))),

            # Pre-configure per-tile total config count.
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps, 1))),

            # ADD.
            IntraCgraPktType(0, 0,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                       ctrl = CtrlType(OPT_ADD,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(1), TileInType(0), TileInType(0), TileInType(0)],
                                                                       # Sends to east tile: tile 1; and self reg.
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(1),
                                                                        FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       write_reg_from = write_reg_from_code,
                                                                       # Reads from the second reg cluster, which is written by the
                                                                       # following OPT_PHI_CONST.
                                                                       read_reg_from = [b1(0), b1(1), b1(0), b1(0)]))),

            # STORE_CONST, indicating the address is a const.
            IntraCgraPktType(0, 0,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                       ctrl = CtrlType(OPT_PHI_CONST,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0)],
                                                                       # Sends to self reg. Needs to be another register cluster to
                                                                       # avoid conflict with previous OPT_ADD.
                                                                       write_reg_from = [b2(0), b2(2), b2(0), b2(0)],
                                                                       read_reg_from = read_reg_from_code))),
            # NAH.
            IntraCgraPktType(0, 0,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                       ctrl = CtrlType(OPT_NAH,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),
            # NAH.
            IntraCgraPktType(0, 0,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 3,
                                                       ctrl = CtrlType(OPT_NAH,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

            # Pre-configure the prologue count for both operation and routing.
            IntraCgraPktType(0, 0,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 0,
                                                       data = DataType(1, 1))),
            IntraCgraPktType(0, 0,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 0,
                                                       ctrl = CtrlType(routing_xbar_outport = [
                                                           TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                           TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                       data = DataType(1, 1))),
            IntraCgraPktType(0, 0,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU_CROSSBAR, ctrl_addr = 0,
                                                       ctrl = CtrlType(fu_xbar_outport = [
                                                           FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                           FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]),
                                                       data = DataType(1, 1))),

            # Launch the tile.
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_LAUNCH))
        ],

        # tile 1
        [
            # Pre-configure per-tile config count per iter.
            IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter, 1))),

            # Pre-configure per-tile total config count.
            IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps, 1))),

            # NAH.
            IntraCgraPktType(0, 1,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                       ctrl = CtrlType(OPT_NAH,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

            # PHI_CONST.
            IntraCgraPktType(0, 1,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                       ctrl = CtrlType(OPT_GRT_PRED,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(3), TileInType(1), TileInType(0), TileInType(0)],
                                                                       # Sends to self first reg cluster.
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       write_reg_from = write_reg_from_code))),
            # OPT_RET.
            IntraCgraPktType(0, 1,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                       ctrl = CtrlType(OPT_RET,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       read_reg_from = read_reg_from_code))),
            # NAH.
            IntraCgraPktType(0, 1,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 3,
                                                       ctrl = CtrlType(OPT_NAH,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),
            IntraCgraPktType(0, 1,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 1,
                                                       data = DataType(1, 1))),
            IntraCgraPktType(0, 1,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 2,
                                                       data = DataType(1, 1))),
            IntraCgraPktType(0, 1,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 1,
                                                       ctrl = CtrlType(routing_xbar_outport = [
                                                           TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                           TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                       data = DataType(1, 1))),
            IntraCgraPktType(0, 1,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 1,
                                                       ctrl = CtrlType(routing_xbar_outport = [
                                                           TileInType(2), TileInType(0), TileInType(0), TileInType(0),
                                                           TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                       data = DataType(1, 1))),
            IntraCgraPktType(0, 1,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU_CROSSBAR, ctrl_addr = 1,
                                                       ctrl = CtrlType(fu_xbar_outport = [
                                                           FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                           FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]),
                                                       data = DataType(1, 1))),

            # Launch the tile.
            IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_LAUNCH))
        ],

        # tile 4
        [
            # Const for ADD_CONST.
            IntraCgraPktType(0, 4, payload = CgraPayloadType(CMD_CONST, data = DataType(kCoefficientBaseAddress, 1))),

            # Pre-configure per-tile config count per iter.
            IntraCgraPktType(0, 4, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter, 1))),

            # Pre-configure per-tile total config count.
            IntraCgraPktType(0, 4, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps, 1))),

            # NAH.
            IntraCgraPktType(0, 4,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                       ctrl = CtrlType(OPT_NAH,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

            # ADD_CONST.
            IntraCgraPktType(0, 4,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                       ctrl = CtrlType(OPT_ADD_CONST,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(1), TileInType(0), TileInType(0), TileInType(0)],
                                                                       # Sends to self reg.
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       write_reg_from = write_reg_from_code))),
            # LD.
            IntraCgraPktType(0, 4,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                       ctrl = CtrlType(OPT_LD,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       # Sends to self reg. Needs to be another register cluster to
                                                                       # avoid conflict with ADD_CONST.
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0)],
                                                                       write_reg_from = [b2(0), b2(2), b2(0), b2(0)],
                                                                       read_reg_from = read_reg_from_code))),
            # MUL.
            IntraCgraPktType(0, 4,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 3,
                                                       ctrl = CtrlType(OPT_MUL,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(1), TileInType(0), TileInType(0), TileInType(0)],
                                                                       # Sends to south tile: tile 0.
                                                                       [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       read_reg_from = [b1(0), b1(1), b1(0), b1(0)]))),

            # Launch the tile.
            IntraCgraPktType(0, 4, payload = CgraPayloadType(CMD_LAUNCH))
        ],

        # tile 5
        [
            # Const for CMP.
            IntraCgraPktType(0, 5, payload = CgraPayloadType(CMD_CONST, data = DataType(kLoopUpperBound, 1))),

            # Pre-configure per-tile config count per iter.
            IntraCgraPktType(0, 5, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter, 1))),

            # Pre-configure per-tile total config count.
            IntraCgraPktType(0, 5, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps, 1))),

            # NAH.
            IntraCgraPktType(0, 5,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                       ctrl = CtrlType(OPT_NAH,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

            # NAH.
            IntraCgraPktType(0, 5,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                       ctrl = CtrlType(OPT_NAH,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

            # CMP.
            IntraCgraPktType(0, 5,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                       ctrl = CtrlType(OPT_NE_CONST,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(1), TileInType(0), TileInType(0), TileInType(0)],
                                                                       # Sends result to north tile9, and self first register cluster.
                                                                       [FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       write_reg_from = write_reg_from_code))),

            # NOT.
            IntraCgraPktType(0, 5,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 3,
                                                       ctrl = CtrlType(OPT_NOT,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       # Sends result to south.
                                                                       [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       # Reads operand for `NOT` from self first register cluster.
                                                                       read_reg_from = read_reg_from_code))),

            # Launch the tile.
            IntraCgraPktType(0, 5, payload = CgraPayloadType(CMD_LAUNCH))
        ],

        # tile 8
        [
            # Const for PHI_CONST.
            IntraCgraPktType(0, 8, payload = CgraPayloadType(CMD_CONST, data = DataType(kLoopLowerBound, 1))),
            # Const for ADD_CONST.
            IntraCgraPktType(0, 8, payload = CgraPayloadType(CMD_CONST, data = DataType(kInputBaseAddress, 1))),

            # Pre-configure per-tile config count per iter.
            IntraCgraPktType(0, 8, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter, 1))),

            # Pre-configure per-tile total config count.
            IntraCgraPktType(0, 8, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps, 1))),

            # PHI_CONST.
            IntraCgraPktType(0, 8,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                       ctrl = CtrlType(OPT_PHI_CONST,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(4), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(1),
                                                                        FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       write_reg_from = write_reg_from_code))),

            # ADD_CONST.
            IntraCgraPktType(0, 8,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                       ctrl = CtrlType(OPT_ADD_CONST,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       # Sends to self reg.
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0)],
                                                                       # 2 indicates the FU xbar port (instead of const queue or routing xbar port).
                                                                       write_reg_from = [b2(0), b2(2), b2(0), b2(0)],
                                                                       read_reg_from = read_reg_from_code))),
            # LD.
            IntraCgraPktType(0, 8,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                       ctrl = CtrlType(OPT_LD,
                                                                       # The first 2 indicates the first operand is from the second inport,
                                                                       # which is actually from the second register cluster rather than the
                                                                       # inport channel, indicated by the `read_reg_from_code`.
                                                                       [FuInType(2), FuInType(0), FuInType(0), FuInType(0)],
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       # Sends to south tile: tile 4.
                                                                       [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       read_reg_from = [b1(0), b1(1), b1(0), b1(0)]))),
            # NAH.
            IntraCgraPktType(0, 8,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 3,
                                                       ctrl = CtrlType(OPT_NAH,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

            # Skips first time incoming from east tile via routing xbar.
            IntraCgraPktType(0, 8,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 0,
                                                       ctrl = CtrlType(routing_xbar_outport = [
                                                           TileInType(3), TileInType(0), TileInType(0), TileInType(0),
                                                           TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                       data = DataType(1, 1))),

            # Launch the tile.
            IntraCgraPktType(0, 8, payload = CgraPayloadType(CMD_LAUNCH))
        ],

        # tile 9
        [
            # Const for ADD_CONST.
            IntraCgraPktType(0, 9, payload = CgraPayloadType(CMD_CONST, data = DataType(kLoopIncrement, 1))),

            # Pre-configure per-tile config count per iter.
            IntraCgraPktType(0, 9, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter, 1))),

            # Pre-configure per-tile total config count.
            IntraCgraPktType(0, 9, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps, 1))),

            # NAH.
            IntraCgraPktType(0, 9,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                       ctrl = CtrlType(OPT_NAH,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

            # ADD_CONST.
            IntraCgraPktType(0, 9,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                       ctrl = CtrlType(OPT_ADD_CONST,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(3), TileInType(0), TileInType(0), TileInType(0)],
                                                                       # Sends to south tile5 and self reg (cluster 1).
                                                                       [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0)],
                                                                       # 2 indicates the FU xbar port (instead of const queue or routing xbar port).
                                                                       write_reg_from = [b2(0), b2(2), b2(0), b2(0)],))),
            # NAH.
            IntraCgraPktType(0, 9,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                       ctrl = CtrlType(OPT_NAH,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

            # GRANT_PREDICATE.
            IntraCgraPktType(0, 9,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 3,
                                                       ctrl = CtrlType(OPT_GRT_PRED,
                                                                       # Swaps the first and second operands as the second one is
                                                                       # by default treated as the condition.
                                                                       [FuInType(2), FuInType(1), FuInType(0), FuInType(0)],
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(2), TileInType(0), TileInType(0), TileInType(0)],
                                                                       # Sends result to west tile8.
                                                                       [FuOutType(0), FuOutType(0), FuOutType(1), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       read_reg_from = [b1(0), b1(1), b1(0), b1(0)]))),

            # Launch the tile.
            IntraCgraPktType(0, 9, payload = CgraPayloadType(CMD_LAUNCH))
        ]
    ]

    src_query_pkt = \
        [
            # IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = kStoreAddress)),
        ]

    expected_complete_sink_out_pkg = \
        [
            IntraCgraPktType(src = 1, dst = 16, payload = CgraPayloadType(CMD_COMPLETE, DataType(kExpectedOutput, 1, 0, 0), ctrl = CtrlType(OPT_RET))) for _ in range(1)
        ]
    expected_mem_sink_out_pkt = \
        [
            # IntraCgraPktType(dst = 16, payload = CgraPayloadType(CMD_LOAD_RESPONSE, data = DataType(kExpectedOutput, 1), data_addr = 16)),
        ]

    for activation in preload_data:
        src_ctrl_pkt.extend(activation)
    for src_opt in src_opt_pkt:
        src_ctrl_pkt.extend(src_opt)

    expected_sink_out_pkt.extend(expected_complete_sink_out_pkg)
    expected_sink_out_pkt.extend(expected_mem_sink_out_pkt)

  elif test_name == 'test_fir_vector':

    data_nbits = 64
    DataType = mk_data(data_nbits, 1)
    DUT = MeshMultiCgraRTL
    FunctionUnit = FlexibleFuRTL
    FuList = [AdderRTL,
              MulRTL,
              LogicRTL,
              ShifterRTL,
              PhiRTL,
              CompRTL,
              GrantRTL,
              MemUnitRTL,
              SelRTL,
              RetRTL,
              # FpAddRTL,
              # FpMulRTL,
              SeqMulAdderRTL,
              # PrlMulAdderRTL, FIXME: https://github.com/tancheng/VectorCGRA/issues/123
              VectorMulComboRTL,
              VectorAdderComboRTL,
              VectorAllReduceRTL]

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
                                         num_rd_tiles,
                                         CgraPayloadType)

    IntraCgraPktType = mk_intra_cgra_pkt(num_cgra_columns,
                                         num_cgra_rows,
                                         num_tiles,
                                         CgraPayloadType)

    routing_xbar_code = [TileInType(0) for _ in range(num_routing_outports)]
    fu_xbar_code = [FuOutType(0) for _ in range(num_routing_outports)]
    write_reg_from_code = [b2(0) for _ in range(num_fu_inports)]
    # 2 indicates the FU xbar port (instead of const queue or routing xbar port).
    write_reg_from_code[0] = b2(2)
    read_reg_from_code = [b1(0) for _ in range(num_fu_inports)]
    read_reg_from_code[0] = b1(1)
    read_reg_idx_code = [RegIdxType(0) for _ in range(num_fu_inports)]

    fu_in_code = [FuInType(x + 1) for x in range(num_fu_inports)]
    src_ctrl_pkt = []
    src_query_pkt = []
    expected_sink_out_pkt = []

    preload_data = [
        [
            # TODO: address granularity is currently in data type size. Instead, we should make it always byte-addressing. This requires
            # the data memory access unit be designed carefully. https://github.com/tancheng/VectorCGRA/issues/179.
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(0x0001000100010001, 1), data_addr = 0)),
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(0x0001000100010001, 1), data_addr = 1)),
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(0x000f000e000d000c, 1), data_addr = 2)),
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(0x0013001200110010, 1), data_addr = 3)),
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(0x00110010000f000e, 1), data_addr = 4)),
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(0x0015001400130012, 1), data_addr = 5)),
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(0x0001000100010001, 1), data_addr = 6)),
        ]
    ]

    # kernel specific parameters.
    kStoreAddress = 16 # We no longer need this for storing the result, as we can directly return it to CPU.
    kInputBaseAddress = 0
    kCoefficientBaseAddress = 2
    kSumInitValue = 3
    kLoopLowerBound = 2
    kLoopIncrement = 1
    kLoopUpperBound = 4
    kCtrlCountPerIter = 4
    ctrl_steps_per_iter = kCtrlCountPerIter
    # Though kTotalCtrlSteps is way more than required loop iteration count,
    # the stored result should still be correct thanks to the grant predicate.
    kTotalCtrlSteps = kCtrlCountPerIter * \
                      (kLoopUpperBound - kLoopLowerBound) + \
                      30
    ctrl_steps_total = kTotalCtrlSteps
    kExpectedOutput = 2215

    # Corresponding DFG:
    #
    #              0(phi_const) <---------┐
    #             /      |      \         |
    #           2(+)    4(+)    8(+4)     |
    #          /       /       /  |       |
    #       3(ld)  5(ld)   9(cmp) |       |
    #          \    /        | \  |       |
    #          6(vmul)  12(not) 10(grant_predicate)
    #             |          |
    #      ┌-> 7(vreduce+)   |
    #      |    /   \        |
    #  1(phi_const)  11(grant_predicate)
    #                        |
    #                     13(ret)
    #
    # Corresponding mapping:
    '''
        ↑ Y
    (0,5)|         🔳
    (0,4)|        .
    (0,3)|      .
    (0,2)|    .
    (0,1)| 🔳
    (0,0)+-------------→ X
        (1,0)(2,0)(3,0)

    ===================================================
    cycle 0:
    [    🔳            🔳            🔳            🔳 ]

    [ 0(phi_const) →   🔳            🔳            🔳 ]
        ↓ ↺
    [    🔳            🔳            🔳            🔳 ]

    [ 7(vreduce+)  ─→  🔳            🔳            🔳 ]
          ↺
    ---------------------------------------------------
    cycle 1:
    [    🔳            🔳            🔳            🔳 ]

    [ 2(+ const)     8(+ const)      🔳            🔳 ]
          ↺            ↓ ↺
    [ 4(+ const)       🔳            🔳            🔳 ]
          ↺
    [ 1(phi_const)  11(grant_pred)   🔳            🔳 ]
          ↺             ↺
    ---------------------------------------------------
    cycle 2:
    [    🔳            🔳            🔳            🔳 ]

    [   3(ld)          🔳            🔳            🔳 ]
          ↓             ↑
    [   5(ld)        9(cmp)          🔳            🔳 ]
          ↺             ↺
    [    🔳         13(ret)          🔳            🔳 ]

    ---------------------------------------------------
    cycle 3:
    [    🔳            🔳            🔳            🔳 ]

    [    🔳   ← 10(grant_predicate)  🔳            🔳 ]

    [  6(vmul)      12(not)          🔳            🔳 ]
          ↓             ↓
    [    🔳            🔳            🔳            🔳 ]

    ---------------------------------------------------
    '''

    src_opt_pkt = [
        # tile 0
        [
            # Const for PHI_CONST.
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONST, data = DataType(kSumInitValue, 1))),

            # # Store address.
            # IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONST, data = DataType(kStoreAddress, 1))),

            # Pre-configure per-tile config count per iter.
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter, 1))),

            # Pre-configure per-tile total config count.
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps, 1))),

            # ADD.
            IntraCgraPktType(0, 0,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                       ctrl = CtrlType(OPT_VEC_REDUCE_ADD_BASE,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(1), TileInType(0), TileInType(0), TileInType(0)],
                                                                       # Sends to east tile: tile 1; and self reg.
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(1),
                                                                        FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       write_reg_from = write_reg_from_code,
                                                                       # Reads from the second reg cluster, which is written by the
                                                                       # following OPT_PHI_CONST.
                                                                       read_reg_from = [b1(0), b1(1), b1(0), b1(0)]))),

            # STORE_CONST, indicating the address is a const.
            IntraCgraPktType(0, 0,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                       ctrl = CtrlType(OPT_PHI_CONST,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0)],
                                                                       # Sends to self reg. Needs to be another register cluster to
                                                                       # avoid conflict with previous OPT_ADD.
                                                                       write_reg_from = [b2(0), b2(2), b2(0), b2(0)],
                                                                       read_reg_from = read_reg_from_code))),
            # NAH.
            IntraCgraPktType(0, 0,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                       ctrl = CtrlType(OPT_NAH,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),
            # NAH.
            IntraCgraPktType(0, 0,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 3,
                                                       ctrl = CtrlType(OPT_NAH,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

            # Pre-configure the prologue count for both operation and routing.
            IntraCgraPktType(0, 0,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 0,
                                                       data = DataType(1, 1))),
            IntraCgraPktType(0, 0,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 0,
                                                       ctrl = CtrlType(routing_xbar_outport = [
                                                           TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                           TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                       data = DataType(1, 1))),
            IntraCgraPktType(0, 0,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU_CROSSBAR, ctrl_addr = 0,
                                                       ctrl = CtrlType(fu_xbar_outport = [
                                                           FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                           FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]),
                                                       data = DataType(1, 1))),

            # Launch the tile.
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_LAUNCH))
        ],

        # tile 1
        [
            # Pre-configure per-tile config count per iter.
            IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter, 1))),

            # Pre-configure per-tile total config count.
            IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps, 1))),

            # NAH.
            IntraCgraPktType(0, 1,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                       ctrl = CtrlType(OPT_NAH,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

            # PHI_CONST.
            IntraCgraPktType(0, 1,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                       ctrl = CtrlType(OPT_GRT_PRED,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(3), TileInType(1), TileInType(0), TileInType(0)],
                                                                       # Sends to self first reg cluster.
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       write_reg_from = write_reg_from_code))),
            # OPT_RET.
            IntraCgraPktType(0, 1,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                       ctrl = CtrlType(OPT_RET,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       read_reg_from = read_reg_from_code))),
            # NAH.
            IntraCgraPktType(0, 1,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 3,
                                                       ctrl = CtrlType(OPT_NAH,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),
            IntraCgraPktType(0, 1,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 1,
                                                       data = DataType(1, 1))),
            IntraCgraPktType(0, 1,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 2,
                                                       data = DataType(1, 1))),
            IntraCgraPktType(0, 1,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 1,
                                                       ctrl = CtrlType(routing_xbar_outport = [
                                                           TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                           TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                       data = DataType(1, 1))),
            IntraCgraPktType(0, 1,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 1,
                                                       ctrl = CtrlType(routing_xbar_outport = [
                                                           TileInType(2), TileInType(0), TileInType(0), TileInType(0),
                                                           TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                       data = DataType(1, 1))),
            IntraCgraPktType(0, 1,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU_CROSSBAR, ctrl_addr = 1,
                                                       ctrl = CtrlType(fu_xbar_outport = [
                                                           FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                           FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]),
                                                       data = DataType(1, 1))),

            # Launch the tile.
            IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_LAUNCH))
        ],

        # tile 4
        [
            # Const for ADD_CONST.
            IntraCgraPktType(0, 4, payload = CgraPayloadType(CMD_CONST, data = DataType(kCoefficientBaseAddress, 1))),

            # Pre-configure per-tile config count per iter.
            IntraCgraPktType(0, 4, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter, 1))),

            # Pre-configure per-tile total config count.
            IntraCgraPktType(0, 4, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps, 1))),

            # NAH.
            IntraCgraPktType(0, 4,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                       ctrl = CtrlType(OPT_NAH,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

            # ADD_CONST.
            IntraCgraPktType(0, 4,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                       ctrl = CtrlType(OPT_ADD_CONST,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(1), TileInType(0), TileInType(0), TileInType(0)],
                                                                       # Sends to self reg.
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       write_reg_from = write_reg_from_code))),
            # LD.
            IntraCgraPktType(0, 4,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                       ctrl = CtrlType(OPT_LD,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       # Sends to self reg. Needs to be another register cluster to
                                                                       # avoid conflict with ADD_CONST.
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0)],
                                                                       write_reg_from = [b2(0), b2(2), b2(0), b2(0)],
                                                                       read_reg_from = read_reg_from_code))),
            # MUL.
            IntraCgraPktType(0, 4,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 3,
                                                       ctrl = CtrlType(OPT_VEC_MUL,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(1), TileInType(0), TileInType(0), TileInType(0)],
                                                                       # Sends to south tile: tile 0.
                                                                       [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       read_reg_from = [b1(0), b1(1), b1(0), b1(0)]))),

            # Launch the tile.
            IntraCgraPktType(0, 4, payload = CgraPayloadType(CMD_LAUNCH))
        ],

        # tile 5
        [
            # Const for CMP.
            IntraCgraPktType(0, 5, payload = CgraPayloadType(CMD_CONST, data = DataType(kLoopUpperBound, 1))),

            # Pre-configure per-tile config count per iter.
            IntraCgraPktType(0, 5, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter, 1))),

            # Pre-configure per-tile total config count.
            IntraCgraPktType(0, 5, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps, 1))),

            # NAH.
            IntraCgraPktType(0, 5,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                       ctrl = CtrlType(OPT_NAH,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

            # NAH.
            IntraCgraPktType(0, 5,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                       ctrl = CtrlType(OPT_NAH,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

            # CMP.
            IntraCgraPktType(0, 5,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                       ctrl = CtrlType(OPT_NE_CONST,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(1), TileInType(0), TileInType(0), TileInType(0)],
                                                                       # Sends result to north tile9, and self first register cluster.
                                                                       [FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       write_reg_from = write_reg_from_code))),

            # NOT.
            IntraCgraPktType(0, 5,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 3,
                                                       ctrl = CtrlType(OPT_NOT,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       # Sends result to south.
                                                                       [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       # Reads operand for `NOT` from self first register cluster.
                                                                       read_reg_from = read_reg_from_code))),

            # Launch the tile.
            IntraCgraPktType(0, 5, payload = CgraPayloadType(CMD_LAUNCH))
        ],

        # tile 8
        [
            # Const for PHI_CONST.
            IntraCgraPktType(0, 8, payload = CgraPayloadType(CMD_CONST, data = DataType(kLoopLowerBound, 1))),
            # Const for ADD_CONST.
            IntraCgraPktType(0, 8, payload = CgraPayloadType(CMD_CONST, data = DataType(kInputBaseAddress, 1))),

            # Pre-configure per-tile config count per iter.
            IntraCgraPktType(0, 8, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter, 1))),

            # Pre-configure per-tile total config count.
            IntraCgraPktType(0, 8, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps, 1))),

            # PHI_CONST.
            IntraCgraPktType(0, 8,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                       ctrl = CtrlType(OPT_PHI_CONST,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(4), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(1),
                                                                        FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       write_reg_from = write_reg_from_code))),

            # ADD_CONST.
            IntraCgraPktType(0, 8,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                       ctrl = CtrlType(OPT_ADD_CONST,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       # Sends to self reg.
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0)],
                                                                       # 2 indicates the FU xbar port (instead of const queue or routing xbar port).
                                                                       write_reg_from = [b2(0), b2(2), b2(0), b2(0)],
                                                                       read_reg_from = read_reg_from_code))),
            # LD.
            IntraCgraPktType(0, 8,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                       ctrl = CtrlType(OPT_LD,
                                                                       # The first 2 indicates the first operand is from the second inport,
                                                                       # which is actually from the second register cluster rather than the
                                                                       # inport channel, indicated by the `read_reg_from_code`.
                                                                       [FuInType(2), FuInType(0), FuInType(0), FuInType(0)],
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       # Sends to south tile: tile 4.
                                                                       [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       read_reg_from = [b1(0), b1(1), b1(0), b1(0)]))),
            # NAH.
            IntraCgraPktType(0, 8,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 3,
                                                       ctrl = CtrlType(OPT_NAH,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

            # Skips first time incoming from east tile via routing xbar.
            IntraCgraPktType(0, 8,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 0,
                                                       ctrl = CtrlType(routing_xbar_outport = [
                                                           TileInType(3), TileInType(0), TileInType(0), TileInType(0),
                                                           TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                       data = DataType(1, 1))),

            # Launch the tile.
            IntraCgraPktType(0, 8, payload = CgraPayloadType(CMD_LAUNCH))
        ],

        # tile 9
        [
            # Const for ADD_CONST.
            IntraCgraPktType(0, 9, payload = CgraPayloadType(CMD_CONST, data = DataType(kLoopIncrement, 1))),

            # Pre-configure per-tile config count per iter.
            IntraCgraPktType(0, 9, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter, 1))),

            # Pre-configure per-tile total config count.
            IntraCgraPktType(0, 9, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps, 1))),

            # NAH.
            IntraCgraPktType(0, 9,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                       ctrl = CtrlType(OPT_NAH,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

            # ADD_CONST.
            IntraCgraPktType(0, 9,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                       ctrl = CtrlType(OPT_ADD_CONST,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(3), TileInType(0), TileInType(0), TileInType(0)],
                                                                       # Sends to south tile5 and self reg (cluster 1).
                                                                       [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0)],
                                                                       # 2 indicates the FU xbar port (instead of const queue or routing xbar port).
                                                                       write_reg_from = [b2(0), b2(2), b2(0), b2(0)],))),
            # NAH.
            IntraCgraPktType(0, 9,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                       ctrl = CtrlType(OPT_NAH,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),
            # GRANT_PREDICATE.
            IntraCgraPktType(0, 9,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 3,
                                                       ctrl = CtrlType(OPT_GRT_PRED,
                                                                       # Swaps the first and second operands as the second one is
                                                                       # by default treated as the condition.
                                                                       [FuInType(2), FuInType(1), FuInType(0), FuInType(0)],
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(2), TileInType(0), TileInType(0), TileInType(0)],
                                                                       # Sends result to west tile8.
                                                                       [FuOutType(0), FuOutType(0), FuOutType(1), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       read_reg_from = [b1(0), b1(1), b1(0), b1(0)]))),

            # Launch the tile.
            IntraCgraPktType(0, 9, payload = CgraPayloadType(CMD_LAUNCH))
        ]
    ]

    src_query_pkt = \
        [
            # IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = kStoreAddress)),
        ]

    expected_complete_sink_out_pkg = \
        [
            IntraCgraPktType(src = 1, dst = 16, payload = CgraPayloadType(CMD_COMPLETE, DataType(kExpectedOutput, 1, 0, 0), ctrl = CtrlType(OPT_RET))) for _ in range(1)
        ]
    expected_mem_sink_out_pkt = \
        [
            # IntraCgraPktType(dst = 16, payload = CgraPayloadType(CMD_LOAD_RESPONSE, data = DataType(kExpectedOutput, 1), data_addr = 16)),
        ]

    for activation in preload_data:
        src_ctrl_pkt.extend(activation)
    for src_opt in src_opt_pkt:
        src_ctrl_pkt.extend(src_opt)

    expected_sink_out_pkt.extend(expected_complete_sink_out_pkg)
    expected_sink_out_pkt.extend(expected_mem_sink_out_pkt)

    # Expects all the fields on the output is exactly same as provided golden reference.
    cmp_func = lambda a, b : a.payload.data == b.payload.data and \
                             a.payload.cmd == b.payload.cmd and \
                             a.payload.ctrl.operation == b.payload.ctrl.operation and \
                             a.src == b.src and \
                             a.dst == b.dst and \
                             a.src_cgra_id == b.src_cgra_id and \
                             a.dst_cgra_id == b.dst_cgra_id and \
                             a.src_cgra_x == b.src_cgra_x and \
                             a.src_cgra_y == b.src_cgra_y and \
                             a.dst_cgra_x == b.dst_cgra_x and \
                             a.dst_cgra_y == b.dst_cgra_y

  elif test_name == 'test_fir_vector_global_reduce':

    data_nbits = 64
    DataType = mk_data(data_nbits, 1)
    DUT = MeshMultiCgraRTL
    FunctionUnit = FlexibleFuRTL
    FuList = [AdderRTL,
              MulRTL,
              LogicRTL,
              ShifterRTL,
              PhiRTL,
              CompRTL,
              GrantRTL,
              MemUnitRTL,
              SelRTL,
              RetRTL,
              # FpAddRTL,
              # FpMulRTL,
              SeqMulAdderRTL,
              # PrlMulAdderRTL, FIXME: https://github.com/tancheng/VectorCGRA/issues/123
              VectorMulComboRTL,
              VectorAdderComboRTL,
              VectorAllReduceRTL]

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
                                        num_rd_tiles,
                                        CgraPayloadType)

    IntraCgraPktType = mk_intra_cgra_pkt(num_cgra_columns,
                                        num_cgra_rows,
                                        num_tiles,
                                        CgraPayloadType)

    routing_xbar_code = [TileInType(0) for _ in range(num_routing_outports)]
    fu_xbar_code = [FuOutType(0) for _ in range(num_routing_outports)]
    write_reg_from_code = [b2(0) for _ in range(num_fu_inports)]
    # 2 indicates the FU xbar port (instead of const queue or routing xbar port).
    write_reg_from_code[0] = b2(2)
    read_reg_from_code = [b1(0) for _ in range(num_fu_inports)]
    read_reg_from_code[0] = b1(1)
    read_reg_idx_code = [RegIdxType(0) for _ in range(num_fu_inports)]

    fu_in_code = [FuInType(x + 1) for x in range(num_fu_inports)]
    src_ctrl_pkt = []
    src_query_pkt = []
    expected_sink_out_pkt = []

    preload_data = [
        [
            # TODO: address granularity is currently in data type size. Instead, we should make it always byte-addressing. This requires
            # the data memory access unit be designed carefully. https://github.com/tancheng/VectorCGRA/issues/179.
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(0x0001000100010001, 1), data_addr = 0)),
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(0x0001000100010001, 1), data_addr = 1)),
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(0x000f000e000d000c, 1), data_addr = 2)),
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(0x0013001200110010, 1), data_addr = 3)),
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(0x00110010000f000e, 1), data_addr = 4)),
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(0x0015001400130012, 1), data_addr = 5)),
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(0x0001000100010001, 1), data_addr = 6)),
        ]
    ]

    # FIR kernel demo.
    '''
    // data = [10, 11, 12, 13, 14, 15, 16, ...] (two banks, each has 16 32-bit elements)
    // &input = 0 (addr)
    // &coeff = 2 (addr)
    // &sum = 11(st_const)'s const = 16 (addr)
    // 0(phi_const)'const = int i = 2
    // 1(phi_const)'const = sum init value = 3

    int i = 2;
    int sum = 3;
    for (int i = 2; i < ?; ++i) {
    sum += input[i] * coeff[i];
    }

    // case 1: when i is in range[2, 3):
    // input[0 + i] * coeff[2 + i]
    //     = input[0 + 2] * coeff[2 + 2]
    //     = 12 * 14
    //     = 168
    // expected sum = 168 + 3 = 171 (0xab)

    // case 2: when i is in range[2, 4):
    // input[0 + i] * coeff[2 + i]
    //     = input[0 + 2] * coeff[2 + 2] +
    //       input[0 + 3] * coeff[2 + 3]
    //     = 12 * 14 + 13 * 15
    //     = 363
    // expected sum = 363 + 3 = 366 (0x16e)

    // case 3: when i is in range[2, 10):
    // input[0 + i] * coeff[2 + i]
    //     = input[0 + 2] * coeff[2 + 2] +
    //       input[0 + 3] * coeff[2 + 3] +
    //       input[0 + 4] * coeff[2 + 4] +
    //       input[0 + 5] * coeff[2 + 5] +
    //       input[0 + 6] * coeff[2 + 6] +
    //       input[0 + 7] * coeff[2 + 7] +
    //       input[0 + 8] * coeff[2 + 8] +
    //       input[0 + 9] * coeff[2 + 9]
    //     = 12 * 14 +
    //       13 * 15 +
    //       14 * 16 +
    //       15 * 17 +
    //       16 * 18 +
    //       17 * 19 +
    //       18 * 20 +
    //       19 * 21
    //     = 168 +
    //       195 +
    //       224 +
    //       255 +
    //       288 +
    //       323 +
    //       360 +
    //       399
    //     = 842 +
    //       1370
    //     = 2212
    '''
    # kernel specific parameters.
    kStoreAddress = 16 # We no longer need this for storing the result, as we can directly return it to CPU.
    kInputBaseAddress = 0
    kCoefficientBaseAddress = 2
    kSumInitValue = 3
    kLoopLowerBound = 2
    kLoopIncrement = 1
    kLoopUpperBound = 4
    kCtrlCountPerIter = 4
    ctrl_steps_per_iter = kCtrlCountPerIter
    # Though kTotalCtrlSteps is way more than required loop iteration count,
    # the stored result should still be correct thanks to the grant predicate.
    kTotalCtrlSteps = kCtrlCountPerIter * \
                      (kLoopUpperBound - kLoopLowerBound) + \
                      30
    ctrl_steps_total = kTotalCtrlSteps
    kExpectedOutput = 2212 * 2 + kSumInitValue

    # Corresponding DFG:
    #
    #              0(phi_const) <---------┐
    #             /      |      \         |
    #           2(+)    4(+)    8(+4)     |
    #          /       /       /  |       |
    #       3(ld)  5(ld)   9(cmp) |       |
    #          \    /        | \  |       |
    #          6(vmul)  12(not) 10(grant_predicate)
    #             |          |
    #      ┌> 7(vreduce+glb) |
    #      |    /   \        |
    #  1(phi_const)  11(grant_predicate)
    #                        |
    #                     13(ret)
    #
    # Corresponding mapping:
    '''
        ↑ Y
    (0,5)|         🔳
    (0,4)|        .
    (0,3)|      .
    (0,2)|    .
    (0,1)| 🔳
    (0,0)+-------------→ X
        (1,0)(2,0)(3,0)

    ===================================================
    cycle 0:
    [    🔳            🔳            🔳            🔳 ]

    [ 0(phi_const) →   🔳            🔳            🔳 ]
        ↓ ↺
    [    🔳            🔳            🔳            🔳 ]

    [ 7(vreduce+)  ─→  🔳            🔳            🔳 ]
          ↺
    ---------------------------------------------------
    cycle 1:
    [    🔳            🔳            🔳            🔳 ]

    [ 2(+ const)     8(+ const)      🔳            🔳 ]
          ↺            ↓ ↺
    [ 4(+ const)       🔳            🔳            🔳 ]
          ↺
    [ 1(phi_const)  11(grant_pred)   🔳            🔳 ]
          ↺             ↺
    ---------------------------------------------------
    cycle 2:
    [    🔳            🔳            🔳            🔳 ]

    [   3(ld)          🔳            🔳            🔳 ]
          ↓             ↑
    [   5(ld)        9(cmp)          🔳            🔳 ]
          ↺             ↺
    [    🔳         13(ret)          🔳            🔳 ]

    ---------------------------------------------------
    cycle 3:
    [    🔳            🔳            🔳            🔳 ]

    [    🔳   ← 10(grant_predicate)  🔳            🔳 ]

    [  6(vmul)      12(not)          🔳            🔳 ]
          ↓             ↓
    [    🔳            🔳            🔳            🔳 ]

    ---------------------------------------------------
    '''

    cgra_0_id = 0
    cgra_0_x = 0
    cgra_0_y = 0
    cgra_1_id = 1
    cgra_1_x = 1
    cgra_1_y = 0
    src_opt_pkt_cgra_0 = [
        # tile 0
        [
            # Const for PHI_CONST.
            IntraCgraPktType(0, 0, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y, payload = CgraPayloadType(CMD_CONST, data = DataType(kSumInitValue, 1))),

            # # Store address.
            # IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONST, data = DataType(kStoreAddress, 1))),

            # Pre-configure per-tile config count per iter.
            IntraCgraPktType(0, 0, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter, 1))),

            # Pre-configure per-tile total config count.
            IntraCgraPktType(0, 0, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps, 1))),

            # ADD.
            IntraCgraPktType(0, 0, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                       ctrl = CtrlType(OPT_VEC_REDUCE_ADD_BASE_GLOBAL,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(1), TileInType(0), TileInType(0), TileInType(0)],
                                                                       # Sends to east tile: tile 1; and self reg.
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(1),
                                                                        FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       write_reg_from = write_reg_from_code,
                                                                       # Reads from the second reg cluster, which is written by the
                                                                       # following OPT_PHI_CONST.
                                                                       read_reg_from = [b1(0), b1(1), b1(0), b1(0)]))),

            # STORE_CONST, indicating the address is a const.
            IntraCgraPktType(0, 0, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                       ctrl = CtrlType(OPT_PHI_CONST,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0)],
                                                                       # Sends to self reg. Needs to be another register cluster to
                                                                       # avoid conflict with previous OPT_ADD.
                                                                       write_reg_from = [b2(0), b2(2), b2(0), b2(0)],
                                                                       read_reg_from = read_reg_from_code))),
            # NAH.
            IntraCgraPktType(0, 0, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                       ctrl = CtrlType(OPT_NAH,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),
            # NAH.
            IntraCgraPktType(0, 0, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 3,
                                                       ctrl = CtrlType(OPT_NAH,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

            # Pre-configure the global reduce unit (2 CGRAs globally reduce).
            IntraCgraPktType(0, 0, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y,
                             payload = CgraPayloadType(CMD_GLOBAL_REDUCE_COUNT,
                                                       data = DataType(2, 1))),

            # Pre-configure the prologue count for both operation and routing.
            IntraCgraPktType(0, 0, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 0,
                                                       data = DataType(1, 1))),
            IntraCgraPktType(0, 0, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 0,
                                                       ctrl = CtrlType(routing_xbar_outport = [
                                                           TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                           TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                       data = DataType(1, 1))),
            IntraCgraPktType(0, 0, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU_CROSSBAR, ctrl_addr = 0,
                                                       ctrl = CtrlType(fu_xbar_outport = [
                                                           FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                           FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]),
                                                       data = DataType(1, 1))),

            # Launch the tile.
            IntraCgraPktType(0, 0, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y, payload = CgraPayloadType(CMD_LAUNCH))
        ],

        # tile 1
        [
            # Pre-configure per-tile config count per iter.
            IntraCgraPktType(0, 1, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter, 1))),

            # Pre-configure per-tile total config count.
            IntraCgraPktType(0, 1, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps, 1))),

            # NAH.
            IntraCgraPktType(0, 1, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                       ctrl = CtrlType(OPT_NAH,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

            # PHI_CONST.
            IntraCgraPktType(0, 1, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                       ctrl = CtrlType(OPT_GRT_PRED,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(3), TileInType(1), TileInType(0), TileInType(0)],
                                                                       # Sends to self first reg cluster.
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       write_reg_from = write_reg_from_code))),
            # OPT_RET.
            IntraCgraPktType(0, 1, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                       ctrl = CtrlType(OPT_RET,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       read_reg_from = read_reg_from_code))),
            # NAH.
            IntraCgraPktType(0, 1, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 3,
                                                       ctrl = CtrlType(OPT_NAH,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),
            IntraCgraPktType(0, 1, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 1,
                                                       data = DataType(1, 1))),
            IntraCgraPktType(0, 1, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 2,
                                                       data = DataType(1, 1))),
            IntraCgraPktType(0, 1, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 1,
                                                       ctrl = CtrlType(routing_xbar_outport = [
                                                           TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                           TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                       data = DataType(1, 1))),
            IntraCgraPktType(0, 1, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 1,
                                                       ctrl = CtrlType(routing_xbar_outport = [
                                                           TileInType(2), TileInType(0), TileInType(0), TileInType(0),
                                                           TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                       data = DataType(1, 1))),
            IntraCgraPktType(0, 1, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU_CROSSBAR, ctrl_addr = 1,
                                                       ctrl = CtrlType(fu_xbar_outport = [
                                                           FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                           FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]),
                                                       data = DataType(1, 1))),

            # Launch the tile.
            IntraCgraPktType(0, 1, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y, payload = CgraPayloadType(CMD_LAUNCH))
        ],

        # tile 4
        [
            # Const for ADD_CONST.
            IntraCgraPktType(0, 4, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y, payload = CgraPayloadType(CMD_CONST, data = DataType(kCoefficientBaseAddress, 1))),

            # Pre-configure per-tile config count per iter.
            IntraCgraPktType(0, 4, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter, 1))),

            # Pre-configure per-tile total config count.
            IntraCgraPktType(0, 4, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps, 1))),

            # NAH.
            IntraCgraPktType(0, 4, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                       ctrl = CtrlType(OPT_NAH,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

            # ADD_CONST.
            IntraCgraPktType(0, 4, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                       ctrl = CtrlType(OPT_ADD_CONST,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(1), TileInType(0), TileInType(0), TileInType(0)],
                                                                       # Sends to self reg.
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       write_reg_from = write_reg_from_code))),
            # LD.
            IntraCgraPktType(0, 4, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                       ctrl = CtrlType(OPT_LD,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       # Sends to self reg. Needs to be another register cluster to
                                                                       # avoid conflict with ADD_CONST.
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0)],
                                                                       write_reg_from = [b2(0), b2(2), b2(0), b2(0)],
                                                                       read_reg_from = read_reg_from_code))),
            # MUL.
            IntraCgraPktType(0, 4, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 3,
                                                       ctrl = CtrlType(OPT_VEC_MUL,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(1), TileInType(0), TileInType(0), TileInType(0)],
                                                                       # Sends to south tile: tile 0.
                                                                       [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       read_reg_from = [b1(0), b1(1), b1(0), b1(0)]))),

            # Launch the tile.
            IntraCgraPktType(0, 4, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y, payload = CgraPayloadType(CMD_LAUNCH))
        ],

        # tile 5
        [
            # Const for CMP.
            IntraCgraPktType(0, 5, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y, payload = CgraPayloadType(CMD_CONST, data = DataType(kLoopUpperBound, 1))),

            # Pre-configure per-tile config count per iter.
            IntraCgraPktType(0, 5, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter, 1))),

            # Pre-configure per-tile total config count.
            IntraCgraPktType(0, 5, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps, 1))),

            # NAH.
            IntraCgraPktType(0, 5, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                       ctrl = CtrlType(OPT_NAH,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

            # NAH.
            IntraCgraPktType(0, 5, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                       ctrl = CtrlType(OPT_NAH,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

            # CMP.
            IntraCgraPktType(0, 5, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                       ctrl = CtrlType(OPT_NE_CONST,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(1), TileInType(0), TileInType(0), TileInType(0)],
                                                                       # Sends result to north tile9, and self first register cluster.
                                                                       [FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       write_reg_from = write_reg_from_code))),

            # NOT.
            IntraCgraPktType(0, 5, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 3,
                                                       ctrl = CtrlType(OPT_NOT,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       # Sends result to south.
                                                                       [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       # Reads operand for `NOT` from self first register cluster.
                                                                       read_reg_from = read_reg_from_code))),

            # Launch the tile.
            IntraCgraPktType(0, 5, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y, payload = CgraPayloadType(CMD_LAUNCH))
        ],

        # tile 8
        [
            # Const for PHI_CONST.
            IntraCgraPktType(0, 8, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y, payload = CgraPayloadType(CMD_CONST, data = DataType(kLoopLowerBound, 1))),
            # Const for ADD_CONST.
            IntraCgraPktType(0, 8, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y, payload = CgraPayloadType(CMD_CONST, data = DataType(kInputBaseAddress, 1))),

            # Pre-configure per-tile config count per iter.
            IntraCgraPktType(0, 8, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter, 1))),

            # Pre-configure per-tile total config count.
            IntraCgraPktType(0, 8, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps, 1))),

            # PHI_CONST.
            IntraCgraPktType(0, 8, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                       ctrl = CtrlType(OPT_PHI_CONST,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(4), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(1),
                                                                        FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       write_reg_from = write_reg_from_code))),

            # ADD_CONST.
            IntraCgraPktType(0, 8, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                       ctrl = CtrlType(OPT_ADD_CONST,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       # Sends to self reg.
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0)],
                                                                       # 2 indicates the FU xbar port (instead of const queue or routing xbar port).
                                                                       write_reg_from = [b2(0), b2(2), b2(0), b2(0)],
                                                                       read_reg_from = read_reg_from_code))),
            # LD.
            IntraCgraPktType(0, 8, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                       ctrl = CtrlType(OPT_LD,
                                                                       # The first 2 indicates the first operand is from the second inport,
                                                                       # which is actually from the second register cluster rather than the
                                                                       # inport channel, indicated by the `read_reg_from_code`.
                                                                       [FuInType(2), FuInType(0), FuInType(0), FuInType(0)],
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       # Sends to south tile: tile 4.
                                                                       [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       read_reg_from = [b1(0), b1(1), b1(0), b1(0)]))),
            # NAH.
            IntraCgraPktType(0, 8, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 3,
                                                       ctrl = CtrlType(OPT_NAH,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

            # Skips first time incoming from east tile via routing xbar.
            IntraCgraPktType(0, 8, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 0,
                                                       ctrl = CtrlType(routing_xbar_outport = [
                                                           TileInType(3), TileInType(0), TileInType(0), TileInType(0),
                                                           TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                       data = DataType(1, 1))),

            # Launch the tile.
            IntraCgraPktType(0, 8, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y, payload = CgraPayloadType(CMD_LAUNCH))
        ],

        # tile 9
        [
            # Const for ADD_CONST.
            IntraCgraPktType(0, 9, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y, payload = CgraPayloadType(CMD_CONST, data = DataType(kLoopIncrement, 1))),

            # Pre-configure per-tile config count per iter.
            IntraCgraPktType(0, 9, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter, 1))),

            # Pre-configure per-tile total config count.
            IntraCgraPktType(0, 9, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps, 1))),

            # NAH.
            IntraCgraPktType(0, 9, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                       ctrl = CtrlType(OPT_NAH,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

            # ADD_CONST.
            IntraCgraPktType(0, 9, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                       ctrl = CtrlType(OPT_ADD_CONST,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(3), TileInType(0), TileInType(0), TileInType(0)],
                                                                       # Sends to south tile5 and self reg (cluster 1).
                                                                       [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0)],
                                                                       # 2 indicates the FU xbar port (instead of const queue or routing xbar port).
                                                                       write_reg_from = [b2(0), b2(2), b2(0), b2(0)],))),
            # NAH.
            IntraCgraPktType(0, 9, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                       ctrl = CtrlType(OPT_NAH,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),
            # GRANT_PREDICATE.
            IntraCgraPktType(0, 9, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 3,
                                                       ctrl = CtrlType(OPT_GRT_PRED,
                                                                       # Swaps the first and second operands as the second one is
                                                                       # by default treated as the condition.
                                                                       [FuInType(2), FuInType(1), FuInType(0), FuInType(0)],
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(2), TileInType(0), TileInType(0), TileInType(0)],
                                                                       # Sends result to west tile8.
                                                                       [FuOutType(0), FuOutType(0), FuOutType(1), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       read_reg_from = [b1(0), b1(1), b1(0), b1(0)]))),

            # Launch the tile.
            IntraCgraPktType(0, 9, 0, cgra_0_id, 0, 0, cgra_0_x, cgra_0_y, payload = CgraPayloadType(CMD_LAUNCH))
        ]
    ]

    src_opt_pkt_cgra_1 = [
        # tile 0
        [
            # Const for PHI_CONST.
            IntraCgraPktType(0, 0, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y, payload = CgraPayloadType(CMD_CONST, data = DataType(kSumInitValue, 1))),

            # # Store address.
            # IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONST, data = DataType(kStoreAddress, 1))),

            # Pre-configure per-tile config count per iter.
            IntraCgraPktType(0, 0, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y,  payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter, 1))),

            # Pre-configure per-tile total config count.
            IntraCgraPktType(0, 0, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y,  payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps, 1))),

            # ADD.
            IntraCgraPktType(0, 0, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y, 
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                       ctrl = CtrlType(OPT_VEC_REDUCE_ADD_BASE_GLOBAL,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(1), TileInType(0), TileInType(0), TileInType(0)],
                                                                       # Sends to east tile: tile 1; and self reg.
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(1),
                                                                        FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       write_reg_from = write_reg_from_code,
                                                                       # Reads from the second reg cluster, which is written by the
                                                                       # following OPT_PHI_CONST.
                                                                       read_reg_from = [b1(0), b1(1), b1(0), b1(0)]))),

            # STORE_CONST, indicating the address is a const.
            IntraCgraPktType(0, 0, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y, 
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                       ctrl = CtrlType(OPT_PHI_CONST,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0)],
                                                                       # Sends to self reg. Needs to be another register cluster to
                                                                       # avoid conflict with previous OPT_ADD.
                                                                       write_reg_from = [b2(0), b2(2), b2(0), b2(0)],
                                                                       read_reg_from = read_reg_from_code))),
            # NAH.
            IntraCgraPktType(0, 0, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y, 
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                       ctrl = CtrlType(OPT_NAH,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),
            # NAH.
            IntraCgraPktType(0, 0, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y, 
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 3,
                                                       ctrl = CtrlType(OPT_NAH,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

            # Pre-configure the prologue count for both operation and routing.
            IntraCgraPktType(0, 0, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y, 
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 0,
                                                       data = DataType(1, 1))),
            IntraCgraPktType(0, 0, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y, 
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 0,
                                                       ctrl = CtrlType(routing_xbar_outport = [
                                                           TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                           TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                       data = DataType(1, 1))),
            IntraCgraPktType(0, 0, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y, 
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU_CROSSBAR, ctrl_addr = 0,
                                                       ctrl = CtrlType(fu_xbar_outport = [
                                                           FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                           FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]),
                                                       data = DataType(1, 1))),

            # Launch the tile.
            IntraCgraPktType(0, 0, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y,  payload = CgraPayloadType(CMD_LAUNCH))
        ],

        # tile 1
        [
            # Pre-configure per-tile config count per iter.
            IntraCgraPktType(0, 1, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y,  payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter, 1))),

            # Pre-configure per-tile total config count.
            IntraCgraPktType(0, 1, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y,  payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps, 1))),

            # NAH.
            IntraCgraPktType(0, 1, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y, 
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                       ctrl = CtrlType(OPT_NAH,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

            # PHI_CONST.
            IntraCgraPktType(0, 1, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y, 
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                       ctrl = CtrlType(OPT_GRT_PRED,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(3), TileInType(1), TileInType(0), TileInType(0)],
                                                                       # Sends to self first reg cluster.
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       write_reg_from = write_reg_from_code))),
            # OPT_RET.
            IntraCgraPktType(0, 1, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y, 
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                       ctrl = CtrlType(OPT_RET,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       read_reg_from = read_reg_from_code))),
            # NAH.
            IntraCgraPktType(0, 1, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y, 
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 3,
                                                       ctrl = CtrlType(OPT_NAH,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),
            IntraCgraPktType(0, 1, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y, 
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 1,
                                                       data = DataType(1, 1))),
            IntraCgraPktType(0, 1, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y, 
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 2,
                                                       data = DataType(1, 1))),
            IntraCgraPktType(0, 1, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y, 
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 1,
                                                       ctrl = CtrlType(routing_xbar_outport = [
                                                           TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                           TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                       data = DataType(1, 1))),
            IntraCgraPktType(0, 1, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y, 
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 1,
                                                       ctrl = CtrlType(routing_xbar_outport = [
                                                           TileInType(2), TileInType(0), TileInType(0), TileInType(0),
                                                           TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                       data = DataType(1, 1))),
            IntraCgraPktType(0, 1, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y, 
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU_CROSSBAR, ctrl_addr = 1,
                                                       ctrl = CtrlType(fu_xbar_outport = [
                                                           FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                           FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]),
                                                       data = DataType(1, 1))),

            # Launch the tile.
            IntraCgraPktType(0, 1, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y,  payload = CgraPayloadType(CMD_LAUNCH))
        ],

        # tile 4
        [
            # Const for ADD_CONST.
            IntraCgraPktType(0, 4, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y,  payload = CgraPayloadType(CMD_CONST, data = DataType(kCoefficientBaseAddress, 1))),

            # Pre-configure per-tile config count per iter.
            IntraCgraPktType(0, 4, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y,  payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter, 1))),

            # Pre-configure per-tile total config count.
            IntraCgraPktType(0, 4, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y,  payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps, 1))),

            # NAH.
            IntraCgraPktType(0, 4, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y, 
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                       ctrl = CtrlType(OPT_NAH,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

            # ADD_CONST.
            IntraCgraPktType(0, 4, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y, 
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                       ctrl = CtrlType(OPT_ADD_CONST,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(1), TileInType(0), TileInType(0), TileInType(0)],
                                                                       # Sends to self reg.
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       write_reg_from = write_reg_from_code))),
            # LD.
            IntraCgraPktType(0, 4, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y, 
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                       ctrl = CtrlType(OPT_LD,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       # Sends to self reg. Needs to be another register cluster to
                                                                       # avoid conflict with ADD_CONST.
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0)],
                                                                       write_reg_from = [b2(0), b2(2), b2(0), b2(0)],
                                                                       read_reg_from = read_reg_from_code))),
            # MUL.
            IntraCgraPktType(0, 4, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y, 
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 3,
                                                       ctrl = CtrlType(OPT_VEC_MUL,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(1), TileInType(0), TileInType(0), TileInType(0)],
                                                                       # Sends to south tile: tile 0.
                                                                       [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       read_reg_from = [b1(0), b1(1), b1(0), b1(0)]))),

            # Launch the tile.
            IntraCgraPktType(0, 4, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y,  payload = CgraPayloadType(CMD_LAUNCH))
        ],

        # tile 5
        [
            # Const for CMP.
            IntraCgraPktType(0, 5, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y,  payload = CgraPayloadType(CMD_CONST, data = DataType(kLoopUpperBound, 1))),

            # Pre-configure per-tile config count per iter.
            IntraCgraPktType(0, 5, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y,  payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter, 1))),

            # Pre-configure per-tile total config count.
            IntraCgraPktType(0, 5, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y,  payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps, 1))),

            # NAH.
            IntraCgraPktType(0, 5, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y, 
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                       ctrl = CtrlType(OPT_NAH,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

            # NAH.
            IntraCgraPktType(0, 5, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y, 
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                       ctrl = CtrlType(OPT_NAH,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

            # CMP.
            IntraCgraPktType(0, 5, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y, 
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                       ctrl = CtrlType(OPT_NE_CONST,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(1), TileInType(0), TileInType(0), TileInType(0)],
                                                                       # Sends result to north tile9, and self first register cluster.
                                                                       [FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       write_reg_from = write_reg_from_code))),

            # NOT.
            IntraCgraPktType(0, 5, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y, 
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 3,
                                                       ctrl = CtrlType(OPT_NOT,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       # Sends result to south.
                                                                       [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       # Reads operand for `NOT` from self first register cluster.
                                                                       read_reg_from = read_reg_from_code))),

            # Launch the tile.
            IntraCgraPktType(0, 5, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y,  payload = CgraPayloadType(CMD_LAUNCH))
        ],

        # tile 8
        [
            # Const for PHI_CONST.
            IntraCgraPktType(0, 8, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y,  payload = CgraPayloadType(CMD_CONST, data = DataType(kLoopLowerBound, 1))),
            # Const for ADD_CONST.
            IntraCgraPktType(0, 8, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y,  payload = CgraPayloadType(CMD_CONST, data = DataType(kInputBaseAddress, 1))),

            # Pre-configure per-tile config count per iter.
            IntraCgraPktType(0, 8, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y,  payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter, 1))),

            # Pre-configure per-tile total config count.
            IntraCgraPktType(0, 8, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y,  payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps, 1))),

            # PHI_CONST.
            IntraCgraPktType(0, 8, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y, 
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                       ctrl = CtrlType(OPT_PHI_CONST,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(4), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(1),
                                                                        FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       write_reg_from = write_reg_from_code))),

            # ADD_CONST.
            IntraCgraPktType(0, 8, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y, 
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                       ctrl = CtrlType(OPT_ADD_CONST,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       # Sends to self reg.
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0)],
                                                                       # 2 indicates the FU xbar port (instead of const queue or routing xbar port).
                                                                       write_reg_from = [b2(0), b2(2), b2(0), b2(0)],
                                                                       read_reg_from = read_reg_from_code))),
            # LD.
            IntraCgraPktType(0, 8, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y, 
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                       ctrl = CtrlType(OPT_LD,
                                                                       # The first 2 indicates the first operand is from the second inport,
                                                                       # which is actually from the second register cluster rather than the
                                                                       # inport channel, indicated by the `read_reg_from_code`.
                                                                       [FuInType(2), FuInType(0), FuInType(0), FuInType(0)],
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       # Sends to south tile: tile 4.
                                                                       [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       read_reg_from = [b1(0), b1(1), b1(0), b1(0)]))),
            # NAH.
            IntraCgraPktType(0, 8, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y, 
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 3,
                                                       ctrl = CtrlType(OPT_NAH,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

            # Skips first time incoming from east tile via routing xbar.
            IntraCgraPktType(0, 8, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y, 
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 0,
                                                       ctrl = CtrlType(routing_xbar_outport = [
                                                           TileInType(3), TileInType(0), TileInType(0), TileInType(0),
                                                           TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                       data = DataType(1, 1))),

            # Launch the tile.
            IntraCgraPktType(0, 8, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y,  payload = CgraPayloadType(CMD_LAUNCH))
        ],

        # tile 9
        [
            # Const for ADD_CONST.
            IntraCgraPktType(0, 9, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y,  payload = CgraPayloadType(CMD_CONST, data = DataType(kLoopIncrement, 1))),

            # Pre-configure per-tile config count per iter.
            IntraCgraPktType(0, 9, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y,  payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter, 1))),

            # Pre-configure per-tile total config count.
            IntraCgraPktType(0, 9, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y,  payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps, 1))),

            # NAH.
            IntraCgraPktType(0, 9, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y, 
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                       ctrl = CtrlType(OPT_NAH,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

            # ADD_CONST.
            IntraCgraPktType(0, 9, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y, 
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                       ctrl = CtrlType(OPT_ADD_CONST,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(3), TileInType(0), TileInType(0), TileInType(0)],
                                                                       # Sends to south tile5 and self reg (cluster 1).
                                                                       [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0)],
                                                                       # 2 indicates the FU xbar port (instead of const queue or routing xbar port).
                                                                       write_reg_from = [b2(0), b2(2), b2(0), b2(0)],))),
            # NAH.
            IntraCgraPktType(0, 9, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y, 
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                       ctrl = CtrlType(OPT_NAH,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),
            # GRANT_PREDICATE.
            IntraCgraPktType(0, 9, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y, 
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 3,
                                                       ctrl = CtrlType(OPT_GRT_PRED,
                                                                       # Swaps the first and second operands as the second one is
                                                                       # by default treated as the condition.
                                                                       [FuInType(2), FuInType(1), FuInType(0), FuInType(0)],
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(2), TileInType(0), TileInType(0), TileInType(0)],
                                                                       # Sends result to west tile8.
                                                                       [FuOutType(0), FuOutType(0), FuOutType(1), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       read_reg_from = [b1(0), b1(1), b1(0), b1(0)]))),

            # Launch the tile.
            IntraCgraPktType(0, 9, 0, cgra_1_id, 0, 0, cgra_1_x, cgra_1_y,  payload = CgraPayloadType(CMD_LAUNCH))
        ]
    ]

    src_query_pkt = \
        [
            # IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = kStoreAddress)),
        ]

    expected_complete_sink_out_pkg = \
        [
            IntraCgraPktType(1, 16, cgra_0_id, 0, cgra_0_x, cgra_0_y, 0, 0, payload = CgraPayloadType(CMD_COMPLETE, DataType(kExpectedOutput, 1, 0, 0), ctrl = CtrlType(OPT_RET))),
            IntraCgraPktType(1, 16, cgra_1_id, 0, cgra_1_x, cgra_1_y, 0, 0, payload = CgraPayloadType(CMD_COMPLETE, DataType(kExpectedOutput, 1, 0, 0), ctrl = CtrlType(OPT_RET))),
        ]
    expected_mem_sink_out_pkt = \
        [
            # IntraCgraPktType(dst = 16, payload = CgraPayloadType(CMD_LOAD_RESPONSE, data = DataType(kExpectedOutput, 1), data_addr = 16)),
        ]

    for activation in preload_data:
        src_ctrl_pkt.extend(activation)
    for src_opt in src_opt_pkt_cgra_0:
        src_ctrl_pkt.extend(src_opt)
    for src_opt in src_opt_pkt_cgra_1:
        src_ctrl_pkt.extend(src_opt)

    expected_sink_out_pkt.extend(expected_complete_sink_out_pkg)
    expected_sink_out_pkt.extend(expected_mem_sink_out_pkt)

    # Expects all the fields on the output is exactly same as provided golden reference.
    cmp_func = lambda a, b : a.payload.data == b.payload.data and \
                             a.payload.cmd == b.payload.cmd and \
                             a.payload.ctrl.operation == b.payload.ctrl.operation and \
                             a.src == b.src and \
                             a.dst == b.dst and \
                             a.src_cgra_id == b.src_cgra_id and \
                             a.dst_cgra_id == b.dst_cgra_id and \
                             a.src_cgra_x == b.src_cgra_x and \
                             a.src_cgra_y == b.src_cgra_y and \
                             a.dst_cgra_x == b.dst_cgra_x and \
                             a.dst_cgra_y == b.dst_cgra_y

  th = TestHarness(DUT, FunctionUnit, FuList, IntraCgraPktType,
                   num_cgra_rows, num_cgra_columns,
                   num_x_tiles_per_cgra, num_y_tiles_per_cgra, ctrl_mem_size, data_mem_size_global,
                   data_mem_size_per_bank, num_banks_per_cgra,
                   num_registers_per_reg_bank, src_ctrl_pkt, src_query_pkt,
                   ctrl_steps_per_iter, ctrl_steps_total, mem_access_is_combinational,
                   controller2addr_map, expected_sink_out_pkt, cmp_func)
  return th

def test_sim_homo_2x2_2x2(cmdline_opts):
  th = initialize_test_harness(cmdline_opts,
                               num_cgra_rows = 2,
                               num_cgra_columns = 2,
                               num_x_tiles_per_cgra = 2,
                               num_y_tiles_per_cgra = 2,
                               num_banks_per_cgra = 2,
                               data_mem_size_per_bank = 16,
                               mem_access_is_combinational = False)
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
                               data_mem_size_per_bank = 256,
                               mem_access_is_combinational = False)
  translate_model(th, ['dut'])

def test_tapeout_2x2_2x2(cmdline_opts):
  th = initialize_test_harness(cmdline_opts,
                               num_cgra_rows = 2,
                               num_cgra_columns = 2,
                               num_x_tiles_per_cgra = 2,
                               num_y_tiles_per_cgra = 2,
                               num_banks_per_cgra = 4,
                               data_mem_size_per_bank = 128,
                               mem_access_is_combinational = False)
  translate_model(th, ['dut'])

def test_multi_CGRA_systolic_2x2_2x2(cmdline_opts):
  th = initialize_test_harness(cmdline_opts,
                               num_cgra_rows = 2,
                               num_cgra_columns = 2,
                               num_x_tiles_per_cgra = 2,
                               num_y_tiles_per_cgra = 2,
                               num_banks_per_cgra = 2,
                               data_mem_size_per_bank = 16,
                               mem_access_is_combinational = True,
                               test_name = 'test_systolic')

  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                      ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                       'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)


def test_multi_CGRA_systolic_2x2_2x2_non_combinational_mem_access(cmdline_opts):
  th = initialize_test_harness(cmdline_opts,
                               num_cgra_rows = 2,
                               num_cgra_columns = 2,
                               num_x_tiles_per_cgra = 2,
                               num_y_tiles_per_cgra = 2,
                               num_banks_per_cgra = 2,
                               data_mem_size_per_bank = 16,
                               mem_access_is_combinational = False,
                               test_name = 'test_systolic')

  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                      ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                       'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)

def test_multi_CGRA_fir_scalar(cmdline_opts):
  th = initialize_test_harness(cmdline_opts,
                               num_cgra_rows = 2,
                               num_cgra_columns = 2,
                               num_x_tiles_per_cgra = 4,
                               num_y_tiles_per_cgra = 4,
                               num_banks_per_cgra = 2,
                               data_mem_size_per_bank = 16,
                               mem_access_is_combinational = True,
                               test_name = 'test_fir_scalar')

  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                      ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                       'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)

def test_multi_CGRA_fir_scalar_translation(cmdline_opts):
  th = initialize_test_harness(cmdline_opts,
                               num_cgra_rows = 2,
                               num_cgra_columns = 2,
                               num_x_tiles_per_cgra = 4,
                               num_y_tiles_per_cgra = 4,
                               num_banks_per_cgra = 2,
                               data_mem_size_per_bank = 16,
                               mem_access_is_combinational = True)
  th.dut.set_metadata(VerilogTranslationPass.explicit_module_name, "MeshMultiCgraRTL__explicit")
  th.dut.set_metadata(VerilogTranslationPass.explicit_file_name, "MeshMultiCgraRTL__explicit__pickled.v")
  translate_model(th, ['dut'])

def test_multi_CGRA_fir_vector(cmdline_opts):
  th = initialize_test_harness(cmdline_opts,
                               num_cgra_rows = 2,
                               num_cgra_columns = 2,
                               num_x_tiles_per_cgra = 4,
                               num_y_tiles_per_cgra = 4,
                               num_banks_per_cgra = 2,
                               data_mem_size_per_bank = 16,
                               mem_access_is_combinational = True,
                               test_name = 'test_fir_vector')

  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                      ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                       'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)

def test_multi_CGRA_fir_vector_global_reduce(cmdline_opts):
  th = initialize_test_harness(cmdline_opts,
                               num_cgra_rows = 2,
                               num_cgra_columns = 2,
                               num_x_tiles_per_cgra = 4,
                               num_y_tiles_per_cgra = 4,
                               num_banks_per_cgra = 2,
                               data_mem_size_per_bank = 16,
                               mem_access_is_combinational = True,
                               test_name = 'test_fir_vector_global_reduce')

  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                      ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                       'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)
