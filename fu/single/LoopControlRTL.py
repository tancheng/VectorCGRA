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
from ...lib.opt_type import OPT_LOOP_CONTROL, OPT_SYMBOL_DICT

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
    FuInType = mk_bits(clog2(num_inports + 1))
    
    # Internal state for loop control
    s.current_index = Wire(PayloadType)
    s.next_index = Wire(PayloadType)
    s.loop_valid = Wire(PredicateType)
    s.loop_active = Wire(b1)
    
    # Loop parameters from operation configuration
    s.start_value = Wire(PayloadType)
    s.end_value = Wire(PayloadType)
    s.step_value = Wire(PayloadType)
    
    # Configurable input operand indices
    s.in0 = Wire(FuInType)  # parent_valid
    s.in1 = Wire(FuInType)  # start
    s.in2 = Wire(FuInType)  # end
    s.in3 = Wire(FuInType)  # step
    s.in0_idx = Wire(FuInType)
    s.in1_idx = Wire(FuInType)
    s.in2_idx = Wire(FuInType)
    s.in3_idx = Wire(FuInType)
    
    # For first iteration detection - use sequential state flag
    s.is_first_iter = Wire(b1)
    s.loop_initialized = Wire(b1)  # Tracks if loop has started
    
    # Compute actual indices from configurable operand indices
    @update
    def update_indices():
      s.in0_idx @= s.in0
      s.in1_idx @= s.in1
      s.in2_idx @= s.in2
      s.in3_idx @= s.in3
    
    # Sequential state for tracking current index and initialization
    @update_ff
    def update_index():
      if s.reset:
        s.current_index <<= PayloadType(0)
        s.loop_initialized <<= b1(0)
      else:
        if ( s.recv_opt.val and s.send_out[0].rdy
             and s.recv_in[s.in0_idx].val and s.recv_in[s.in1_idx].val
             and s.recv_in[s.in2_idx].val and s.recv_in[s.in3_idx].val ):
          if s.recv_opt.msg.operation == OPT_LOOP_CONTROL:
            # Update current index after sending output
            s.current_index <<= s.next_index
            # Mark loop as initialized after first iteration
            if s.is_first_iter:
              s.loop_initialized <<= b1(1)
            # Reset initialization when loop completes (valid becomes 0)
            elif not s.loop_valid:
              s.loop_initialized <<= b1(0)
    
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
      
      # Extract loop parameters - default values
      s.start_value @= PayloadType(0)
      s.end_value @= PayloadType(0)
      s.step_value @= PayloadType(1)

      # Configure input operand indices from operation message
      if s.recv_opt.val:
        if s.recv_opt.msg.fu_in[0] != 0:
          s.in0 @= zext(s.recv_opt.msg.fu_in[0] - 1, FuInType)
        if s.recv_opt.msg.fu_in[1] != 0:
          s.in1 @= zext(s.recv_opt.msg.fu_in[1] - 1, FuInType)
        if s.recv_opt.msg.fu_in[2] != 0:
          s.in2 @= zext(s.recv_opt.msg.fu_in[2] - 1, FuInType)
        if s.recv_opt.msg.fu_in[3] != 0:
          s.in3 @= zext(s.recv_opt.msg.fu_in[3] - 1, FuInType)

      # Only process when all required inputs are valid
      all_inputs_valid = (
        s.recv_opt.val and
        s.recv_opt.msg.operation == OPT_LOOP_CONTROL and
        s.recv_in[s.in0_idx].val and
        s.recv_in[s.in1_idx].val and
        s.recv_in[s.in2_idx].val and
        s.recv_in[s.in3_idx].val
      )

      if all_inputs_valid:
        # Get inputs:
        # recv_in[in0]: parent_valid predicate
        # recv_in[in1]: start value
        # recv_in[in2]: end value  
        # recv_in[in3]: step value
        parent_valid = s.recv_in[s.in0_idx].msg.predicate
        s.start_value @= s.recv_in[s.in1_idx].msg.payload
        s.end_value @= s.recv_in[s.in2_idx].msg.payload
        s.step_value @= s.recv_in[s.in3_idx].msg.payload

        # Detect first iteration: loop not yet initialized
        # This correctly handles start_value=0 and loop reinvocation
        s.is_first_iter @= ~s.loop_initialized

        # Compute next index and validity
        current_idx = s.current_index

        if s.is_first_iter:
          # First iteration: output start value
          output_idx = s.start_value
          s.next_index @= s.start_value + s.step_value
          # Check if start is within bounds
          if s.start_value < s.end_value:
            s.loop_active @= b1(1)
            s.loop_valid @= parent_valid
          else:
            s.loop_active @= b1(0)
            s.loop_valid @= PredicateType(0)
        else:
          # Subsequent iterations: output current index
          output_idx = current_idx
          s.next_index @= current_idx + s.step_value
          # Check if current index is within bounds
          if current_idx < s.end_value:
            s.loop_active @= b1(1)
            s.loop_valid @= parent_valid
          else:
            s.loop_active @= b1(0)
            s.loop_valid @= PredicateType(0)

        # Output 0: current loop index with predicate
        s.send_out[0].msg.payload @= output_idx
        s.send_out[0].msg.predicate @= s.loop_valid & s.reached_vector_factor
        s.send_out[0].val @= b1(1)
        
        # Output 1: loop_valid (boolean predicate indicating if loop should continue)
        if num_outports > 1:
          s.send_out[1].msg.payload @= zext(s.loop_valid, PayloadType)
          s.send_out[1].msg.predicate @= s.reached_vector_factor
          s.send_out[1].val @= b1(1)
        
        # Set ready signals for inputs when all inputs are consumed
        s.recv_in[s.in0_idx].rdy @= b1(1)
        s.recv_in[s.in1_idx].rdy @= b1(1)
        s.recv_in[s.in2_idx].rdy @= b1(1)
        s.recv_in[s.in3_idx].rdy @= b1(1)
        s.recv_opt.rdy @= b1(1)

  def line_trace(s):
    opt_str = " #"
    if s.recv_opt.val:
      opt_str = OPT_SYMBOL_DICT.get(s.recv_opt.msg.operation, f"(op:{s.recv_opt.msg.operation})")
    out_str = ",".join([f"{x.msg.payload}:{x.msg.predicate}" for x in s.send_out if x.val])
    return f'[LC: idx={s.current_index}, nxt={s.next_index}, valid={s.loop_valid}] {opt_str} -> [{out_str}]'
