"""
==========================================================================
CgraRTL_gemv_test_from_yaml.py
==========================================================================
Test cases for CGRA with crossbar-based data memory and ring-based control
memory of each tile, using gemv.yaml compiled kernel.

Author : Bohan Cui
  Date : April 5, 2026
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
from ...fu.single.DivRTL import DivRTL
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
          DivRTL,
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
ctrl_mem_size = 11
data_mem_size_global = 256
data_mem_size_per_bank = 32
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

# GEMV kernel (from compiled gemv.yaml):
#
# Kernel semantics (4x4 matrix-vector multiply y = A * x):
#   Outer loop: i = 0..3     (GRANT_ONCE #0, ICMP_EQ #4, ADD #1)
#     Inner loop: j = 0..3   (GRANT_ONCE #0, ICMP_EQ #4, ADD #1)
#       A_addr = i << 2 + j  (SHL #2, GEP)        -- stride-4 row layout
#       x_addr = j            (GEP #0)
#       acc += A[A_addr] * x[x_addr]  (LOAD, LOAD, MUL, ADD)
#     y_addr = 4 + i          (GEP #4)
#     y[y_addr] = acc          (STORE)
#   RETURN_VOID               (signals completion)
#
# Memory layout (word-addressed, shared memory):
#   A[0][0..3] / x[0..3]  at addresses  0..3   (overlap: A row 0 == x)
#   A[1][0..3] / y[0..3]  at addresses  4..7   (overlap: A row 1 == y)
#   A[2][0..3]             at addresses  8..11
#   A[3][0..3]             at addresses 12..15
#
# Note: In the original Zeonica per-tile-memory model, A and x/y live
#       in different tile memories.  In VectorCGRA's shared memory the
#       addresses collide.  We preload all 16 words (A rows 0-3) and
#       accept that stores to y[i] (addr 4+i) overwrite A[1].
#
#   RETURN_VOID sends CMD_COMPLETE with data = 0.

# Preload matrix A (stride 4) and vector x with value 1.
# A is row-major at addresses 0..15 with stride 4.
# x overlaps A[0] at addresses 0..3.
preload_data = [
    [
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(1, 1), data_addr = i))
        for i in range(16)
    ]
]


def sim_gemv(cmdline_opts, mem_access_is_combinational):
  src_ctrl_pkt = []
  complete_signal_sink_out = []
  src_query_pkt = []

  # Kernel specific parameters (matching gemv.yaml constants).
  # Nested loop: outer i=0..3, inner j=0..3, total 16 inner iterations.
  kCtrlCountPerIter = 11      # compiled_ii: 11
  kTotalIterations = 4 * 4    # outer_bound * inner_bound
  kTotalCtrlSteps = kCtrlCountPerIter * kTotalIterations + 20

  from ...validation.script_generator import ScriptFactory
  script_factory = ScriptFactory(path = "validation/test/gemv/gemv.yaml",
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

  # Order the packets according to the x (first) and y (second) coordinates.
  src_opt_pkt0 = []
  for x, y in src_opt_pkt0_:
    src_opt_pkt0.append(src_opt_pkt0_[(x, y)])

  src_query_pkt = \
      [
      ]

  # RETURN_VOID is at core 8 (col 0, row 2), so src = 8.
  # RETURN_VOID sends CMD_COMPLETE with data = 0.
  expected_complete_sink_out_pkg = \
      [
          IntraCgraPktType(src = 8, dst = 16, payload = CgraPayloadType(CMD_COMPLETE, DataType(0, 0, 0, 0))) for _ in range(1)
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
  trace_file = os.path.join(trace_dir, 'trace_gemv_4x4_Mesh.jsonl')
  init_trace_logger(trace_file, x_tiles, y_tiles, "Mesh", cgra_id)

  run_sim(th)

  close_trace_logger()

  cycles = th.sim_cycle_count()
  print("\n\n\ncycles: ", cycles)


def test_homogeneous_4x4_gemv_combinational_mem_access(cmdline_opts):
  sim_gemv(cmdline_opts, mem_access_is_combinational = True)
