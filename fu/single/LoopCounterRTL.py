"""
==========================================================================
LoopCounterRTL.py
==========================================================================
Loop Counter (DCU) for CGRA tile.

This FU manages loop counters indexed by ctrl_addr from control memory.
Each ctrl_addr has:
- Leaf counter state (lower_bound, upper_bound, step, current_value)
- Shadow register (for relay/root counter values from AC)

Supports two operation modes per ctrl_addr:
1. OPT_LOOP_COUNT: Loop-Driven Mode (Leaf counter execution)
2. OPT_LOOP_DELIVERY: Loop-Delivery Mode (Shadow register output)

Configuration methods:
1. Initial config (via ConstQueue): Configure leaf counter parameters
2. Runtime updates (via AC): Reset leaf counter or update shadow register

Author : Shangkun Li
  Date : January 27, 2026
"""

from pymtl3 import *
from ...lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL, ValRdySendIfcRTL
from ..basic.Fu import Fu
from ...lib.opt_type import *
from ...lib.messages import *
from ...lib.cmd_type import *

class LoopCounterRTL(Fu):
  
  def construct(s, DataType, CtrlType,
                num_inports, num_outports,
                data_mem_size, ctrl_mem_size = 8,
                vector_factor_power = 0, data_bitwidth = 32):
    
    super(LoopCounterRTL, s).construct(DataType, CtrlType,
                                      num_inports, num_outports,
                                      data_mem_size, ctrl_mem_size,
                                      1, vector_factor_power,
                                      data_bitwidth = data_bitwidth)
    
    AddrType = mk_bits(clog2(data_mem_size))
    CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
    s.CgraPayloadType = mk_cgra_payload(DataType, AddrType, CtrlType, CtrlAddrType)
    
    # ===== Per-ctrl_addr State Arrays =====
    # Each ctrl_addr has its own leaf counter configuration and state.
    s.leaf_lower_bound = [Wire(DataType) for _ in range(ctrl_mem_size)]
    s.leaf_upper_bound = [Wire(DataType) for _ in range(ctrl_mem_size)]
    s.leaf_step = [Wire(DataType) for _ in range(ctrl_mem_size)]
    s.leaf_current_value = [Wire(DataType) for _ in range(ctrl_mem_size)]
    
    # Configuration state for each ctrl_addr's leaf counter.
    LoopStateType = mk_bits(3)
    s.kWaitConfig = LoopStateType(0)
    s.kLoadLowerBound = LoopStateType(1)
    s.kLoadUpperBound = LoopStateType(2)
    s.kLoadStep = LoopStateType(3)
    s.kLoopConfigDone = LoopStateType(4)
    
    s.leaf_config_state = [Wire(LoopStateType) for _ in range(ctrl_mem_size)]
    
    # Shadow register for each ctrl_addr (stores relay/root counter values).
    s.shadow_regs = [Wire(DataType) for _ in range(ctrl_mem_size)]
    s.shadow_valid = [Wire(1) for _ in range(ctrl_mem_size)]
    
    # Completion tracking for each ctrl_addr.
    s.already_done = [Wire(1) for _ in range(ctrl_mem_size)]
    
    # ===== Control Signals =====
    s.current_ctrl_addr = Wire(CtrlAddrType)
    s.leaf_is_running = Wire(1)
    s.loop_terminated = Wire(1)
    
    # Update triggers from AC.
    s.should_reset_counter = Wire(1)
    s.should_update_shadow = Wire(1)
    s.reset_counter_addr = Wire(CtrlAddrType)
    s.update_shadow_addr = Wire(CtrlAddrType)
    s.update_shadow_value = Wire(DataType)
    
    @update
    def comb_logic():
      # Default values.
      for i in range(num_inports):
        s.recv_in[i].rdy @= b1(0)
      for i in range(num_outports):
        s.send_out[i].val @= b1(0)
        s.send_out[i].msg @= DataType()
      
      s.recv_const.rdy @= b1(0)
      s.recv_opt.rdy @= b1(0)
      s.send_to_ctrl_mem.val @= b1(0)
      s.send_to_ctrl_mem.msg @= s.CgraPayloadType(0, 0, 0, 0, 0)
      s.recv_from_ctrl_mem.rdy @= b1(0)
      
      # Gets current ctrl_addr for operation.
      s.current_ctrl_addr @= s.ctrl_addr_inport
      s.leaf_is_running @= (s.leaf_config_state[s.current_ctrl_addr] == s.kLoopConfigDone)
      s.loop_terminated @= (s.leaf_current_value[s.current_ctrl_addr].payload >= 
                            s.leaf_upper_bound[s.current_ctrl_addr].payload)
      
      s.should_reset_counter @= b1(0)
      s.should_update_shadow @= b1(0)
      s.reset_counter_addr @= CtrlAddrType(0)
      s.update_shadow_addr @= CtrlAddrType(0)
      s.update_shadow_value @= DataType(0, 0)
      
      if s.recv_opt.val:
        # ===== OPT_LOOP_COUNT: Loop-Driven Mode (Leaf Counter) =====
        if s.recv_opt.msg.operation == OPT_LOOP_COUNT:
          addr = s.current_ctrl_addr
          
          # Configuration phase: sequentially read 3 constants.
          if ~s.leaf_is_running:
            if s.leaf_config_state[addr] == s.kLoadLowerBound:
              if s.recv_const.val:
                s.recv_const.rdy @= b1(1)
              s.recv_opt.rdy @= b1(0)
              s.send_out[0].val @= b1(0)
              
            elif s.leaf_config_state[addr] == s.kLoadUpperBound:
              if s.recv_const.val:
                s.recv_const.rdy @= b1(1)
              s.recv_opt.rdy @= b1(0)
              s.send_out[0].val @= b1(0)
              
            elif s.leaf_config_state[addr] == s.kLoadStep:
              if s.recv_const.val:
                s.recv_const.rdy @= b1(1)
              s.recv_opt.rdy @= b1(0)
              s.send_out[0].val @= b1(0)
              
            else:
              s.recv_opt.rdy @= b1(0)
              s.send_out[0].val @= b1(0)
          
          # Execution phase: output current counter value.
          else:
            s.recv_const.rdy @= b1(0)
            s.send_out[0].msg.payload @= s.leaf_current_value[addr].payload
            
            if s.loop_terminated:
              # Loop terminated: predicate = 0.
              s.send_out[0].msg.predicate @= 0
              
              # Sends CMD_COMPLETE if not already done (meaning it has not sent a completion message).
              if ~s.already_done[addr]:
                s.send_to_ctrl_mem.val @= b1(1)
                s.send_to_ctrl_mem.msg @= s.CgraPayloadType(
                  CMD_COMPLETE, DataType(0, 0), 0, s.recv_opt.msg, addr
                )
                s.send_out[0].val @= b1(1)
                s.recv_opt.rdy @= s.send_to_ctrl_mem.rdy & s.send_out[0].rdy
              else:
                # Already sent completion.
                s.send_out[0].val @= b1(1)
                s.recv_opt.rdy @= s.send_out[0].rdy
            else:
              # Valid iteration: predicate = 1.
              s.send_out[0].msg.predicate @= 1
              s.send_out[0].val @= b1(1)
              s.recv_opt.rdy @= s.send_out[0].rdy
        
        # ===== OPT_LOOP_DELIVERY: Loop-Delivery Mode (Shadow Register) =====
        elif s.recv_opt.msg.operation == OPT_LOOP_DELIVERY:
          addr = s.current_ctrl_addr
          
          if s.shadow_valid[addr]:
            s.send_out[0].val @= b1(1)
            s.send_out[0].msg @= s.shadow_regs[addr]
            s.recv_opt.rdy @= s.send_out[0].rdy
          else:
            # Shadow register not valid yet
            s.send_out[0].val @= b1(0)
            s.recv_opt.rdy @= b1(0)
      
      # ===== Handle messages from AC (runtime updates) =====
      if s.recv_from_ctrl_mem.val:
        s.recv_from_ctrl_mem.rdy @= b1(1)
        
        # CMD_RESET_LEAF_COUNTER: Resets leaf counter to lower_bound.
        if s.recv_from_ctrl_mem.msg.cmd == CMD_RESET_LEAF_COUNTER:
          s.should_reset_counter @= b1(1)
          s.reset_counter_addr @= s.recv_from_ctrl_mem.msg.ctrl_addr
        
        # CMD_UPDATE_COUNTER_SHADOW_VALUE: Updates shadow register.
        elif s.recv_from_ctrl_mem.msg.cmd == CMD_UPDATE_COUNTER_SHADOW_VALUE:
          s.should_update_shadow @= b1(1)
          s.update_shadow_addr @= s.recv_from_ctrl_mem.msg.ctrl_addr
          s.update_shadow_value @= s.recv_from_ctrl_mem.msg.data
    
    @update_ff
    def update_leaf_config_state():
      if s.reset | s.clear:
        for i in range(ctrl_mem_size):
          s.leaf_config_state[i] <<= s.kWaitConfig
      else:
        if s.recv_opt.val & (s.recv_opt.msg.operation == OPT_LOOP_COUNT):
          addr = s.current_ctrl_addr
          
          if s.leaf_config_state[addr] == s.kWaitConfig:
            s.leaf_config_state[addr] <<= s.kLoadLowerBound
          elif s.leaf_config_state[addr] == s.kLoadLowerBound:
            if s.recv_const.val & s.recv_const.rdy:
              s.leaf_config_state[addr] <<= s.kLoadUpperBound
          elif s.leaf_config_state[addr] == s.kLoadUpperBound:
            if s.recv_const.val & s.recv_const.rdy:
              s.leaf_config_state[addr] <<= s.kLoadStep
          elif s.leaf_config_state[addr] == s.kLoadStep:
            if s.recv_const.val & s.recv_const.rdy:
              s.leaf_config_state[addr] <<= s.kLoopConfigDone
    
    @update_ff
    def update_leaf_counters():
      if s.reset | s.clear:
        for i in range(ctrl_mem_size):
          s.leaf_lower_bound[i] <<= DataType(0, 0)
          s.leaf_upper_bound[i] <<= DataType(0, 0)
          s.leaf_step[i] <<= DataType(0, 0)
          s.leaf_current_value[i] <<= DataType(0, 0)
      else:
        # Initial configuration phase.
        if s.recv_opt.val & (s.recv_opt.msg.operation == OPT_LOOP_COUNT) & ~s.leaf_is_running:
          addr = s.current_ctrl_addr
          
          if s.leaf_config_state[addr] == s.kLoadLowerBound:
            if s.recv_const.val & s.recv_const.rdy:
              s.leaf_lower_bound[addr] <<= s.recv_const.msg
          elif s.leaf_config_state[addr] == s.kLoadUpperBound:
            if s.recv_const.val & s.recv_const.rdy:
              s.leaf_upper_bound[addr] <<= s.recv_const.msg
          elif s.leaf_config_state[addr] == s.kLoadStep:
            if s.recv_const.val & s.recv_const.rdy:
              s.leaf_step[addr] <<= s.recv_const.msg
              # Initializes current_value to lower_bound.
              s.leaf_current_value[addr] <<= s.leaf_lower_bound[addr]
        
        # Execution phase: increments counter.
        elif s.recv_opt.val & (s.recv_opt.msg.operation == OPT_LOOP_COUNT) & s.leaf_is_running:
          addr = s.current_ctrl_addr
          if s.send_out[0].val & s.send_out[0].rdy:
            if s.leaf_current_value[addr].payload < s.leaf_upper_bound[addr].payload:
              s.leaf_current_value[addr] <<= DataType(
                s.leaf_current_value[addr].payload + s.leaf_step[addr].payload, b1(1)
              )
        
        # Runtime reset from AC.
        if s.should_reset_counter:
          addr = s.reset_counter_addr
          s.leaf_current_value[addr] <<= s.leaf_lower_bound[addr]
    
    @update_ff
    def update_shadow_registers():
      if s.reset | s.clear:
        for i in range(ctrl_mem_size):
          s.shadow_regs[i] <<= DataType(0, 0)
          s.shadow_valid[i] <<= b1(0)
      else:
        # Runtime update from AC.
        if s.should_update_shadow:
          addr = s.update_shadow_addr
          s.shadow_regs[addr] <<= s.update_shadow_value
          s.shadow_valid[addr] <<= b1(1)
    
    @update_ff
    def update_already_done():
      if s.reset | s.clear:
        for i in range(ctrl_mem_size):
          s.already_done[i] <<= b1(0)
      else:
        # Sets done flag when loop completes.
        if s.recv_opt.val & \
           (s.recv_opt.msg.operation == OPT_LOOP_COUNT) & \
           s.leaf_is_running & \
           ~s.already_done[s.current_ctrl_addr] & \
           s.loop_terminated & \
           s.send_to_ctrl_mem.val & \
           s.send_to_ctrl_mem.rdy:
          addr = s.current_ctrl_addr
          s.already_done[addr] <<= b1(1)
        
        # Resets done flag when counter is reset from AC.
        if s.should_reset_counter:
          addr = s.reset_counter_addr
          s.already_done[addr] <<= b1(0)
    
  def line_trace(s):
    addr = s.current_ctrl_addr
    config_state_str = ['WAIT', 'LOWER', 'UPPER', 'STEP', 'DONE'][s.leaf_config_state[addr]]
    opt_str = " #"
    if s.recv_opt.val:
      opt_str = OPT_SYMBOL_DICT[s.recv_opt.msg.operation]
    
    if s.recv_opt.val and s.recv_opt.msg.operation == OPT_LOOP_COUNT:
      return f'[DCU|addr={addr}|{config_state_str}|{opt_str}|' + \
             f'cnt={s.leaf_current_value[addr].payload}/{s.leaf_upper_bound[addr].payload}|' + \
             f'pred={s.send_out[0].msg.predicate}|val={s.send_out[0].val}|' + \
             f'done={s.already_done[addr]}]'
    elif s.recv_opt.val and s.recv_opt.msg.operation == OPT_LOOP_DELIVERY:
      return f'[DCU|addr={addr}|{opt_str}|' + \
             f'shadow={s.shadow_regs[addr].payload}|' + \
             f'valid={s.shadow_valid[addr]}|val={s.send_out[0].val}]'
    else:
      return f'[DCU|addr={addr}|IDLE]'