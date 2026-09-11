"""Run a Neura-generated systolic GEMM on the VectorCGRA RTL."""

from pathlib import Path

import pytest
from pymtl3 import mk_bits
from pymtl3.passes.backends.verilog import VerilogVerilatorImportPass
from pymtl3.passes.sim.PrepareSimPass import b1
from pymtl3.stdlib.test_utils import config_model_with_cmdline_opts, run_sim

from ...fu.double.SeqMulAdderRTL import SeqMulAdderRTL
from ...fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from ...fu.single.MemUnitRTL import MemUnitRTL
from ...fu.single.MulRTL import MulRTL
from ...validation.script_generator import ScriptFactory
from .CgraRTL_gemm_test_from_yaml import (
  CgraPayloadType,
  CgraRTL,
  CtrlAddrType,
  CtrlType,
  DataAddrType,
  DataType,
  FuInType,
  FuOutType,
  IntraCgraPktType,
  RegIdxType,
  TestHarness,
  TileInType,
  controller2addr_map,
  ctrl_mem_size,
  data_mem_size_global,
  data_mem_size_per_bank,
  idTo2d_map,
  num_banks_per_cgra,
  num_cgra_columns,
  num_cgra_rows,
  num_registers_per_reg_bank,
  x_tiles,
  y_tiles,
)
from ...lib.cmd_type import (
  CMD_COMPLETE,
  CMD_CONFIG,
  CMD_CONFIG_COUNT_PER_ITER,
  CMD_CONFIG_PROLOGUE_FU,
  CMD_CONFIG_PROLOGUE_FU_CROSSBAR,
  CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR,
  CMD_CONFIG_TOTAL_CTRL_COUNT,
  CMD_CONST,
  CMD_LAUNCH,
  CMD_LOAD_REQUEST,
  CMD_LOAD_RESPONSE,
  CMD_STORE_REQUEST,
)


YAML_PATH = (
  Path(__file__).parents[2]
  / "validation"
  / "test"
  / "gemm"
  / "neura_systolic_3x3.yaml"
)


@pytest.mark.parametrize("mem_access_is_combinational", [True, False])
def test_neura_systolic_gemm(cmdline_opts, mem_access_is_combinational):
  """Checks every output produced from Neura's generated YAML."""

  matrix_a = [
    1, -2, 3,
    4, 0, -1,
    2, 5, 1,
  ]
  matrix_b = [
    2, 1, -1,
    0, 3, 4,
    -2, 5, 2,
  ]
  matrix_c = [123] * 9
  bases = [5, 20, 40]
  inputs = [matrix_a, matrix_b, matrix_c]
  bindings = [
    {"base": base, "values": values}
    for base, values in zip(bases, inputs)
  ]

  expected = [
    sum(
      matrix_a[row * 3 + reduction]
      * matrix_b[reduction * 3 + column]
      for reduction in range(3)
    ) & 0xFFFFFFFF
    for row in range(3)
    for column in range(3)
  ]

  factory = ScriptFactory(
    path=str(YAML_PATH),
    CtrlType=CtrlType,
    IntraCgraPktType=IntraCgraPktType,
    CgraPayloadType=CgraPayloadType,
    TileInType=TileInType,
    FuOutType=FuOutType,
    CMD_CONFIG_input=CMD_CONFIG,
    FuInType=FuInType,
    ii=1,
    loop_times=3,
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
    B2Type=mk_bits(2),
    RegIdxType=RegIdxType,
    CtrlAddrType=CtrlAddrType,
    DataAddrType=DataAddrType,
    num_registers_per_reg_bank=num_registers_per_reg_bank,
    kernel_inputs=bindings,
  )
  tile_packets = factory.makeVectorCGRAPkts()

  control_packets = [
    IntraCgraPktType(
      0,
      0,
      payload=CgraPayloadType(
        CMD_STORE_REQUEST,
        data=DataType(value & 0xFFFFFFFF, 1),
        data_addr=base + offset,
      ),
    )
    for base, values in zip(bases, inputs)
    for offset, value in enumerate(values)
  ]

  launch_packets = []
  for packets in tile_packets.values():
    for packet in packets:
      if packet.payload.cmd == CMD_LAUNCH:
        launch_packets.append(packet)
      else:
        control_packets.append(packet)

  # Configure every consumer before the load Tiles begin producing data.
  control_packets.extend(reversed(launch_packets))

  query_packets = [
    IntraCgraPktType(
      0,
      0,
      payload=CgraPayloadType(
        CMD_LOAD_REQUEST,
        data_addr=bases[2] + offset,
      ),
    )
    for offset in range(9)
  ]

  expected_packets = [
    IntraCgraPktType(payload=CgraPayloadType(CMD_COMPLETE))
    for _ in tile_packets
  ]
  expected_packets.extend(
    IntraCgraPktType(
      payload=CgraPayloadType(
        CMD_LOAD_RESPONSE,
        data=DataType(value, 1),
        data_addr=bases[2] + offset,
      )
    )
    for offset, value in enumerate(expected)
  )

  harness = TestHarness(
    CgraRTL,
    FlexibleFuRTL,
    [MulRTL, MemUnitRTL, SeqMulAdderRTL],
    IntraCgraPktType,
    0,
    x_tiles,
    y_tiles,
    ctrl_mem_size,
    data_mem_size_global,
    data_mem_size_per_bank,
    num_banks_per_cgra,
    num_registers_per_reg_bank,
    control_packets,
    1,
    3,
    mem_access_is_combinational,
    controller2addr_map,
    idTo2d_map,
    expected_packets,
    num_cgra_rows,
    num_cgra_columns,
    query_packets,
  )

  harness.elaborate()
  harness.dut.set_metadata(
    VerilogVerilatorImportPass.vl_Wno_list,
    ["UNSIGNED", "UNOPTFLAT", "WIDTH", "WIDTHCONCAT", "ALWCOMBORDER"],
  )
  harness = config_model_with_cmdline_opts(
    harness, cmdline_opts, duts=["dut"]
  )
  run_sim(
    harness,
    cmdline_opts={**cmdline_opts, "max_cycles": 500},
    print_line_trace=False,
    duts=["dut"],
  )
