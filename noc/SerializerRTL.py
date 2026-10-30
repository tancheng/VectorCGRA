"""
==========================================================================
SerializerRTL.py
==========================================================================
Serializer for converting a full NoCPktType packet into multiple
NoCFlitType flits to be sent over the NoC.

The packet payload is serialized from LSB to MSB. If the packet payload
width is not an integer multiple of the flit payload width, the final
flit is padded with zeros in its upper bits.

Author : Yufei Yang
Date   : Aug 24, 2026
"""

from pymtl3 import *
from ..lib.basic.val_rdy.ifcs import RecvIfcRTL, SendIfcRTL
from ..lib.util.common import *
from ..lib.util.data_struct_attr import *

class SerializerRTL( Component ):

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
    s.in_pkt = RecvIfcRTL( NoCPktType )
    s.out_flit = SendIfcRTL( NoCFlitType )

    # Registers.
    s.counter = Wire( mk_bits( counter_nbits ) )
    s.in_pkt_reg = Wire( NoCPktType )
    s.state = Wire( StateType )

    # Internal combinational signals.
    s.start_serializing = Wire( 1 )
    s.flit_consumed_by_noc = Wire( 1 )
    s.sending_last_flit = Wire( 1 )

    # Pre-sliced payload flits.
    #
    # The packet payload is statically divided into flit-sized wires
    # during elaboration. Runtime logic only selects one of these wires
    # according to the counter, avoiding variable slicing and shifting.
    s.flit_payloads = [
      Wire( mk_bits(flit_payload_nbits) )
      for _ in range( num_flits )
    ]

    # Statically connect packet payload slices to each flit payload.
    #
    # Example for a non-standard 232-bit packet payload and 32-bit flits:
    #
    # flit_payloads[0] = payload[0:32]
    # flit_payloads[1] = payload[32:64]
    # ...
    # flit_payloads[6] = payload[192:224]
    # flit_payloads[7][0:8] = payload[224:232]
    # flit_payloads[7][8:32] = 0
    #
    # start and end are Python integers evaluated during elaboration,
    # so all slice bounds are static constants for RTL translation.
    for i in range( num_flits ):
      start = i * flit_payload_nbits
      end = min( start + flit_payload_nbits, pkt_payload_nbits )
      valid_nbits = end - start

      if valid_nbits == flit_payload_nbits:
        connect(
          s.flit_payloads[i],
          s.in_pkt_reg.payload[start:end]
        )
      else:
        # Connect remaining valid payload bits to the lower bits.
        connect(
          s.flit_payloads[i][0:valid_nbits],
          s.in_pkt_reg.payload[start:end]
        )

        # Zero-pad the unused upper bits of the final flit.
        connect(
          s.flit_payloads[i][valid_nbits:flit_payload_nbits],
          mk_bits(flit_payload_nbits-valid_nbits)(0)
        )

    @update
    def update_comb_logic():

      # FSM output control.
      if s.state == 0:  # idle
        s.in_pkt.rdy @= 1
        s.out_flit.val @= 0
      elif s.state == 1:  # working
        s.in_pkt.rdy @= 0
        s.out_flit.val @= 1
      else:  # done
        s.in_pkt.rdy @= 0
        s.out_flit.val @= 0

      # Handshake signals.
      s.start_serializing @= s.in_pkt.val & s.in_pkt.rdy
      s.flit_consumed_by_noc @= s.out_flit.val & s.out_flit.rdy
      s.sending_last_flit @= \
        ( s.counter == num_flits - 1 ) & s.flit_consumed_by_noc

      # Copy packet header fields into each output flit.
      s.out_flit.msg.src @= s.in_pkt_reg.src
      s.out_flit.msg.dst @= s.in_pkt_reg.dst
      s.out_flit.msg.src_x @= s.in_pkt_reg.src_x
      s.out_flit.msg.src_y @= s.in_pkt_reg.src_y
      s.out_flit.msg.dst_x @= s.in_pkt_reg.dst_x
      s.out_flit.msg.dst_y @= s.in_pkt_reg.dst_y
      s.out_flit.msg.src_tile_id @= s.in_pkt_reg.src_tile_id
      s.out_flit.msg.dst_tile_id @= s.in_pkt_reg.dst_tile_id
      s.out_flit.msg.remote_src_port @= s.in_pkt_reg.remote_src_port
      s.out_flit.msg.opaque @= s.in_pkt_reg.opaque
      s.out_flit.msg.vc_id @= s.in_pkt_reg.vc_id

      # Select the current payload flit.
      # This synthesizes to a counter-controlled MUX. There is no
      # multiplier, variable shifter, or runtime variable slice.
      s.out_flit.msg.payload @= 0
      for i in range( num_flits ):
        if s.counter == i:
          s.out_flit.msg.payload @= s.flit_payloads[i]

    @update_ff
    def up_state():
      if s.reset:
        s.state <<= StateType( 0 )
      else:
        if ( s.state == 0 ) & s.start_serializing:
          s.state <<= StateType( 1 )
        elif ( s.state == 1 ) & s.sending_last_flit:
          s.state <<= StateType( 2 )
        elif s.state == 2:
          s.state <<= StateType( 0 )

    @update_ff
    def up_in_pkt_reg():
      if s.reset:
        s.in_pkt_reg <<= NoCPktType()
      elif s.start_serializing:
        s.in_pkt_reg <<= s.in_pkt.msg

    @update_ff
    def up_counter():
      if s.reset:
        s.counter <<= 0
      elif s.state == 2:
        s.counter <<= 0
      elif s.flit_consumed_by_noc & ~s.sending_last_flit:
        # Do not increment after the last flit.
        s.counter <<= s.counter + 1

  def line_trace( s ):
    state_str = "idle" if s.state == 0 else \
                ("working" if s.state == 1 else "done")
    return f"in_pkt_reg.payload:{s.in_pkt_reg.payload} | " \
           f"{state_str} | ctr:{s.counter} | " \
           f"in_val:{s.in_pkt.val} in_rdy:{s.in_pkt.rdy} | " \
           f"out_val:{s.out_flit.val} out_rdy:{s.out_flit.rdy} | " \
           f"out_payload:{s.out_flit.msg.payload}"
