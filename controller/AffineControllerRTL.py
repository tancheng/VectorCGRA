"""
==========================================================================
AffineControllerRTL.py
==========================================================================
Affine Controller (AC) for managing outer loop counters in CGRA.

Each AC contains configurable number of Configurable Counter Units (CCUs).
CCUs form a DAG topology supporting:
  - Multiple independent counter chains
  - 1-to-N fanout (one CCU controls multiple CCUs)
  - Cross-AC CCU chaining for logic CGRA fusion

CCU types:
  - Root CCU: No parent, drives loop from scratch
  - Relay CCU: Receives current value from remote parent AC
  - Regular CCU: Has a local parent CCU

Author : Shangkun Li
  Date : February 19, 2026
"""

from pymtl3 import *
from ..lib.basic.val_rdy.ifcs import RecvIfcRTL, SendIfcRTL
from ..lib.messages import *
from ..lib.cmd_type import *
from ..lib.util.data_struct_attr import *

# CCU States
CCU_STATE_IDLE        = 0
CCU_STATE_RUNNING     = 1
CCU_STATE_DISPATCHING = 2
CCU_STATE_COMPLETE    = 3

class AffineControllerRTL(Component):

  def construct(s, DataType, CtrlType,
                num_ccus = 8,
                max_targets_per_ccu = 4,
                data_mem_size = 8,
                ctrl_mem_size = 8,
                num_tiles = 4,
                num_cgra_columns = 1,
                num_cgra_rows = 1):

    # ===== Derived Types =====
    AddrType = mk_bits(clog2(data_mem_size))
    CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
    CgraPayloadType = mk_cgra_payload(DataType, AddrType, CtrlType, CtrlAddrType)
    CCUIdType = mk_bits(max(clog2(num_ccus), 1))
    TileIdType = mk_bits(clog2(num_tiles + 1))
    CgraIdType = mk_bits(max(clog2(num_cgra_columns * num_cgra_rows), 1))
    StateType = mk_bits(2)
    CountType = mk_bits(4)
    TargetIdxType = mk_bits(max(clog2(max_targets_per_ccu), 1))

    # ===== Interfaces =====
    # Configuration from CPU (via Controller).
    s.recv_config = RecvIfcRTL(CgraPayloadType)

    # From/To tile array ctrl ring (local DCU communication).
    s.recv_from_tile = RecvIfcRTL(CgraPayloadType)
    s.send_to_tile = SendIfcRTL(CgraPayloadType)

    # Inter-AC communication (via Controller NoC).
    s.recv_from_remote = RecvIfcRTL(CgraPayloadType)
    s.send_to_remote = SendIfcRTL(CgraPayloadType)

    # Status output.
    s.all_loops_complete = OutPort(1)

    # ===== Per-CCU State Arrays =====
    s.ccu_lower_bound    = [Wire(DataType) for _ in range(num_ccus)]
    s.ccu_upper_bound    = [Wire(DataType) for _ in range(num_ccus)]
    s.ccu_step           = [Wire(DataType) for _ in range(num_ccus)]
    s.ccu_current_value  = [Wire(DataType) for _ in range(num_ccus)]
    s.ccu_state          = [Wire(StateType) for _ in range(num_ccus)]

    # Child completion tracking.
    s.ccu_child_complete_count    = [Wire(CountType) for _ in range(num_ccus)]
    s.ccu_received_complete_count = [Wire(CountType) for _ in range(num_ccus)]

    # Target configuration (who to send reset/shadow to).
    s.ccu_num_targets      = [Wire(CountType) for _ in range(num_ccus)]
    s.ccu_target_tile_ids  = [[Wire(TileIdType) for _ in range(max_targets_per_ccu)]
                              for _ in range(num_ccus)]
    s.ccu_target_ctrl_addrs = [[Wire(CtrlAddrType) for _ in range(max_targets_per_ccu)]
                               for _ in range(num_ccus)]
    s.ccu_target_is_remote = [[Wire(1) for _ in range(max_targets_per_ccu)]
                              for _ in range(num_ccus)]
    s.ccu_target_cgra_ids  = [[Wire(CgraIdType) for _ in range(max_targets_per_ccu)]
                              for _ in range(num_ccus)]

    # Parent configuration.
    s.ccu_is_root        = [Wire(1) for _ in range(num_ccus)]
    s.ccu_is_relay       = [Wire(1) for _ in range(num_ccus)]
    s.ccu_parent_ccu_id  = [Wire(CCUIdType) for _ in range(num_ccus)]
    s.ccu_parent_is_remote = [Wire(1) for _ in range(num_ccus)]
    s.ccu_parent_cgra_id = [Wire(CgraIdType) for _ in range(num_ccus)]

    # Dispatch progress: which target we're sending to next.
    s.ccu_dispatch_idx = [Wire(TargetIdxType) for _ in range(num_ccus)]
    # Dispatch sub-phase: 0 = send reset, 1 = send shadow value.
    s.ccu_dispatch_phase = [Wire(1) for _ in range(num_ccus)]

    # Config target index for sequential target configuration.
    s.ccu_config_target_idx = [Wire(CountType) for _ in range(num_ccus)]

    # ===== Internal Control Signals =====
    # Which CCU is currently being serviced for dispatch.
    s.active_dispatch_ccu = Wire(CCUIdType)
    s.has_active_dispatch = Wire(1)

    # Signals for incoming events.
    s.config_cmd_valid = Wire(1)
    s.tile_event_valid = Wire(1)
    s.remote_event_valid = Wire(1)

    # ===================================================================
    # Combinational Logic
    # ===================================================================

    @update
    def comb_logic():

      # ----- Default output signals -----
      s.recv_config.rdy @= b1(0)
      s.recv_from_tile.rdy @= b1(0)
      s.recv_from_remote.rdy @= b1(0)
      s.send_to_tile.val @= b1(0)
      s.send_to_tile.msg @= CgraPayloadType(0, DataType(0, 0), 0, CtrlType(0), 0)
      s.send_to_remote.val @= b1(0)
      s.send_to_remote.msg @= CgraPayloadType(0, DataType(0, 0), 0, CtrlType(0), 0)

      s.config_cmd_valid @= b1(0)
      s.tile_event_valid @= b1(0)
      s.remote_event_valid @= b1(0)

      # ----- Compute all_loops_complete -----
      all_complete = b1(1)
      for i in range(num_ccus):
        if s.ccu_is_root[i] & (s.ccu_state[i] != StateType(CCU_STATE_COMPLETE)) & \
           (s.ccu_state[i] != StateType(CCU_STATE_IDLE)):
          all_complete = b1(0)
      s.all_loops_complete @= all_complete

      # ----- Find active dispatching CCU (round-robin / first-found) -----
      s.has_active_dispatch @= b1(0)
      s.active_dispatch_ccu @= CCUIdType(0)
      for i in range(num_ccus):
        if (s.ccu_state[i] == StateType(CCU_STATE_DISPATCHING)) & ~s.has_active_dispatch:
          s.has_active_dispatch @= b1(1)
          s.active_dispatch_ccu @= CCUIdType(i)

      # ============================================
      # Priority 1: Handle DISPATCHING CCU outputs
      # ============================================
      if s.has_active_dispatch:
        ccu_id = s.active_dispatch_ccu
        tidx = s.ccu_dispatch_idx[ccu_id]

        if s.ccu_target_is_remote[ccu_id][tidx]:
          # Remote target: send via inter-AC interface.
          if s.ccu_dispatch_phase[ccu_id] == b1(0):
            # Phase 0: Send reset.
            s.send_to_remote.val @= b1(1)
            s.send_to_remote.msg @= CgraPayloadType(
              CMD_AC_CHILD_RESET,
              s.ccu_current_value[ccu_id],
              0,
              CtrlType(0),
              s.ccu_target_ctrl_addrs[ccu_id][tidx]
            )
          else:
            # Phase 1: Send value sync.
            s.send_to_remote.val @= b1(1)
            s.send_to_remote.msg @= CgraPayloadType(
              CMD_AC_SYNC_VALUE,
              s.ccu_current_value[ccu_id],
              0,
              CtrlType(0),
              s.ccu_target_ctrl_addrs[ccu_id][tidx]
            )
        else:
          # Local target: send via tile interface.
          if s.ccu_dispatch_phase[ccu_id] == b1(0):
            # Phase 0: Send CMD_RESET_LEAF_COUNTER.
            s.send_to_tile.val @= b1(1)
            s.send_to_tile.msg @= CgraPayloadType(
              CMD_RESET_LEAF_COUNTER,
              DataType(0, 0),
              0,
              CtrlType(0),
              s.ccu_target_ctrl_addrs[ccu_id][tidx]
            )
          else:
            # Phase 1: Send CMD_UPDATE_COUNTER_SHADOW_VALUE.
            s.send_to_tile.val @= b1(1)
            s.send_to_tile.msg @= CgraPayloadType(
              CMD_UPDATE_COUNTER_SHADOW_VALUE,
              s.ccu_current_value[ccu_id],
              0,
              CtrlType(0),
              s.ccu_target_ctrl_addrs[ccu_id][tidx]
            )

      # ==========================================
      # Priority 2: Handle configuration commands
      # ==========================================
      if s.recv_config.val:
        s.config_cmd_valid @= b1(1)
        s.recv_config.rdy @= b1(1)

      # ====================================================
      # Priority 3: Handle DCU completion from tile ctrl ring
      # ====================================================
      if s.recv_from_tile.val:
        if s.recv_from_tile.msg.cmd == CMD_LEAF_COUNTER_COMPLETE:
          # Only consume the event if a CCU in RUNNING state can match it.
          incoming_ctrl_addr_comb = s.recv_from_tile.msg.ctrl_addr
          can_match = b1(0)
          for i in range(num_ccus):
            if s.ccu_state[i] == StateType(CCU_STATE_RUNNING):
              for t in range(max_targets_per_ccu):
                if (zext(TargetIdxType(t), CountType) < s.ccu_num_targets[i]) & \
                   (~s.ccu_target_is_remote[i][t]) & \
                   (s.ccu_target_ctrl_addrs[i][t] == incoming_ctrl_addr_comb):
                  can_match = b1(1)
          if can_match:
            s.tile_event_valid @= b1(1)
            s.recv_from_tile.rdy @= b1(1)
          # If no match, leave rdy=0 to apply backpressure.
        else:
          # Unknown tile event, consume and discard.
          s.recv_from_tile.rdy @= b1(1)

      # ============================================
      # Priority 4: Handle remote AC messages
      # ============================================
      if s.recv_from_remote.val:
        s.remote_event_valid @= b1(1)
        s.recv_from_remote.rdy @= b1(1)

    # ===================================================================
    # Sequential Logic: CCU State Updates
    # ===================================================================

    @update_ff
    def update_ccu_ff():
      """Consolidated sequential logic for CCU config + state machine."""
      if s.reset:
        for i in range(num_ccus):
          # Config state.
          s.ccu_lower_bound[i] <<= DataType(0, 0)
          s.ccu_upper_bound[i] <<= DataType(0, 0)
          s.ccu_step[i] <<= DataType(0, 0)
          s.ccu_is_root[i] <<= b1(0)
          s.ccu_is_relay[i] <<= b1(0)
          s.ccu_parent_ccu_id[i] <<= CCUIdType(0)
          s.ccu_parent_is_remote[i] <<= b1(0)
          s.ccu_parent_cgra_id[i] <<= CgraIdType(0)
          s.ccu_child_complete_count[i] <<= CountType(0)
          s.ccu_num_targets[i] <<= CountType(0)
          s.ccu_config_target_idx[i] <<= CountType(0)
          for t in range(max_targets_per_ccu):
            s.ccu_target_tile_ids[i][t] <<= TileIdType(0)
            s.ccu_target_ctrl_addrs[i][t] <<= CtrlAddrType(0)
            s.ccu_target_is_remote[i][t] <<= b1(0)
            s.ccu_target_cgra_ids[i][t] <<= CgraIdType(0)
          # Runtime state.
          s.ccu_state[i] <<= StateType(CCU_STATE_IDLE)
          s.ccu_current_value[i] <<= DataType(0, 0)
          s.ccu_received_complete_count[i] <<= CountType(0)
          s.ccu_dispatch_idx[i] <<= TargetIdxType(0)
          s.ccu_dispatch_phase[i] <<= b1(0)
      else:
        # ===== Handle configuration commands from CPU =====
        if s.config_cmd_valid:
          ccu_idx = s.recv_config.msg.ctrl_addr

          if s.recv_config.msg.cmd == CMD_AC_CONFIG_LOWER:
            s.ccu_lower_bound[ccu_idx] <<= s.recv_config.msg.data
            s.ccu_current_value[ccu_idx] <<= s.recv_config.msg.data

          elif s.recv_config.msg.cmd == CMD_AC_CONFIG_UPPER:
            s.ccu_upper_bound[ccu_idx] <<= s.recv_config.msg.data

          elif s.recv_config.msg.cmd == CMD_AC_CONFIG_STEP:
            s.ccu_step[ccu_idx] <<= s.recv_config.msg.data

          elif s.recv_config.msg.cmd == CMD_AC_CONFIG_CHILD_COUNT:
            s.ccu_child_complete_count[ccu_idx] <<= \
                CountType(s.recv_config.msg.data.payload[0:4])

          elif s.recv_config.msg.cmd == CMD_AC_CONFIG_TARGET:
            tidx = s.ccu_config_target_idx[ccu_idx]
            s.ccu_target_ctrl_addrs[ccu_idx][tidx] <<= \
                CtrlAddrType(s.recv_config.msg.data.payload[0:clog2(ctrl_mem_size)])
            s.ccu_target_tile_ids[ccu_idx][tidx] <<= \
                TileIdType(s.recv_config.msg.data.payload[clog2(ctrl_mem_size):clog2(ctrl_mem_size)+clog2(num_tiles+1)])
            s.ccu_target_is_remote[ccu_idx][tidx] <<= \
                s.recv_config.msg.data.predicate
            s.ccu_target_cgra_ids[ccu_idx][tidx] <<= \
                trunc(s.recv_config.msg.data_addr, CgraIdType)
            s.ccu_config_target_idx[ccu_idx] <<= tidx + CountType(1)
            s.ccu_num_targets[ccu_idx] <<= tidx + CountType(1)

          elif s.recv_config.msg.cmd == CMD_AC_CONFIG_PARENT:
            s.ccu_parent_ccu_id[ccu_idx] <<= \
                CCUIdType(s.recv_config.msg.data.payload[0:max(clog2(num_ccus),1)])
            s.ccu_is_root[ccu_idx] <<= \
                s.recv_config.msg.data.payload[max(clog2(num_ccus),1)]
            s.ccu_is_relay[ccu_idx] <<= \
                s.recv_config.msg.data.payload[max(clog2(num_ccus),1)+1]
            s.ccu_parent_is_remote[ccu_idx] <<= \
                s.recv_config.msg.data.predicate
            s.ccu_parent_cgra_id[ccu_idx] <<= \
                trunc(s.recv_config.msg.data_addr, CgraIdType)

          elif s.recv_config.msg.cmd == CMD_AC_LAUNCH:
            # Launch: all configured CCUs enter RUNNING.
            for i in range(num_ccus):
              if s.ccu_is_root[i] | s.ccu_is_relay[i]:
                s.ccu_state[i] <<= StateType(CCU_STATE_RUNNING)
                s.ccu_current_value[i] <<= s.ccu_lower_bound[i]
                s.ccu_received_complete_count[i] <<= CountType(0)
                s.ccu_dispatch_idx[i] <<= TargetIdxType(0)
                s.ccu_dispatch_phase[i] <<= b1(0)

        # ===== Handle DISPATCHING progress =====
        if s.has_active_dispatch:
          ccu_id = s.active_dispatch_ccu
          tidx = s.ccu_dispatch_idx[ccu_id]
          sent = b1(0)

          if s.ccu_target_is_remote[ccu_id][tidx]:
            sent = s.send_to_remote.val & s.send_to_remote.rdy
          else:
            sent = s.send_to_tile.val & s.send_to_tile.rdy

          if sent:
            if s.ccu_dispatch_phase[ccu_id] == b1(0):
              s.ccu_dispatch_phase[ccu_id] <<= b1(1)
            else:
              s.ccu_dispatch_phase[ccu_id] <<= b1(0)
              next_idx = s.ccu_dispatch_idx[ccu_id] + TargetIdxType(1)

              if zext(next_idx, CountType) >= s.ccu_num_targets[ccu_id]:
                s.ccu_dispatch_idx[ccu_id] <<= TargetIdxType(0)
                s.ccu_received_complete_count[ccu_id] <<= CountType(0)

                if s.ccu_current_value[ccu_id].payload >= \
                   s.ccu_upper_bound[ccu_id].payload:
                  s.ccu_state[ccu_id] <<= StateType(CCU_STATE_COMPLETE)
                else:
                  s.ccu_state[ccu_id] <<= StateType(CCU_STATE_RUNNING)
              else:
                s.ccu_dispatch_idx[ccu_id] <<= next_idx

        # ===== Handle tile events (CMD_LEAF_COUNTER_COMPLETE) =====
        if s.tile_event_valid:
          incoming_ctrl_addr = s.recv_from_tile.msg.ctrl_addr
          for i in range(num_ccus):
            if s.ccu_state[i] == StateType(CCU_STATE_RUNNING):
              for t in range(max_targets_per_ccu):
                if (zext(TargetIdxType(t), CountType) < s.ccu_num_targets[i]) & \
                   (~s.ccu_target_is_remote[i][t]) & \
                   (s.ccu_target_ctrl_addrs[i][t] == incoming_ctrl_addr):
                  new_count = s.ccu_received_complete_count[i] + CountType(1)
                  s.ccu_received_complete_count[i] <<= new_count

                  if new_count >= s.ccu_child_complete_count[i]:
                    s.ccu_current_value[i] <<= DataType(
                      s.ccu_current_value[i].payload + s.ccu_step[i].payload,
                      b1(1)
                    )
                    s.ccu_state[i] <<= StateType(CCU_STATE_DISPATCHING)
                    s.ccu_dispatch_idx[i] <<= TargetIdxType(0)
                    s.ccu_dispatch_phase[i] <<= b1(0)

        # ===== Handle remote AC events =====
        if s.remote_event_valid:
          remote_cmd = s.recv_from_remote.msg.cmd
          remote_ccu_idx = s.recv_from_remote.msg.ctrl_addr

          if remote_cmd == CMD_AC_SYNC_VALUE:
            s.ccu_current_value[remote_ccu_idx] <<= s.recv_from_remote.msg.data
            s.ccu_state[remote_ccu_idx] <<= StateType(CCU_STATE_DISPATCHING)
            s.ccu_dispatch_idx[remote_ccu_idx] <<= TargetIdxType(0)
            s.ccu_dispatch_phase[remote_ccu_idx] <<= b1(0)

          elif remote_cmd == CMD_AC_CHILD_COMPLETE:
            for i in range(num_ccus):
              if s.ccu_state[i] == StateType(CCU_STATE_RUNNING):
                new_count = s.ccu_received_complete_count[i] + CountType(1)
                s.ccu_received_complete_count[i] <<= new_count

                if new_count >= s.ccu_child_complete_count[i]:
                  s.ccu_current_value[i] <<= DataType(
                    s.ccu_current_value[i].payload + s.ccu_step[i].payload,
                    b1(1)
                  )
                  s.ccu_state[i] <<= StateType(CCU_STATE_DISPATCHING)
                  s.ccu_dispatch_idx[i] <<= TargetIdxType(0)
                  s.ccu_dispatch_phase[i] <<= b1(0)

          elif remote_cmd == CMD_AC_CHILD_RESET:
            s.ccu_current_value[remote_ccu_idx] <<= \
                s.ccu_lower_bound[remote_ccu_idx]
            s.ccu_received_complete_count[remote_ccu_idx] <<= CountType(0)
            s.ccu_state[remote_ccu_idx] <<= StateType(CCU_STATE_RUNNING)


  def line_trace(s):
    states = ['IDLE', 'RUN', 'DISP', 'DONE']
    traces = []
    for i in range(len(s.ccu_state)):
      st = int(s.ccu_state[i])
      if st != CCU_STATE_IDLE:
        traces.append(
          f'CCU[{i}]:{states[st]}|'
          f'val={s.ccu_current_value[i].payload}/'
          f'{s.ccu_upper_bound[i].payload}|'
          f'rcv={s.ccu_received_complete_count[i]}/'
          f'{s.ccu_child_complete_count[i]}'
        )
    if not traces:
      return '[AC|IDLE]'
    return '[AC|' + ' '.join(traces) + ']'
