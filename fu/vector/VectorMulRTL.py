"""
==========================================================================
VectorMulRTL.py
==========================================================================
Vectorized multiplier to support SIMD Multiplication in different
granularities.
This basic multiplier is different from the scalar one:
    1. Can directly perform on bits rather than CGRADataType.

Author : Cheng Tan
  Date : APril 17, 2022

"""

from pymtl3             import *
from ...lib.ifcs import SendIfcRTL, RecvIfcRTL
from ...lib.opt_type    import *

class VectorMulRTL( Component ):

  def construct( s, bw, CtrlType,
                 num_inports, num_outports, data_mem_size ):

    # DataType should be 2 times due to the longer output
    DataType    = mk_bits( bw * 2 )
    num_entries = 2
    FuInType    = mk_bits( clog2( num_inports + 1 ) )
    CountType   = mk_bits( clog2( num_entries + 1 ) )
    FuInType    = mk_bits( clog2( num_inports + 1 ) )

    # Constant
    s.const_zero  = DataType(0)
    s.const_one   = DataType(1)

    # Interface
    s.recv_in        = [ RecvIfcRTL( DataType ) for _ in range( num_inports ) ]
    s.recv_in_count  = [ InPort( CountType ) for _ in range( num_inports ) ]
    s.recv_const     = RecvIfcRTL( DataType )
    s.recv_opt       = RecvIfcRTL( CtrlType )
    s.send_out       = [ SendIfcRTL( DataType ) for _ in range( num_outports ) ]

    s.in0 = Wire( FuInType )
    s.in1 = Wire( FuInType )

    idx_nbits = clog2( num_inports )
    s.in0_idx = Wire( idx_nbits )
    s.in1_idx = Wire( idx_nbits )

    s.in0_idx //= s.in0[0:idx_nbits]
    s.in1_idx //= s.in1[0:idx_nbits]

    # Components
    s.recv_rdy_vector = Wire( num_outports )

    @update
    def update_signal():
      for j in range( num_outports ):
        # s.recv_const.rdy @= s.send_out[j].rdy | s.recv_const.rdy
        # s.recv_opt.rdy @= s.send_out[j].rdy | s.recv_opt.rdy
        s.recv_rdy_vector[j] @= s.send_out[j].rdy
      s.recv_const.rdy @= reduce_or( s.recv_rdy_vector )
      s.recv_opt.rdy   @= reduce_or( s.recv_rdy_vector )

    @update
    def comb_logic():

      # Pick input register
      s.in0 @= FuInType( 0 )
      s.in1 @= FuInType( 0 )
      for i in range( num_inports ):
        s.recv_in[i].rdy @= b1( 0 )

      if s.recv_opt.en:
        if s.recv_opt.msg.fu_in[0] != 0:
          s.in0 @= zext( s.recv_opt.msg.fu_in[0] - 1, FuInType )
          s.recv_in[s.in0_idx].rdy @= b1( 1 )
        if s.recv_opt.msg.fu_in[1] != 0:
          s.in1 @= zext( s.recv_opt.msg.fu_in[1] - 1, FuInType )
          s.recv_in[s.in1_idx].rdy @= b1( 1 )

      for j in range( num_outports ):
        s.send_out[j].en @= s.recv_opt.en

      if s.recv_opt.msg.ctrl == OPT_MUL:
        s.send_out[0].msg @= s.recv_in[s.in0_idx].msg * s.recv_in[s.in1_idx].msg
        if s.recv_opt.en & ( (s.recv_in_count[s.in0_idx] == 0) | \
                             (s.recv_in_count[s.in1_idx] == 0) ):
          s.recv_in[s.in0_idx].rdy @= b1( 0 )
          s.recv_in[s.in1_idx].rdy @= b1( 0 )

      else:
        for j in range( num_outports ):
          s.send_out[j].en @= b1( 0 )

      # if s.recv_opt.msg.predicate == b1( 1 ):
      #   s.send_out[0].msg.predicate = s.send_out[0].msg.predicate


  def line_trace( s ):
    opt_str = " #"
    if s.recv_opt.en:
      opt_str = OPT_SYMBOL_DICT[s.recv_opt.msg.ctrl]
    out_str = ",".join([str(x.msg) for x in s.send_out])
    recv_str = ",".join([str(x.msg) for x in s.recv_in])
    return f'[recv: {recv_str}] {opt_str}(P{s.recv_opt.msg.predicate}) (const_reg: {s.recv_const.msg}) ] = [out: {out_str}] (s.recv_opt.rdy: {s.recv_opt.rdy}, {OPT_SYMBOL_DICT[s.recv_opt.msg.ctrl]}, recv_opt.en: {s.recv_opt.en}, send[0].en: {s.send_out[0].en}) '
