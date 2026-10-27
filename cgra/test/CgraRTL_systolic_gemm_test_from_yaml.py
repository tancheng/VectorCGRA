"""
==========================================================================
CgraRTL_systolic_gemm_test_from_yaml.py
==========================================================================

Test cases for CGRA with crossbar-based data memory and ring-based control
memory of each tile, using neura_systolic_3x3.yaml compiled kernel.

Author : Shangkun Li, Jia Sun
  Date : Oct 11, 2026
"""

import os
from pathlib import Path

from pymtl3 import mk_bits
from pymtl3.passes.backends.verilog import (VerilogVerilatorImportPass)
from pymtl3.passes.sim.PrepareSimPass import b1
from pymtl3.stdlib.test_utils import (run_sim, config_model_with_cmdline_opts)

from ..CgraRTL import CgraRTL
from ...fu.double.SeqMulAdderRTL import SeqMulAdderRTL
from ...fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from ...fu.single.MemUnitRTL import MemUnitRTL
from ...fu.single.MulRTL import MulRTL
from ...lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ...lib.cmd_type import (
  CMD_COMPLETE, CMD_CONFIG, CMD_CONFIG_COUNT_PER_ITER,
  CMD_CONFIG_PROLOGUE_FU, CMD_CONFIG_PROLOGUE_FU_CROSSBAR,
  CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, CMD_CONFIG_TOTAL_CTRL_COUNT,
  CMD_CONST, CMD_LAUNCH, CMD_LOAD_REQUEST, CMD_LOAD_RESPONSE,
  CMD_STORE_REQUEST)
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
FuList = [MulRTL, MemUnitRTL, SeqMulAdderRTL]
x_tiles = 4
y_tiles = 4
data_bitwidth = 32
tile_ports = 4
num_tile_inports = tile_ports
num_tile_outports = tile_ports
num_fu_inports = 4
num_fu_outports = 2
num_routing_outports = num_tile_outports + num_fu_inports
ctrl_mem_size = 3
data_mem_size_global = 256
data_mem_size_per_bank = 32
num_banks_per_cgra = 2
num_cgra_columns = 4
num_cgra_rows = 1
num_cgras = num_cgra_columns * num_cgra_rows
num_registers_per_reg_bank = 8
TileInType = mk_bits(clog2(num_tile_inports + num_fu_inports + 1))
FuInType = mk_bits(clog2(num_fu_inports + 1))
FuOutType = mk_bits(clog2(num_fu_outports + 1))
addr_nbits = clog2(data_mem_size_global)

DataAddrType = mk_bits(addr_nbits)
RegIdxType = mk_bits(clog2(num_registers_per_reg_bank))
DataType = mk_data(data_bitwidth, 1)
cgra_id = 0
per_cgra_data_size = int(data_mem_size_global / num_cgras)
controller2addr_map = {
  i: [i * per_cgra_data_size, (i + 1) * per_cgra_data_size - 1]
  for i in range(num_cgras)
}
idTo2d_map = {
  0: [0, 0],
  1: [1, 0],
  2: [2, 0],
  3: [3, 0],
}

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
IntraCgraPktType = mk_intra_cgra_pkt(num_cgra_columns,
                                     num_cgra_rows,
                                     x_tiles * y_tiles,
                                     CgraPayloadType)


# Systolic GEMM kernel (from compiled neura_systolic_3x3.yaml).
# Kernel Semantics C = A * B, where A, B, C are 3x3 matrices.
# The 4×4 CGRA uses:
# one column of Tiles for loading;
# one row of Tiles for storing;
# the remaining 3×3 Tiles for MAC computation.
# The figure:
# Draw the 4×4 CGRA with the following layout:
#   +---+---+---+---+
#   |   | S | S | S |
#   +---+---+---+---+
#   | L | M | M | M |
#   +---+---+---+---+
#   | L | M | M | M |
#   +---+---+---+---+
#   | L | M | M | M |
#   +---+---+---+---+
# Where L = load, S = store, M = MAC.

N = 3  # matrix dimension

# Initialize matrices per PolyBench gemm_int.c init_array.
# A[i][j] = (i * (j+1)) % 17
# B[i][j] = (i * (j+2)) % 19
# C[i][j] = (i * j) % 13
BaseA = 0
BaseB = 9
BaseC = 18

preload_data_A = [
  IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST,
                   data = DataType((i * (k + 1)) % 17, 1),
                   data_addr = BaseA + i * N + k))
  for i in range(N) for k in range(N)
]

preload_data_B = [
  IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST,
                   data = DataType((k * (j + 2)) % 19, 1),
                   data_addr = BaseB + k * N + j))
  for k in range(N) for j in range(N)
]

preload_data_C = [
  IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST,
                   data = DataType((i * j) % 13, 1),
                   data_addr = BaseC + i * N + j))
  for i in range(N) for j in range(N)
]

preload_data = [preload_data_A + preload_data_B + preload_data_C]


def sim_neura_systolic_3x3_gemm(cmdline_opts, mem_access_is_combinational):
  src_ctrl_pkt = []
  complete_signal_sink_out = []
  src_query_pkt = []

  kCtrlCountPerIter = 1
  kTotalCtrlSteps = N
  matrix_a = [int(pkt.payload.data.payload) for pkt in preload_data_A]
  matrix_b = [int(pkt.payload.data.payload) for pkt in preload_data_B]
  matrix_c = [int(pkt.payload.data.payload) for pkt in preload_data_C]
  bases = [BaseA, BaseB, BaseC]
  inputs = [matrix_a, matrix_b, matrix_c]
  bindings = [
    {"base": base, "values": values}
    for base, values in zip(bases, inputs)
  ]

  expected = [
    sum(
      matrix_a[row * N + reduction]
      * matrix_b[reduction * N + column]
      for reduction in range(N)
    ) & 0xFFFFFFFF
    for row in range(N)
    for column in range(N)
  ]
  from ...validation.script_generator import ScriptFactory
  yaml_path = (Path(__file__).resolve().parents[2] / "validation" / "test" / "gemm" / "neura_systolic_3x3.yaml")
  script_factory = ScriptFactory(
    path=yaml_path,
    CtrlType=CtrlType,
    IntraCgraPktType=IntraCgraPktType,
    CgraPayloadType=CgraPayloadType,
    TileInType=TileInType,
    FuOutType=FuOutType,
    CMD_CONFIG_input=CMD_CONFIG,
    FuInType=FuInType,
    ii=kCtrlCountPerIter,
    loop_times=kTotalCtrlSteps,
    CMD_CONST_input=CMD_CONST,
    CMD_CONFIG_COUNT_PER_ITER_input=CMD_CONFIG_COUNT_PER_ITER,
    CMD_CONFIG_TOTAL_CTRL_COUNT_input=CMD_CONFIG_TOTAL_CTRL_COUNT,
    CMD_CONFIG_PROLOGUE_FU_input=CMD_CONFIG_PROLOGUE_FU,
    CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR_input=(
      CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR
    ),
    CMD_CONFIG_PROLOGUE_FU_CROSSBAR_input=(
      CMD_CONFIG_PROLOGUE_FU_CROSSBAR
    ),
    CMD_LAUNCH_input=CMD_LAUNCH,
    DataType=DataType,
    B1Type=b1,
    B2Type=b2,
    RegIdxType=RegIdxType,
    CtrlAddrType=CtrlAddrType,
    DataAddrType=DataAddrType,
    num_registers_per_reg_bank=num_registers_per_reg_bank,
    kernel_inputs=bindings,
  )
  src_opt_pkt0_ = script_factory.makeVectorCGRAPkts()

  for activation in preload_data:
    src_ctrl_pkt.extend(activation)

  launch_packets = []
  for packets in src_opt_pkt0_.values():
    for packet in packets:
      if packet.payload.cmd == CMD_LAUNCH:
        launch_packets.append(packet)
      else:
        src_ctrl_pkt.append(packet)
  src_ctrl_pkt.extend(reversed(launch_packets))

  src_query_pkt.extend([
    IntraCgraPktType(0, 0, payload=CgraPayloadType(
      CMD_LOAD_REQUEST,
      data_addr=BaseC + offset))
    for offset in range(N * N)
  ])

  complete_signal_sink_out.extend([
    IntraCgraPktType(payload=CgraPayloadType(CMD_COMPLETE))
    for _ in src_opt_pkt0_
  ])
  complete_signal_sink_out.extend(
    IntraCgraPktType(
      payload=CgraPayloadType(
        CMD_LOAD_RESPONSE,
        data=DataType(value, 1),
        data_addr=BaseC + offset,
      ))
    for offset, value in enumerate(expected)
  )

  th = TestHarness(CgraRTL,
                   FlexibleFuRTL,
                   [MulRTL, MemUnitRTL, SeqMulAdderRTL],
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
  trace_file = os.path.join(trace_dir, 'trace_systolic_gemm_3x3_Mesh.jsonl')
  init_trace_logger(trace_file, x_tiles, y_tiles, "Mesh", cgra_id)
  
  run_sim(th)
  
  close_trace_logger()
  cycles = th.sim_cycle_count()
  print("\n\n\ncycles: ", cycles)


def test_neura_systolic_3x3_gemm_combinational_mem_access(cmdline_opts):
  sim_neura_systolic_3x3_gemm(cmdline_opts, mem_access_is_combinational = True)


def test_neura_systolic_3x3_gemm_non_combinational_mem_access(cmdline_opts):
  sim_neura_systolic_3x3_gemm(cmdline_opts, mem_access_is_combinational = False)
