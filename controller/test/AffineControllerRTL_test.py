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

    # Custom compare: only check cmd and data fields.
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


def run_sim(test_harness, max_cycles=200):
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


#-------------------------------------------------------------------------
# Test: Basic 2-layer loop
#-------------------------------------------------------------------------

def test_basic_2_layer_loop():
  """
  Test: for(i=0; i<3; i++) { for(j=...) body }
  CCU[0] is root, controls 1 leaf DCU at (tile=0, ctrl_addr=0).
  We simulate DCU completions and expect AC to dispatch reset+shadow.
  """
  ccu_id_bits = max(clog2(num_ccus), 1)
  tile_id_bits = clog2(num_tiles + 1)

  # Encode target: ctrl_addr in lower bits, tile_id in next bits.
  target_payload = (0 << 0) | (0 << clog2(ctrl_mem_size))  # ctrl_addr=0, tile_id=0

  # Encode parent: parent_ccu_id=0, is_root=1, is_relay=0.
  parent_payload = (0) | (1 << ccu_id_bits) | (0 << (ccu_id_bits+1))

  src_config = [
    # Configure CCU[0]: lower=0, upper=3, step=1
    CgraPayloadType(CMD_AC_CONFIG_LOWER, DataType(0, 1), 0, CtrlType(0), 0),
    CgraPayloadType(CMD_AC_CONFIG_UPPER, DataType(3, 1), 0, CtrlType(0), 0),
    CgraPayloadType(CMD_AC_CONFIG_STEP,  DataType(1, 1), 0, CtrlType(0), 0),

    # child_complete_count = 1
    CgraPayloadType(CMD_AC_CONFIG_CHILD_COUNT, DataType(1, 0), 0, CtrlType(0), 0),

    # Configure target: (tile_id=0, ctrl_addr=0, is_remote=0)
    CgraPayloadType(CMD_AC_CONFIG_TARGET, DataType(target_payload, 0), 0, CtrlType(0), 0),

    # Configure parent: is_root=1
    CgraPayloadType(CMD_AC_CONFIG_PARENT, DataType(parent_payload, 0), 0, CtrlType(0), 0),

    # Launch!
    CgraPayloadType(CMD_AC_LAUNCH, DataType(0, 0), 0, CtrlType(0), 0),
  ]

  # Simulate 3 DCU completions (one per outer-loop iteration i=0,1,2).
  src_from_tile = [
    CgraPayloadType(CMD_LEAF_COUNTER_COMPLETE, DataType(0, 0), 0, CtrlType(0), 0),
    CgraPayloadType(CMD_LEAF_COUNTER_COMPLETE, DataType(0, 0), 0, CtrlType(0), 0),
    CgraPayloadType(CMD_LEAF_COUNTER_COMPLETE, DataType(0, 0), 0, CtrlType(0), 0),
  ]

  src_from_remote = []

  # Expected outputs to tile:
  # After launch, CCU[0] starts at RUNNING with i=0, but first dispatch
  # happens when the first DCU completion arrives.
  # Iteration i=0 complete → advance to i=1 → dispatch (reset + shadow=1)
  # Iteration i=1 complete → advance to i=2 → dispatch (reset + shadow=2)
  # Iteration i=2 complete → advance to i=3 >= upper=3 → COMPLETE (no dispatch)
  sink_to_tile = [
    # After 1st completion: i advances to 1, dispatch reset then shadow=1
    CgraPayloadType(CMD_RESET_LEAF_COUNTER, DataType(0, 0), 0, CtrlType(0), 0),
    CgraPayloadType(CMD_UPDATE_COUNTER_SHADOW_VALUE, DataType(1, 1), 0, CtrlType(0), 0),
    # After 2nd completion: i advances to 2, dispatch reset then shadow=2
    CgraPayloadType(CMD_RESET_LEAF_COUNTER, DataType(0, 0), 0, CtrlType(0), 0),
    CgraPayloadType(CMD_UPDATE_COUNTER_SHADOW_VALUE, DataType(2, 1), 0, CtrlType(0), 0),
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
#-------------------------------------------------------------------------

def test_sibling_barrier():
  """
  Test: for(i=0; i<2; i++) { for(j...) body_j; for(k...) body_k }
  CCU[0] is root with child_count=2.
  Two leaf DCUs at ctrl_addr=0 and ctrl_addr=1.
  Both must complete before CCU[0] advances.
  """
  ccu_id_bits = max(clog2(num_ccus), 1)

  # Target 0: ctrl_addr=0, tile_id=0
  target0_payload = (0 << 0) | (0 << clog2(ctrl_mem_size))
  # Target 1: ctrl_addr=1, tile_id=1
  target1_payload = (1 << 0) | (1 << clog2(ctrl_mem_size))

  parent_payload = (0) | (1 << ccu_id_bits)  # is_root=1

  src_config = [
    CgraPayloadType(CMD_AC_CONFIG_LOWER, DataType(0, 1), 0, CtrlType(0), 0),
    CgraPayloadType(CMD_AC_CONFIG_UPPER, DataType(2, 1), 0, CtrlType(0), 0),
    CgraPayloadType(CMD_AC_CONFIG_STEP,  DataType(1, 1), 0, CtrlType(0), 0),
    CgraPayloadType(CMD_AC_CONFIG_CHILD_COUNT, DataType(2, 0), 0, CtrlType(0), 0),
    CgraPayloadType(CMD_AC_CONFIG_TARGET, DataType(target0_payload, 0), 0, CtrlType(0), 0),
    CgraPayloadType(CMD_AC_CONFIG_TARGET, DataType(target1_payload, 0), 0, CtrlType(0), 0),
    CgraPayloadType(CMD_AC_CONFIG_PARENT, DataType(parent_payload, 0), 0, CtrlType(0), 0),
    CgraPayloadType(CMD_AC_LAUNCH, DataType(0, 0), 0, CtrlType(0), 0),
  ]

  # Iteration i=0: both DCUs complete.
  # Iteration i=1: both DCUs complete again.
  src_from_tile = [
    # i=0: DCU at ctrl_addr=0 completes
    CgraPayloadType(CMD_LEAF_COUNTER_COMPLETE, DataType(0, 0), 0, CtrlType(0), 0),
    # i=0: DCU at ctrl_addr=1 completes
    CgraPayloadType(CMD_LEAF_COUNTER_COMPLETE, DataType(0, 0), 0, CtrlType(0), 1),
    # i=1: DCU at ctrl_addr=0 completes
    CgraPayloadType(CMD_LEAF_COUNTER_COMPLETE, DataType(0, 0), 0, CtrlType(0), 0),
    # i=1: DCU at ctrl_addr=1 completes
    CgraPayloadType(CMD_LEAF_COUNTER_COMPLETE, DataType(0, 0), 0, CtrlType(0), 1),
  ]

  src_from_remote = []

  # After i=0 both complete → advance to i=1 → dispatch to both targets:
  # Target 0: reset + shadow=1
  # Target 1: reset + shadow=1
  # After i=1 both complete → i=2 >= upper=2 → COMPLETE, no dispatch
  sink_to_tile = [
    # Dispatch for i=1 to target 0
    CgraPayloadType(CMD_RESET_LEAF_COUNTER, DataType(0, 0), 0, CtrlType(0), 0),
    CgraPayloadType(CMD_UPDATE_COUNTER_SHADOW_VALUE, DataType(1, 1), 0, CtrlType(0), 0),
    # Dispatch for i=1 to target 1
    CgraPayloadType(CMD_RESET_LEAF_COUNTER, DataType(0, 0), 0, CtrlType(0), 1),
    CgraPayloadType(CMD_UPDATE_COUNTER_SHADOW_VALUE, DataType(1, 1), 0, CtrlType(0), 1),
  ]

  sink_to_remote = []

  th = TestHarness(DataType, CtrlType, CgraPayloadType,
                   num_ccus, max_targets, data_mem_size, ctrl_mem_size,
                   num_tiles,
                   src_config, src_from_tile, src_from_remote,
                   sink_to_tile, sink_to_remote)
  run_sim(th)


#-------------------------------------------------------------------------
# Test: Remote AC sync (relay CCU)
#-------------------------------------------------------------------------

def test_remote_relay_ccu():
  """
  Test relay CCU receiving CMD_AC_SYNC_VALUE from remote parent.
  CCU[0] is a relay with 1 local target.
  """
  ccu_id_bits = max(clog2(num_ccus), 1)

  target_payload = (0 << 0) | (0 << clog2(ctrl_mem_size))

  # is_relay=1, is_root=0
  parent_payload = (0) | (0 << ccu_id_bits) | (1 << (ccu_id_bits+1))

  src_config = [
    CgraPayloadType(CMD_AC_CONFIG_LOWER, DataType(0, 1), 0, CtrlType(0), 0),
    CgraPayloadType(CMD_AC_CONFIG_UPPER, DataType(10, 1), 0, CtrlType(0), 0),
    CgraPayloadType(CMD_AC_CONFIG_STEP,  DataType(1, 1), 0, CtrlType(0), 0),
    CgraPayloadType(CMD_AC_CONFIG_CHILD_COUNT, DataType(1, 0), 0, CtrlType(0), 0),
    CgraPayloadType(CMD_AC_CONFIG_TARGET, DataType(target_payload, 0), 0, CtrlType(0), 0),
    CgraPayloadType(CMD_AC_CONFIG_PARENT, DataType(parent_payload, 1), 0, CtrlType(0), 0),
    CgraPayloadType(CMD_AC_LAUNCH, DataType(0, 0), 0, CtrlType(0), 0),
  ]

  src_from_tile = []

  # Remote parent sends sync value to CCU[0].
  src_from_remote = [
    CgraPayloadType(CMD_AC_SYNC_VALUE, DataType(5, 1), 0, CtrlType(0), 0),
  ]

  # Relay CCU receives value 5, dispatches to local target:
  sink_to_tile = [
    CgraPayloadType(CMD_RESET_LEAF_COUNTER, DataType(0, 0), 0, CtrlType(0), 0),
    CgraPayloadType(CMD_UPDATE_COUNTER_SHADOW_VALUE, DataType(5, 1), 0, CtrlType(0), 0),
  ]

  sink_to_remote = []

  th = TestHarness(DataType, CtrlType, CgraPayloadType,
                   num_ccus, max_targets, data_mem_size, ctrl_mem_size,
                   num_tiles,
                   src_config, src_from_tile, src_from_remote,
                   sink_to_tile, sink_to_remote)
  run_sim(th)
