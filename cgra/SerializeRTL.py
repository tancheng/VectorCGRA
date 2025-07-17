"""
=========================================================================
SerdesRTL.py
=========================================================================

Author : Darren Lu
  Date : Dec 22, 2024
"""
from pymtl3.stdlib.primitive import Reg
from ..lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ..lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ..lib.opt_type import *
from ..lib.util.common import *


class SerializeRTL(Component):
  def construct(s, InputType, output_width=32):
        
        # States
        s.STATE_IDLE = 0
        s.STATE_SERIALIZING = 1
        
        # Calculate how many 32-bit outputs needed for input type
        s.input_width = InputType.nbits
        s.output_width = output_width
        s.outputs_per_input = (s.input_width + s.output_width - 1) // s.output_width  # Ceiling division
        
        # Interfaces
        s.recv = RecvIfcRTL(InputType)               # Parametrized input type
        s.send = SendIfcRTL(mk_bits(output_width))   # 32-bit output
        
        # State variables - use simple approach
        s.state = Wire(mk_bits(1))  # Only 2 states, so 1 bit is enough
        s.buffer = Wire(mk_bits(s.input_width))
        s.output_count = Wire(mk_bits(8))
        
        # Constants as wires for comparison
        s.outputs_per_input_const = Wire(mk_bits(8))
        s.outputs_per_input_minus_one = Wire(mk_bits(8))
        
        s.outputs_per_input_const //= mk_bits(8)(s.outputs_per_input)
        s.outputs_per_input_minus_one //= mk_bits(8)(s.outputs_per_input - 1)
        
        # FSM logic with simple state variables
        @update_ff
        def state_update():
            if s.reset:
                s.state <<= s.STATE_IDLE
            elif s.state == s.STATE_IDLE:
                if s.recv.val & s.recv.rdy:
                    s.state <<= s.STATE_SERIALIZING
            elif s.state == s.STATE_SERIALIZING:
                if s.send.val & s.send.rdy:
                    if s.output_count == s.outputs_per_input_minus_one:
                        s.state <<= s.STATE_IDLE
        
        @update_ff
        def buffer_update():
            if s.reset:
                s.buffer <<= 0
            elif (s.state == s.STATE_IDLE) & s.recv.val & s.recv.rdy:
                s.buffer <<= s.recv.msg
            elif (s.state == s.STATE_SERIALIZING) & s.send.val & s.send.rdy:
                if s.output_count == s.outputs_per_input_minus_one:
                    s.buffer <<= 0
        
        @update_ff
        def count_update():
            if s.reset:
                s.output_count <<= 0
            elif (s.state == s.STATE_IDLE) & s.recv.val & s.recv.rdy:
                s.output_count <<= 0
            elif (s.state == s.STATE_SERIALIZING) & s.send.val & s.send.rdy:
                if s.output_count == s.outputs_per_input_minus_one:
                    s.output_count <<= 0
                else:
                    s.output_count <<= s.output_count + 1
        
        # Control signals and output generation
        s.state_is_idle = Wire(mk_bits(1))
        s.state_is_serializing = Wire(mk_bits(1))
        s.current_chunk = Wire(mk_bits(s.output_width))
        s.count_equals_target_minus_one = Wire(mk_bits(1))
        
        @update
        def control_logic():
            s.state_is_idle @= s.state == s.STATE_IDLE
            s.state_is_serializing @= s.state == s.STATE_SERIALIZING
            s.count_equals_target_minus_one @= s.output_count == s.outputs_per_input_minus_one
            
            # Extract current chunk using shift and mask instead of slicing
            # Shift buffer right by (output_count * output_width) bits
            shift_amount = s.output_count * s.output_width
            shifted_buffer = s.buffer >> shift_amount
            
            # Mask to get only the bottom output_width bits and truncate to correct width
            mask = (1 << s.output_width) - 1
            masked_result = shifted_buffer & mask
            s.current_chunk @= trunc(masked_result, s.output_width)
        
        s.recv.rdy //= s.state_is_idle
        s.send.val //= s.state_is_serializing
        s.send.msg //= s.current_chunk

  # Line trace
  def line_trace(s):
    res = "SerdesRTLUnit |"
    return res