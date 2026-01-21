"""
==========================================================================
LoopCounterRTL.py
==========================================================================
Loop Leaf Counter for CGRA tile.

This FU generates loop indices and valid predicates for loop when its output is
consumed. It supports configuration of loop lower bound, upper bound, and step
size through constants.

Author : Shangkun Li
  Date : January 21, 2026
"""

from pymtl3 import *
from ...lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL, ValRdySendIfcRTL
from ...lib.opt_type import *
from ...lib.messages import *

class LoopCounterRTL(Component):
  
  def construct(s, DataType, CtrlType,
                num_inports, num_outports,
                data_mem_size, ctrl_mem_size = 4,
                vector_factor_power = 0, data_bitwidth = 32):
    
    AddrType = mk_bits(clog2(data_mem_size))
    CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
    FuInType = mk_bits(clog2(num_inports + 1))
    s.CgraPayloadType = mk_cgra_payload(DataType, AddrType, CtrlType, CtrlAddrType)
    
    # Interfaces.
    s.recv_in = [ValRdyRecvIfcRTL(DataType) for _ in range(num_inports)]
    s.recv_const = ValRdyRecvIfcRTL(DataType)
    s.recv_opt = ValRdyRecvIfcRTL(CtrlType)
    s.send_out = [ValRdySendIfcRTL(DataType) for _ in range(num_outports)]
    
    # Redundant interface for compatibility.
    s.clear = InPort(b1)
    
    # Counter configuration registers (persistent storage across cycles).
    s.lower_bound_reg = Wire(DataType)
    s.upper_bound_reg = Wire(DataType)
    s.step_reg = Wire(DataType)
    
    # Counter state.
    s.current_loop_cnt = Wire(DataType)
    
    # Configuration state machine.
    ConfigStateType = mk_bits(3)
    s.kConfigIdle = ConfigStateType(0)
    s.kConfigLowerBound = ConfigStateType(1)
    s.kConfigUpperBound = ConfigStateType(2)
    s.kConfigStep = ConfigStateType(3)
    s.kConfigDone = ConfigStateType(4) 
    
    s.config_state = Wire(ConfigStateType)
    s.is_configured = Wire(1)
    
    @update
    def comb_logic():
      # Default values for interfaces.
      for i in range(num_inports):
        s.recv_in[i].rdy @= b1(0)
      for i in range(num_outports):
        s.send_out[i].val @= b1(0)
        s.send_out[i].msg @= DataType()
      
      s.recv_const.rdy @= b1(0)
      s.recv_opt.rdy @= b1(0)
      
      s.is_configured @= (s.config_state == s.kConfigDone)
      
      if s.recv_opt.val:
        if s.recv_opt.msg.operation == OPT_LOOP_COUNT:
          # Configuration phase: sequentially reads 3 constants from ConstQueue.
          if ~s.is_configured:
            if s.config_state == s.kConfigLowerBound:
              if s.recv_const.val:
                # Tells ConstQueue to dequeue the constant.
                s.recv_const.rdy @= b1(1)
              # Don't consume recv_opt yet, continues to next config state.
              s.recv_opt.rdy @= b1(0)
              s.send_out[0].val @= b1(0)
            elif s.config_state == s.kConfigUpperBound:
              if s.recv_const.val:
                # Tells ConstQueue to dequeue the constant.
                s.recv_const.rdy @= b1(1)
              # Don't consume recv_opt yet, continues to next config state.
              s.recv_opt.rdy @= b1(0)
              s.send_out[0].val @= b1(0)
            elif s.config_state == s.kConfigStep:
              if s.recv_const.val:
                # Tells ConstQueue to dequeue the constant.
                s.recv_const.rdy @= b1(1)
              # Configuration done, but don't consumes opt yet.
              # Will be consumed in next cycle when kConfigDone.
              s.recv_opt.rdy @= b1(0)
              s.send_out[0].val @= b1(0)
            else:
              # kConfigIdle or unexpected state.
              s.recv_opt.rdy @= b1(0)
              s.send_out[0].val @= b1(0)
          # Execution phase: uses stored configuration to count loops.
          else:
            # No longer accesses recv_const.
            s.recv_const.rdy @= b1(0)
            # Outputs current loop cnt value.
            s.send_out[0].msg.payload @= s.current_loop_cnt.payload
            
            # Checks if current_loop_cnt < upper_bound_reg.
            if s.current_loop_cnt.payload < s.upper_bound_reg.payload:
              # Valid iteration: predicate = 1
              s.send_out[0].msg.predicate @= 1
            else:
              # Loop terminated: predicate = 0
              s.send_out[0].msg.predicate @= 0
            s.send_out[0].val @= b1(1)
            s.recv_opt.rdy @= s.send_out[0].rdy
        else:
          # Invalid operation for LoopCounterRTL.
          s.recv_const.rdy @= b1(0)
          for j in range(num_outports):
            s.send_out[j].val @= b1(0)
    
    @update_ff
    def update_config_state():
      if s.reset | s.clear:
        s.config_state <<= s.kConfigIdle
      else:
        if s.recv_opt.val & (s.recv_opt.msg.operation == OPT_LOOP_COUNT):
          if s.config_state == s.kConfigIdle:
            s.config_state <<= s.kConfigLowerBound
          elif s.config_state == s.kConfigLowerBound:
            if s.recv_const.val & s.recv_const.rdy:
              s.config_state <<= s.kConfigUpperBound
          elif s.config_state == s.kConfigUpperBound:
            if s.recv_const.val & s.recv_const.rdy:
              s.config_state <<= s.kConfigStep
          elif s.config_state == s.kConfigStep:
            if s.recv_const.val & s.recv_const.rdy:
              s.config_state <<= s.kConfigDone
    
    @update_ff
    def update_counter_state():
      if s.reset | s.clear:
        s.current_loop_cnt <<= DataType(0,0)
        s.lower_bound_reg <<= DataType(0,0)
        s.upper_bound_reg <<= DataType(0,0)
        s.step_reg <<= DataType(0,0)
      else:
        # Configuration phase: captures constants when rdy is asserted.
        if s.recv_opt.val & (s.recv_opt.msg.operation == OPT_LOOP_COUNT) & ~s.is_configured:
          if s.config_state == s.kConfigLowerBound:
            if s.recv_const.val & s.recv_const.rdy:
              s.lower_bound_reg <<= s.recv_const.msg
          elif s.config_state == s.kConfigUpperBound:
            if s.recv_const.val & s.recv_const.rdy:
              s.upper_bound_reg <<= s.recv_const.msg
          elif s.config_state == s.kConfigStep:
            if s.recv_const.val & s.recv_const.rdy:
              s.step_reg <<= s.recv_const.msg
              # Initializes current_loop_cnt to lower_bound when step config done.
              s.current_loop_cnt <<= s.lower_bound_reg
        # Execution phase: updates counter operation every cycle when configured and output consumed. 
        elif s.recv_opt.val & (s.recv_opt.msg.operation == OPT_LOOP_COUNT) & s.is_configured:
          if s.send_out[0].val & s.send_out[0].rdy:
            # Only increments if is still below upper_bound.
            if s.current_loop_cnt.payload < s.upper_bound_reg.payload:
              s.current_loop_cnt <<= DataType(s.current_loop_cnt.payload + s.step_reg.payload, b1(1))
    
  def line_trace(s):
    config_state_str = ['IDLE', 'LOWER', 'UPPER', 'STEP', 'DONE'][s.config_state]
    opt_str = " #"
    if s.recv_opt.val:
      opt_str = OPT_SYMBOL_DICT[s.recv_opt.msg.operation]
    return f'[DCU:{config_state_str}|{opt_str}|idx={s.current_loop_cnt.payload}/{s.upper_bound_reg.payload}|' + \
           f'pred={s.send_out[0].msg.predicate}|out.val={s.send_out[0].val}] ' + \
           f'<const:{s.recv_const.val}|{s.recv_const.msg}>'
      
              
            
              
              
        