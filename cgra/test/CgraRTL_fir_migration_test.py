"""
==========================================================================
CgraRTL_fir_test.py
==========================================================================
Test cases for CGRA with crossbar-based data memory and ring-based control
memory of each tile.

Author : Cheng Tan
  Date : Aug 30, 2025
"""

from pymtl3.passes.backends.verilog import (VerilogVerilatorImportPass)
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)

from ..CgraRTL import CgraRTL
from ...fu.double.SeqMulAdderRTL import SeqMulAdderRTL
from ...fu.double.SeqAddMemRTL import SeqAddMemRTL
from ...fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from ...fu.float.FpAddRTL import FpAddRTL
from ...fu.float.FpMulRTL import FpMulRTL
from ...fu.single.AdderRTL import AdderRTL
from ...fu.single.GrantRTL import GrantRTL
from ...fu.single.CompRTL import CompRTL
from ...fu.single.FourIncCmpNotGrantRTL import FourIncCmpNotGrantRTL
from ...fu.single.LogicRTL import LogicRTL
from ...fu.single.MemUnitRTL import MemUnitRTL
from ...fu.single.MulRTL import MulRTL
from ...fu.single.PhiRTL import PhiRTL
from ...fu.single.RetRTL import RetRTL
from ...fu.single.SelRTL import SelRTL
from ...fu.single.ShifterRTL import ShifterRTL
from ...fu.vector.VectorAdderComboRTL import VectorAdderComboRTL
from ...fu.vector.VectorMulComboRTL import VectorMulComboRTL
from ...fu.vector.VectorAllReduceRTL import VectorAllReduceRTL
from ...lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ...lib.messages import *
from ...lib.opt_type import *


#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, DUT, FunctionUnit, FuList, DataType, PredicateType,
                CtrlPktType, CgraPayloadType, CtrlSignalType, NocPktType,
                ControllerIdType, data_bitwidth, cgra_id, width, height,
                ctrl_mem_size, data_mem_size_global,
                data_mem_size_per_bank, num_banks_per_cgra,
                num_registers_per_reg_bank,
                src_ctrl_pkt, kCtrlCountPerIter, kTotalCtrlSteps,
                mem_access_is_combinational, controller2addr_map,
                idTo2d_map, complete_signal_sink_out,
                multi_cgra_rows, multi_cgra_columns, src_query_pkt):

    DataAddrType = mk_bits(clog2(data_mem_size_global))
    s.num_tiles = width * height
    s.src_ctrl_pkt = TestSrcRTL(CtrlPktType, src_ctrl_pkt)
    s.src_query_pkt = TestSrcRTL(CtrlPktType, src_query_pkt)

    s.dut = DUT(DataType, PredicateType, CtrlPktType, CgraPayloadType,
                CtrlSignalType, NocPktType, ControllerIdType,
                data_bitwidth,
                # CGRA terminals on x/y. Assume in total 4, though this
                # test is for single CGRA.
                multi_cgra_rows, multi_cgra_columns,
                width, height, ctrl_mem_size,
                data_mem_size_global, data_mem_size_per_bank,
                num_banks_per_cgra, num_registers_per_reg_bank,
                kCtrlCountPerIter, kTotalCtrlSteps,
                mem_access_is_combinational,
                FunctionUnit, FuList, "KingMesh",
                controller2addr_map, idTo2d_map,
                is_multi_cgra = False)

    cmp_fn = lambda a, b : a.payload.data == b.payload.data and a.payload.cmd == b.payload.cmd
    s.complete_signal_sink_out = TestSinkRTL(CtrlPktType, complete_signal_sink_out, cmp_fn = cmp_fn)

    # Connections
    s.dut.cgra_id //= cgra_id
    s.complete_signal_sink_out.recv //= s.dut.send_to_cpu_pkt

    complete_count_value = \
            sum(1 for pkt in complete_signal_sink_out \
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
        if s.complete_signal_sink_out.recv.val & s.complete_signal_sink_out.recv.rdy & \
           (s.complete_count < complete_count_value):
          s.complete_count <<= s.complete_count + CompleteCountType(1)

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
    return (s.src_ctrl_pkt.done() and s.src_query_pkt.done()
            and s.complete_signal_sink_out.done())

  def line_trace(s):
    return s.dut.line_trace()

# Common configurations/setups.
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
          FourIncCmpNotGrantRTL,
          SeqAddMemRTL,
          ]
x_tiles = 2
y_tiles = 2
data_bitwidth = 32
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
num_cgra_columns = 4
num_cgra_rows = 1
num_cgras = num_cgra_columns * num_cgra_rows
num_ctrl_operations = 64
num_registers_per_reg_bank = 16
TileInType = mk_bits(clog2(num_tile_inports + 1))
FuInType = mk_bits(clog2(num_fu_inports + 1))
FuOutType = mk_bits(clog2(num_fu_outports + 1))
addr_nbits = clog2(data_mem_size_global)
num_tiles = x_tiles * y_tiles
num_rd_tiles = x_tiles + y_tiles - 1
per_cgra_data_size = int(data_mem_size_global / num_cgras)

DUT = CgraRTL
FunctionUnit = FlexibleFuRTL

DataAddrType = mk_bits(addr_nbits)
RegIdxType = mk_bits(clog2(num_registers_per_reg_bank))
DataType = mk_data(data_bitwidth, 1)
PredicateType = mk_predicate(1, 1)
ControllerIdType = mk_bits(max(1, clog2(num_cgras)))
cgra_id = 0
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
// expected sum = 2212 + 3 = 2215 (0x8a7)
'''

def sim_fir_return(cmdline_opts, mem_access_is_combinational):
  src_ctrl_pkt = []
  complete_signal_sink_out = []
  src_query_pkt = []

  # kernel specific parameters.
  kStoreAddress = 16 # We no longer need this for storing the result, as we can directly return it to CPU.
  kInputBaseAddress = 0
  kCoefficientBaseAddress = 2
  kSumInitValue = 3
  kLoopLowerBound = 2
  kLoopIncrement = 1
  kLoopUpperBound = 10
  kCtrlCountPerIter = 3
  # Though kTotalCtrlSteps is way more than required loop iteration count,
  # the stored result should still be correct thanks to the grant predicate.
  kTotalCtrlSteps = kCtrlCountPerIter * \
                    (kLoopUpperBound - kLoopLowerBound) + \
                    10
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
  # Migrated mirrored mapping (II = 2):
  '''
  =============================
  cycle 0:
  [    🔳            🔳       ]

  [    🔳         13(ret)     ]
  - - - - - - - - - - - - - - -

  [   6(x)   ←  0(phi_const)  ]
            ↙↘        ↺ ↑
  [ 1(phi_c) → 11(grant_pred) ]
                      ↺
  =============================
  cycle 1:
  [    🔳            🔳       ]

  [    🔳            🔳       ]
  - - - - - - - - - - - - - - -
                      ↑
  [ 2(+ ld)       8(fused)    ]
       ↺ ↑          ↓ ↺
  [ 4(+ ld)   ←     7(+)      ]
                      ↺
  =============================
  '''

  src_opt_pkt = [
      # tile 0
      [
          # Const for PHI_CONST.
          IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONST, data = DataType(kSumInitValue, 1))),

          # Const for ADD_CONST_LD.
          IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONST, data = DataType(kCoefficientBaseAddress, 1))),

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
                                                                       TileInType(3), TileInType(0), TileInType(0), TileInType(0)],
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
          IntraCgraPktType(0, 0,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 0,
                                                     ctrl = CtrlType(routing_xbar_outport = [
                                                        TileInType(3), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                     data = DataType(1, 1))),
          IntraCgraPktType(0, 0,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU_CROSSBAR, ctrl_addr = 0,
                                                     ctrl = CtrlType(fu_xbar_outport = [
                                                        FuOutType(3), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
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
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
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
          IntraCgraPktType(src = 1, dst = 16, payload = CgraPayloadType(CMD_COMPLETE, DataType(kExpectedOutput, 1, 0, 0))) for _ in range(1)
      ]
  expected_mem_sink_out_pkt = \
      [
          # IntraCgraPktType(dst = 16, payload = CgraPayloadType(CMD_LOAD_RESPONSE, data = DataType(kExpectedOutput, 1), data_addr = 16)),
      ]

  for activation in preload_data:
      src_ctrl_pkt.extend(activation)
  for src_opt in src_opt_pkt:
      src_ctrl_pkt.extend(src_opt)

  complete_signal_sink_out.extend(expected_complete_sink_out_pkg)
  complete_signal_sink_out.extend(expected_mem_sink_out_pkt)

  th = TestHarness(DUT, FunctionUnit, FuList, DataType, PredicateType,
                   IntraCgraPktType, CgraPayloadType, CtrlType, InterCgraPktType,
                   ControllerIdType, data_bitwidth, cgra_id, x_tiles, y_tiles,
                   ctrl_mem_size, data_mem_size_global,
                   data_mem_size_per_bank, num_banks_per_cgra,
                   num_registers_per_reg_bank,
                   src_ctrl_pkt, kCtrlCountPerIter, kTotalCtrlSteps,
                   mem_access_is_combinational,
                   controller2addr_map, idTo2d_map, complete_signal_sink_out,
                   num_cgra_rows, num_cgra_columns,
                   src_query_pkt)

  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                       ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                        'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)

def test_homogeneous_2x2_fir_combinational_mem_access_return(cmdline_opts):
  sim_fir_return(cmdline_opts, mem_access_is_combinational = True)
