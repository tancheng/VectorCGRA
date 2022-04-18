"""
==========================================================================
VectorAdderRTL.py
==========================================================================
Vectorized adder to support SIMD addition in different granularities.
This basic adder is different from the scalar one:
    1. Need to handle the carry in/out value.
    2. Can directly perform on bits rather than CGRADataType.

Author : Cheng Tan
  Date : March 27, 2022

"""

from pymtl3             import *
from pymtl3.stdlib.ifcs import SendIfcRTL, RecvIfcRTL
from ...lib.opt_type    import *

class VectorAdderRTL( Component ):

  def construct( s, bw, CtrlType,
                 num_inports, num_outports, data_mem_size ):

    # DataType should be 1-bit more due to the carry-out
    DataType    = mk_bits( bw+1 )
    num_entries = 4
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
    s.carry_in       = InPort( b1 )
    s.carry_out      = OutPort( b1 )
    s.carry_in_temp  = Wire( DataType )


    @s.update
    def update_signal():
      for j in range( num_outports ):
        s.recv_const.rdy = s.send_out[j].rdy or s.recv_const.rdy
        s.recv_opt.rdy = s.send_out[j].rdy or s.recv_opt.rdy

    @s.update
    def comb_logic():

      # For pick input register
      in0 = FuInType( 0 )
      in1 = FuInType( 0 )
      for i in range( num_inports ):
        s.recv_in[i].rdy = b1( 0 )

      s.carry_in_temp[0] = s.carry_in
      if s.recv_opt.en:
        if s.recv_opt.msg.fu_in[0] != FuInType( 0 ):
          in0 = s.recv_opt.msg.fu_in[0] - FuInType( 1 )
          s.recv_in[in0].rdy = b1( 1 )
        if s.recv_opt.msg.fu_in[1] != FuInType( 0 ):
          in1 = s.recv_opt.msg.fu_in[1] - FuInType( 1 )
          s.recv_in[in1].rdy = b1( 1 )


      for j in range( num_outports ):
        s.send_out[j].en = s.recv_opt.en

      if s.recv_opt.msg.ctrl == OPT_ADD:
        s.send_out[0].msg = s.recv_in[in0].msg + s.recv_in[in1].msg + s.carry_in_temp
        if s.recv_opt.en and ( s.recv_in_count[in0] == CountType( 0 ) or\
                               s.recv_in_count[in1] == CountType( 0 ) ):
          s.recv_in[in0].rdy = b1( 0 )
          s.recv_in[in1].rdy = b1( 0 )

      elif s.recv_opt.msg.ctrl == OPT_ADD_CONST:
        s.send_out[0].msg = s.recv_in[in0].msg + s.recv_const.msg + s.carry_in_temp

      elif s.recv_opt.msg.ctrl == OPT_INC:
        s.send_out[0].msg = s.recv_in[in0].msg + s.const_one

      elif s.recv_opt.msg.ctrl == OPT_SUB:
        s.send_out[0].msg = s.recv_in[in0].msg - s.recv_in[in1].msg - s.carry_in_temp
        if s.recv_opt.en and ( s.recv_in_count[in0] == CountType( 0 ) or\
                               s.recv_in_count[in1] == CountType( 0 ) ):
          s.recv_in[in0].rdy = b1( 0 )
          s.recv_in[in1].rdy = b1( 0 )

      elif s.recv_opt.msg.ctrl == OPT_SUB_CONST:
        s.send_out[0].msg = s.recv_in[in0].msg - s.recv_const.msg - s.carry_in_temp

      elif s.recv_opt.msg.ctrl == OPT_PAS:
        s.send_out[0].msg = s.recv_in[in0].msg

      else:
        for j in range( num_outports ):
          s.send_out[j].en = b1( 0 )

      s.carry_out = s.send_out[0].msg[bw:bw+1]

      # if s.recv_opt.msg.predicate == b1( 1 ):
      #   s.send_out[0].msg.predicate = s.send_out[0].msg.predicate
                                      

  def line_trace( s ):
    opt_str = " #"
    if s.recv_opt.en:
      opt_str = OPT_SYMBOL_DICT[s.recv_opt.msg.ctrl]
    out_str = ",".join([str(x.msg) for x in s.send_out])
    recv_str = ",".join([str(x.msg) for x in s.recv_in])
    return f'[recv: {recv_str}] {opt_str}(P{s.recv_opt.msg.predicate}) (const_reg: {s.recv_const.msg}) ] = [out: {out_str}] (s.recv_opt.rdy: {s.recv_opt.rdy}, {OPT_SYMBOL_DICT[s.recv_opt.msg.ctrl]}, recv_opt.en: {s.recv_opt.en}, send[0].en: {s.send_out[0].en}) '
