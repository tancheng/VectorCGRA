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

from ..CgraWithContextSwitchRTL import CgraWithContextSwitchRTL
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
from ...fu.vector.VectorAdderComboRTL import VectorAdderComboRTL
from ...fu.vector.VectorMulComboRTL import VectorMulComboRTL
from ...fu.vector.VectorAllReduceRTL import VectorAllReduceRTL
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
                mem_access_is_combinational, controller2addr_map,
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
          ]
x_tiles = 4
y_tiles = 4
data_bitwidth = 32
tile_ports = 8
num_tile_inports  = tile_ports
num_tile_outports = tile_ports
num_fu_inports = 4
num_fu_outports = 2
num_routing_outports = num_tile_outports + num_fu_inports
ctrl_mem_size = 8
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

DUT = CgraWithContextSwitchRTL
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


def sim_fir_return_two_tasks(cmdline_opts, mem_access_is_combinational):
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
  kLoopUpperBound_Task1 = 10
  kLoopUpperBound_Task2 = 9
  kCtrlCountPerIter_Task1 = 4
  kCtrlCountPerIter_Task2 = 3
  # Though kTotalCtrlSteps is way more than required loop iteration count,
  # the stored result should still be correct thanks to the grant predicate.
  kTotalCtrlSteps_Task1 = kCtrlCountPerIter_Task1 * \
                          (kLoopUpperBound_Task1 - kLoopLowerBound) + \
                          100
  kTotalCtrlSteps_Task2 = kCtrlCountPerIter_Task2 * \
                          (kLoopUpperBound_Task2 - kLoopLowerBound) + \
                          100
  kExpectedOutput_Task1 = 2215
  kExpectedOutput_Task2 = 1816
  src_opt_pkt = [
      # -------------------------------- Loads all configs of two tasks to respective tiles --------------------------------------    
      # tile 0
      [
          # Configs for Task 1.
          # ADD.
          IntraCgraPktType(0, 0,
                            payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                      ctrl = CtrlType(OPT_ADD,
                                                                      fu_in_code,
                                                                      [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       # North -> FU
                                                                       TileInType(PORT_NORTH), TileInType(0), TileInType(0), TileInType(0)],
                                                                                                                 # FU -> East
                                                                      [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(1),
                                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                       # FU -> FU
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
                                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                      [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                                     # FU -> FU
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
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),
          # NAH.
          IntraCgraPktType(0, 0,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 3,
                                                     ctrl = CtrlType(OPT_NAH,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

          # Configs for Task 2.
          # PHI_CONST, indicating the address is a const.
          IntraCgraPktType(0, 0,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 4,
                                                     ctrl = CtrlType(OPT_PHI_CONST,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      # East -> FU
                                                                      TileInType(PORT_EAST), TileInType(0), TileInType(0), TileInType(0)],
                                                                                                                # FU -> East
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(1),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),
          # ADD_CONST_LD.
          IntraCgraPktType(0, 0,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 5,
                                                     ctrl = CtrlType(OPT_ADD_CONST_LD,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      # NorthEast -> FU
                                                                      TileInType(PORT_NORTHEAST), TileInType(0), TileInType(0), TileInType(0)],
                                                                      # FU -> North
                                                                     [FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),
          # NAH.
          IntraCgraPktType(0, 0,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 6,
                                                     ctrl = CtrlType(OPT_NAH,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)])))
      ],

      # tile 1
      [
          # Configs for Task 1.
          # NAH.
          IntraCgraPktType(0, 1,
                            payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                      ctrl = CtrlType(OPT_NAH,
                                                                      fu_in_code,
                                                                      [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                      [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

          # PHI_CONST.
          IntraCgraPktType(0, 1,
                            payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                      ctrl = CtrlType(OPT_GRT_PRED,
                                                                      fu_in_code,
                                                                      [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       # West -> FU,  North -> FU
                                                                       TileInType(PORT_WEST), TileInType(PORT_NORTH), TileInType(0), TileInType(0)],
                                                                      [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                       # FU -> FU
                                                                       FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                      write_reg_from = write_reg_from_code))),
          # NAH.
          IntraCgraPktType(0, 1,
                            payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                      ctrl = CtrlType(OPT_RET,
                                                                      fu_in_code,
                                                                      [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                      [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                      read_reg_from = read_reg_from_code))),
          # NAH.
          IntraCgraPktType(0, 1,
                            payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 3,
                                                      ctrl = CtrlType(OPT_NAH,
                                                                      fu_in_code,
                                                                      [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                      [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

          # Configs for Task 2.
          # GRT_PRED.
          IntraCgraPktType(0, 1,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 4,
                                                     ctrl = CtrlType(OPT_GRT_PRED,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), 
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                                     # North -> FU
                                                                      TileInType(0), TileInType(PORT_NORTH), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), 
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                                    # FU -> FU
                                                                      FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0)],
                                                                     # 2 indicates the FU xbar port (instead of const queue or routing xbar port).
                                                                     write_reg_from = [b2(0), b2(2), b2(0), b2(0)],
                                                                     read_reg_from = [b1(1), b1(0), b1(0), b1(0)]))),

          # ADD.
          IntraCgraPktType(0, 1,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 5,
                                                     ctrl = CtrlType(OPT_ADD,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), 
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      # NorthWest -> FU, West -> FU
                                                                      TileInType(PORT_NORTHWEST), TileInType(PORT_WEST), TileInType(0), TileInType(0)],
                                                                                                  # FU -> West
                                                                     [FuOutType(0), FuOutType(0), FuOutType(1), FuOutType(0), 
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      # FU -> FU
                                                                      FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                     write_reg_from = [b2(2), b2(0), b2(0), b2(0)]))),
          # RET.
          IntraCgraPktType(0, 1,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 6,
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
                                                                     read_reg_from = [b1(0), b1(1), b1(0), b1(0)])))
      
      ],

      # tile 4
      [
          # Configs for Task 1.
          # NAH.
          IntraCgraPktType(0, 4,
                            payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                      ctrl = CtrlType(OPT_NAH,
                                                                      fu_in_code,
                                                                      [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                      [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

          # ADD_CONST.
          IntraCgraPktType(0, 4,
                            payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                      ctrl = CtrlType(OPT_ADD_CONST,
                                                                      fu_in_code,
                                                                      [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       # North -> FU
                                                                       TileInType(PORT_NORTH), TileInType(0), TileInType(0), TileInType(0)],
                                                                      # Sends to self reg.
                                                                      [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                       # FU -> FU
                                                                       FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                      write_reg_from = write_reg_from_code))),
          # LD.
          IntraCgraPktType(0, 4,
                            payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                      ctrl = CtrlType(OPT_LD,
                                                                      fu_in_code,
                                                                      [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                      # Sends to self reg. Needs to be another register cluster to
                                                                      # avoid conflict with ADD_CONST.
                                                                      [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                                     # FU -> FU
                                                                       FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0)],
                                                                      write_reg_from = [b2(0), b2(2), b2(0), b2(0)],
                                                                      read_reg_from = read_reg_from_code))),
          # MUL.
          IntraCgraPktType(0, 4,
                            payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 3,
                                                      ctrl = CtrlType(OPT_MUL,
                                                                      fu_in_code,
                                                                      [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(PORT_NORTH), TileInType(0), TileInType(0), TileInType(0)],
                                                                      # Sends to south tile: tile 0.
                                                                      [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0),
                                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                      read_reg_from = [b1(0), b1(1), b1(0), b1(0)]))),

          # Configs for Task 2.
          # MUL.
          IntraCgraPktType(0, 4,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 4,
                                                     ctrl = CtrlType(OPT_MUL,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), 
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                                     # South -> FU
                                                                      TileInType(0), TileInType(PORT_SOUTH), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), 
                                                                                                  # FU -> SouthEast
                                                                      FuOutType(0), FuOutType(0), FuOutType(1), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                     read_reg_from = [b1(1), b1(0), b1(0), b1(0)]))),
          # ADD_CONST_LD.
          IntraCgraPktType(0, 4,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 5,
                                                     ctrl = CtrlType(OPT_ADD_CONST_LD,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), 
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      # East -> FU
                                                                      TileInType(PORT_EAST), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), 
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      # FU -> FU
                                                                      FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                     write_reg_from = [b2(2), b2(0), b2(0), b2(0)]))),
          # NAH.
          IntraCgraPktType(0, 4,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 6,
                                                     ctrl = CtrlType(OPT_NAH,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), 
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), 
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)])))
      ],

      # tile 5
      [
          # Configs for Task 1.
          # NAH.
          IntraCgraPktType(0, 5,
                            payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                      ctrl = CtrlType(OPT_NAH,
                                                                      fu_in_code,
                                                                      [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                      [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

          # NAH.
          IntraCgraPktType(0, 5,
                            payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                      ctrl = CtrlType(OPT_NAH,
                                                                      fu_in_code,
                                                                      [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                      [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

          # CMP.
          IntraCgraPktType(0, 5,
                            payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                      ctrl = CtrlType(OPT_NE_CONST,
                                                                      fu_in_code,
                                                                      [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       # North -> FU
                                                                       TileInType(PORT_NORTH), TileInType(0), TileInType(0), TileInType(0)],
                                                                      # Sends result to north tile9, and self first register cluster.
                                                                       # FU -> North
                                                                      [FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                       # FU -> FU
                                                                       FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                      write_reg_from = write_reg_from_code))),

          # NOT.
          IntraCgraPktType(0, 5,
                            payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 3,
                                                      ctrl = CtrlType(OPT_NOT,
                                                                      fu_in_code,
                                                                      [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                                     # FU -> South
                                                                      [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0),
                                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                      # Reads operand for `NOT` from self first register cluster.
                                                                      read_reg_from = read_reg_from_code))),

          # Configs for Task 2.
          # PHI_CONST.
          IntraCgraPktType(0, 5,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 4,
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
          IntraCgraPktType(0, 5,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 5,
                                                     ctrl = CtrlType(OPT_INC_NE_CONST_NOT_GRT,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), 
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                                    # FU -> South
                                                                     [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0), 
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                                    # FU -> FU
                                                                      FuOutType(0), FuOutType(2), FuOutType(0), FuOutType(0)],
                                                                     # 2 indicates the FU xbar port (instead of const queue or routing xbar port).
                                                                     write_reg_from = [b2(0), b2(2), b2(0), b2(0)],
                                                                     read_reg_from = [b1(1), b1(0), b1(0), b1(0)]))),
          # NAH.
          IntraCgraPktType(0, 5,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 6,
                                                     ctrl = CtrlType(OPT_NAH,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), 
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), 
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)])))
      ],

      # tile 8
      # There are no configs for Task 2 on tile 8.
      [
          # Configs for Task 1.
          # PHI_CONST.
          IntraCgraPktType(0, 8,
                            payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                      ctrl = CtrlType(OPT_PHI_CONST,
                                                                      fu_in_code,
                                                                      [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       # East -> FU
                                                                       TileInType(PORT_EAST), TileInType(0), TileInType(0), TileInType(0)],
                                                                                     # FU -> South               # FU -> East
                                                                      [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(1),
                                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                       # FU -> FU
                                                                       FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                      write_reg_from = write_reg_from_code))),

          # ADD_CONST.
          IntraCgraPktType(0, 8,
                            payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                      ctrl = CtrlType(OPT_ADD_CONST,
                                                                      fu_in_code,
                                                                      [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                      [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                                     # FU -> FU
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
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     # Sends to south tile: tile 4.
                                                                                    # FU -> South
                                                                     [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                     read_reg_from = [b1(0), b1(1), b1(0), b1(0)]))),
          # NAH.
          IntraCgraPktType(0, 8,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 3,
                                                     ctrl = CtrlType(OPT_NAH,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)])))
      ],

      # tile 9
      # There are no configs for Task 2 on tile 9.
      [
          # NAH.
          IntraCgraPktType(0, 9,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                     ctrl = CtrlType(OPT_NAH,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

          # ADD_CONST.
          IntraCgraPktType(0, 9,
                            payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                      ctrl = CtrlType(OPT_ADD_CONST,
                                                                      fu_in_code,
                                                                      [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(PORT_WEST), TileInType(0), TileInType(0), TileInType(0)],
                                                                                     # FU -> South
                                                                      [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0),
                                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                                     # FU -> FU
                                                                       FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0)],
                                                                      # 2 indicates the FU xbar port (instead of const queue or routing xbar port).
                                                                      write_reg_from = [b2(0), b2(2), b2(0), b2(0)],))),
          # NAH.
          IntraCgraPktType(0, 9,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                     ctrl = CtrlType(OPT_NAH,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),
          # GRANT_PREDICATE.
          IntraCgraPktType(0, 9,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 3,
                                                     ctrl = CtrlType(OPT_GRT_PRED,
                                                                     # Swaps the first and second operands as the second one is
                                                                     # by default treated as the condition.
                                                                     [FuInType(2), FuInType(1), FuInType(0), FuInType(0)],
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      # South -> FU
                                                                      TileInType(PORT_SOUTH), TileInType(0), TileInType(0), TileInType(0)],
                                                                                                  # FU -> West
                                                                     [FuOutType(0), FuOutType(0), FuOutType(1), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                     read_reg_from = [b1(0), b1(1), b1(0), b1(0)])))
      ],

      # ------------------------------------------------------Starts executing Task 1------------------------------------------------------------
      # tile 0
      [
          # Const for PHI_CONST.
          IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONST, data = DataType(kSumInitValue, 1))),

          # Pre-configure per-tile config count per iter.
          IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter_Task1, 1))),

          # Pre-configure per-tile total config count.
          IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps_Task1, 1))),

          # Pre-configure the prologue count for both operation and routing.
          IntraCgraPktType(0, 0,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 0,
                                                     data = DataType(1, 1))),
          IntraCgraPktType(0, 0,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 0,
                                                     ctrl = CtrlType(routing_xbar_outport = [
                                                        TileInType(PORT_NORTH), TileInType(0), TileInType(0), TileInType(0),
                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                     data = DataType(1, 1))),
          IntraCgraPktType(0, 0,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU_CROSSBAR, ctrl_addr = 0,
                                                     ctrl = CtrlType(fu_xbar_outport = [
                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]),
                                                     data = DataType(1, 1))),

          # Prepares the context switch.
          IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_RECORD_PHI_ADDR, ctrl_addr = CtrlAddrType(1))),

          # Launch the tile.
          IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_LAUNCH))
      ],

      # tile 1
      [
          # Pre-configure per-tile config count per iter.
          IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter_Task1, 1))),

          # Pre-configure per-tile total config count.
          IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps_Task1, 1))),

          IntraCgraPktType(0, 1,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 1,
                                                     data = DataType(1, 1))),
          IntraCgraPktType(0, 1,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 2,
                                                     data = DataType(1, 1))),
          IntraCgraPktType(0, 1,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 1,
                                                     ctrl = CtrlType(routing_xbar_outport = [
                                                        TileInType(PORT_NORTH), TileInType(0), TileInType(0), TileInType(0),
                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                     data = DataType(1, 1))),
          IntraCgraPktType(0, 1,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 1,
                                                     ctrl = CtrlType(routing_xbar_outport = [
                                                        TileInType(PORT_WEST), TileInType(0), TileInType(0), TileInType(0),
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

      # tile 4
      [
          # Const for ADD_CONST.
          IntraCgraPktType(0, 4, payload = CgraPayloadType(CMD_CONST, data = DataType(kCoefficientBaseAddress, 1))),

          # Pre-configure per-tile config count per iter.
          IntraCgraPktType(0, 4, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter_Task1, 1))),

          # Pre-configure per-tile total config count.
          IntraCgraPktType(0, 4, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps_Task1, 1))),

          # Launch the tile.
          IntraCgraPktType(0, 4, payload = CgraPayloadType(CMD_LAUNCH))
      ],

      # tile 5
      [
          # Const for CMP.
          IntraCgraPktType(0, 5, payload = CgraPayloadType(CMD_CONST, data = DataType(kLoopUpperBound_Task1, 1))),

          # Pre-configure per-tile config count per iter.
          IntraCgraPktType(0, 5, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter_Task1, 1))),

          # Pre-configure per-tile total config count.
          IntraCgraPktType(0, 5, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps_Task1, 1))),

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
          IntraCgraPktType(0, 8, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter_Task1, 1))),

          # Pre-configure per-tile total config count.
          IntraCgraPktType(0, 8, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps_Task1, 1))),

          # Skips first time incoming from east tile via routing xbar.
          IntraCgraPktType(0, 8,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 0,
                                                     ctrl = CtrlType(routing_xbar_outport = [
                                                        TileInType(PORT_EAST), TileInType(0), TileInType(0), TileInType(0),
                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                     data = DataType(1, 1))),

          # Prepares the context switch.
          IntraCgraPktType(0, 8, payload = CgraPayloadType(CMD_RECORD_PHI_ADDR, ctrl_addr = CtrlAddrType(0))),

          # Launch the tile.
          IntraCgraPktType(0, 8, payload = CgraPayloadType(CMD_LAUNCH))
      ],

      # tile 9
      [
          # Const for ADD_CONST.
          IntraCgraPktType(0, 9, payload = CgraPayloadType(CMD_CONST, data = DataType(kLoopIncrement, 1))),

          # Pre-configure per-tile config count per iter.
          IntraCgraPktType(0, 9, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter_Task1, 1))),

          # Pre-configure per-tile total config count.
          IntraCgraPktType(0, 9, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps_Task1, 1))),

          # Launch the tile.
          IntraCgraPktType(0, 9, payload = CgraPayloadType(CMD_LAUNCH))
      ],

      # ------------------------------------------------------Pausing Task 1------------------------------------------------------------
      # Let all tiles free running for 12 cycles.
      # We repeately write the first data to addr 0 of memory bank to simulate the free-running.
      [ IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(10, 1), data_addr = 0)) for _ in range(12) ],

      # Sends preserving command to tile 0 to record accumulation results.
      [ IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_PRESERVE)) ],
      
      # Free running another 12 cycles to make sure tile 0 has already captured one accumulation result.
      [ IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(10, 1), data_addr = 0)) for _ in range(12) ],

      # Sends pausing command to tile 8 to record iteration results.
      [ IntraCgraPktType(0, 8, payload = CgraPayloadType(CMD_PAUSE)) ],
      
      # Free running another 12 cycles to make sure all data has been drained.
      [ IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(10, 1), data_addr = 0)) for _ in range(12) ],
      # Terminates all tiles after saving iteration and accumulation results.
      # Terminating refers to stop issuing configs from tile's config mem,
      # and clear all necessary values in various registers left by Task 1.
      [
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_TERMINATE)),
        IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_TERMINATE)),
        IntraCgraPktType(0, 4, payload = CgraPayloadType(CMD_TERMINATE)),
        IntraCgraPktType(0, 5, payload = CgraPayloadType(CMD_TERMINATE)),
        IntraCgraPktType(0, 8, payload = CgraPayloadType(CMD_TERMINATE)),
        IntraCgraPktType(0, 9, payload = CgraPayloadType(CMD_TERMINATE))
      ],
      
      # Terminate double time to make sure all registers are cleared, ready for executing Task 2.
      [
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_TERMINATE)),
        IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_TERMINATE)),
        IntraCgraPktType(0, 4, payload = CgraPayloadType(CMD_TERMINATE)),
        IntraCgraPktType(0, 5, payload = CgraPayloadType(CMD_TERMINATE)),
        IntraCgraPktType(0, 8, payload = CgraPayloadType(CMD_TERMINATE)),
        IntraCgraPktType(0, 9, payload = CgraPayloadType(CMD_TERMINATE))
      ],

      # ------------------------------------------------------Starts executing Task 2------------------------------------------------------------
      # tile 0
      [
          # Const for ADD_CONST_LD.
          IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONST, data = DataType(kCoefficientBaseAddress, 1))),

          # Const for PHI_CONST.
          IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONST, data = DataType(kSumInitValue, 1))),

          # Sets ctrl mem raddr to Task 2.
          IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONFIG_CTRL_LOWER_BOUND, data = DataType(4, 1))),

          # Pre-configure per-tile config count per iter.
          IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter_Task2, 1))),

          # Pre-configure per-tile total config count.
          IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps_Task2, 1))),

          # Pre-configure the prologue count for both operation and routing.
          IntraCgraPktType(0, 0,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 4,
                                                     data = DataType(1, 1))),
          # Prologue for phi_const should be carefully set. i.e., phi_const
          # by default should have a prologue to skip the first time non-const
          # operand arrival. So if it also needs prologue due to loop pipelining,
          # the prologue count should be incremented by 1. Therefore, we set
          # it to 2 here.
          IntraCgraPktType(0, 0,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 4,
                                                     ctrl = CtrlType(routing_xbar_outport = [
                                                        TileInType(PORT_EAST), TileInType(0), TileInType(0), TileInType(0), 
                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                     data = DataType(2, 1))),
          IntraCgraPktType(0, 0,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU_CROSSBAR, ctrl_addr = 4,
                                                     ctrl = CtrlType(fu_xbar_outport = [
                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), 
                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]),
                                                     data = DataType(1, 1))),

          # Launch the tile.
          IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_LAUNCH))
      ],

      # tile 1
      [
          # Sets ctrl mem raddr to Task 2.
          IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_CONFIG_CTRL_LOWER_BOUND, data = DataType(4, 1))),

          # Pre-configure per-tile config count per iter.
          IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter_Task2, 1))),

          # Pre-configure per-tile total config count.
          IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps_Task2, 1))),

          IntraCgraPktType(0, 1,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 4,
                                                     data = DataType(2, 1))),
          IntraCgraPktType(0, 1,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 4,
                                                     ctrl = CtrlType(routing_xbar_outport = [
                                                        TileInType(PORT_NORTH), TileInType(0), TileInType(0), TileInType(0), 
                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                     data = DataType(2, 1))),
          IntraCgraPktType(0, 1,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU_CROSSBAR, ctrl_addr = 4,
                                                     ctrl = CtrlType(fu_xbar_outport = [
                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), 
                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]),
                                                     data = DataType(2, 1))),
          IntraCgraPktType(0, 1,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 5,
                                                     data = DataType(1, 1))),
          IntraCgraPktType(0, 1,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 5,
                                                     ctrl = CtrlType(routing_xbar_outport = [
                                                        TileInType(PORT_WEST), TileInType(0), TileInType(0), TileInType(0), 
                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                     data = DataType(1, 1))),
          IntraCgraPktType(0, 1,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 5,
                                                     ctrl = CtrlType(routing_xbar_outport = [
                                                        TileInType(PORT_NORTHWEST), TileInType(0), TileInType(0), TileInType(0), 
                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                     data = DataType(1, 1))),
          IntraCgraPktType(0, 1,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU_CROSSBAR, ctrl_addr = 5,
                                                     ctrl = CtrlType(fu_xbar_outport = [
                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), 
                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]),
                                                     data = DataType(1, 1))),
          IntraCgraPktType(0, 1,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 6,
                                                     data = DataType(2, 1))),

          # Launch the tile.
          IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_LAUNCH))
      ],

      # tile 4
      [
          # Sets ctrl mem raddr to Task 2.
          IntraCgraPktType(0, 4, payload = CgraPayloadType(CMD_CONFIG_CTRL_LOWER_BOUND, data = DataType(4, 1))),

          # Pre-configure per-tile config count per iter.
          IntraCgraPktType(0, 4, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter_Task2, 1))),

          # Pre-configure per-tile total config count.
          IntraCgraPktType(0, 4, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps_Task2, 1))),

          # Const for ADD_CONST_LD.
          IntraCgraPktType(0, 4, payload = CgraPayloadType(CMD_CONST, data = DataType(kInputBaseAddress, 1))),

          IntraCgraPktType(0, 4,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 4,
                                                     data = DataType(1, 1))),
          IntraCgraPktType(0, 4,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 4,
                                                     ctrl = CtrlType(routing_xbar_outport = [
                                                        TileInType(PORT_SOUTH), TileInType(0), TileInType(0), TileInType(0), 
                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                     data = DataType(1, 1))),
          IntraCgraPktType(0, 4,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU_CROSSBAR, ctrl_addr = 4,
                                                     ctrl = CtrlType(fu_xbar_outport = [
                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), 
                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]),
                                                     data = DataType(1, 1))),

          # Launch the tile.
          IntraCgraPktType(0, 4, payload = CgraPayloadType(CMD_LAUNCH))
      ],

      # tile 5
      [
          # Const for PHI_CONST.
          IntraCgraPktType(0, 5, payload = CgraPayloadType(CMD_CONST, data = DataType(kLoopLowerBound, 1))),

          # Const for CMP.
          IntraCgraPktType(0, 5, payload = CgraPayloadType(CMD_CONST, data = DataType(kLoopUpperBound_Task2, 1))),

          # Sets ctrl mem raddr to Task 2.
          IntraCgraPktType(0, 5, payload = CgraPayloadType(CMD_CONFIG_CTRL_LOWER_BOUND, data = DataType(4, 1))),

          # Pre-configure per-tile config count per iter.
          IntraCgraPktType(0, 5, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter_Task2, 1))),

          # Pre-configure per-tile total config count.
          IntraCgraPktType(0, 5, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps_Task2, 1))),
          
          # Launch the tile.
          IntraCgraPktType(0, 5, payload = CgraPayloadType(CMD_LAUNCH))
      ],

      # Let all tiles free running for 60 cycles to finish Task 2.
      # We send useless data to unused tiles to simulate the free-running.
      # When simulating free runnig cycles, do not load too many consts to one single tile.
      [ IntraCgraPktType(0, 2, payload = CgraPayloadType(CMD_CONST, data = DataType(0, 0))) for _ in range(12) ],
      [ IntraCgraPktType(0, 3, payload = CgraPayloadType(CMD_CONST, data = DataType(0, 0))) for _ in range(12) ],
      [ IntraCgraPktType(0, 6, payload = CgraPayloadType(CMD_CONST, data = DataType(0, 0))) for _ in range(12) ],
      [ IntraCgraPktType(0, 7, payload = CgraPayloadType(CMD_CONST, data = DataType(0, 0))) for _ in range(12) ],
      [ IntraCgraPktType(0, 10, payload = CgraPayloadType(CMD_CONST, data = DataType(0, 0))) for _ in range(12) ],

      # Clear all necessary values in various registers left by Task 2.
      [
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_TERMINATE)),
        IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_TERMINATE)),
        IntraCgraPktType(0, 4, payload = CgraPayloadType(CMD_TERMINATE)),
        IntraCgraPktType(0, 5, payload = CgraPayloadType(CMD_TERMINATE)),
        IntraCgraPktType(0, 8, payload = CgraPayloadType(CMD_TERMINATE)),
        IntraCgraPktType(0, 9, payload = CgraPayloadType(CMD_TERMINATE))
      ],

      # Terminate double time to make sure all registers are cleared, ready for resuming Task 1.
      [
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_TERMINATE)),
        IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_TERMINATE)),
        IntraCgraPktType(0, 4, payload = CgraPayloadType(CMD_TERMINATE)),
        IntraCgraPktType(0, 5, payload = CgraPayloadType(CMD_TERMINATE)),
        IntraCgraPktType(0, 8, payload = CgraPayloadType(CMD_TERMINATE)),
        IntraCgraPktType(0, 9, payload = CgraPayloadType(CMD_TERMINATE))
      ],

      # ------------------------------------------------------Resuming Task 1------------------------------------------------------------
      # Reload all necessary const and prologue settings for tiles and launch again.
      # tile 0
      [
          # Const for PHI_CONST.
          IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONST, data = DataType(kSumInitValue, 1))),

          # Sets ctrl mem raddr to Task 1.
          IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONFIG_CTRL_LOWER_BOUND, data = DataType(0, 1))),

          # Pre-configure per-tile config count per iter.
          IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter_Task1, 1))),

          # Pre-configure per-tile total config count.
          IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps_Task1, 1))),

          # Pre-configure the prologue count for both operation and routing.
          IntraCgraPktType(0, 0,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 0,
                                                     data = DataType(1, 1))),
          IntraCgraPktType(0, 0,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 0,
                                                     ctrl = CtrlType(routing_xbar_outport = [
                                                        TileInType(PORT_NORTH), TileInType(0), TileInType(0), TileInType(0),
                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                     data = DataType(1, 1))),
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

      # tile 1
      [
          # Sets ctrl mem raddr to Task 1.
          IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_CONFIG_CTRL_LOWER_BOUND, data = DataType(0, 1))),

          # Pre-configure per-tile config count per iter.
          IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter_Task1, 1))),

          # Pre-configure per-tile total config count.
          IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps_Task1, 1))),

          IntraCgraPktType(0, 1,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 1,
                                                     data = DataType(1, 1))),
          IntraCgraPktType(0, 1,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 2,
                                                     data = DataType(1, 1))),
          IntraCgraPktType(0, 1,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 1,
                                                     ctrl = CtrlType(routing_xbar_outport = [
                                                        TileInType(PORT_NORTH), TileInType(0), TileInType(0), TileInType(0),
                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                     data = DataType(1, 1))),
          IntraCgraPktType(0, 1,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 1,
                                                     ctrl = CtrlType(routing_xbar_outport = [
                                                        TileInType(PORT_WEST), TileInType(0), TileInType(0), TileInType(0),
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

      # tile 4
      [
          # Const for ADD_CONST.
          IntraCgraPktType(0, 4, payload = CgraPayloadType(CMD_CONST, data = DataType(kCoefficientBaseAddress, 1))),

          # Sets ctrl mem raddr to Task 1.
          IntraCgraPktType(0, 4, payload = CgraPayloadType(CMD_CONFIG_CTRL_LOWER_BOUND, data = DataType(0, 1))),

          # Pre-configure per-tile config count per iter.
          IntraCgraPktType(0, 4, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter_Task1, 1))),

          # Pre-configure per-tile total config count.
          IntraCgraPktType(0, 4, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps_Task1, 1))),

          # Launch the tile.
          IntraCgraPktType(0, 4, payload = CgraPayloadType(CMD_LAUNCH))
      ],

      # tile 5
      [
          # Const for CMP.
          IntraCgraPktType(0, 5, payload = CgraPayloadType(CMD_CONST, data = DataType(kLoopUpperBound_Task1, 1))),

          # Sets ctrl mem raddr to Task 1.
          IntraCgraPktType(0, 5, payload = CgraPayloadType(CMD_CONFIG_CTRL_LOWER_BOUND, data = DataType(0, 1))),

          # Pre-configure per-tile config count per iter.
          IntraCgraPktType(0, 5, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter_Task1, 1))),

          # Pre-configure per-tile total config count.
          IntraCgraPktType(0, 5, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps_Task1, 1))),

          # Launch the tile.
          IntraCgraPktType(0, 5, payload = CgraPayloadType(CMD_LAUNCH))
      ],

      # tile 8
      [
          # Const for PHI_CONST.
          IntraCgraPktType(0, 8, payload = CgraPayloadType(CMD_CONST, data = DataType(kLoopLowerBound, 1))),
          # Const for ADD_CONST.
          IntraCgraPktType(0, 8, payload = CgraPayloadType(CMD_CONST, data = DataType(kInputBaseAddress, 1))),

          # Sets ctrl mem raddr to Task 1.
          IntraCgraPktType(0, 8, payload = CgraPayloadType(CMD_CONFIG_CTRL_LOWER_BOUND, data = DataType(0, 1))),

          # Pre-configure per-tile config count per iter.
          IntraCgraPktType(0, 8, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter_Task1, 1))),

          # Pre-configure per-tile total config count.
          IntraCgraPktType(0, 8, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps_Task1, 1))),

          # Skips first time incoming from east tile via routing xbar.
          IntraCgraPktType(0, 8,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 0,
                                                     ctrl = CtrlType(routing_xbar_outport = [
                                                        TileInType(PORT_EAST), TileInType(0), TileInType(0), TileInType(0),
                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                     data = DataType(1, 1))),

          # For tile which is mapped with PHI operation, Launch the tile using CMD_RESUME instead of CMD_LAUNCH.
          # CMD_RESUME not only triggers the config issuing, but also resume the progress for phi operations.
          IntraCgraPktType(0, 8, payload = CgraPayloadType(CMD_RESUME))
      ],

      # tile 9
      [
          # Const for ADD_CONST.
          IntraCgraPktType(0, 9, payload = CgraPayloadType(CMD_CONST, data = DataType(kLoopIncrement, 1))),

          # Sets ctrl mem raddr to Task 1.
          IntraCgraPktType(0, 9, payload = CgraPayloadType(CMD_CONFIG_CTRL_LOWER_BOUND, data = DataType(0, 1))),

          # Pre-configure per-tile config count per iter.
          IntraCgraPktType(0, 9, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter_Task1, 1))),

          # Pre-configure per-tile total config count.
          IntraCgraPktType(0, 9, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps_Task1, 1))),

          # Launch the tile.
          IntraCgraPktType(0, 9, payload = CgraPayloadType(CMD_LAUNCH))
      ]
  ]

  src_query_pkt = \
      [
#          IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = kStoreAddress)),
      ]

  expected_complete_sink_out_pkg = \
      [
          # Results for Task 2.
          IntraCgraPktType(src = 1, dst = 16, payload = CgraPayloadType(CMD_COMPLETE, DataType(kExpectedOutput_Task2, 1, 0, 0))),
          # Results for Task 1.
          IntraCgraPktType(src = 1, dst = 16, payload = CgraPayloadType(CMD_COMPLETE, DataType(kExpectedOutput_Task1, 1, 0, 0)))
      ]
  expected_mem_sink_out_pkt = \
      [
#          IntraCgraPktType(dst = 16, payload = CgraPayloadType(CMD_LOAD_RESPONSE, data = DataType(kExpectedOutput, 1), data_addr = 16)),
      ]

  for activation in preload_data:
      src_ctrl_pkt.extend(activation)
  for src_opt in src_opt_pkt:
      src_ctrl_pkt.extend(src_opt)

  complete_signal_sink_out.extend(expected_complete_sink_out_pkg)
  complete_signal_sink_out.extend(expected_mem_sink_out_pkt)

  th = TestHarness(DUT, FunctionUnit, FuList,
                   IntraCgraPktType,
                   cgra_id, x_tiles, y_tiles,
                   ctrl_mem_size, data_mem_size_global,
                   data_mem_size_per_bank, num_banks_per_cgra,
                   num_registers_per_reg_bank,
                   src_ctrl_pkt, kCtrlCountPerIter_Task1, kTotalCtrlSteps_Task1,
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

def test_sim_fir_combinational_mem_access_return_two_tasks(cmdline_opts):
  sim_fir_return_two_tasks(cmdline_opts, mem_access_is_combinational = True)

def test_sim_fir_multi_cycle_mem_access_return_two_tasks(cmdline_opts):
  sim_fir_return_two_tasks(cmdline_opts, mem_access_is_combinational = False)
