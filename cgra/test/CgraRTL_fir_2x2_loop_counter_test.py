"""
==========================================================================
CgraRTL_fir_2x2_loop_counter_test.py
==========================================================================
Test cases for CGRA with LoopCounter and ExtractPredicate FUs.
Based on mapping IR from compiler.

Author : Shangkun Li
  Date : Jan 29, 2026
"""

from pymtl3.passes.backends.verilog import (VerilogVerilatorImportPass)
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)

from ..CgraRTL import CgraRTL
from ...fu.double.SeqMulAdderRTL import SeqMulAdderRTL
from ...fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from ...fu.single.AdderRTL import AdderRTL
from ...fu.single.GrantRTL import GrantRTL
from ...fu.single.CompRTL import CompRTL
from ...fu.single.LogicRTL import LogicRTL
from ...fu.single.LoopCounterRTL import LoopCounterRTL
from ...fu.single.ExtractPredicateRTL import ExtractPredicateRTL
from ...fu.single.MemUnitRTL import MemUnitRTL
from ...fu.single.MulRTL import MulRTL
from ...fu.single.PhiRTL import PhiRTL
from ...fu.single.RetRTL import RetRTL
from ...fu.single.SelRTL import SelRTL
from ...fu.single.ShifterRTL import ShifterRTL
from ...lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ...lib.messages import *
from ...lib.opt_type import *
from ...lib.util.common import *

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, DUT, FunctionUnit, FuList,
                CtrlPktType,
                cgra_id, width, height,
                ctrl_mem_size, data_mem_size_global,
                data_mem_size_per_bank, num_banks_per_cgra,
                num_registers_per_reg_bank,
                src_ctrl_pkt, kCtrlCountPerIter, kTotalCtrlSteps,
                mem_access_is_combinational,
                has_ctrl_ring,
                controller2addr_map,
                idTo2d_map, complete_signal_sink_out,
                multi_cgra_rows, multi_cgra_columns, src_query_pkt):

    CgraPayloadType = CtrlPktType.get_field_type(kAttrPayload)
    DataType = CgraPayloadType.get_field_type(kAttrData)
    DataAddrType = mk_bits(clog2(data_mem_size_global))
    s.num_tiles = width * height
    s.src_ctrl_pkt = TestSrcRTL(CtrlPktType, src_ctrl_pkt)
    s.src_query_pkt = TestSrcRTL(CtrlPktType, src_query_pkt)

    s.dut = DUT(CgraPayloadType,
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
                is_multi_cgra = False,
                has_ctrl_ring = has_ctrl_ring)

    s.has_ctrl_ring = has_ctrl_ring

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
    if not s.has_ctrl_ring:
      return True
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
          LoopCounterRTL,
          ExtractPredicateRTL
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

def sim_fir_with_loop_counter(cmdline_opts, mem_access_is_combinational, has_ctrl_ring):
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
  #       0(loop_count)---------┐
  #        /       \            |
  #     1(+,ld)  2(+,ld)  6(extract_pred)
  #        \       /            |
  #         \     /          7(not)
  #          3(x)               |
  #           |                 |
  #    ┌---> 4(+)               |
  #    |    /                   |
  # 5(phi_const) ----- 8(grant_predicate)
  #                             |
  #                          9(ret)
  #
  # Corresponding mapping (II = 3):
  '''
       ↑ Y
       |
  (0,1)|  Tile 2   Tile 3
       |
  (0,0)|  Tile 0   Tile 1
       +-----------------→ X
        (0,0)    (1,0)

  Tile 0: 0(loop_count), 1(+,ld)
  Tile 1: 6(extract_pred), 7(not)
  Tile 2: 4(+), 2(+,ld), 3(x)
  Tile 3: 8(grant_predicate), 9(ret), 5(phi_const)
  =============================
  cycle 0:
  [   4(+)   →   8(grant_pred)]
       ↑              ↺
  [0(loop_cnt) →      🔳      ]
       ↺
  =============================
  cycle 1:
  [ 2(+,ld)        9(ret)     ]
      ↑↺             
  [ 1(+,ld)    6(extract_pred)]
                     ↺
  =============================
  cycle 2:
  [  3(x)   ←   5(phi_const)  ]
       ↺             ↑↺
  [   🔳            7(not)    ]

  =============================
  '''

  src_opt_pkt = [
      # tile 0
      [
          # Const for ADD_CONST_LD.
          IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONST, data = DataType(kCoefficientBaseAddress, 1))),
          
           # Configure loop counter parameters via CMD.
          IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONFIG_LOOP_LOWER, data = DataType(kLoopLowerBound, 1), ctrl_addr = 0)),
          IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONFIG_LOOP_UPPER, data = DataType(kLoopUpperBound, 1), ctrl_addr = 0)),
          IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONFIG_LOOP_STEP, data = DataType(kLoopIncrement, 1), ctrl_addr = 0)),
          
          # Pre-configure per-tile config count per iter.
          IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter, 1))),

          # Pre-configure per-tile total config count.
          IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps, 1))),

          # LOOP_COUNT.
          IntraCgraPktType(0, 0,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                     ctrl = CtrlType(OPT_LOOP_COUNT,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                     # 2 indicates the FU xbar port (instead of const queue or routing xbar port).
                                                                     write_reg_from = [b2(2), b2(0), b2(0), b2(0)]))),
          
          # ADD_CONST_LD.
          IntraCgraPktType(0, 0,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                     ctrl = CtrlType(OPT_ADD_CONST_LD,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                     read_reg_from = [b1(1), b1(0), b1(0), b1(0)]))),

          # NAH.
          IntraCgraPktType(0, 0,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                     ctrl = CtrlType(OPT_NAH,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),
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
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

          # EXTRACT_PREDICATE.
          IntraCgraPktType(0, 1,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                     ctrl = CtrlType(OPT_EXTRACT_PREDICATE,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(PORT_WEST), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                     # 2 indicates the FU xbar port (instead of const queue or routing xbar port).
                                                                     write_reg_from = [b2(2), b2(0), b2(0), b2(0)]))),

          # NOT.
          IntraCgraPktType(0, 1,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                     ctrl = CtrlType(OPT_NOT,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                     read_reg_from = [b1(1), b1(0), b1(0), b1(0)]))),

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

          # ADD.
          IntraCgraPktType(0, 2,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                     ctrl = CtrlType(OPT_ADD,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(PORT_EAST), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                     read_reg_from = [b1(1), b1(0), b1(0), b1(0)]))),
          # ADD_CONST_LD.
          IntraCgraPktType(0, 2,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                     ctrl = CtrlType(OPT_ADD_CONST_LD,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(PORT_SOUTH), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0)],
                                                                     write_reg_from = [b2(0), b2(2), b2(0), b2(0)]))),
          # MUL.
          IntraCgraPktType(0, 2,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                     ctrl = CtrlType(OPT_MUL,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(PORT_SOUTH), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                     read_reg_from = [b1(0), b1(1), b1(0), b1(0)],
                                                                     write_reg_from = [b2(2), b2(0), b2(0), b2(0)]))),

          IntraCgraPktType(0, 2,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 0,
                                                     data = DataType(1, 1))),
          
          IntraCgraPktType(0, 2,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 0,
                                                     ctrl = CtrlType(routing_xbar_outport = [
                                                        TileInType(PORT_EAST), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
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
          IntraCgraPktType(0, 3, payload = CgraPayloadType(CMD_CONST, data = DataType(kSumInitValue, 1))),

          # Pre-configure per-tile config count per iter.
          IntraCgraPktType(0, 3, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter, 1))),

          # Pre-configure per-tile total config count.
          IntraCgraPktType(0, 3, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps, 1))),

          # GRT_PRED.
          IntraCgraPktType(0, 3,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                     ctrl = CtrlType(OPT_GRT_PRED,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(PORT_SOUTH), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0)],
                                                                     read_reg_from = [b1(1), b1(0), b1(0), b1(0)],
                                                                     write_reg_from = [b2(0), b2(2), b2(0), b2(0)]))),
          # RET.
          IntraCgraPktType(0, 3,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                     ctrl = CtrlType(OPT_RET,
                                                                     # The first 2 indicates the first operand is from the second inport,
                                                                     # which is actually from the second register cluster rather than the
                                                                     # inport channel, indicated by the `read_reg_from_code`.
                                                                     [FuInType(2), FuInType(0), FuInType(0), FuInType(0)],
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(PORT_WEST), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                     read_reg_from = [b1(0), b1(1), b1(0), b1(0)],
                                                                     write_reg_from = [b2(0), b2(0), b2(1), b2(0)]))),
          # PHI_CONST.
          IntraCgraPktType(0, 3,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                     ctrl = CtrlType(OPT_PHI_CONST,
                                                                     # The first 3 indicates the first operand is from the third inport,
                                                                     # which is actually from the third register cluster rather than the
                                                                     # inport channel, indicated by the `read_reg_from_code`.
                                                                     [FuInType(3), FuInType(0), FuInType(0), FuInType(0)],
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                     read_reg_from = [b1(0), b1(0), b1(1), b1(0)],
                                                                     write_reg_from = [b2(2), b2(0), b2(0), b2(0)]))),

          IntraCgraPktType(0, 3,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 0,
                                                     ctrl = CtrlType(routing_xbar_outport = [
                                                        TileInType(PORT_SOUTH), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                     data = DataType(1, 1))),
          IntraCgraPktType(0, 3,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 0,
                                                     data = DataType(1, 1))),
          IntraCgraPktType(0, 3,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU_CROSSBAR, ctrl_addr = 0,
                                                     ctrl = CtrlType(fu_xbar_outport = [
                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]),
                                                     data = DataType(1, 1))),

          IntraCgraPktType(0, 3,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 1,
                                                     ctrl = CtrlType(routing_xbar_outport = [
                                                        TileInType(PORT_WEST), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                     data = DataType(1, 1))),
          IntraCgraPktType(0, 3,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 1,
                                                     data = DataType(1, 1))),
          IntraCgraPktType(0, 3,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU_CROSSBAR, ctrl_addr = 1,
                                                     ctrl = CtrlType(fu_xbar_outport = [
                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]),
                                                     data = DataType(1, 1))),

          # Launch the tile.
          IntraCgraPktType(0, 3, payload = CgraPayloadType(CMD_LAUNCH))
      ],
  ]

  src_query_pkt = []

  expected_complete_sink_out_pkg = \
      [
          IntraCgraPktType(src = 3, dst = 4, payload = CgraPayloadType(CMD_COMPLETE, DataType(kExpectedOutput, 1, 0, 0))) for _ in range(1)
      ]
  expected_mem_sink_out_pkt = []

  for activation in preload_data:
      src_ctrl_pkt.extend(activation)
  # Launch order matters for synchronization:
  # T2, T3 are downstream consumers - launch first so channels are ready
  # T0 is the producer (LoopCounter) - launch before T1 so they stay in sync
  # T1 forwards T0's output - launch last, just after T0
  for tile_idx in [2, 3, 0, 1]:
      src_ctrl_pkt.extend(src_opt_pkt[tile_idx])

  complete_signal_sink_out.extend(expected_complete_sink_out_pkg)
  complete_signal_sink_out.extend(expected_mem_sink_out_pkt)

  th = TestHarness(DUT, FunctionUnit, FuList,
                   IntraCgraPktType,
                   cgra_id, x_tiles, y_tiles,
                   ctrl_mem_size, data_mem_size_global,
                   data_mem_size_per_bank, num_banks_per_cgra,
                   num_registers_per_reg_bank,
                   src_ctrl_pkt, kCtrlCountPerIter, kTotalCtrlSteps,
                   mem_access_is_combinational,
                   has_ctrl_ring,
                   controller2addr_map, idTo2d_map, complete_signal_sink_out,
                   num_cgra_rows, num_cgra_columns,
                   src_query_pkt)

  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                       ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                        'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th, cmdline_opts)

def test_homogeneous_2x2_fir_with_loop_counter_combinational_mem_access_return(cmdline_opts):
  sim_fir_with_loop_counter(cmdline_opts, mem_access_is_combinational = True, has_ctrl_ring = True)

# def test_homogeneous_2x2_fir_with_loop_counter_non_combinational_mem_access_return(cmdline_opts):
#   sim_fir_with_loop_counter(cmdline_opts, mem_access_is_combinational = False, has_ctrl_ring = True)
