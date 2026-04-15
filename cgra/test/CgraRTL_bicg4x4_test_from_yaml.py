"""
==========================================================================
CgraRTL_bicg4x4_test_from_yaml.py
==========================================================================
Test cases for CGRA with crossbar-based data memory and ring-based control
memory of each tile, using bicg.yaml compiled kernel.

BiCG kernel semantics (M=8, N=8):
  for j in [0,M): s[j] = 0
  for i in [0,N):
      q[i] = 0
      for j in [0,M):
          a = A[i*M + j]
          s[j] += r[i] * a
          q[i] += a * p[j]

Memory layout (per-tile local memory):
  Tile (0,2): A[8x8] at base 0, row stride=32 (SHL #5). A[i][j] at addr i*32+j.
  Tile (1,0): p[8] at base 0 (addr 0..7), s[8] at base 8 (addr 8..15).
  Tile (0,1): r[8] at base 0 (addr 0..7).
  Tile (0,3): q[8] at base 0 (addr 0..7).

Author : Shiran Guo
  Date : Apr 7, 2026
"""

import os

from pymtl3.datatypes import b1, b2
from pymtl3.passes.backends.verilog import (VerilogVerilatorImportPass)
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)

from ..CgraRTL import CgraRTL
from ...fu.double.SeqMulAdderRTL import SeqMulAdderRTL
from ...fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from ...fu.float.FpAddRTL import FpAddRTL
from ...fu.float.FpMulRTL import FpMulRTL
from ...fu.single.AdderRTL import AdderRTL
from ...fu.single.DivRTL import DivRTL
from ...fu.single.GepRTL import GepRTL
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
          GepRTL,
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
ctrl_mem_size = 12   # ii=10, need at least 10 slots
data_mem_size_global = 512
data_mem_size_per_bank = 256
num_banks_per_cgra = 2
num_cgra_columns = 1
num_cgra_rows = 1
num_cgras = num_cgra_columns * num_cgra_rows
num_ctrl_operations = 64
num_registers_per_reg_bank = 8  # $0..$7 = cluster 1, $8..$15 = cluster 2
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

# Helper to convert signed int to unsigned 32-bit representation.
def to_uint32(val):
  """Convert signed Python int to 32-bit unsigned representation."""
  if val < 0:
    return val + (1 << data_bitwidth)
  return val


# ========================================================================
# BiCG kernel parameters (M=8, N=8)
# ========================================================================
# IMPORTANT: The compiled YAML assumes per-tile local memory (each tile
# has its own independent memory). VectorCGRA has a SHARED global memory
# across all tiles. This means addresses 0-7 overlap between A (tile 8),
# p (tile 1), r (tile 4), and q (tile 12). Numerical results will be
# INCORRECT until per-tile memory support is added. However, the control
# flow (loop counters, PHI nodes, predication, completion) should work.
#
# Memory layout (Zeonica per-tile view):
#   Tile (0,2): A[8x8] at base 0, row stride=32. A[i][j] = addr i*32+j
#   Tile (1,0): p[8] at base 0 (addr 0..7), s[8] at base 8 (addr 8..15)
#   Tile (0,1): r[8] at base 0 (addr 0..7)
#   Tile (0,3): q[8] at base 0 (addr 0..7)
#
# Input data (matching main.go):
#   A[i][j] = (i*(j+1)) % 17 + 1
#   p[j] = (j*3) % 13 + 1
#   r[i] = (i*2) % 11 + 1
#
# Expected (correct only with per-tile memory):
#   s[j] = sum_i( r[i] * A[i][j] )   for j in [0,M)
#   q[i] = sum_j( A[i][j] * p[j] )   for i in [0,N)

M = 8
N = 8
RowStride = 32  # A row stride = 32 (SHL #5)
BaseA = 0       # A base address in tile (0,2)
# Match PE(0,0) GEP bases in bicg.yaml (#256 / #264): p and s live in bank 1 to reduce mem port/bank contention with other tiles.
BaseP = 256     # p base address in tile (1,0) — was 0 when GEP used #0
BaseS = 264     # s base address in tile (1,0) — was 8 when GEP used #8 (256+8)
BaseR = 0       # r base address in tile (0,1)
BaseQ = 0       # q base address in tile (0,3)

# Input data (matching main.go formulas)
A_values = [[(i*(j+1)) % 17 + 1 for j in range(M)] for i in range(N)]
p_values = [(j*3) % 13 + 1 for j in range(M)]
r_values = [(i*2) % 11 + 1 for i in range(N)]

# Expected outputs
expected_s = [0] * M
expected_q = [0] * N
for i in range(N):
  for j in range(M):
    a = A_values[i][j]
    expected_s[j] += r_values[i] * a
    expected_q[i] += a * p_values[j]

print(f"A = {A_values}")
print(f"p = {p_values}")
print(f"r = {r_values}")
print(f"expected_s = {expected_s}")
print(f"expected_q = {expected_q}")

# Preload data into shared global memory.
#
# WARNING: VectorCGRA has a single shared memory for all tiles.
# The compiled YAML assumes per-tile memory, so base addresses overlap:
#   A starts at 0, p starts at 0, r starts at 0, q starts at 0, s starts at 8.
# We preload A first (uses sparse addresses with stride 32), then
# overwrite overlapping addresses with the smaller arrays.
# This means A[0][0..7] at addresses 0-7 will be overwritten by the
# last array loaded at those addresses. Numerical results will be wrong.
#
# Tile memory port mapping (col 0 or row 0 tiles only):
#   tile 0 (col0,row0) → mem port 0
#   tile 1 (col1,row0) → mem port 1
#   tile 2 (col2,row0) → mem port 2
#   tile 3 (col3,row0) → mem port 3
#   tile 4 (col0,row1) → mem port 4
#   tile 8 (col0,row2) → mem port 5
#   tile 12(col0,row3) → mem port 6

preload_data = []

# Preload A into shared memory (stride 32, sparse).
# Addresses used: {0-7, 32-39, 64-71, ..., 224-231}
for i in range(N):
  for j in range(M):
    addr = BaseA + i * RowStride + j
    preload_data.append(
      IntraCgraPktType(0, 8, payload = CgraPayloadType(CMD_STORE_REQUEST,
          data = DataType(A_values[i][j], 1), data_addr = addr))
    )

# Preload p at addresses 0..7 (overwrites A[0][0..7])
for j in range(M):
  preload_data.append(
    IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_STORE_REQUEST,
        data = DataType(p_values[j], 1), data_addr = BaseP + j))
  )

# Pre-initialize s to 0 at addresses 8..15
for j in range(M):
  preload_data.append(
    IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_STORE_REQUEST,
        data = DataType(0, 1), data_addr = BaseS + j))
  )

# Preload r at addresses 0..7 (overwrites p[0..7])
for i in range(N):
  preload_data.append(
    IntraCgraPktType(0, 4, payload = CgraPayloadType(CMD_STORE_REQUEST,
        data = DataType(r_values[i], 1), data_addr = BaseR + i))
  )

# Pre-initialize q to 0 at addresses 0..7 (overwrites r[0..7])
for i in range(N):
  preload_data.append(
    IntraCgraPktType(0, 12, payload = CgraPayloadType(CMD_STORE_REQUEST,
        data = DataType(0, 1), data_addr = BaseQ + i))
  )


def sim_bicg(cmdline_opts, mem_access_is_combinational):
  src_ctrl_pkt = []
  complete_signal_sink_out = []
  src_query_pkt = []

  # kernel specific parameters (matching bicg.yaml constants).
  kInnerLoopBound = M             # ICMP_EQ #8 (inner j loop)
  kOuterLoopBound = N             # ICMP_EQ #8 (outer i loop)
  kCtrlCountPerIter = 10          # compiled_ii: 10
  # Total ctrl steps = ii * (N * M) + extra margin for prologue/epilogue
  kTotalCtrlSteps = kCtrlCountPerIter * (kOuterLoopBound * kInnerLoopBound) + 20

  from ...validation.script_generator import ScriptFactory
  script_factory = ScriptFactory(path = "validation/test/bicg/bicg.yaml",
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

  import sys
  print(">>> makeVectorCGRAPkts returned, ordering packets...")
  sys.stdout.flush()

  # order the packets according to the x (first) and y (second) coordinates
  src_opt_pkt0 = []
  for x, y in src_opt_pkt0_:
    src_opt_pkt0.append(src_opt_pkt0_[(x, y)])

  print(f">>> Packets ordered, creating expected sink packets...")
  sys.stdout.flush()

  src_query_pkt = []

  # RETURN_VOID is at core 6 (col 2, row 1), so src = 6.
  # RET_VOID sends CMD_COMPLETE with data = 0.
  expected_complete_sink_out_pkg = \
      [
          IntraCgraPktType(src = 6, dst = 16,
                           payload = CgraPayloadType(CMD_COMPLETE,
                                                      DataType(0, 0, 0, 0)))
          for _ in range(1)
      ]
  expected_mem_sink_out_pkt = []

  # print("src_opt_pkt0: ", src_opt_pkt0)  # Suppressed: too large
  print(f"Packet generation done. {len(src_opt_pkt0)} tile packet lists generated.")

  # Add preload data first
  src_ctrl_pkt.extend(preload_data)

  # Add tile configuration packets
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

  # Use pure-Python simulation (no Verilog translation) for debugging.
  from pymtl3 import DefaultPassGroup
  print(">>> Starting elaborate()...")
  sys.stdout.flush()
  th.elaborate()
  print(">>> elaborate() done. Applying DefaultPassGroup...")
  sys.stdout.flush()
  th.apply(DefaultPassGroup(linetrace=False))
  print(">>> DefaultPassGroup applied. Running sim_reset()...")
  sys.stdout.flush()
  th.sim_reset()
  print(">>> sim_reset() done. Starting simulation...")
  sys.stdout.flush()

  trace_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'trace_output')
  trace_file = os.path.join(trace_dir, 'trace_bicg4x4_4x4_Mesh.jsonl')
  trace_logger = init_trace_logger(trace_file, x_tiles, y_tiles, "Mesh", cgra_id)

  # Active tiles for BiCG: cores 0,1,2,4,5,6,8,9,12,13
  # Flat tile indices: 0,1,2,4,5,6,8,9,12,13
  active_tiles = {}
  for tid in [0, 1, 2, 4, 5, 6, 8, 9, 12, 13]:
    active_tiles[tid] = th.dut.tile[tid]

  prev_state = {}
  for tid in active_tiles:
    prev_state[tid] = (-1, -1)
  stall_count = 0

  # RTL II measurement: track per-tile cycle-by-cycle (times, raddr, val, rdy)
  # We detect each time PC wraps around (raddr goes from II-1 back to 0) to
  # measure how many wall-clock cycles one "iteration" actually takes in RTL.
  ii_trace = {tid: [] for tid in active_tiles}   # list of (cycle, times, raddr, val, rdy)
  # Records the wall-clock cycle when each wrap-around happens per tile
  iter_wrap_cycles = {tid: [] for tid in active_tiles}
  prev_raddr = {tid: -1 for tid in active_tiles}

  MAX_CYCLES = 2000
  for cycle in range(MAX_CYCLES):
    th.sim_tick()
    trace_logger.log_cycle(th.dut)

    # Collect state for all active tiles
    cur_state = {}
    for tid, t in active_tiles.items():
      cq = t.const_mem
      cm = t.ctrl_mem
      raddr = int(cm.reg_file.raddr[0])
      rdcur = int(cq.rd_cur)
      cur_state[tid] = (raddr, rdcur)

    # RTL II measurement: record per-tile trace and detect PC wrap-arounds
    for tid, t in active_tiles.items():
      cm = t.ctrl_mem
      raddr = int(cm.reg_file.raddr[0])
      times = int(cm.times)
      val   = int(cm.send_ctrl.val)
      rdy   = int(cm.send_ctrl.rdy)
      started = int(cm.start_iterate_ctrl)
      ii_trace[tid].append((cycle, times, raddr, val, rdy, started))
      # Detect wrap: PC goes from (kCtrlCountPerIter-1) back to 0
      if started and prev_raddr[tid] == kCtrlCountPerIter - 1 and raddr == 0:
        iter_wrap_cycles[tid].append(cycle)
      prev_raddr[tid] = raddr

    any_changed = any(cur_state[tid] != prev_state[tid] for tid in active_tiles)
    any_started = any(int(t.ctrl_mem.start_iterate_ctrl) for t in active_tiles.values())

    if any_changed or not any_started:
      stall_count = 0
    else:
      stall_count += 1
      if stall_count >= 100:
        print(f"\n=== EARLY DEADLOCK DETECTED at cycle {cycle} (stalled {stall_count} cycles) ===")
        break

    should_print = (cycle < 3) or (cycle % 100 == 0)
    if should_print:
      parts = []
      for tid, t in sorted(active_tiles.items()):
        cm = t.ctrl_mem
        cq = t.const_mem
        raddr = int(cm.reg_file.raddr[0])
        times = int(cm.times)
        start = int(cm.start_iterate_ctrl)
        op = int(cm.send_ctrl.msg.operation) if start else 0
        e = int(t.element_done)
        r = int(t.routing_crossbar_done)
        f = int(t.fu_crossbar_done)
        rdcur = int(cq.rd_cur)
        cv = int(cq.send_const.val)
        cr = int(cq.send_const.rdy)
        pf = int(cm.prologue_count_outport_fu)
        changed = "*" if cur_state[tid] != prev_state[tid] else " "
        parts.append(f"t{tid}{changed}a{raddr}:0x{op:02x}t{times}e{e}r{r}f{f}q{rdcur}c{cv}{cr}p{pf}")
      print(f"[cyc={cycle:4d}] {' | '.join(parts)}")
      sys.stdout.flush()

    prev_state = cur_state

    if th.done():
      print(f"\n=== SIMULATION DONE at cycle {cycle} ===")
      break

  if not th.done():
    print(f"\n=== DEADLOCK after {MAX_CYCLES} cycles ===")
    # Print final state of all active tiles
    dir_names = ["N", "S", "W", "E"]
    for tid, t in sorted(active_tiles.items()):
      cq = t.const_mem
      cm = t.ctrl_mem
      raddr = int(cm.reg_file.raddr[0])
      times = int(cm.times)
      op = int(cm.send_ctrl.msg.operation)
      rdcur = int(cq.rd_cur)
      wrcur = int(cq.wr_cur)
      cval = int(cq.send_const.msg.payload)
      cv = int(cq.send_const.val)
      cr = int(cq.send_const.rdy)
      cp = int(cq.ctrl_proceed)
      ed = int(t.element_done)
      rd = int(t.routing_crossbar_done)
      fd = int(t.fu_crossbar_done)
      print(f"  tile{tid}: raddr={raddr} op=0x{op:02x} times={times} | rd_cur={rdcur} wr_cur={wrcur} const={cval}.v={cv}.rdy={cr} | "
            f"ctrl_proceed={cp} e={ed} r={rd} f={fd}")
      ch_parts = []
      for pi in range(4):
        rv = int(t.recv_data[pi].val)
        rr = int(t.recv_data[pi].rdy)
        sv = int(t.send_data[pi].val)
        sr = int(t.send_data[pi].rdy)
        ch_parts.append(f"{dir_names[pi]}:rv{rv}rr{rr}sv{sv}sr{sr}")
      print(f"          channels: {' | '.join(ch_parts)}")

  close_trace_logger()

  cycles = cycle + 1
  print(f"\n\n\ncycles: {cycles}")

  # -----------------------------------------------------------------------
  # RTL II Analysis
  # -----------------------------------------------------------------------
  # Method 1: wall-clock cycles between consecutive PC wrap-arounds per tile.
  # Each wrap means one full II slot table has been consumed.
  print("\n=== RTL II Analysis (wall-clock cycles per II period) ===")
  print(f"  compiled_ii (ctrl table size) = {kCtrlCountPerIter}")
  print(f"  total sim cycles = {cycles}")
  print()

  all_gaps = []
  for tid in sorted(active_tiles.keys()):
    wraps = iter_wrap_cycles[tid]
    if len(wraps) >= 2:
      gaps = [wraps[i+1] - wraps[i] for i in range(len(wraps)-1)]
      avg_gap = sum(gaps) / len(gaps)
      min_gap = min(gaps)
      max_gap = max(gaps)
      all_gaps.extend(gaps)
      print(f"  tile {tid:2d}: {len(wraps)} wraps, "
            f"avg_rtl_ii={avg_gap:.2f}  min={min_gap}  max={max_gap}  "
            f"stall_overhead={avg_gap - kCtrlCountPerIter:.2f} cycles/iter")
    elif len(wraps) == 1:
      print(f"  tile {tid:2d}: only 1 wrap recorded (not enough for gap analysis)")
    else:
      print(f"  tile {tid:2d}: no PC wrap-arounds detected "
            f"(tile may use fewer than {kCtrlCountPerIter} ctrl steps)")

  if all_gaps:
    global_avg = sum(all_gaps) / len(all_gaps)
    print(f"\n  GLOBAL avg RTL II = {global_avg:.2f} cycles  "
          f"(compiled II = {kCtrlCountPerIter}, "
          f"overhead = {global_avg - kCtrlCountPerIter:.2f} cycles = "
          f"{(global_avg/kCtrlCountPerIter - 1)*100:.1f}% stall)")

  # Method 2: count total wall-clock cycles when any tile is active
  # (start_iterate_ctrl=1) vs total effective ctrl steps consumed.
  print("\n  Method 2: times-based (effective ctrl steps / wall cycles)")
  for tid in sorted(active_tiles.keys()):
    trace = ii_trace[tid]
    # Find the range when the tile was active (started=1)
    active_entries = [(c, t, r, v, rd) for c, t, r, v, rd, st in trace if st == 1]
    if len(active_entries) >= 2:
      first_cyc = active_entries[0][0]
      last_cyc  = active_entries[-1][0]
      last_times = active_entries[-1][1]
      wall_span = last_cyc - first_cyc + 1
      if last_times > 0:
        effective_ii = wall_span / last_times
        print(f"  tile {tid:2d}: active {first_cyc}..{last_cyc} "
              f"({wall_span} cycles), times={last_times}, "
              f"effective_rtl_ii = {effective_ii:.2f}")
  print()

  # -----------------------------------------------------------------------
  # Memory Dump (post-simulation)
  # -----------------------------------------------------------------------
  print("\n=== Memory Dump (shared global memory banks) ===")
  num_banks = num_banks_per_cgra
  for b in range(num_banks):
    wrapper = th.dut.data_mem.memory_wrapper[b]
    regs = wrapper.memory.regs
    print(f"\n  Bank {b} ({len(regs)} entries):")
    # Print non-zero entries
    nz_entries = []
    for addr_idx in range(len(regs)):
      reg = regs[addr_idx]
      data_val = int(reg.payload)
      pred = int(reg.predicate)
      if data_val != 0 or pred != 0:
        # Convert to signed 32-bit if needed
        if data_val >= (1 << (data_bitwidth - 1)):
          signed_val = data_val - (1 << data_bitwidth)
        else:
          signed_val = data_val
        nz_entries.append((addr_idx, data_val, signed_val, pred))
    for addr_idx, uval, sval, pred in nz_entries:
      print(f"    [{addr_idx:3d}] = {sval:10d} (0x{uval:08x}, pred={pred})")
    if not nz_entries:
      print(f"    (all zeros)")

  # Cross-reference with expected outputs
  print("\n=== Expected vs Actual Results (shared memory limitations apply) ===")
  print(f"  expected_s = {expected_s}")
  print(f"  expected_q = {expected_q}")

  # Try reading from bank 0 (primary bank) at expected addresses:
  print("\n  Checking global memory addresses 0..15 (bank 0):")
  wrapper0 = th.dut.data_mem.memory_wrapper[0]
  regs0 = wrapper0.memory.regs
  for addr in range(min(16, len(regs0))):
    reg = regs0[addr]
    data_val = int(reg.payload)
    if data_val >= (1 << (data_bitwidth - 1)):
      signed_val = data_val - (1 << data_bitwidth)
    else:
      signed_val = data_val
    label = ""
    if BaseS <= addr < BaseS + M:
      label = f"  ← s[{addr - BaseS}]? (expected {expected_s[addr - BaseS]})"
    if BaseQ <= addr < BaseQ + N:
      label += f"  ← q[{addr - BaseQ}]? (expected {expected_q[addr - BaseQ]})"
    if BaseP <= addr < BaseP + M:
      label += f"  ← p[{addr - BaseP}]={p_values[addr - BaseP]}"
    if BaseR <= addr < BaseR + N:
      label += f"  ← r[{addr - BaseR}]={r_values[addr - BaseR]}"
    print(f"    [{addr:3d}] = {signed_val:10d}{label}")

  # Also check A addresses (sparse with stride 32)
  print("\n  Checking A matrix addresses (stride 32):")
  for i in range(min(3, N)):  # Just first 3 rows
    for j in range(M):
      addr = BaseA + i * RowStride + j
      if addr < len(regs0):
        reg = regs0[addr]
        data_val = int(reg.payload)
        if data_val >= (1 << (data_bitwidth - 1)):
          signed_val = data_val - (1 << data_bitwidth)
        else:
          signed_val = data_val
        print(f"    A[{i}][{j}] @ [{addr:3d}] = {signed_val:10d} (expected {A_values[i][j]})")

  # Also check bank 1 if it has non-zero data
  if num_banks > 1:
    wrapper1 = th.dut.data_mem.memory_wrapper[1]
    regs1 = wrapper1.memory.regs
    print(f"\n  Bank 1 addresses 0..15:")
    for addr in range(min(16, len(regs1))):
      reg = regs1[addr]
      data_val = int(reg.payload)
      if data_val >= (1 << (data_bitwidth - 1)):
        signed_val = data_val - (1 << data_bitwidth)
      else:
        signed_val = data_val
      if data_val != 0:
        print(f"    [{addr:3d}] = {signed_val:10d} (0x{data_val:08x})")

  # -----------------------------------------------------------------------
  # Stall Pattern Analysis
  # -----------------------------------------------------------------------
  print("\n=== Stall Pattern Analysis ===")
  # For each tile, identify which PC addresses (ctrl steps) cause stalls
  # A stall occurs when the tile is active but PC doesn't advance
  for tid in sorted(active_tiles.keys()):
    trace = ii_trace[tid]
    stall_at_addr = {}  # raddr -> count of cycles stalled at that address
    prev_entry = None
    for entry in trace:
      cyc, times, raddr, val, rdy, started = entry
      if started and prev_entry is not None:
        prev_cyc, prev_times, prev_raddr, prev_val, prev_rdy, prev_started = prev_entry
        if prev_started and raddr == prev_raddr and times == prev_times:
          # Stalled: same PC and same times
          stall_at_addr[raddr] = stall_at_addr.get(raddr, 0) + 1
      prev_entry = entry
    total_stalls = sum(stall_at_addr.values())
    if stall_at_addr:
      sorted_stalls = sorted(stall_at_addr.items(), key=lambda x: -x[1])
      top5 = sorted_stalls[:5]
      top5_str = ", ".join([f"step{a}:{c}" for a, c in top5])
      print(f"  tile {tid:2d}: {total_stalls} total stalls. Top stall steps: {top5_str}")
    else:
      print(f"  tile {tid:2d}: no stalls detected")

  print()


def test_homogeneous_4x4_bicg_combinational_mem_access(cmdline_opts):
  sim_bicg(cmdline_opts, mem_access_is_combinational = True)
