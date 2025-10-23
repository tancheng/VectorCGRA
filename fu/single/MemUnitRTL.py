from pymtl3 import *
from pymtl3.stdlib.ifcs import SendIfcRTL, RecvIfcRTL
from pymtl3.passes.backends.verilog import *

class MemUnitRTL( Component ):

  def construct( s, CgraPayloadType ):

    # Interface
    s.recv = RecvIfcRTL( CgraPayloadType )
    s.send = SendIfcRTL( CgraPayloadType )

    # Derived parameters
    addr_nbits = CgraPayloadType.get_field_type('addr').nbits
    data_nbits = CgraPayloadType.get_field_type('data').nbits

    # Component logic
    @s.update
    def up_mem_unit():
      s.send.msg = s.recv.msg
      s.send.en  = s.recv.en

  def line_trace( s ):
    return f'{s.recv.msg}(){s.send.msg}'
