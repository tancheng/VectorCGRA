"""
=========================================================================
SerdesRTL.py
=========================================================================

Author : Darren Lu
  Date : Dec 22, 2024
"""
from pymtl3.stdlib.primitive import RegisterFile
from ..lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ..lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ..lib.opt_type import *
from ..lib.util.common import *


class DeSerializeRTL(Component):
  def construct(s, OutputType, input_width=32):
        
        # States
        s.STATE_IDLE = 0
        s.STATE_ASSEMBLING = 1
        s.STATE_OUTPUT = 2
        
        # Calculate how many 32-bit inputs needed for output type
        s.input_width = input_width
        s.output_width = OutputType.nbits
        s.inputs_per_output = (s.output_width + s.input_width - 1) // s.input_width  # Ceiling division
        
        # Interfaces
        s.recv = RecvIfcRTL(mk_bits(input_width))  # 32-bit input
        s.send = SendIfcRTL(OutputType)            # Parametrized output type
        
        # State variables - use registers
        s.state_reg = Wire(mk_bits(2))
        s.buffer_reg = Wire(mk_bits(s.output_width))
        s.input_count_reg = Wire(mk_bits(8))
        
        # Constants as wires for comparison
        s.inputs_per_output_const = Wire(mk_bits(8))
        s.inputs_per_output_minus_one = Wire(mk_bits(8))
        
        s.inputs_per_output_const //= mk_bits(8)(s.inputs_per_output)
        s.inputs_per_output_minus_one //= mk_bits(8)(s.inputs_per_output - 1)
        
        # Internal state storage using basic flip-flops
        @update_ff
        def state_update():
            if s.reset:
                s.state_reg <<= s.STATE_IDLE
            elif s.state_reg == s.STATE_IDLE:
                if s.recv.val:
                    s.state_reg <<= s.STATE_ASSEMBLING
            elif s.state_reg == s.STATE_ASSEMBLING:
                if s.recv.val & s.recv.rdy:
                    if s.count_equals_target_minus_one:
                        s.state_reg <<= s.STATE_OUTPUT
            elif s.state_reg == s.STATE_OUTPUT:
                if s.send.rdy:
                    s.state_reg <<= s.STATE_IDLE
        
        @update_ff  
        def buffer_update():
            if s.reset:
                s.buffer_reg <<= 0
            elif (s.state_reg == s.STATE_IDLE) & s.recv.val:
                # First input - initialize buffer with input data
                s.buffer_reg <<= zext(s.recv.msg, s.output_width)
            elif (s.state_reg == s.STATE_ASSEMBLING) & s.recv.val & s.recv.rdy:
                # Subsequent inputs - shift existing data and OR in new data
                bit_pos = s.input_count_reg * s.input_width
                # Simple approach: just shift and OR the full input
                shifted_data = zext(s.recv.msg, s.output_width) << bit_pos
                s.buffer_reg <<= s.buffer_reg | shifted_data
            elif (s.state_reg == s.STATE_OUTPUT) & s.send.rdy:
                # Clear buffer when output is accepted
                s.buffer_reg <<= 0
        
        @update_ff
        def count_update():
            if s.reset:
                s.input_count_reg <<= 0
            elif (s.state_reg == s.STATE_IDLE) & s.recv.val:
                s.input_count_reg <<= 1
            elif (s.state_reg == s.STATE_ASSEMBLING) & s.recv.val & s.recv.rdy:
                s.input_count_reg <<= s.input_count_reg + 1
            elif (s.state_reg == s.STATE_OUTPUT) & s.send.rdy:
                s.input_count_reg <<= 0
        
        # Control signals - use combinational logic for comparisons
        s.count_less_than_target = Wire(mk_bits(1))
        s.count_equals_target_minus_one = Wire(mk_bits(1))
        s.state_is_idle = Wire(mk_bits(1))
        s.state_is_assembling = Wire(mk_bits(1))
        s.state_is_output = Wire(mk_bits(1))
        s.recv_ready = Wire(mk_bits(1))
        s.send_msg = Wire(OutputType)  # Wire of the correct output type
        
        @update
        def control_logic():
            s.count_less_than_target @= s.input_count_reg < s.inputs_per_output_const
            s.count_equals_target_minus_one @= s.input_count_reg == s.inputs_per_output_minus_one
            s.state_is_idle @= s.state_reg == s.STATE_IDLE
            s.state_is_assembling @= s.state_reg == s.STATE_ASSEMBLING
            s.state_is_output @= s.state_reg == s.STATE_OUTPUT
            
            # Compute recv.rdy logic
            s.recv_ready @= s.state_is_idle | (s.state_is_assembling & s.count_less_than_target)
            
            # Convert buffer bits to output type - truncate if necessary
            # Since buffer_reg is already sized to output_width, just assign directly
            s.send_msg @= s.buffer_reg
        
        s.recv.rdy //= s.recv_ready
        s.send.val //= s.state_is_output
        s.send.msg //= s.send_msg

  # Line trace
  def line_trace(s):
    res = "SerdesRTLUnit |"
    return res