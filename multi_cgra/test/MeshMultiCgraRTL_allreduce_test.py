"""
==========================================================================
MeshMultiCgraRTL_allreduce_test.py
==========================================================================
Test case for one kernel replicated across CGRAs, using the allreduce.yaml
compiled kernel: every CGRA computes a partial dot product on its own
slice of the data, and a global reduce sums the partials.

  Date : Nov 10, 2026
"""

from pathlib import Path

from pymtl3.passes.backends.verilog import VerilogVerilatorImportPass
from pymtl3.stdlib.test_utils import config_model_with_cmdline_opts

from ..MeshMultiCgraRTL import MeshMultiCgraRTL
from ...fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from ...fu.single.AdderRTL import AdderRTL
from ...fu.single.CompRTL import CompRTL
from ...fu.single.GrantRTL import GrantRTL
from ...fu.single.LogicRTL import LogicRTL
from ...fu.single.MemUnitRTL import MemUnitRTL
from ...fu.single.PhiRTL import PhiRTL
from ...fu.single.RetRTL import RetRTL
from ...fu.vector.VectorAdderComboRTL import VectorAdderComboRTL
from ...fu.vector.VectorAllReduceRTL import VectorAllReduceRTL
from ...fu.vector.VectorMulComboRTL import VectorMulComboRTL
from ...lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ...lib.messages import *
from ...validation.script_generator import ScriptFactory

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, DUT, FunctionUnit, FuList,
                IntraCgraPktType,
                cgra_rows, cgra_columns, width, height, ctrl_mem_size,
                data_mem_size_global, data_mem_size_per_bank,
                num_banks_per_cgra, num_registers_per_reg_bank,
                src_ctrl_pkt, ctrl_steps_per_iter, ctrl_steps_total,
                mem_access_is_combinational,
                controller2addr_map, expected_sink_out_pkt,
                cmp_func):

    CgraPayloadType = IntraCgraPktType.get_field_type(kAttrPayload)

    s.src_ctrl_pkt = TestSrcRTL(IntraCgraPktType, src_ctrl_pkt)
    s.expected_sink_out = TestSinkRTL(IntraCgraPktType, expected_sink_out_pkt,
                                      cmp_fn = cmp_func)

    s.dut = DUT(CgraPayloadType, cgra_rows, cgra_columns,
                height, width, ctrl_mem_size, data_mem_size_global,
                data_mem_size_per_bank, num_banks_per_cgra,
                num_registers_per_reg_bank,
                ctrl_steps_per_iter, ctrl_steps_total,
                mem_access_is_combinational,
                FunctionUnit, FuList, "Mesh", controller2addr_map)

    # Connections
    s.src_ctrl_pkt.send //= s.dut.recv_from_cpu_pkt
    s.expected_sink_out.recv //= s.dut.send_to_cpu_pkt

  def done(s):
    return s.src_ctrl_pkt.done() and s.expected_sink_out.done()

  def line_trace(s):
    return s.dut.line_trace()

def run_sim(test_harness, max_cycles):
  test_harness.apply(DefaultPassGroup())
  test_harness.sim_reset()

  ncycles = 0
  while not test_harness.done() and ncycles < max_cycles:
    test_harness.sim_tick()
    ncycles += 1
  print("cycles: ", ncycles)

  # Checks timeout.
  assert ncycles < max_cycles

  test_harness.sim_tick()
  test_harness.sim_tick()
  test_harness.sim_tick()

#-------------------------------------------------------------------------
# Common configurations/setups.
#-------------------------------------------------------------------------

FuList = [AdderRTL,
          LogicRTL,
          PhiRTL,
          CompRTL,
          GrantRTL,
          MemUnitRTL,
          RetRTL,
          VectorMulComboRTL,
          VectorAdderComboRTL,
          VectorAllReduceRTL]
num_cgra_rows = 2
num_cgra_columns = 2
x_tiles = 4
y_tiles = 4
num_tile_inports = 4
num_tile_outports = 4
num_fu_inports = 4
num_fu_outports = 2
ctrl_mem_size = 16
data_mem_size_per_bank = 16
num_banks_per_cgra = 2
# allreduce.yaml numbers registers as $(bank * 8 + index).
num_registers_per_reg_bank = 8
num_cgras = num_cgra_rows * num_cgra_columns
num_tiles = x_tiles * y_tiles
per_cgra_data_size = data_mem_size_per_bank * num_banks_per_cgra
data_mem_size_global = per_cgra_data_size * num_cgras

# One data word holds one vector: 4 lanes of 16 bits.
data_nbits = 64
kVectorFactor = 4
kLaneNbits = data_nbits // kVectorFactor

TileInType = mk_bits(clog2(num_tile_inports + num_fu_inports + 1))
FuInType = mk_bits(clog2(num_fu_inports + 1))
FuOutType = mk_bits(clog2(num_fu_outports + 1))
DataType = mk_data(data_nbits, 1)
DataAddrType = mk_bits(clog2(data_mem_size_global))
RegIdxType = mk_bits(clog2(num_registers_per_reg_bank))
CtrlAddrType = mk_bits(clog2(ctrl_mem_size))

controller2addr_map = {}
for i in range(num_cgras):
  controller2addr_map[i] = [i * per_cgra_data_size,
                            (i + 1) * per_cgra_data_size - 1]

CtrlType = mk_ctrl(num_fu_inports,
                   num_fu_outports,
                   num_tile_inports,
                   num_tile_outports,
                   num_registers_per_reg_bank)

CgraPayloadType = mk_cgra_payload(DataType,
                                  DataAddrType,
                                  CtrlType,
                                  CtrlAddrType)

IntraCgraPktType = mk_intra_cgra_pkt(num_cgra_columns,
                                     num_cgra_rows,
                                     num_tiles,
                                     CgraPayloadType)

#-------------------------------------------------------------------------
# Kernel (compiled into allreduce.yaml)
#-------------------------------------------------------------------------
#
#   int kernel(int input[], int coefficient[]) {     // arg0, arg1
#     int partial = 0;
#     for (int i = 0; i < 32; ++i)
#       partial += input[i] * coefficient[i];
#     return cgra_allreduce_add(partial);
#   }
#
# The compiled loop is vectorized by 4 and still indexes by element (i += 4),
# while one data memory address holds a whole vector. So vector k of an
# array lives at address base + 4 * k. Each array therefore spans 29
# addresses, and the two arrays of one CGRA are interleaved one address
# apart so that both fit in the CGRA's 32 addresses.

kNumElements = 32          # ICMP_EQ #32
kCtrlCountPerIter = 5      # compiled_ii: 5
# A tile reports a plain COMPLETE once it has run this many ctrl steps, which
# must not happen before the kernel returns. Tiles that are launched first
# run ahead of the others until backpressure stops them, so the budget needs
# slack on top of the ii * iterations that the return tile itself takes.
kTotalCtrlSteps = kCtrlCountPerIter * (kNumElements // kVectorFactor) + 40
kReturnTile = 9            # RETURN_VALUE is at core 9 (col 1, row 2).

#                    id, x, y
kParticipatingCgras = [(0,  0, 0),
                       (1,  1, 0)]

def input_of(cgra_id):
  return [cgra_id * kNumElements + i + 1 for i in range(kNumElements)]

def coefficient_of(cgra_id):
  return [(i + cgra_id) % 5 + 1 for i in range(kNumElements)]

def arg_values_of(cgra_id):
  base = controller2addr_map[cgra_id][0]
  return {"arg0": base, "arg1": base + 1}

def mk_preload_pkts(cgra_id, cgra_x, cgra_y, base, elements):
  pkts = []
  for k in range(kNumElements // kVectorFactor):
    lanes = elements[k * kVectorFactor : (k + 1) * kVectorFactor]
    word = sum(value << (lane * kLaneNbits) for lane, value in enumerate(lanes))
    pkts.append(
        #                src, dst, src_cgra, dst_cgra, src_x, src_y, dst_x,  dst_y
        IntraCgraPktType(0,   0,   0,        cgra_id,  0,     0,     cgra_x, cgra_y,
                         payload = CgraPayloadType(CMD_STORE_REQUEST,
                                                   data = DataType(word, 1),
                                                   data_addr = base + kVectorFactor * k)))
  return pkts

def test_multi_CGRA_allreduce(cmdline_opts):
  yaml_path = Path(__file__).resolve().parents[2] / "validation" / "test" / "allreduce.yaml"
  script_factory = ScriptFactory(path = yaml_path,
                                 CtrlType = CtrlType,
                                 IntraCgraPktType = IntraCgraPktType,
                                 CgraPayloadType = CgraPayloadType,
                                 TileInType = TileInType,
                                 FuOutType = FuOutType,
                                 CMD_CONFIG_input = CMD_CONFIG,
                                 FuInType = FuInType,
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

  src_ctrl_pkt = []
  expected_total = 0
  for cgra_id, cgra_x, cgra_y in kParticipatingCgras:
    arg_values = arg_values_of(cgra_id)
    src_ctrl_pkt.extend(mk_preload_pkts(cgra_id, cgra_x, cgra_y, arg_values["arg0"], input_of(cgra_id)))
    src_ctrl_pkt.extend(mk_preload_pkts(cgra_id, cgra_x, cgra_y, arg_values["arg1"], coefficient_of(cgra_id)))
    expected_total += sum(a * b for a, b in zip(input_of(cgra_id), coefficient_of(cgra_id)))

  src_ctrl_pkt.extend(script_factory.makeGlobalReduceCountPkts(len(kParticipatingCgras)))

  for cgra_id, cgra_x, cgra_y in kParticipatingCgras:
    tile_pkts = script_factory.makeVectorCGRAPkts(arg_values_of(cgra_id), cgra_id, cgra_x, cgra_y)
    for pkts in tile_pkts.values():
      src_ctrl_pkt.extend(pkts)

  # Every participating CGRA returns the same total.
  expected_sink_out_pkt = [
      #                src,         dst,       src_cgra, dst_cgra, src_x,  src_y,  dst_x, dst_y
      IntraCgraPktType(kReturnTile, num_tiles, cgra_id,  0,        cgra_x, cgra_y, 0,     0,
                       payload = CgraPayloadType(CMD_COMPLETE, DataType(expected_total, 1, 0, 0)))
      for cgra_id, cgra_x, cgra_y in kParticipatingCgras]

  cmp_func = lambda a, b : a.payload.cmd == b.payload.cmd and \
                           a.payload.data == b.payload.data and \
                           a.src == b.src and \
                           a.src_cgra_id == b.src_cgra_id

  th = TestHarness(MeshMultiCgraRTL, FlexibleFuRTL, FuList,
                   IntraCgraPktType,
                   num_cgra_rows, num_cgra_columns, x_tiles, y_tiles,
                   ctrl_mem_size, data_mem_size_global,
                   data_mem_size_per_bank, num_banks_per_cgra,
                   num_registers_per_reg_bank,
                   src_ctrl_pkt, kCtrlCountPerIter, kTotalCtrlSteps,
                   True, # mem_access_is_combinational
                   controller2addr_map, expected_sink_out_pkt, cmp_func)

  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                      ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                       'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th, max_cycles = 1000)
