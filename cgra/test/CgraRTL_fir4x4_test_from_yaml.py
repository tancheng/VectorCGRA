"""
==========================================================================
CgraRTL_fir4x4_test_from_yaml.py
==========================================================================
Test cases for CGRA with crossbar-based data memory and ring-based control
memory of each tile, using fir4x4.yaml compiled kernel.

Author : Cheng Tan
  Date : Aug 30, 2025
"""

import os

from pymtl3.passes.backends.verilog import (VerilogVerilatorImportPass)
from pymtl3.passes.sim.PrepareSimPass import b1
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)

from ..CgraRTL import CgraRTL
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
from ...fu.vector.VectorAdderComboRTL import VectorAdderComboRTL
from ...fu.vector.VectorMulComboRTL import VectorMulComboRTL
from ...fu.vector.VectorAllReduceRTL import VectorAllReduceRTL
from ...lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ...lib.messages import *
from ...lib.opt_type import *
from ...lib.util.common import *
from ...lib.trace_logger import init_trace_logger, close_trace_logger

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
                FunctionUnit, FuList, "Mesh",
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
          ]
x_tiles = 4
y_tiles = 4
data_bitwidth = 32
tile_ports = 4
num_tile_inports  = tile_ports
num_tile_outports = tile_ports
num_fu_inports = 4
num_fu_outports = 2
num_routing_outports = num_tile_outports + num_fu_inports
ctrl_mem_size = 6
data_mem_size_global = 128
data_mem_size_per_bank = 16
num_banks_per_cgra = 2
num_cgra_columns = 4
num_cgra_rows = 1
num_cgras = num_cgra_columns * num_cgra_rows
num_ctrl_operations = 64
num_registers_per_reg_bank = 8
TileInType = mk_bits(clog2(num_tile_inports + num_fu_inports + 1))
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
read_reg_towards_code = [b2(0) for _ in range(num_fu_inports)]
read_reg_towards_code[0] = b2(1)
read_reg_idx_code = [RegIdxType(0) for _ in range(num_fu_inports)]

fu_in_code = [FuInType(x + 1) for x in range(num_fu_inports)]

# Preload 32 data values at addresses 0~31 with values 10~41.
# Both GEP base addresses in fir4x4.yaml are #0, so both LOADs access
# data[i]. The kernel computes sum = Σ data[i]^2 for i in [0, 32).
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
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(26, 1), data_addr = 16)),
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(27, 1), data_addr = 17)),
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(28, 1), data_addr = 18)),
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(29, 1), data_addr = 19)),
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(30, 1), data_addr = 20)),
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(31, 1), data_addr = 21)),
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(32, 1), data_addr = 22)),
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(33, 1), data_addr = 23)),
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(34, 1), data_addr = 24)),
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(35, 1), data_addr = 25)),
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(36, 1), data_addr = 26)),
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(37, 1), data_addr = 27)),
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(38, 1), data_addr = 28)),
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(39, 1), data_addr = 29)),
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(40, 1), data_addr = 30)),
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(41, 1), data_addr = 31)),
    ]
]

# FIR4x4 kernel (from compiled fir4x4.yaml):
#
# Kernel semantics (constants baked into fir4x4.yaml):
#   i = 0          (GRANT_ONCE #0)
#   sum = 0        (GRANT_ONCE #0)
#   while (i != 32):   (ICMP_EQ #32)
#     addr = 0 + i     (GEP #0, i)  -- same base for both LOADs
#     sum += data[addr] * data[addr]
#     i += 1           (ADD #1)
#
# With data[k] = 10 + k for k in [0, 32):
#   expected sum = Σ (10+k)^2 for k=0..31
#                = Σ k^2 for k=10..41
#                = 23536 (0x5BF0)


def sim_fir4x4_return(cmdline_opts, mem_access_is_combinational):
  src_ctrl_pkt = []
  complete_signal_sink_out = []
  src_query_pkt = []

  # kernel specific parameters (matching fir4x4.yaml constants).
  kStoreAddress = 16 # Unused; result is returned to CPU via RETURN_VALUE.
  kInputBaseAddress = 0       # GEP #0
  kCoefficientBaseAddress = 0 # GEP #0 (same base as input)
  kSumInitValue = 0           # GRANT_ONCE #0
  kLoopLowerBound = 0         # GRANT_ONCE #0
  kLoopIncrement = 1          # ADD #1
  kLoopUpperBound = 32        # ICMP_EQ #32
  kCtrlCountPerIter = 5       # compiled_ii: 5
  kTotalCtrlSteps = kCtrlCountPerIter * \
                    (kLoopUpperBound - kLoopLowerBound) + \
                    10
  # sum = Σ (10+k)^2 for k=0..31 = 23536
  kExpectedOutput = 23536

  from ...validation.script_generator import ScriptFactory
  script_factory = ScriptFactory(path = "validation/test/fir4x4.yaml",
                                    CtrlType = CtrlType,
                                    IntraCgraPktType = IntraCgraPktType,
                                    CgraPayloadType = CgraPayloadType,
                                    TileInType = TileInType,
                                    FuOutType = FuOutType,
                                    CMD_CONFIG_input = CMD_CONFIG,
                                    FuInType=FuInType,
                                    ii = kCtrlCountPerIter,
                                    loop_times = kTotalCtrlSteps,
                                    CMD_CONST_input = CMD_CONST,
                                    CMD_CONFIG_COUNT_PER_ITER_input = CMD_CONFIG_COUNT_PER_ITER,
                                    CMD_CONFIG_TOTAL_CTRL_COUNT_input = CMD_CONFIG_TOTAL_CTRL_COUNT,
                                    CMD_CONFIG_PROLOGUE_FU_input = CMD_CONFIG_PROLOGUE_FU,
                                    CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR_input = CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR,
                                    CMD_CONFIG_PROLOGUE_FU_CROSSBAR_input = CMD_CONFIG_PROLOGUE_FU_CROSSBAR,
                                    CMD_LAUNCH_input = CMD_LAUNCH,
                                    DataType = DataType,
                                    B1Type = b1,
                                    B2Type = b2,
                                    RegIdxType = RegIdxType,
                                    CtrlAddrType = CtrlAddrType,
                                    DataAddrType = DataAddrType,
                                    num_registers_per_reg_bank = num_registers_per_reg_bank)

  src_opt_pkt0_ = script_factory.makeVectorCGRAPkts()

  # order the packets according to the x (first) and y (second) coordinates
  src_opt_pkt0 = []
  for x, y in src_opt_pkt0_:
    src_opt_pkt0.append(src_opt_pkt0_[(x, y)])

  src_query_pkt = \
      [
      ]

  # RETURN_VALUE is at core 5 (col 1, row 1), so src = 5.
  expected_complete_sink_out_pkg = \
      [
          IntraCgraPktType(src = 5, dst = 16, payload = CgraPayloadType(CMD_COMPLETE, DataType(kExpectedOutput, 1, 0, 0))) for _ in range(1)
      ]
  expected_mem_sink_out_pkt = \
      [
      ]

  print("src_opt_pkt0: ", src_opt_pkt0)

  for activation in preload_data:
      src_ctrl_pkt.extend(activation)

  for tile_pkts in src_opt_pkt0:
      src_ctrl_pkt.extend(tile_pkts)

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
                   controller2addr_map, idTo2d_map, complete_signal_sink_out,
                   num_cgra_rows, num_cgra_columns,
                   src_query_pkt)

  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                       ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                        'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])

  trace_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'trace_output')
  trace_file = os.path.join(trace_dir, 'trace_fir4x4_4x4_Mesh.jsonl')
  init_trace_logger(trace_file, x_tiles, y_tiles, "Mesh", cgra_id)

  run_sim(th)

  close_trace_logger()

  cycles = th.sim_cycle_count()
  print("\n\n\ncycles: ", cycles)


def test_homogeneous_4x4_fir4x4_combinational_mem_access_return(cmdline_opts):
  sim_fir4x4_return(cmdline_opts, mem_access_is_combinational = True)
