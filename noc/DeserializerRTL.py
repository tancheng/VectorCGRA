"""
==========================================================================
DeserializerRTL.py
==========================================================================
Deserializer for converting multiple NoCFlitType flits into a full
NoCPktType packet received from the NoC.

The packet payload is deserialized from LSB to MSB. If the packet payload
width is not an integer multiple of the flit payload width, the padded
upper bits of the final flit are discarded.

Author : Yufei Yang
Date   : Aug 27, 2026
"""

from pymtl3 import *
from ..lib.basic.val_rdy.ifcs import RecvIfcRTL, SendIfcRTL
from ..lib.util.common import *
from ..lib.util.data_struct_attr import *

class DeserializerRTL( Component ):

  def construct( s, NoCPktType, NoCFlitType ):

    # Payload bit widths.
    pkt_payload_nbits = int( NoCPktType.get_field_type(kAttrPayload).nbits )
    flit_payload_nbits = int( NoCFlitType.get_field_type(kAttrPayload).nbits )

    # Number of flits required, using ceiling division.
    num_flits = (
      pkt_payload_nbits + flit_payload_nbits - 1
    ) // flit_payload_nbits

    # Counter bit width.
    counter_nbits = max( clog2( num_flits + 1 ), 1 )

    # FSM state: 0=idle, 1=working, 2=done.
    StateType = mk_bits( 2 )

    # Interfaces.
    s.in_flit = RecvIfcRTL( NoCFlitType )
    s.out_pkt = SendIfcRTL( NoCPktType )

    # Registers.
    s.counter = Wire( mk_bits( counter_nbits ) )
    s.header_reg = Wire( NoCFlitType )
    s.state = Wire( StateType )

    # Internal combinational signals.
    s.flit_accepted = Wire( 1 )
    s.start_deserializing = Wire( 1 )
    s.receiving_last_flit = Wire( 1 )
    s.consumed_by_controller = Wire( 1 )

    # Flit payload registers.
    s.flit_payload_regs = [
      Wire( mk_bits(flit_payload_nbits) )
      for _ in range( num_flits )
    ]

    # Reassembled packet payload.
    s.pkt_payload = Wire( mk_bits(pkt_payload_nbits) )

    # Statically connect flit payload registers to packet payload slices.
    #
    # Example for a non-standard 232-bit packet payload and 32-bit flits:
    #
    # pkt_payload[0:32] = flit_payload_regs[0]
    # pkt_payload[32:64] = flit_payload_regs[1]
    # ...
    # pkt_payload[192:224] = flit_payload_regs[6]
    # pkt_payload[224:232] = flit_payload_regs[7][0:8]
    #
    # start and end are Python integers evaluated during elaboration,
    # so all slice bounds are static constants for RTL translation.
    for i in range( num_flits ):
      start = i * flit_payload_nbits
      end = min( start + flit_payload_nbits, pkt_payload_nbits )
      valid_nbits = end - start

      if valid_nbits == flit_payload_nbits:
        connect(
          s.pkt_payload[start:end],
          s.flit_payload_regs[i]
        )
      else:
        connect(
          s.pkt_payload[start:end],
          s.flit_payload_regs[i][0:valid_nbits]
        )

    @update
    def update_comb_logic():

      # FSM output control.
      if s.state == 0:  # idle
        s.in_flit.rdy @= 1
        s.out_pkt.val @= 0
      elif s.state == 1:  # working
        s.in_flit.rdy @= 1
        s.out_pkt.val @= 0
      else:  # done
        s.in_flit.rdy @= 0
        s.out_pkt.val @= 1

      # Handshake signals.
      s.flit_accepted @= s.in_flit.val & s.in_flit.rdy
      s.start_deserializing @= \
        ( s.state == 0 ) & s.flit_accepted
      s.receiving_last_flit @= \
        ( s.counter == num_flits - 1 ) & s.flit_accepted
      s.consumed_by_controller @= \
        s.out_pkt.val & s.out_pkt.rdy

      # Copy stored flit header fields into the output packet.
      s.out_pkt.msg.src @= s.header_reg.src
      s.out_pkt.msg.dst @= s.header_reg.dst
      s.out_pkt.msg.src_x @= s.header_reg.src_x
      s.out_pkt.msg.src_y @= s.header_reg.src_y
      s.out_pkt.msg.dst_x @= s.header_reg.dst_x
      s.out_pkt.msg.dst_y @= s.header_reg.dst_y
      s.out_pkt.msg.src_tile_id @= s.header_reg.src_tile_id
      s.out_pkt.msg.dst_tile_id @= s.header_reg.dst_tile_id
      s.out_pkt.msg.remote_src_port @= s.header_reg.remote_src_port
      s.out_pkt.msg.opaque @= s.header_reg.opaque
      s.out_pkt.msg.vc_id @= s.header_reg.vc_id

      # Output the reassembled packet payload.
      s.out_pkt.msg.payload @= s.pkt_payload

    @update_ff
    def up_state():
      if s.reset:
        s.state <<= StateType( 0 )
      else:
        if ( s.state == 0 ) & s.start_deserializing:
            s.state <<= StateType( 1 )
        elif ( s.state == 1 ) & s.receiving_last_flit:
          s.state <<= StateType( 2 )
        elif ( s.state == 2 ) & s.consumed_by_controller:
          s.state <<= StateType( 0 )

    @update_ff
    def up_header_reg():
      if s.reset:
        s.header_reg <<= NoCFlitType()
      elif s.consumed_by_controller:
        s.header_reg <<= NoCFlitType()
      elif s.start_deserializing:
        s.header_reg <<= s.in_flit.msg

    @update_ff
    def up_flit_payload_regs():
      if s.reset:
        for i in range( num_flits ):
          s.flit_payload_regs[i] <<= 0
      elif s.consumed_by_controller:
        for i in range( num_flits ):
          s.flit_payload_regs[i] <<= 0
      elif s.flit_accepted:
        for i in range( num_flits ):
          if s.counter == i:
            s.flit_payload_regs[i] <<= s.in_flit.msg.payload

    @update_ff
    def up_counter():
      if s.reset:
        s.counter <<= 0
      elif s.consumed_by_controller:
        s.counter <<= 0
      elif s.flit_accepted & ~s.receiving_last_flit:
        # Do not increment after the last flit.
        s.counter <<= s.counter + 1

  def line_trace( s ):
    state_str = "idle" if s.state == 0 else \
                ("working" if s.state == 1 else "done")
    return f"{state_str} | ctr:{s.counter} | " \
           f"in_val:{s.in_flit.val} in_rdy:{s.in_flit.rdy} | " \
           f"in_payload:{s.in_flit.msg.payload} | " \
           f"out_val:{s.out_pkt.val} out_rdy:{s.out_pkt.rdy} | " \
           f"out_payload:{s.out_pkt.msg.payload}"
