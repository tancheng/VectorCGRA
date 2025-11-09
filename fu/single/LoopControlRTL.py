"""
==========================================================================
LoopControlRTL.py
==========================================================================
Loop control functional unit for CGRA tile.

This FU generates loop indices and valid predicates with minimal recurrence
cycle length. It combines comparison and increment logic into a single 
operation for efficient loop execution on dataflow architectures.

Author : Shiran Guo
  Date : November 7, 2025
"""

from pymtl3 import *
from ..basic.Fu import Fu
from ...lib.opt_type import *

class LoopControlRTL(Fu):

  def construct(s, DataType, CtrlType, num_inports,
                num_outports, data_mem_size, ctrl_mem_size = 4,
                vector_factor_power = 0,
                data_bitwidth = 32):

    # LoopControl needs at least 4 inputs:
    # recv_in[0]: parent_valid (predicate from parent loop, always 1 for outermost)
    # recv_in[1]: start value
    # recv_in[2]: end value  
    # recv_in[3]: step value
    # OR use recv_const for configuration parameters
    assert num_inports >= 4, "LoopControlRTL requires at least 4 input ports"

    super(LoopControlRTL, s).construct(DataType, CtrlType,
                                       num_inports, num_outports,
                                       data_mem_size, ctrl_mem_size,
                                       1, vector_factor_power,
                                       data_bitwidth = data_bitwidth)

    PayloadType = DataType.get_field_type('payload')
    PredicateType = DataType.get_field_type('predicate')
    
    # Internal state for loop control
    s.current_index = Wire(PayloadType)
    s.next_index = Wire(PayloadType)
    s.loop_valid = Wire(PredicateType)
    s.loop_active = Wire(b1)
    
    # Loop parameters from operation configuration
    s.start_value = Wire(PayloadType)
    s.end_value = Wire(PayloadType)
    s.step_value = Wire(PayloadType)
    
    # For first iteration detection
    s.is_first_iter = Wire(b1)
    
    # Sequential state for tracking current index
    @update_ff
    def update_index():
      if s.reset:
        s.current_index <<= PayloadType(0)
      else:
        if ( s.recv_opt.val and s.send_out[0].rdy
             and s.recv_in[0].val and s.recv_in[1].val
             and s.recv_in[2].val and s.recv_in[3].val ):
          if s.recv_opt.msg.operation == OPT_LOOP_CONTROL:
            # Update current index after sending output
            s.current_index <<= s.next_index
    
    @update
    def comb_logic():
      # Default signal values
      for i in range(num_inports):
        s.recv_in[i].rdy @= b1(0)
      for i in range(num_outports):
        s.send_out[i].val @= 0
        s.send_out[i].msg @= DataType()

      s.recv_const.rdy @= 0
      s.recv_opt.rdy @= 0

      s.send_to_ctrl_mem.val @= 0
      s.send_to_ctrl_mem.msg @= s.CgraPayloadType(0, 0, 0, 0, 0)
      s.recv_from_ctrl_mem.rdy @= 0
      
      # Default loop control values
      s.loop_valid @= PredicateType(0)
      s.loop_active @= b1(0)
      s.is_first_iter @= b1(0)
      s.next_index @= PayloadType(0)
      
      # Extract loop parameters from constant or operation attributes
      # These would typically come from the recv_const interface or
      # embedded in the operation configuration
      s.start_value @= PayloadType(0)
      s.end_value @= PayloadType(0)
      s.step_value @= PayloadType(1)

      if s.recv_opt.val:
        if s.recv_opt.msg.operation == OPT_LOOP_CONTROL:
          # Get inputs:
          # recv_in[0]: parent_valid predicate
          # recv_in[1]: start value
          # recv_in[2]: end value  
          # recv_in[3]: step value
          parent_valid = s.recv_in[0].msg.predicate if s.recv_in[0].val else PredicateType(0)
          
          # Read loop parameters from input ports
          if s.recv_in[1].val:
            s.start_value @= s.recv_in[1].msg.payload
          if s.recv_in[2].val:
            s.end_value @= s.recv_in[2].msg.payload
          if s.recv_in[3].val:
            s.step_value @= s.recv_in[3].msg.payload
          
          # Detect first iteration: current_index == 0 or predicate was 0
          s.is_first_iter @= (s.current_index == PayloadType(0))
          
          # Compute next index and validity
          current_idx = s.current_index
          
          if s.is_first_iter:
            # First iteration: output start value
            output_idx = s.start_value
            s.next_index @= s.start_value
            # Check if start is within bounds
            # Handle both positive and negative step values
            if s.step_value > PayloadType(0):
              valid = s.start_value < s.end_value
            elif s.step_value < PayloadType(0):
              valid = s.start_value > s.end_value
            else:
              valid = b1(0)  # step == 0, invalid loop
            s.loop_active @= b1(valid)
            s.loop_valid @= parent_valid & PredicateType(valid)
          else:
            # Subsequent iterations: output current index
            output_idx = current_idx
            s.next_index @= current_idx + s.step_value
            # Check if current index is within bounds
            if s.step_value > PayloadType(0):
              valid = current_idx < s.end_value
            elif s.step_value < PayloadType(0):
              valid = current_idx > s.end_value
            else:
              valid = b1(0)  # step == 0, invalid loop
            s.loop_active @= b1(valid)
            s.loop_valid @= parent_valid & PredicateType(valid)
          
          # Output 0: current loop index with predicate
          s.send_out[0].msg.payload @= output_idx
          s.send_out[0].msg.predicate @= s.loop_valid & s.reached_vector_factor
          s.send_out[0].val @= b1(1)
          
          # Output 1: loop_valid (boolean predicate indicating if loop should continue)
          if num_outports > 1:
            s.send_out[1].msg.payload @= zext(s.loop_valid, PayloadType)
            s.send_out[1].msg.predicate @= s.reached_vector_factor
            s.send_out[1].val @= b1(1)
          
          # Ready signals - all inputs consumed together
          s.recv_in[0].rdy @= s.send_out[0].rdy
          s.recv_in[1].rdy @= s.send_out[0].rdy
          s.recv_in[2].rdy @= s.send_out[0].rdy
          s.recv_in[3].rdy @= s.send_out[0].rdy
          s.recv_opt.rdy @= s.send_out[0].rdy

  def line_trace(s):
    opt_str = " #"
    if s.recv_opt.val:
      opt_str = OPT_SYMBOL_DICT.get(s.recv_opt.msg.operation, f"(op:{s.recv_opt.msg.operation})")
    out_str = ",".join([f"{x.msg.payload}:{x.msg.predicate}" for x in s.send_out if x.val])
    return f'[LC: idx={s.current_index}, nxt={s.next_index}, valid={s.loop_valid}] {opt_str} -> [{out_str}]'
