"""
==========================================================================
AffineControllerRTL_test.py
==========================================================================
Test cases for the Affine Controller.

Author : Shangkun Li
  Date : February 19, 2026
"""

from pymtl3 import *
from ..AffineControllerRTL import AffineControllerRTL
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ...lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ...lib.messages import *
from ...lib.opt_type import *
from ...lib.cmd_type import *

#-------------------------------------------------------------------------
# Test Harness
#-------------------------------------------------------------------------

class TestHarness(Component):
  def construct(s, DataType, CtrlType, CgraPayloadType,
                num_ccus, max_targets_per_ccu,
                data_mem_size, ctrl_mem_size, num_tiles,
                src_config, src_from_tile, src_from_remote,
                sink_to_tile, sink_to_remote):

    s.src_config = TestSrcRTL(CgraPayloadType, src_config)
    s.src_from_tile = TestSrcRTL(CgraPayloadType, src_from_tile)
    s.src_from_remote = TestSrcRTL(CgraPayloadType, src_from_remote)

    cmp_fn = lambda a, b: (a.cmd == b.cmd) and \
                           (a.data.payload == b.data.payload) and \
                           (a.ctrl_addr == b.ctrl_addr)

    s.sink_to_tile = TestSinkRTL(CgraPayloadType, sink_to_tile, cmp_fn=cmp_fn)
    s.sink_to_remote = TestSinkRTL(CgraPayloadType, sink_to_remote, cmp_fn=cmp_fn)

    s.dut = AffineControllerRTL(DataType, CtrlType,
                                 num_ccus=num_ccus,
                                 max_targets_per_ccu=max_targets_per_ccu,
                                 data_mem_size=data_mem_size,
                                 ctrl_mem_size=ctrl_mem_size,
                                 num_tiles=num_tiles)

    connect(s.src_config.send, s.dut.recv_config)
    connect(s.src_from_tile.send, s.dut.recv_from_tile)
    connect(s.src_from_remote.send, s.dut.recv_from_remote)
    connect(s.dut.send_to_tile, s.sink_to_tile.recv)
    connect(s.dut.send_to_remote, s.sink_to_remote.recv)

  def done(s):
    return s.src_config.done() and s.src_from_tile.done() and \
           s.src_from_remote.done() and s.sink_to_tile.done() and \
           s.sink_to_remote.done()

  def line_trace(s):
    return s.dut.line_trace()


def run_sim(test_harness, max_cycles=300):
  test_harness.elaborate()
  test_harness.apply(DefaultPassGroup())
  test_harness.sim_reset()

  ncycles = 0
  print()
  print("{}:{}".format(ncycles, test_harness.line_trace()))
  while not test_harness.done() and ncycles < max_cycles:
    test_harness.sim_tick()
    ncycles += 1
    print("{}:{}".format(ncycles, test_harness.line_trace()))

  assert ncycles < max_cycles, f"Timed out after {max_cycles} cycles"

  test_harness.sim_tick()
  test_harness.sim_tick()
  test_harness.sim_tick()


#-------------------------------------------------------------------------
# Common setup
#-------------------------------------------------------------------------

num_ccus = 8
max_targets = 4
data_mem_size = 8
ctrl_mem_size = 8
num_tiles = 4
num_inports = 4
num_outports = 2

DataType = mk_data(32, 1)
CtrlType = mk_ctrl(num_inports, num_outports, num_inports, num_outports)
AddrType = mk_bits(clog2(data_mem_size))
CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
CgraPayloadType = mk_cgra_payload(DataType, AddrType, CtrlType, CtrlAddrType)

ccu_id_bits = max(clog2(num_ccus), 1)


def mk_target_config(ctrl_addr, tile_id, shadow_only=False):
  """Create a CMD_AC_CONFIG_TARGET packet.
     shadow_only is encoded in the MSB of data_addr."""
  payload = (ctrl_addr & ((1 << clog2(ctrl_mem_size)) - 1)) | \
            ((tile_id & ((1 << clog2(num_tiles + 1)) - 1)) << clog2(ctrl_mem_size))
  # shadow_only encoded in MSB of data_addr (bit index = clog2(data_mem_size)-1).
  so_bit = (1 << (clog2(data_mem_size) - 1)) if shadow_only else 0
  return DataType(payload, 0), so_bit


def mk_parent_payload(parent_id, is_root):
  """Encode parent info into data.payload."""
  return (parent_id & ((1 << ccu_id_bits) - 1)) | \
         ((1 if is_root else 0) << ccu_id_bits)


#-------------------------------------------------------------------------
# Test: Basic 2-layer loop
#   for(i=0; i<3; i++) { for(j=...) body }
#   CCU[0] is root, 1 leaf DCU at ctrl_addr=0.
#   On each DCU completion, CCU[0] advances i.
#   Dispatches reset+shadow for i=1 and i=2.
#   When i reaches 3, COMPLETE without dispatch.
#-------------------------------------------------------------------------

def test_basic_2_layer_loop():
  src_config = [
    CgraPayloadType(CMD_AC_CONFIG_LOWER, DataType(0, 1), 0, CtrlType(0), 0),
    CgraPayloadType(CMD_AC_CONFIG_UPPER, DataType(3, 1), 0, CtrlType(0), 0),
    CgraPayloadType(CMD_AC_CONFIG_STEP,  DataType(1, 1), 0, CtrlType(0), 0),
    CgraPayloadType(CMD_AC_CONFIG_CHILD_COUNT, DataType(1, 0), 0, CtrlType(0), 0),
    # Leaf-mode target: reset + shadow (shadow_only=False).
    CgraPayloadType(CMD_AC_CONFIG_TARGET,
                    *mk_target_config(0, 0, shadow_only=False), CtrlType(0), 0),
    CgraPayloadType(CMD_AC_CONFIG_PARENT,
                    DataType(mk_parent_payload(0, True), 0), 0, CtrlType(0), 0),
    CgraPayloadType(CMD_AC_LAUNCH, DataType(0, 0), 0, CtrlType(0), 0),
  ]

  # 3 completions: i=0 done → dispatch, i=1 done → dispatch, i=2 done → COMPLETE
  src_from_tile = [
    CgraPayloadType(CMD_LEAF_COUNTER_COMPLETE, DataType(0, 0), 0, CtrlType(0), 0),
    CgraPayloadType(CMD_LEAF_COUNTER_COMPLETE, DataType(0, 0), 0, CtrlType(0), 0),
    CgraPayloadType(CMD_LEAF_COUNTER_COMPLETE, DataType(0, 0), 0, CtrlType(0), 0),
  ]

  src_from_remote = []

  # After 1st completion: i=1, dispatch reset to leaf DCU (1 cycle)
  # After 2nd completion: i=2, dispatch reset (1 cycle)
  # After 3rd completion: i=3 >= 3, COMPLETE (no dispatch)
  sink_to_tile = [
    CgraPayloadType(CMD_RESET_LEAF_COUNTER, DataType(0, 0), 0, CtrlType(0), 0),
    CgraPayloadType(CMD_RESET_LEAF_COUNTER, DataType(0, 0), 0, CtrlType(0), 0),
  ]

  sink_to_remote = []

  th = TestHarness(DataType, CtrlType, CgraPayloadType,
                   num_ccus, max_targets, data_mem_size, ctrl_mem_size,
                   num_tiles,
                   src_config, src_from_tile, src_from_remote,
                   sink_to_tile, sink_to_remote)
  run_sim(th)


#-------------------------------------------------------------------------
# Test: Sibling barrier (1 root CCU, 2 leaf DCUs)
#   for(i=0; i<2; i++) { body_a; body_b }
#   CCU[0] child_count=2, targets at ctrl_addr=0 and ctrl_addr=1.
#-------------------------------------------------------------------------

def test_sibling_barrier():
  src_config = [
    CgraPayloadType(CMD_AC_CONFIG_LOWER, DataType(0, 1), 0, CtrlType(0), 0),
    CgraPayloadType(CMD_AC_CONFIG_UPPER, DataType(2, 1), 0, CtrlType(0), 0),
    CgraPayloadType(CMD_AC_CONFIG_STEP,  DataType(1, 1), 0, CtrlType(0), 0),
    CgraPayloadType(CMD_AC_CONFIG_CHILD_COUNT, DataType(2, 0), 0, CtrlType(0), 0),
    CgraPayloadType(CMD_AC_CONFIG_TARGET,
                    *mk_target_config(0, 0), CtrlType(0), 0),
    CgraPayloadType(CMD_AC_CONFIG_TARGET,
                    *mk_target_config(1, 1), CtrlType(0), 0),
    CgraPayloadType(CMD_AC_CONFIG_PARENT,
                    DataType(mk_parent_payload(0, True), 0), 0, CtrlType(0), 0),
    CgraPayloadType(CMD_AC_LAUNCH, DataType(0, 0), 0, CtrlType(0), 0),
  ]

  # i=0: both DCUs complete (2 events). i=1: both complete again.
  src_from_tile = [
    CgraPayloadType(CMD_LEAF_COUNTER_COMPLETE, DataType(0, 0), 0, CtrlType(0), 0),
    CgraPayloadType(CMD_LEAF_COUNTER_COMPLETE, DataType(0, 0), 0, CtrlType(0), 1),
    CgraPayloadType(CMD_LEAF_COUNTER_COMPLETE, DataType(0, 0), 0, CtrlType(0), 0),
    CgraPayloadType(CMD_LEAF_COUNTER_COMPLETE, DataType(0, 0), 0, CtrlType(0), 1),
  ]

  src_from_remote = []

  # After i=0 both complete: i=1, dispatch reset to both leaf targets
  # After i=1 both complete: i=2 >= 2, COMPLETE (no dispatch)
  sink_to_tile = [
    CgraPayloadType(CMD_RESET_LEAF_COUNTER, DataType(0, 0), 0, CtrlType(0), 0),
    CgraPayloadType(CMD_RESET_LEAF_COUNTER, DataType(0, 0), 0, CtrlType(0), 1),
  ]

  sink_to_remote = []

  th = TestHarness(DataType, CtrlType, CgraPayloadType,
                   num_ccus, max_targets, data_mem_size, ctrl_mem_size,
                   num_tiles,
                   src_config, src_from_tile, src_from_remote,
                   sink_to_tile, sink_to_remote)
  run_sim(th)


#-------------------------------------------------------------------------
# Test: 3-layer loop (CCU chain: CCU[0] → CCU[1] → DCU)
#
#   for(i=0; i<2; i++) {             // CCU[0], root
#     for(j=0; j<3; j++) {           // CCU[1], parent=CCU[0]
#       for(k=0; k<N; k++) body;     // DCU at ctrl_addr=0
#     }
#   }
#
#   CCU[0]: i loop, child_count=1 (CCU[1] completes once per i iter)
#           target = [i-delivery DCU at ctrl_addr=1]
#   CCU[1]: j loop, child_count=1 (DCU completes once per j iter)
#           parent = CCU[0]
#           targets = [k-DCU at ctrl_addr=0, j-delivery DCU at ctrl_addr=2]
#
#   Flow:
#     Launch → CCU[0] RUNNING(i=0), CCU[1] RUNNING(j=0)
#     DCU runs k-loop, sends COMPLETE → CCU[1] match → j++ → dispatch
#     ... j=3 >= 3 → CCU[1] COMPLETE → notify CCU[0] → i++ → dispatch
#     CCU[0] dispatch done → RUNNING → reset CCU[1] (j=0)
#     Repeat until i=2 >= 2 → all complete
#-------------------------------------------------------------------------

def test_3_layer_loop():
  # ===== Configure CCU[0]: i = 0..1 =====
  config_ccu0 = [
    CgraPayloadType(CMD_AC_CONFIG_LOWER, DataType(0, 1), 0, CtrlType(0), 0),
    CgraPayloadType(CMD_AC_CONFIG_UPPER, DataType(2, 1), 0, CtrlType(0), 0),
    CgraPayloadType(CMD_AC_CONFIG_STEP,  DataType(1, 1), 0, CtrlType(0), 0),
    CgraPayloadType(CMD_AC_CONFIG_CHILD_COUNT, DataType(1, 0), 0, CtrlType(0), 0),
    # CCU[0] target: i-delivery DCU at ctrl_addr=1 (shadow_only!)
    CgraPayloadType(CMD_AC_CONFIG_TARGET,
                    *mk_target_config(1, 0, shadow_only=True), CtrlType(0), 0),
    CgraPayloadType(CMD_AC_CONFIG_PARENT,
                    DataType(mk_parent_payload(0, True), 0), 0, CtrlType(0), 0),
  ]

  # ===== Configure CCU[1]: j = 0..2, parent = CCU[0] =====
  config_ccu1 = [
    CgraPayloadType(CMD_AC_CONFIG_LOWER, DataType(0, 1), 0, CtrlType(0), 1),
    CgraPayloadType(CMD_AC_CONFIG_UPPER, DataType(3, 1), 0, CtrlType(0), 1),
    CgraPayloadType(CMD_AC_CONFIG_STEP,  DataType(1, 1), 0, CtrlType(0), 1),
    CgraPayloadType(CMD_AC_CONFIG_CHILD_COUNT, DataType(1, 0), 0, CtrlType(0), 1),
    # CCU[1] target 0: k-DCU at ctrl_addr=0 (leaf, needs reset + shadow)
    CgraPayloadType(CMD_AC_CONFIG_TARGET,
                    *mk_target_config(0, 0, shadow_only=False), CtrlType(0), 1),
    # CCU[1] target 1: j-delivery DCU at ctrl_addr=2 (shadow_only!)
    CgraPayloadType(CMD_AC_CONFIG_TARGET,
                    *mk_target_config(2, 0, shadow_only=True), CtrlType(0), 1),
    CgraPayloadType(CMD_AC_CONFIG_PARENT,
                    DataType(mk_parent_payload(0, False), 0), 0, CtrlType(0), 1),
  ]

  launch = [
    CgraPayloadType(CMD_AC_LAUNCH, DataType(0, 0), 0, CtrlType(0), 0),
  ]

  src_config = config_ccu0 + config_ccu1 + launch

  # Simulate DCU k-loop completions at ctrl_addr=0.
  # Total inner iterations: 2 (i) × 3 (j) = 6 DCU completions.
  src_from_tile = [
    CgraPayloadType(CMD_LEAF_COUNTER_COMPLETE, DataType(0, 0), 0, CtrlType(0), 0),
  ] * 6

  src_from_remote = []

  # Expected output to tile (single-phase dispatch):
  # leaf target (k-DCU @ctrl_addr=0) → CMD_RESET_LEAF_COUNTER
  # shadow target (j-delivery @ctrl_addr=2) → CMD_UPDATE_COUNTER_SHADOW_VALUE
  # shadow target (i-delivery @ctrl_addr=1) → CMD_UPDATE_COUNTER_SHADOW_VALUE
  #
  # CCU[1] targets: [0]=k-DCU(reset), [1]=j-delivery(shadow)
  # CCU[0] targets: [0]=i-delivery(shadow)

  sink_to_tile = [
    # i=0, j=0→1: CCU[1] dispatches (reset k-DCU, shadow j=1)
    CgraPayloadType(CMD_RESET_LEAF_COUNTER, DataType(0, 0), 0, CtrlType(0), 0),
    CgraPayloadType(CMD_UPDATE_COUNTER_SHADOW_VALUE, DataType(1, 1), 0, CtrlType(0), 2),

    # i=0, j=1→2: CCU[1] dispatches
    CgraPayloadType(CMD_RESET_LEAF_COUNTER, DataType(0, 0), 0, CtrlType(0), 0),
    CgraPayloadType(CMD_UPDATE_COUNTER_SHADOW_VALUE, DataType(2, 1), 0, CtrlType(0), 2),

    # i=0→1: CCU[0] dispatches (shadow i=1 to i-delivery)
    CgraPayloadType(CMD_UPDATE_COUNTER_SHADOW_VALUE, DataType(1, 1), 0, CtrlType(0), 1),

    # i=1, j=0→1: CCU[1] dispatches
    CgraPayloadType(CMD_RESET_LEAF_COUNTER, DataType(0, 0), 0, CtrlType(0), 0),
    CgraPayloadType(CMD_UPDATE_COUNTER_SHADOW_VALUE, DataType(1, 1), 0, CtrlType(0), 2),

    # i=1, j=1→2: CCU[1] dispatches
    CgraPayloadType(CMD_RESET_LEAF_COUNTER, DataType(0, 0), 0, CtrlType(0), 0),
    CgraPayloadType(CMD_UPDATE_COUNTER_SHADOW_VALUE, DataType(2, 1), 0, CtrlType(0), 2),

    # i=1, j=2→3: CCU[1] COMPLETE, CCU[0] i=2 >= 2 → COMPLETE (no dispatch)
  ]

  sink_to_remote = []

  th = TestHarness(DataType, CtrlType, CgraPayloadType,
                   num_ccus, max_targets, data_mem_size, ctrl_mem_size,
                   num_tiles,
                   src_config, src_from_tile, src_from_remote,
                   sink_to_tile, sink_to_remote)
  run_sim(th)
