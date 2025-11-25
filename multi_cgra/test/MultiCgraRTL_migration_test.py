"""
==========================================================================
MultiCgraRTL_migration_test.py
==========================================================================
Test cases for multi-CGRA with migratable FIR kernel.

Author : Cheng Tan
  Date : Nov 1, 2025
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
from ...fu.quadra.FourIncCmpNotGrantRTL import FourIncCmpNotGrantRTL
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
                per_cgra_topology,
                controller2addr_map, expected_sink_out_pkt,
                cmp_func,
                support_task_switching):

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
                FunctionUnit, FuList, per_cgra_topology, controller2addr_map, 
                support_task_switching)

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

def run_sim(test_harness, max_cycles = 400):
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
                            num_tile_ports = 4,
                            num_banks_per_cgra = 2,
                            data_mem_size_per_bank = 16,
                            mem_access_is_combinational = True,
                            per_cgra_topology = 'Mesh',
                            test_name = 'test_fir_scalar'):
  num_tile_inports = num_tile_ports
  num_tile_outports = num_tile_ports
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
            FourIncCmpNotGrantRTL,
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

  // When i is in range[2, 10):
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
  kLoopUpperBound = 10
  kCtrlCountPerIter = 3
  kCtrlCountPerIter_migration = 2
  ctrl_steps_per_iter = kCtrlCountPerIter
  # Though kTotalCtrlSteps is way more than required loop iteration count,
  # the stored result should still be correct thanks to the grant predicate.
  kTotalCtrlSteps = kCtrlCountPerIter * \
                    (kLoopUpperBound - kLoopLowerBound) + \
                    100
  kTotalCtrlSteps_migration = kCtrlCountPerIter_migration * \
                          (kLoopUpperBound - kLoopLowerBound) + \
                          100
  ctrl_steps_total = kTotalCtrlSteps
  kExpectedOutput = 2215
  support_task_switching = False

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

  if test_name == 'test_fir_scalar_fused':
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
    # After fusion:
    #
    #           0(phi_const) <---------┐
    #          /       |      \        |
    #     2(+,ld)  4(+,ld)  8(+,cmp,not,grant_pred)
    #          \      /        |
    #           \    /         |
    #            6(x)          |
    #             |            |
    #      ┌---> 7(+)          |
    #      |    /   \          |
    #  1(phi_const)  11(grant_predicate)
    #                          |
    #                       13(ret)
    #
    # Corresponding mapping (II = 3):
    '''
        ↑ Y
        |
    (0,1)|  🔳   🔳
        |
    (0,0)|  🔳   🔳
        +-----------→ X
          (1,0) (2,0)

    =============================
    cycle 0:
    [   6(x)   ←  0(phi_const)  ]
              ↙↘        ↺
    [ 1(phi_c) → 11(grant_pred) ]
                        ↺
    =============================
    cycle 1:
    [ 2(+ ld)       8(fused)    ]
        ↺ ↑          ↓ ↺
    [ 4(+ ld)   ←     7(+)      ]
                        ↺
    =============================
    cycle 2:
    [    🔳            🔳       ]

    [    🔳         13(ret)     ]

    =============================
    '''

    src_opt_pkt = [
        # tile 0
        [
            # Const for ADD_CONST_LD.
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONST, data = DataType(kCoefficientBaseAddress, 1))),

            # Const for PHI_CONST.
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONST, data = DataType(kSumInitValue, 1))),

            # Pre-configure per-tile config count per iter.
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter, 1))),

            # Pre-configure per-tile total config count.
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps, 1))),

            # PHI_CONST, indicating the address is a const.
            IntraCgraPktType(0, 0,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                       ctrl = CtrlType(OPT_PHI_CONST,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(4), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),
            # ADD_CONST_LD.
            IntraCgraPktType(0, 0,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                       ctrl = CtrlType(OPT_ADD_CONST_LD,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(6), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),
            # NAH.
            IntraCgraPktType(0, 0,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                       ctrl = CtrlType(OPT_NAH,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

            # Pre-configure the prologue count for both operation and routing.
            IntraCgraPktType(0, 0,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 0,
                                                       data = DataType(1, 1))),
            # Prologue for phi_const should be carefully set. i.e., phi_const
            # by default should have a prologue to skip the first time non-const
            # operand arrival. So if it also needs prologue due to loop pipelining,
            # the prologue count should be incremented by 1. Therefore, we set
            # it to 2 here.
            IntraCgraPktType(0, 0,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 0,
                                                       ctrl = CtrlType(routing_xbar_outport = [
                                                           TileInType(3), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                           TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                       data = DataType(2, 1))),
            IntraCgraPktType(0, 0,
                            payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU_CROSSBAR, ctrl_addr = 0,
                                                      ctrl = CtrlType(fu_xbar_outport = [
                                                          FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
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

            # GRT_PRED.
            IntraCgraPktType(0, 1,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                       ctrl = CtrlType(OPT_GRT_PRED,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(1), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0)],
                                                                       # 2 indicates the FU xbar port (instead of const queue or routing xbar port).
                                                                       write_reg_from = [b2(0), b2(2), b2(0), b2(0)],
                                                                       read_reg_from = [b1(1), b1(0), b1(0), b1(0)]))),

            # ADD.
            IntraCgraPktType(0, 1,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                       ctrl = CtrlType(OPT_ADD,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(5), TileInType(3), TileInType(0), TileInType(0)],
                                                                       # Sends to west and self first reg cluster.
                                                                       [FuOutType(0), FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       write_reg_from = [b2(2), b2(0), b2(0), b2(0)]))),
            # RET.
            IntraCgraPktType(0, 1,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                       ctrl = CtrlType(OPT_RET,
                                                                       # The first 2 indicates the first operand is from the second inport,
                                                                       # which is actually from the second register cluster rather than the
                                                                       # inport channel, indicated by the `read_reg_from_code`.
                                                                       [FuInType(2), FuInType(0), FuInType(0), FuInType(0)],
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       read_reg_from = [b1(0), b1(1), b1(0), b1(0)]))),

            IntraCgraPktType(0, 1,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 0,
                                                       data = DataType(2, 1))),
            IntraCgraPktType(0, 1,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 0,
                                                       ctrl = CtrlType(routing_xbar_outport = [
                                                           TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                           TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                       data = DataType(2, 1))),
            IntraCgraPktType(0, 1,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU_CROSSBAR, ctrl_addr = 0,
                                                       ctrl = CtrlType(fu_xbar_outport = [
                                                           FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                           FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]),
                                                       data = DataType(2, 1))),
            IntraCgraPktType(0, 1,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 1,
                                                       data = DataType(1, 1))),
            IntraCgraPktType(0, 1,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 1,
                                                       ctrl = CtrlType(routing_xbar_outport = [
                                                           TileInType(2), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                           TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                       data = DataType(1, 1))),
            IntraCgraPktType(0, 1,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 1,
                                                       ctrl = CtrlType(routing_xbar_outport = [
                                                           TileInType(4), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                           TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                       data = DataType(1, 1))),
            IntraCgraPktType(0, 1,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU_CROSSBAR, ctrl_addr = 1,
                                                       ctrl = CtrlType(fu_xbar_outport = [
                                                           FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                           FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]),
                                                       data = DataType(1, 1))),
            IntraCgraPktType(0, 1,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 2,
                                                       data = DataType(2, 1))),

            # Launch the tile.
            IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_LAUNCH))
        ],

        # tile 2
        [
            # Const for ADD_CONST_LD.
            IntraCgraPktType(0, 2, payload = CgraPayloadType(CMD_CONST, data = DataType(kInputBaseAddress, 1))),

            # Pre-configure per-tile config count per iter.
            IntraCgraPktType(0, 2, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter, 1))),

            # Pre-configure per-tile total config count.
            IntraCgraPktType(0, 2, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps, 1))),

            # MUL.
            IntraCgraPktType(0, 2,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                       ctrl = CtrlType(OPT_MUL,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(2), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(1), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       read_reg_from = [b1(1), b1(0), b1(0), b1(0)]))),
            # ADD_CONST_LD.
            IntraCgraPktType(0, 2,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                       ctrl = CtrlType(OPT_ADD_CONST_LD,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                         TileInType(4), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       write_reg_from = [b2(2), b2(0), b2(0), b2(0)]))),
            # NAH.
            IntraCgraPktType(0, 2,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                       ctrl = CtrlType(OPT_NAH,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

            IntraCgraPktType(0, 2,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 0,
                                                       data = DataType(1, 1))),
            IntraCgraPktType(0, 2,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 0,
                                                       ctrl = CtrlType(routing_xbar_outport = [
                                                           TileInType(1), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                           TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                       data = DataType(1, 1))),
            IntraCgraPktType(0, 2,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU_CROSSBAR, ctrl_addr = 0,
                                                       ctrl = CtrlType(fu_xbar_outport = [
                                                           FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                           FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]),
                                                       data = DataType(1, 1))),

            # Launch the tile.
            IntraCgraPktType(0, 2, payload = CgraPayloadType(CMD_LAUNCH))
        ],

        # tile 3
        [
            # Const for PHI_CONST.
            IntraCgraPktType(0, 3, payload = CgraPayloadType(CMD_CONST, data = DataType(kLoopLowerBound, 1))),

            # Const for CMP.
            IntraCgraPktType(0, 3, payload = CgraPayloadType(CMD_CONST, data = DataType(kLoopUpperBound, 1))),

            # Pre-configure per-tile config count per iter.
            IntraCgraPktType(0, 3, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter, 1))),

            # Pre-configure per-tile total config count.
            IntraCgraPktType(0, 3, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps, 1))),

            # PHI_CONST.
            IntraCgraPktType(0, 3,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                       ctrl = CtrlType(OPT_PHI_CONST,
                                                                       # The first 2 indicates the first operand is from the second inport,
                                                                       # which is actually from the second register cluster rather than the
                                                                       # inport channel, indicated by the `read_reg_from_code`.
                                                                       [FuInType(2), FuInType(0), FuInType(0), FuInType(0)],
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(1),
                                                                        FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       write_reg_from = [b2(2), b2(0), b2(0), b2(0)],
                                                                       read_reg_from = [b1(0), b1(1), b1(0), b1(0)]))),

            # INC_NE_CONST_NOT_GRT.
            IntraCgraPktType(0, 3,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                       ctrl = CtrlType(OPT_INC_NE_CONST_NOT_GRT,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       # Sends two outputs to south and self reg, respectively.
                                                                       [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(2), FuOutType(0), FuOutType(0)],
                                                                       # 2 indicates the FU xbar port (instead of const queue or routing xbar port).
                                                                       write_reg_from = [b2(0), b2(2), b2(0), b2(0)],
                                                                       read_reg_from = [b1(1), b1(0), b1(0), b1(0)]))),
            # NAH.
            IntraCgraPktType(0, 3,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                       ctrl = CtrlType(OPT_NAH,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

            # Launch the tile.
            IntraCgraPktType(0, 3, payload = CgraPayloadType(CMD_LAUNCH))
        ],
    ]

    src_query_pkt = \
        [
            # IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = kStoreAddress)),
        ]

    expected_complete_sink_out_pkg = \
        [
            IntraCgraPktType(src = 1, dst = num_tiles, payload = CgraPayloadType(CMD_COMPLETE, DataType(kExpectedOutput, 1, 0, 0), ctrl = CtrlType(OPT_RET))) for _ in range(1)
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

  elif test_name == 'test_fir_scalar_migrated':
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
    # After fusion:
    #
    #           0(phi_const) <---------┐
    #          /       |      \        |
    #     2(+,ld)  4(+,ld)  8(+,cmp,not,grant_pred)
    #          \      /        |
    #           \    /         |
    #            6(x)          |
    #             |            |
    #      ┌---> 7(+)          |
    #      |    /   \          |
    #  1(phi_const)  11(grant_predicate)
    #                          |
    #                       13(ret)
    #
    # Corresponding mapping (II = 2) with 2 CGRAs:
    '''
        ↑ Y
        |
    (0,1)|  🔳   🔳
        |
    (0,0)|  🔳   🔳
        +-----------→ X
          (1,0) (2,0)

    =============================
    cycle 0:
    [    🔳            🔳       ]

    [    🔳         13(ret)     ]
    - - - - - - - - - - - - - - -

    [   6(x)   ←  0(phi_const)  ]
              ↙↘       ↺ ↑
    [ 1(phi_c) → 11(grant_pred) ]

    =============================
    cycle 1:
    [    🔳            🔳       ]

    [    🔳            🔳       ]
    - - - - - - - - - - - - - - -
                        ↑
    [ 2(+ ld)       8(fused)    ]
        ↺ ↑            ↓ ↺
    [ 4(+ ld)   ←     7(+)      ]
                        ↺
    =============================
    '''

    # Updates the II from 3 to 2 thanks to the migration.
    kCtrlCountPerIter = 2

    cgra_2_id = 2
    cgra_2_x = 0
    cgra_2_y = 1

    src_opt_pkt = [
        # cgra 0, tile 0
        [
            # Const for ADD_CONST_LD.
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONST, data = DataType(kCoefficientBaseAddress, 1))),

            # Const for PHI_CONST.
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONST, data = DataType(kSumInitValue, 1))),

            # Pre-configure per-tile config count per iter.
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter, 1))),

            # Pre-configure per-tile total config count.
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps, 1))),

            # PHI_CONST, indicating the address is a const.
            IntraCgraPktType(0, 0,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                       ctrl = CtrlType(OPT_PHI_CONST,
                                                                       fu_in_code,
                                                                       # [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       #  TileInType(3), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(4), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),
            # ADD_CONST_LD.
            IntraCgraPktType(0, 0,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                       ctrl = CtrlType(OPT_ADD_CONST_LD,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(6), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

            # Pre-configure the prologue count for both operation and routing.
            IntraCgraPktType(0, 0,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 0,
                                                       data = DataType(1, 1))),
            # Prologue for phi_const should be carefully set. i.e., phi_const
            # by default should have a prologue to skip the first time non-const
            # operand arrival. So if it also needs prologue due to loop pipelining,
            # the prologue count should be incremented by 1. Therefore, we set
            # it to 2 here.
            IntraCgraPktType(0, 0,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 0,
                                                       ctrl = CtrlType(routing_xbar_outport = [
                                                           TileInType(3), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                           TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                       data = DataType(2, 1))),
            IntraCgraPktType(0, 0,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU_CROSSBAR, ctrl_addr = 0,
                                                       ctrl = CtrlType(fu_xbar_outport = [
                                                           FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                           FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]),
                                                       data = DataType(1, 1))),

            # Launch the tile.
            IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_LAUNCH))
        ],

        # cgra 0, tile 1
        [
            # Pre-configure per-tile config count per iter.
            IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter, 1))),

            # Pre-configure per-tile total config count.
            IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps, 1))),

            # GRT_PRED.
            IntraCgraPktType(0, 1,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                       ctrl = CtrlType(OPT_GRT_PRED,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(1), TileInType(0), TileInType(0)],
                                                                       [FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       read_reg_from = [b1(1), b1(0), b1(0), b1(0)]))),

            # ADD.
            IntraCgraPktType(0, 1,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                       ctrl = CtrlType(OPT_ADD,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(5), TileInType(3), TileInType(0), TileInType(0)],
                                                                       # Sends to west and self first reg cluster.
                                                                       [FuOutType(0), FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       write_reg_from = [b2(2), b2(0), b2(0), b2(0)]))),

            IntraCgraPktType(0, 1,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 0,
                                                       data = DataType(2, 1))),
            IntraCgraPktType(0, 1,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 0,
                                                       ctrl = CtrlType(routing_xbar_outport = [
                                                           TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                           TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                       data = DataType(2, 1))),
            IntraCgraPktType(0, 1,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU_CROSSBAR, ctrl_addr = 0,
                                                       ctrl = CtrlType(fu_xbar_outport = [
                                                           FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                           FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]),
                                                       data = DataType(2, 1))),
            IntraCgraPktType(0, 1,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 1,
                                                       data = DataType(1, 1))),
            IntraCgraPktType(0, 1,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 1,
                                                       ctrl = CtrlType(routing_xbar_outport = [
                                                           TileInType(2), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                           TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                       data = DataType(1, 1))),
            IntraCgraPktType(0, 1,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 1,
                                                       ctrl = CtrlType(routing_xbar_outport = [
                                                           TileInType(4), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                           TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                       data = DataType(1, 1))),
            IntraCgraPktType(0, 1,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU_CROSSBAR, ctrl_addr = 1,
                                                       ctrl = CtrlType(fu_xbar_outport = [
                                                           FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                           FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]),
                                                       data = DataType(1, 1))),

            # Launch the tile.
            IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_LAUNCH))
        ],

        # cgra 0, tile 2
        [
            # Const for ADD_CONST_LD.
            IntraCgraPktType(0, 2, payload = CgraPayloadType(CMD_CONST, data = DataType(kInputBaseAddress, 1))),

            # Pre-configure per-tile config count per iter.
            IntraCgraPktType(0, 2, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter, 1))),

            # Pre-configure per-tile total config count.
            IntraCgraPktType(0, 2, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps, 1))),

            # MUL.
            IntraCgraPktType(0, 2,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                       ctrl = CtrlType(OPT_MUL,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(2), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(1), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       read_reg_from = [b1(1), b1(0), b1(0), b1(0)]))),
            # ADD_CONST_LD.
            IntraCgraPktType(0, 2,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                       ctrl = CtrlType(OPT_ADD_CONST_LD,
                                                                       fu_in_code,
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(4), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       write_reg_from = [b2(2), b2(0), b2(0), b2(0)]))),

            IntraCgraPktType(0, 2,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 0,
                                                       data = DataType(1, 1))),
            IntraCgraPktType(0, 2,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 0,
                                                       ctrl = CtrlType(routing_xbar_outport = [
                                                           TileInType(1), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                           TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                       data = DataType(1, 1))),
            IntraCgraPktType(0, 2,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU_CROSSBAR, ctrl_addr = 0,
                                                       ctrl = CtrlType(fu_xbar_outport = [
                                                           FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                           FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]),
                                                       data = DataType(1, 1))),

            # Launch the tile.
            IntraCgraPktType(0, 2, payload = CgraPayloadType(CMD_LAUNCH))
        ],

        # cgra 0, tile 3
        [
            # Const for PHI_CONST.
            IntraCgraPktType(0, 3, payload = CgraPayloadType(CMD_CONST, data = DataType(kLoopLowerBound, 1))),

            # Const for CMP.
            IntraCgraPktType(0, 3, payload = CgraPayloadType(CMD_CONST, data = DataType(kLoopUpperBound, 1))),

            # Pre-configure per-tile config count per iter.
            IntraCgraPktType(0, 3, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter, 1))),

            # Pre-configure per-tile total config count.
            IntraCgraPktType(0, 3, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps, 1))),

            # PHI_CONST.
            IntraCgraPktType(0, 3,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                       ctrl = CtrlType(OPT_PHI_CONST,
                                                                       # The first 2 indicates the first operand is from the second inport,
                                                                       # which is actually from the second register cluster rather than the
                                                                       # inport channel, indicated by the `read_reg_from_code`.
                                                                       [FuInType(2), FuInType(0), FuInType(0), FuInType(0)],
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(1),
                                                                        FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                       write_reg_from = [b2(2), b2(0), b2(0), b2(0)],
                                                                       read_reg_from = [b1(0), b1(1), b1(0), b1(0)]))),

            # INC_NE_CONST_NOT_GRT.
            IntraCgraPktType(0, 3,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                       ctrl = CtrlType(OPT_INC_NE_CONST_NOT_GRT,
                                                                       fu_in_code,
                                                                       [TileInType(2), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                       # Sends two outputs to south and self reg, respectively.
                                                                       [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(2), FuOutType(0), FuOutType(0)],
                                                                       # 2 indicates the FU xbar port (instead of const queue or routing xbar port).
                                                                       write_reg_from = [b2(0), b2(2), b2(0), b2(0)],
                                                                       read_reg_from = [b1(1), b1(0), b1(0), b1(0)]))),

            IntraCgraPktType(0, 3,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 1,
                                                       ctrl = CtrlType(routing_xbar_outport = [
                                                           TileInType(1), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                           TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                       data = DataType(2, 1))),

            # Launch the tile.
            IntraCgraPktType(0, 3, payload = CgraPayloadType(CMD_LAUNCH))
        ],

        # cgra 2, tile 1
        [
            # Pre-configure per-tile config count per iter. We only needs 1 control signal here if NAH is not provided.
            IntraCgraPktType(0, 1, 0, cgra_2_id, 0, 0, cgra_2_x, cgra_2_y, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(1, 1))),

            # Pre-configure per-tile total config count.
            IntraCgraPktType(0, 1, 0, cgra_2_id, 0, 0, cgra_2_x, cgra_2_y, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps, 1))),

            # RET.
            IntraCgraPktType(0, 1, 0, cgra_2_id, 0, 0, cgra_2_x, cgra_2_y,
                             payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                       ctrl = CtrlType(OPT_RET,
                                                                       [FuInType(1), FuInType(0), FuInType(0), FuInType(0)],
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        # Input of `return` is from south port.
                                                                        TileInType(2), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),
            # Launch the tile.
            IntraCgraPktType(0, 1, 0, cgra_2_id, 0, 0, cgra_2_x, cgra_2_y, payload = CgraPayloadType(CMD_LAUNCH))
        ],
    ]

    src_query_pkt = \
        [
            # IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = kStoreAddress)),
        ]

    expected_complete_sink_out_pkg = \
        [
            IntraCgraPktType(src = 1, dst = num_tiles,
                             src_cgra_id = cgra_2_id,
                             dst_cgra_id = 0,
                             src_cgra_x = cgra_2_x,
                             src_cgra_y = cgra_2_y,
                             dst_cgra_x = 0,
                             dst_cgra_y = 0,
                             payload = CgraPayloadType(CMD_COMPLETE, DataType(kExpectedOutput, 1, 0, 0), ctrl = CtrlType(OPT_RET))) for _ in range(1)
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


  # This branch is to test the dynamic migration functionality:
  elif test_name == 'test_fir_scalar_dynamic_migration':
    # Before and after migration can be regarded as two tasks,
    # therefore here we enable task switching funtionality to CGRAs.
    support_task_switching = True
    kCtrlCountPerIter = 3

    cgra_2_id = 2
    cgra_2_x = 0
    cgra_2_y = 1

    src_opt_pkt = [
      # ---------------------------------------- Loads kernel configs to all tiles -----------------------------------------------    
      # cgra 0, tile 0
      [
        # PHI_CONST, indicating the address is a const.
        IntraCgraPktType(0, 0,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                     ctrl = CtrlType(OPT_PHI_CONST,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), 
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      # East -> FU
                                                                      TileInType(4), TileInType(0), TileInType(0), TileInType(0)],
                                                                                                                # FU -> East
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(1), 
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),
        # ADD_CONST_LD.
        IntraCgraPktType(0, 0,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                     ctrl = CtrlType(OPT_ADD_CONST_LD,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), 
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      # NorthEast -> FU
                                                                      TileInType(6), TileInType(0), TileInType(0), TileInType(0)],
                                                                      # FU -> North
                                                                     [FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0), 
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),
        # NAH.
        IntraCgraPktType(0, 0,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                     ctrl = CtrlType(OPT_NAH,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), 
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), 
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),
      ],

      # cgra 0, tile 1
      [
        # GRT_PRED.
        IntraCgraPktType(0, 1,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                     ctrl = CtrlType(OPT_GRT_PRED,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), 
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                                     # North -> FU
                                                                      TileInType(0), TileInType(1), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), 
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                                    # FU -> FU
                                                                      FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0)],
                                                                     # 2 indicates the FU xbar port (instead of const queue or routing xbar port).
                                                                     write_reg_from = [b2(0), b2(2), b2(0), b2(0)],
                                                                     read_reg_from = [b1(1), b1(0), b1(0), b1(0)]))),
        # ADD.
        IntraCgraPktType(0, 1,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                     ctrl = CtrlType(OPT_ADD,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), 
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      # NorthWest -> FU,  # West -> FU
                                                                      TileInType(5),      TileInType(3), TileInType(0), TileInType(0)],
                                                                     # Sends to west and self first reg cluster.
                                                                                                  # FU -> West
                                                                     [FuOutType(0), FuOutType(0), FuOutType(1), FuOutType(0), 
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      # FU -> FU
                                                                      FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                     write_reg_from = [b2(2), b2(0), b2(0), b2(0)]))),
        # RET.
        IntraCgraPktType(0, 1,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                     ctrl = CtrlType(OPT_RET,
                                                                     # The first 2 indicates the first operand is from the second inport,
                                                                     # which is actually from the second register cluster rather than the
                                                                     # inport channel, indicated by the `read_reg_from_code`.
                                                                     [FuInType(2), FuInType(0), FuInType(0), FuInType(0)],
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), 
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), 
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                     read_reg_from = [b1(0), b1(1), b1(0), b1(0)]))),
      ],

      # cgra 0, tile 2
      [
        # MUL.
        IntraCgraPktType(0, 2,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                     ctrl = CtrlType(OPT_MUL,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), 
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                                     # FU -> South
                                                                      TileInType(0), TileInType(2), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), 
                                                                                                  # FU -> SouthEast
                                                                      FuOutType(0), FuOutType(0), FuOutType(1), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                     read_reg_from = [b1(1), b1(0), b1(0), b1(0)]))),
        # ADD_CONST_LD.
        IntraCgraPktType(0, 2,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                     ctrl = CtrlType(OPT_ADD_CONST_LD,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), 
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      # East -> FU
                                                                      TileInType(4), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), 
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      # FU -> FU
                                                                      FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                     write_reg_from = [b2(2), b2(0), b2(0), b2(0)]))),
        # NAH.
        IntraCgraPktType(0, 2,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                     ctrl = CtrlType(OPT_NAH,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), 
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), 
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),
      ],

      # cgra 0, tile 3
      [
        # PHI_CONST.
        IntraCgraPktType(0, 3,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                     ctrl = CtrlType(OPT_PHI_CONST,
                                                                     # The first 2 indicates the first operand is from the second inport,
                                                                     # which is actually from the second register cluster rather than the
                                                                     # inport channel, indicated by the `read_reg_from_code`.
                                                                     [FuInType(2), FuInType(0), FuInType(0), FuInType(0)],
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), 
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                                                  # FU -> West
                                                                     [FuOutType(0), FuOutType(0), FuOutType(1), FuOutType(0), 
                                                                                                                # FU -> SouthWest
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(1),
                                                                      # FU -> FU
                                                                      FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                     write_reg_from = [b2(2), b2(0), b2(0), b2(0)],
                                                                     read_reg_from = [b1(0), b1(1), b1(0), b1(0)]))),

        # INC_NE_CONST_NOT_GRT.
        IntraCgraPktType(0, 3,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                     ctrl = CtrlType(OPT_INC_NE_CONST_NOT_GRT,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), 
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     # Sends two outputs to south and self reg, respectively.
                                                                                    # FU -> North
                                                                     [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0), 
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                                    # FU -> FU
                                                                      FuOutType(0), FuOutType(2), FuOutType(0), FuOutType(0)],
                                                                     # 2 indicates the FU xbar port (instead of const queue or routing xbar port).
                                                                     write_reg_from = [b2(0), b2(2), b2(0), b2(0)],
                                                                     read_reg_from = [b1(1), b1(0), b1(0), b1(0)]))),
        # NAH.
        IntraCgraPktType(0, 3,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                     ctrl = CtrlType(OPT_NAH,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), 
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), 
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),
      ],

      # --------------------------------------------- Starts executing the kernel ------------------------------------------------------------
      # cgra 0, tile 0
      [
        # Const for ADD_CONST_LD.
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONST, data = DataType(kCoefficientBaseAddress, 1))),

        # Const for PHI_CONST.
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONST, data = DataType(kSumInitValue, 1))),

        # Pre-configure per-tile config count per iter.
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter, 1))),

        # Pre-configure per-tile total config count.
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps, 1))),

        # Pre-configure the prologue count for both operation and routing.
        IntraCgraPktType(0, 0,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 0,
                                                       data = DataType(1, 1))),
        # Prologue for phi_const should be carefully set. i.e., phi_const
        # by default should have a prologue to skip the first time non-const
        # operand arrival. So if it also needs prologue due to loop pipelining,
        # the prologue count should be incremented by 1. Therefore, we set
        # it to 2 here.
        IntraCgraPktType(0, 0,
                             payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 0,
                                                       ctrl = CtrlType(routing_xbar_outport = [
                                                           # West -> North
                                                           TileInType(3), TileInType(0), TileInType(0), TileInType(0), 
                                                           TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                           TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                       data = DataType(2, 1))),
        IntraCgraPktType(0, 0,
                            payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU_CROSSBAR, ctrl_addr = 0,
                                                      ctrl = CtrlType(fu_xbar_outport = [
                                                          FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), 
                                                          FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                          FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]),
                                                      data = DataType(1, 1))),

        # Launch the tile.
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_LAUNCH))
      ],

      # cgra 0, tile 1
      [
        # Pre-configure per-tile config count per iter.
        IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter, 1))),

        # Pre-configure per-tile total config count.
        IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps, 1))),

        IntraCgraPktType(0, 1,
                         payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 0,
                                                   data = DataType(2, 1))),
        IntraCgraPktType(0, 1,
                         payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 0,
                                                   ctrl = CtrlType(routing_xbar_outport = [
                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0), 
                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                   data = DataType(2, 1))),
        IntraCgraPktType(0, 1,
                         payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU_CROSSBAR, ctrl_addr = 0,
                                                   ctrl = CtrlType(fu_xbar_outport = [
                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), 
                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]),
                                                   data = DataType(2, 1))),
        IntraCgraPktType(0, 1,
                         payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 1,
                                                   data = DataType(1, 1))),
        IntraCgraPktType(0, 1,
                         payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 1,
                                                   ctrl = CtrlType(routing_xbar_outport = [
                                                       # South -> North
                                                       TileInType(2), TileInType(0), TileInType(0), TileInType(0), 
                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                   data = DataType(1, 1))),
        IntraCgraPktType(0, 1,
                         payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 1,
                                                   ctrl = CtrlType(routing_xbar_outport = [
                                                       # East -> North
                                                       TileInType(4), TileInType(0), TileInType(0), TileInType(0), 
                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                   data = DataType(1, 1))),
        IntraCgraPktType(0, 1,
                         payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU_CROSSBAR, ctrl_addr = 1,
                                                   ctrl = CtrlType(fu_xbar_outport = [
                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), 
                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]),
                                                   data = DataType(1, 1))),
        IntraCgraPktType(0, 1,
                         payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 2,
                                                   data = DataType(2, 1))),

        # Launch the tile.
        IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_LAUNCH))
      ],

      # cgra 0, tile 2
      [
        # Const for ADD_CONST_LD.
        IntraCgraPktType(0, 2, payload = CgraPayloadType(CMD_CONST, data = DataType(kInputBaseAddress, 1))),

        # Pre-configure per-tile config count per iter.
        IntraCgraPktType(0, 2, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter, 1))),

        # Pre-configure per-tile total config count.
        IntraCgraPktType(0, 2, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps, 1))),

        IntraCgraPktType(0, 2,
                         payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 0,
                                                   data = DataType(1, 1))),
        IntraCgraPktType(0, 2,
                         payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 0,
                                                   ctrl = CtrlType(routing_xbar_outport = [
                                                       # North -> North
                                                       TileInType(1), TileInType(0), TileInType(0), TileInType(0), 
                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                   data = DataType(1, 1))),
        IntraCgraPktType(0, 2,
                         payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU_CROSSBAR, ctrl_addr = 0,
                                                   ctrl = CtrlType(fu_xbar_outport = [
                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), 
                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]),
                                                   data = DataType(1, 1))),

        # Launch the tile.
        IntraCgraPktType(0, 2, payload = CgraPayloadType(CMD_LAUNCH))
      ],

      # cgra 0, tile 3
      [
        # Const for PHI_CONST.
        IntraCgraPktType(0, 3, payload = CgraPayloadType(CMD_CONST, data = DataType(kLoopLowerBound, 1))),

        # Const for CMP.
        IntraCgraPktType(0, 3, payload = CgraPayloadType(CMD_CONST, data = DataType(kLoopUpperBound, 1))),

        # Pre-configure per-tile config count per iter.
        IntraCgraPktType(0, 3, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter, 1))),

        # Pre-configure per-tile total config count.
        IntraCgraPktType(0, 3, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps, 1))),

        # Launch the tile.
        IntraCgraPktType(0, 3, payload = CgraPayloadType(CMD_LAUNCH))
      ],

      # ---------------------------------- Pauses execution and prepares for dynamic migration ----------------------------------------
      # Let all tiles free running for 6 cycles.
      # We repeately write the first data to addr 0 of memory bank to simulate the free-running.
      [ IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(10, 1), data_addr = 0)) for _ in range(6) ],

      # Sends preserving command to tile 0 to record accumulation results.
      [ IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_PRESERVE)) ],

      # Free running another 6 cycles to make sure tile 0 has already captured one accumulation result.
      [ IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(10, 1), data_addr = 0)) for _ in range(6) ],

      # Sends pausing command to tile 3 to record iteration results.
      [ IntraCgraPktType(0, 3, payload = CgraPayloadType(CMD_PAUSE)) ],

      # Free running another 6 cycles to make sure all data has been drained.
      [ IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(10, 1), data_addr = 0)) for _ in range(6) ],
      # Terminates all tiles after saving iteration and accumulation results.
      # Terminating refers to stop issuing configs from tile's config mem,
      # and clear all necessary values in various registers.
      [
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_TERMINATE)),
        IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_TERMINATE)),
        IntraCgraPktType(0, 2, payload = CgraPayloadType(CMD_TERMINATE)),
        IntraCgraPktType(0, 3, payload = CgraPayloadType(CMD_TERMINATE)),
      ],

      # Terminate double time to make sure all registers are cleared, ready for migration.
      [
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_TERMINATE)),
        IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_TERMINATE)),
        IntraCgraPktType(0, 2, payload = CgraPayloadType(CMD_TERMINATE)),
        IntraCgraPktType(0, 3, payload = CgraPayloadType(CMD_TERMINATE)),
      ],

      # ------------------------------------ Performs dynamic migration and resumes execution -------------------------------------------
      # cgra 0, tile 0
      [
        # Const for ADD_CONST_LD.
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONST, data = DataType(kCoefficientBaseAddress, 1))),

        # Const for PHI_CONST.
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONST, data = DataType(kSumInitValue, 1))),

        # Resets ctrl mem raddr.
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONFIG_CTRL_LOWER_BOUND, data = DataType(0, 1))),

        # Pre-configure per-tile config count per iter.
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter_migration, 1))),

        # Pre-configure per-tile total config count.
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps_migration, 1))),

        # Pre-configure the prologue count for both operation and routing.
        IntraCgraPktType(0, 0,
                         payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 0,
                                                   data = DataType(1, 1))),
        # Prologue for phi_const should be carefully set. i.e., phi_const
        # by default should have a prologue to skip the first time non-const
        # operand arrival. So if it also needs prologue due to loop pipelining,
        # the prologue count should be incremented by 1. Therefore, we set
        # it to 2 here.
        IntraCgraPktType(0, 0,
                         payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 0,
                                                   ctrl = CtrlType(routing_xbar_outport = [
                                                       # West -> North
                                                       TileInType(3), TileInType(0), TileInType(0), TileInType(0), 
                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                   data = DataType(2, 1))),
        IntraCgraPktType(0, 0,
                         payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU_CROSSBAR, ctrl_addr = 0,
                                                   ctrl = CtrlType(fu_xbar_outport = [
                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), 
                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]),
                                                   data = DataType(1, 1))),

        # For tile which is mapped with PHI operation, Launch the tile using CMD_RESUME instead of CMD_LAUNCH.
        # CMD_RESUME not only triggers the config issuing, but also resume the progress for phi operations.
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_RESUME))
      ],

      # cgra 0, tile 1
      [
        # Overwrites config 0 to perform migration.
        # GRT_PRED.
        IntraCgraPktType(0, 1,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                     ctrl = CtrlType(OPT_GRT_PRED,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                                     # North -> FU
                                                                      TileInType(0), TileInType(1), TileInType(0), TileInType(0)],
                                                                      # FU -> North
                                                                     [FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                     # 2 indicates the FU xbar port (instead of const queue or routing xbar port).
                                                                     read_reg_from = [b1(1), b1(0), b1(0), b1(0)]))),
        # Resets ctrl mem raddr.
        IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_CONFIG_CTRL_LOWER_BOUND, data = DataType(0, 1))),

        # Pre-configure per-tile config count per iter.
        IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter_migration, 1))),

        # Pre-configure per-tile total config count.
        IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps_migration, 1))),

        IntraCgraPktType(0, 1,
                         payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 0,
                                                   data = DataType(2, 1))),
        IntraCgraPktType(0, 1,
                         payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 0,
                                                   ctrl = CtrlType(routing_xbar_outport = [
                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0), 
                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                   data = DataType(2, 1))),
        IntraCgraPktType(0, 1,
                         payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU_CROSSBAR, ctrl_addr = 0,
                                                   ctrl = CtrlType(fu_xbar_outport = [
                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), 
                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]),
                                                   data = DataType(2, 1))),
        IntraCgraPktType(0, 1,
                         payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 1,
                                                   data = DataType(1, 1))),
        IntraCgraPktType(0, 1,
                         payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 1,
                                                   ctrl = CtrlType(routing_xbar_outport = [
                                                       # South -> North
                                                       TileInType(2), TileInType(0), TileInType(0), TileInType(0), 
                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                   data = DataType(1, 1))),
        IntraCgraPktType(0, 1,
                         payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 1,
                                                   ctrl = CtrlType(routing_xbar_outport = [
                                                       # East -> North
                                                       TileInType(4), TileInType(0), TileInType(0), TileInType(0), 
                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                   data = DataType(1, 1))),
        IntraCgraPktType(0, 1,
                         payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU_CROSSBAR, ctrl_addr = 1,
                                                   ctrl = CtrlType(fu_xbar_outport = [
                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), 
                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]),
                                                   data = DataType(1, 1))),

        # Launch the tile.
        IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_LAUNCH))
      ],

      # cgra 0, tile 2
      [
        # Const for ADD_CONST_LD.
        IntraCgraPktType(0, 2, payload = CgraPayloadType(CMD_CONST, data = DataType(kInputBaseAddress, 1))),

        # Resets ctrl mem raddr.
        IntraCgraPktType(0, 2, payload = CgraPayloadType(CMD_CONFIG_CTRL_LOWER_BOUND, data = DataType(0, 1))),

        # Pre-configure per-tile config count per iter.
        IntraCgraPktType(0, 2, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter_migration, 1))),

        # Pre-configure per-tile total config count.
        IntraCgraPktType(0, 2, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps_migration, 1))),

        IntraCgraPktType(0, 2,
                         payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 0,
                                                   data = DataType(1, 1))),
        IntraCgraPktType(0, 2,
                         payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 0,
                                                   ctrl = CtrlType(routing_xbar_outport = [
                                                       # North -> North
                                                       TileInType(1), TileInType(0), TileInType(0), TileInType(0), 
                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                   data = DataType(1, 1))),
        IntraCgraPktType(0, 2,
                         payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU_CROSSBAR, ctrl_addr = 0,
                                                   ctrl = CtrlType(fu_xbar_outport = [
                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), 
                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]),
                                                   data = DataType(1, 1))),

        # Launch the tile.
        IntraCgraPktType(0, 2, payload = CgraPayloadType(CMD_LAUNCH))
      ],

      # cgra 0, tile 3
      [
        # Overwrites config 1 to perform migration.
        # INC_NE_CONST_NOT_GRT.
        IntraCgraPktType(0, 3,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                     ctrl = CtrlType(OPT_INC_NE_CONST_NOT_GRT,
                                                                     fu_in_code,
                                                                      # South -> North
                                                                     [TileInType(2), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     # Sends two outputs to south and self reg, respectively.
                                                                                    # FU -> North
                                                                     [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                                    # FU -> FU
                                                                      FuOutType(0), FuOutType(2), FuOutType(0), FuOutType(0)],
                                                                     # 2 indicates the FU xbar port (instead of const queue or routing xbar port).
                                                                     write_reg_from = [b2(0), b2(2), b2(0), b2(0)],
                                                                     read_reg_from = [b1(1), b1(0), b1(0), b1(0)]))),
        # Const for PHI_CONST.
        IntraCgraPktType(0, 3, payload = CgraPayloadType(CMD_CONST, data = DataType(kLoopLowerBound, 1))),

        # Const for CMP.
        IntraCgraPktType(0, 3, payload = CgraPayloadType(CMD_CONST, data = DataType(kLoopUpperBound, 1))),

        # Resets ctrl mem raddr.
        IntraCgraPktType(0, 3, payload = CgraPayloadType(CMD_CONFIG_CTRL_LOWER_BOUND, data = DataType(0, 1))),

        # Pre-configure per-tile config count per iter.
        IntraCgraPktType(0, 3, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter_migration, 1))),

        # Pre-configure per-tile total config count.
        IntraCgraPktType(0, 3, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps_migration, 1))),

        IntraCgraPktType(0, 3,
                         payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 1,
                                                   ctrl = CtrlType(routing_xbar_outport = [
                                                       # North -> North
                                                       TileInType(1), TileInType(0), TileInType(0), TileInType(0), 
                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                   data = DataType(2, 1))),

        # For tile which is mapped with PHI operation, Launch the tile using CMD_RESUME instead of CMD_LAUNCH.
        # CMD_RESUME not only triggers the config issuing, but also resume the progress for phi operations.
        IntraCgraPktType(0, 3, payload = CgraPayloadType(CMD_RESUME))
      ],

      # cgra 2, tile 1
      [
        # Dynamically migrate RET node to cgra 2, tile 1 to reduce II from 3 to 2.
        IntraCgraPktType(0, 1, 0, cgra_2_id, 0, 0, cgra_2_x, cgra_2_y,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                       ctrl = CtrlType(OPT_RET,
                                                                       [FuInType(1), FuInType(0), FuInType(0), FuInType(0)],
                                                                       [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                        # Input of `return` is from south port.
                                                                        TileInType(2), TileInType(0), TileInType(0), TileInType(0)],
                                                                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

        # Pre-configure per-tile config count per iter. We only needs 1 control signal here if NAH is not provided.
        IntraCgraPktType(0, 1, 0, cgra_2_id, 0, 0, cgra_2_x, cgra_2_y, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(1, 1))),

        # Pre-configure per-tile total config count.
        IntraCgraPktType(0, 1, 0, cgra_2_id, 0, 0, cgra_2_x, cgra_2_y, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps_migration, 1))),
        # Launch the tile.
        IntraCgraPktType(0, 1, 0, cgra_2_id, 0, 0, cgra_2_x, cgra_2_y, payload = CgraPayloadType(CMD_LAUNCH))
      ],
    ]

    src_query_pkt = \
        [
            # IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = kStoreAddress)),
        ]

    expected_complete_sink_out_pkg = \
        [
            # Results for dynamic migration.
            IntraCgraPktType(src = 1, dst = num_tiles,
                             src_cgra_id = cgra_2_id,
                             dst_cgra_id = 0,
                             src_cgra_x = cgra_2_x,
                             src_cgra_y = cgra_2_y,
                             dst_cgra_x = 0,
                             dst_cgra_y = 0,
                             payload = CgraPayloadType(CMD_COMPLETE, DataType(kExpectedOutput, 1, 0, 0), ctrl = CtrlType(OPT_RET))),
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

  th = TestHarness(DUT, FunctionUnit, FuList,IntraCgraPktType,
                   num_cgra_rows, num_cgra_columns,
                   num_x_tiles_per_cgra, num_y_tiles_per_cgra, ctrl_mem_size, data_mem_size_global,
                   data_mem_size_per_bank, num_banks_per_cgra,
                   num_registers_per_reg_bank, src_ctrl_pkt, src_query_pkt,
                   kCtrlCountPerIter, kTotalCtrlSteps, mem_access_is_combinational,
                   per_cgra_topology,
                   controller2addr_map,
                   expected_sink_out_pkt,
                   cmp_func,
                   support_task_switching)
  return th

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

def test_multi_CGRA_fir_scalar_fused(cmdline_opts):
  th = initialize_test_harness(cmdline_opts,
                               num_cgra_rows = 2,
                               num_cgra_columns = 2,
                               num_x_tiles_per_cgra = 2,
                               num_y_tiles_per_cgra = 2,
                               num_tile_ports = 8, # Indicating KingMesh, i.e., 8 directions
                               num_banks_per_cgra = 2,
                               data_mem_size_per_bank = 16,
                               mem_access_is_combinational = True,
                               per_cgra_topology = 'KingMesh',
                               test_name = 'test_fir_scalar_fused')

  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                      ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                       'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)

def test_multi_CGRA_fir_scalar_migrated(cmdline_opts):
  th = initialize_test_harness(cmdline_opts,
                               num_cgra_rows = 2,
                               num_cgra_columns = 2,
                               num_x_tiles_per_cgra = 2,
                               num_y_tiles_per_cgra = 2,
                               num_tile_ports = 8, # Indicating KingMesh, i.e., 8 directions
                               num_banks_per_cgra = 2,
                               data_mem_size_per_bank = 16,
                               mem_access_is_combinational = True,
                               per_cgra_topology = 'KingMesh',
                               test_name = 'test_fir_scalar_migrated')

  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                      ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                       'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)

def test_multi_CGRA_fir_scalar_dynamic_migration(cmdline_opts):
  th = initialize_test_harness(cmdline_opts,
                               num_cgra_rows = 2,
                               num_cgra_columns = 2,
                               num_x_tiles_per_cgra = 2,
                               num_y_tiles_per_cgra = 2,
                               num_tile_ports = 8, # Indicating KingMesh, i.e., 8 directions
                               num_banks_per_cgra = 2,
                               data_mem_size_per_bank = 16,
                               mem_access_is_combinational = True,
                               per_cgra_topology = 'KingMesh',
                               test_name = 'test_fir_scalar_dynamic_migration')

  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                      ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                       'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)

