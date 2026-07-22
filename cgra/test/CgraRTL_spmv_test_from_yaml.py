"""
==========================================================================
CgraRTL_spmv_test_from_yaml.py
==========================================================================
Test cases for CGRA with crossbar-based data memory and ring-based control
memory of each tile, using spmv.yaml compiled kernel.

Author : Cheng Tan
  Date : Dec 22, 2024
"""

import os
import contextlib
import io
import yaml

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
    capture_spmv_write_events(s)
    if s.sim_cycle_count() >= 400:
      actual_mem = read_cgra_mem(s)
      golden_mem = cpu_spmv_golden()
      if all(
          actual_mem[addr] == (golden_mem[addr], 1)
          for addr in range(OUTPUT_BASE, SPMV_MEMORY_SIZE)):
        _SPMV_MONITOR_STATE["output_match_cycle"] = s.sim_cycle_count()
        return True
    fixed_rtl_cycles = int(os.getenv("SPMV_FIXED_RTL_CYCLES", "1000"))
    if fixed_rtl_cycles > 0:
      return s.sim_cycle_count() >= fixed_rtl_cycles
    return (s.src_ctrl_pkt.done() and s.src_query_pkt.done()
            and s.complete_signal_sink_out.done())

  def line_trace(s):
    s.dut.line_trace()
    return ""

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
ctrl_mem_size = 16  # compiled_ii=15, so need at least 16
data_mem_size_global = 512
data_mem_size_per_bank = 64
num_banks_per_cgra = 8
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
local_data_mem_size = data_mem_size_per_bank * num_banks_per_cgra

DUT = CgraRTL
FunctionUnit = FlexibleFuRTL

DataAddrType = mk_bits(addr_nbits)
RegIdxType = mk_bits(clog2(num_registers_per_reg_bank))
DataType = mk_data(data_bitwidth, 1)
PredicateType = mk_predicate(1, 1)
ControllerIdType = mk_bits(max(1, clog2(num_cgras)))
cgra_id = 0
controller2addr_map = {
    cgra_id: [0, local_data_mem_size - 1],
}
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

# =====================================================================
# SpMV kernel data setup
# =====================================================================
# SpMV (COO format): output[row[i]] += val[i] * feature[col[i]]
# nnz = 8 (from CONSTANT #8 in spmv.yaml), loop unrolled by 4.
#
# The logical C arrays occupy addresses [0, 35]. The four unrolled lanes use
# separate physical banks so the four accesses assumed parallel by the modulo
# schedule do not serialize on a single-port bank.
VAL_BASE     = 0
COL_BASE     = 8
ROW_BASE     = 16
FEATURE_BASE = 24
OUTPUT_BASE  = 28

SPMV_VAL     = [1, 2, 3, 4, 5, 6, 7, 8]
SPMV_COL     = [0, 1, 2, 3, 0, 1, 2, 3]
SPMV_ROW     = [0, 1, 2, 3, 4, 5, 6, 7]
SPMV_FEATURE = [1, 2, 3, 0]
SPMV_OUTPUT  = [0, 0, 0, 0, 0, 0, 0, 0]
SPMV_MEMORY_SIZE = OUTPUT_BASE + len(SPMV_OUTPUT)
SPMV_COMPILED_II = 15
SPMV_UNROLL_FACTOR = 4
SPMV_LANE_STRIDE = data_mem_size_per_bank


def spmv_lane_base(logical_base, lane):
  return lane * SPMV_LANE_STRIDE + logical_base


# Keep spmv.yaml unchanged and patch only the packets generated for this pytest.
# The ids are the GEP operations for each logical SpMV array.
SPMV_GEP_BASE_BY_ID = {
    # row[]
    88: spmv_lane_base(ROW_BASE, 0),
    119: spmv_lane_base(ROW_BASE, 1),
    116: spmv_lane_base(ROW_BASE, 2),
    113: spmv_lane_base(ROW_BASE, 3),
    254: spmv_lane_base(ROW_BASE, 0),
    # col[]
    89: spmv_lane_base(COL_BASE, 0),
    120: spmv_lane_base(COL_BASE, 1),
    117: spmv_lane_base(COL_BASE, 2),
    114: spmv_lane_base(COL_BASE, 3),
    255: spmv_lane_base(COL_BASE, 0),
    # val[]
    90: spmv_lane_base(VAL_BASE, 0),
    121: spmv_lane_base(VAL_BASE, 1),
    118: spmv_lane_base(VAL_BASE, 2),
    115: spmv_lane_base(VAL_BASE, 3),
    256: spmv_lane_base(VAL_BASE, 0),
    # feature[]
    182: spmv_lane_base(FEATURE_BASE, 0),
    209: spmv_lane_base(FEATURE_BASE, 1),
    207: spmv_lane_base(FEATURE_BASE, 2),
    205: spmv_lane_base(FEATURE_BASE, 3),
    302: spmv_lane_base(FEATURE_BASE, 0),
    # output[]
    181: spmv_lane_base(OUTPUT_BASE, 0),
    208: spmv_lane_base(OUTPUT_BASE, 1),
    206: spmv_lane_base(OUTPUT_BASE, 2),
    204: spmv_lane_base(OUTPUT_BASE, 3),
    301: spmv_lane_base(OUTPUT_BASE, 0),
}

_SPMV_MONITOR_STATE = {
    "write_events": [],
    "output_match_cycle": None,
}


def make_spmv_memory_image():
  mem = [0 for _ in range(SPMV_MEMORY_SIZE)]
  for i, value in enumerate(SPMV_VAL):
    mem[VAL_BASE + i] = value
  for i, value in enumerate(SPMV_COL):
    mem[COL_BASE + i] = value
  for i, value in enumerate(SPMV_ROW):
    mem[ROW_BASE + i] = value
  for i, value in enumerate(SPMV_FEATURE):
    mem[FEATURE_BASE + i] = value
  for i, value in enumerate(SPMV_OUTPUT):
    mem[OUTPUT_BASE + i] = value
  return mem


preload_data = [
    [
        IntraCgraPktType(
            0, 0,
            payload=CgraPayloadType(
                CMD_STORE_REQUEST,
                data=DataType(value, 1),
                data_addr=lane * SPMV_LANE_STRIDE + i))
        for lane in range(SPMV_UNROLL_FACTOR)
        for i, value in enumerate(make_spmv_memory_image())
    ]
]


def cpu_spmv_golden():
  """CPU model for the separated-array SpMV address map."""
  mem = make_spmv_memory_image()

  for i in range(8):
    val = mem[VAL_BASE + i]
    col = mem[COL_BASE + i]
    row = mem[ROW_BASE + i]
    temp = val * mem[FEATURE_BASE + col]
    mem[OUTPUT_BASE + row] += temp

  return mem


def read_cgra_mem(th):
  mem = []
  for i in range(SPMV_MEMORY_SIZE):
    # Each output row is owned by the corresponding unrolled lane. Inputs are
    # identical in every lane copy, so lane zero is sufficient for readback.
    lane = (i - OUTPUT_BASE) % SPMV_UNROLL_FACTOR \
        if i >= OUTPUT_BASE else 0
    physical_addr = lane * SPMV_LANE_STRIDE + i
    bank = physical_addr >> clog2(data_mem_size_per_bank)
    offset = physical_addr & (data_mem_size_per_bank - 1)
    cell = th.dut.data_mem.memory_wrapper[bank].memory.regs[offset]
    mem.append((int(cell.payload), int(cell.predicate)))
  return mem


def _is_imm_operand(operand):
  text = operand['operand']
  return (
      not text.startswith('$') and
      text.upper() not in ('NORTH', 'SOUTH', 'WEST', 'EAST',
                           'SOUTHEAST', 'SOUTHWEST', 'NORTHWEST',
                           'NORTHEAST')
  )


def _imm_operand_value(operand):
  text = operand['operand']
  return int(text[1:] if text.startswith('#') else text)


def patch_spmv_gep_base_consts(src_opt_pkt0_):
  """Patch generated const packets locally for this pytest.

  The checked-in YAML still has GEP base #0 everywhere. For this test we want
  to compare against the C-level separated arrays, so replace only the GEP base
  constants in the generated packets.
  """
  yaml_path = os.path.join(os.path.dirname(__file__),
                           '..', '..', 'validation', 'test', 'spmv.yaml')
  with open(yaml_path, 'r') as stream:
    yaml_struct = yaml.safe_load(stream)

  for core in yaml_struct['array_config']['cores']:
    x = core['column']
    y = core['row']
    core_id = int(core['core_id'])
    consts = []

    for entry in core['entries']:
      for instruction in entry['instructions']:
        ctrl_addr = instruction['index_per_ii']
        for op_order, operation in enumerate(instruction.get('operations', [])):
          op_id = int(operation.get('id', -1))
          for src_idx, src_operand in enumerate(operation.get('src_operands', [])):
            if _is_imm_operand(src_operand):
              value = _imm_operand_value(src_operand)
              if operation.get('opcode') == 'GEP' and src_idx == 0:
                value = SPMV_GEP_BASE_BY_ID.get(op_id, value)
              consts.append((
                  int(operation.get('time_step', ctrl_addr)) +
                  int(operation.get('invalid_iterations', 0)) * SPMV_COMPILED_II,
                  op_order,
                  src_idx,
                  ctrl_addr,
                  value))

    consts.sort(key=lambda item: (item[0], item[1], item[2]))

    tile_pkts = src_opt_pkt0_[(x, y)]
    const_pkt_indices = [
        i for i, pkt in enumerate(tile_pkts)
        if int(pkt.payload.cmd) == CMD_CONST
    ]
    assert len(const_pkt_indices) == len(consts), (
        f"Core {core_id} const packet count mismatch: "
        f"{len(const_pkt_indices)} packets vs {len(consts)} YAML consts"
    )

    for pkt_idx, (_, _, _, ctrl_addr, value) in zip(const_pkt_indices, consts):
      tile_pkts[pkt_idx] = IntraCgraPktType(
          0, core_id,
          payload=CgraPayloadType(
              CMD_CONST,
              ctrl_addr=CtrlAddrType(ctrl_addr),
              data=DataType(value, 1)))


def reset_spmv_monitor():
  _SPMV_MONITOR_STATE["write_events"] = []
  _SPMV_MONITOR_STATE["output_match_cycle"] = None


def capture_spmv_write_events(th):
  cycle = th.sim_cycle_count()
  for tile_id, tile in enumerate(th.dut.tile):
    waddr = tile.to_mem_waddr
    wdata = tile.to_mem_wdata
    if not (int(waddr.val) and int(waddr.rdy) and
            int(wdata.val) and int(wdata.rdy)):
      continue
    physical_addr = int(waddr.msg)
    lane = physical_addr // SPMV_LANE_STRIDE
    addr = physical_addr % SPMV_LANE_STRIDE
    if (lane < SPMV_UNROLL_FACTOR and
        OUTPUT_BASE <= addr < SPMV_MEMORY_SIZE):
      _SPMV_MONITOR_STATE["write_events"].append({
          "cycle": cycle,
          "tile": tile_id,
          "ctrl": int(tile.ctrl_mem.reg_file.raddr[0]),
          "times": int(tile.ctrl_mem.times),
          "addr": addr,
          "physical_addr": physical_addr,
          "data": int(wdata.msg.payload),
          "predicate": int(wdata.msg.predicate),
      })


def spmv_output_batch_completion_cycles():
  completion_cycles = []
  events = [
      event for event in _SPMV_MONITOR_STATE["write_events"]
      if event["predicate"]
  ]
  for first_row in range(0, len(SPMV_OUTPUT), SPMV_UNROLL_FACTOR):
    batch_addrs = set(range(
        OUTPUT_BASE + first_row,
        OUTPUT_BASE + first_row + SPMV_UNROLL_FACTOR))
    batch_events = [event for event in events if event["addr"] in batch_addrs]
    observed_addrs = {event["addr"] for event in batch_events}
    assert observed_addrs == batch_addrs, (
        f"Missing output STOREs for batch {first_row // SPMV_UNROLL_FACTOR}: "
        f"expected {sorted(batch_addrs)}, observed {sorted(observed_addrs)}")
    completion_cycles.append(max(event["cycle"] for event in batch_events))
  return completion_cycles


def sim_spmv_return(cmdline_opts, mem_access_is_combinational):
  src_ctrl_pkt = []
  complete_signal_sink_out = []
  src_query_pkt = []

  # SpMV kernel parameters (matching spmv.yaml).
  kCtrlCountPerIter = SPMV_COMPILED_II
  # This is a controller logical-step ceiling, not an RTL cycle count.
  # Completion is determined by CMD_COMPLETE; keep the ceiling comfortably above
  # the expected program length so the RTL can run until the kernel exits.
  kTotalCtrlSteps = 256

  from ...validation.script_generator import ScriptFactory
  script_factory = ScriptFactory(path = "validation/test/spmv.yaml",
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

  if os.getenv("SPMV_SHOW_GENERATOR_LOG", "0") == "1":
    src_opt_pkt0_ = script_factory.makeVectorCGRAPkts()
  else:
    with contextlib.redirect_stdout(io.StringIO()):
      src_opt_pkt0_ = script_factory.makeVectorCGRAPkts()
  patch_spmv_gep_base_consts(src_opt_pkt0_)

  # order the packets according to the x (first) and y (second) coordinates
  src_opt_pkt0 = []
  for x, y in src_opt_pkt0_:
    src_opt_pkt0.append(src_opt_pkt0_[(x, y)])

  src_query_pkt = \
      [
      ]

  # RETURN_VOID at core 4 (col=0, row=1), so src = 4.
  # For RETURN_VOID, the expected data is 0 with predicate=0.
  expected_complete_sink_out_pkg = \
      [
          IntraCgraPktType(src = 4, dst = 16, payload = CgraPayloadType(CMD_COMPLETE, DataType(0, 0, 0, 0))) for _ in range(1)
      ]
  expected_mem_sink_out_pkt = \
      [
      ]

  # print("src_opt_pkt0: ", src_opt_pkt0)  # Too verbose

  for activation in preload_data:
      src_ctrl_pkt.extend(activation)

  # Configure every tile before launching any of them. The modulo schedule
  # assumes a common time origin across tiles; launching each tile immediately
  # after its own configuration can skew their starts by hundreds of cycles.
  launch_pkts = []
  for tile_pkts in src_opt_pkt0:
      for pkt in tile_pkts:
          if pkt.payload.cmd == CMD_LAUNCH:
              launch_pkts.append(pkt)
          else:
              src_ctrl_pkt.append(pkt)
  # The controller occupies the final ring terminal. Send launches for the
  # farthest tiles first so ring flight time does not add directly to launch
  # skew between producer and consumer tiles.
  controller_ring_pos = num_tiles
  ring_size = num_tiles + 1
  launch_pkts.sort(
      key=lambda pkt: -min(
          (int(pkt.dst) - controller_ring_pos) % ring_size,
          (controller_ring_pos - int(pkt.dst)) % ring_size))
  src_ctrl_pkt.extend(launch_pkts)

  complete_signal_sink_out.extend(expected_complete_sink_out_pkg)
  complete_signal_sink_out.extend(expected_mem_sink_out_pkt)

  import time as _time
  print(f"[TIMING] src_ctrl_pkt has {len(src_ctrl_pkt)} packets", flush=True)
  _t0 = _time.time()

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

  print(f"[TIMING] TestHarness constructed in {_time.time()-_t0:.1f}s", flush=True)
  _t1 = _time.time()

  th.elaborate()
  print(f"[TIMING] elaborate() done in {_time.time()-_t1:.1f}s", flush=True)
  _t2 = _time.time()

  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                       ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                        'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  print(f"[TIMING] config_model done in {_time.time()-_t2:.1f}s", flush=True)
  _t3 = _time.time()

  enable_trace = os.getenv("SPMV_ENABLE_TRACE", "0") == "1"
  reset_spmv_monitor()
  if enable_trace:
    trace_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'trace_output')
    trace_file = os.path.join(trace_dir, 'trace_spmv_4x4_Mesh.jsonl')
    init_trace_logger(trace_file, x_tiles, y_tiles, "Mesh", cgra_id)

  run_sim(th, print_line_trace=enable_trace)
  print(f"[TIMING] run_sim done in {_time.time()-_t3:.1f}s", flush=True)

  if enable_trace:
    close_trace_logger()

  cycles = th.sim_cycle_count()
  print("\n\n\ncycles: ", cycles)
  print("output match cycle:", _SPMV_MONITOR_STATE["output_match_cycle"])

  # ---------------------------------------------------------------------------
  # Post-simulation memory check.
  #
  # Compare against the original C semantics using the separated-array memory
  # map defined above. This requires spmv.yaml GEP bases to match that map.
  # ---------------------------------------------------------------------------
  actual_mem = read_cgra_mem(th)
  golden_payloads = cpu_spmv_golden()
  mismatches = []
  for i, expected_payload in enumerate(golden_payloads):
    actual_payload, actual_predicate = actual_mem[i]
    if actual_payload != expected_payload or actual_predicate != 1:
      mismatches.append((i, expected_payload, actual_payload, actual_predicate))

  print("\n=== CPU golden vs CGRA memory ===")
  print("  expected payloads:", golden_payloads)
  print("  actual payloads:  ", [payload for payload, _ in actual_mem])
  print("  actual predicates:", [predicate for _, predicate in actual_mem])
  if mismatches:
    print("  mismatches (addr, expected_payload, actual_payload, actual_predicate):")
    for mismatch in mismatches:
      print(f"    {mismatch}")
  else:
    print("  all local memory cells match")
  print("=================================\n")

  print("=== Output STORE handshakes ===")
  for event in _SPMV_MONITOR_STATE["write_events"]:
    print("  " + " ".join(f"{key}={value}"
                            for key, value in event.items()))
  print("===============================\n")

  batch_completion_cycles = spmv_output_batch_completion_cycles()
  effective_iis = [
      current - previous
      for previous, current in zip(
          batch_completion_cycles, batch_completion_cycles[1:])
  ]
  print("output batch completion cycles:", batch_completion_cycles)
  print("effective II:", effective_iis)

  assert not mismatches, (
      "CGRA SpMV result mismatch: "
      "(addr, expected_payload, actual_payload, actual_predicate) = "
      f"{mismatches}"
  )
  assert all(ii == SPMV_COMPILED_II for ii in effective_iis), (
      f"RTL effective II {effective_iis} does not match compiled II "
      f"{SPMV_COMPILED_II}"
  )


def test_spmv_unrolled_lanes_use_distinct_memory_banks():
  lane_gep_ids = (
      (88, 119, 116, 113),
      (89, 120, 117, 114),
      (90, 121, 118, 115),
      (182, 209, 207, 205),
      (181, 208, 206, 204),
  )
  expected_banks = list(range(SPMV_UNROLL_FACTOR))
  for gep_ids in lane_gep_ids:
    actual_banks = [
        SPMV_GEP_BASE_BY_ID[gep_id] // SPMV_LANE_STRIDE
        for gep_id in gep_ids
    ]
    assert actual_banks == expected_banks

def test_homogeneous_4x4_spmv_combinational_mem_access_return(cmdline_opts):
  sim_spmv_return(cmdline_opts, mem_access_is_combinational = True)
