"""
==========================================================================
RetRTL.py
==========================================================================
Functional unit Ret as a CGRA tile.

Author : Cheng Tan
  Date : September 21, 2021
"""


from pymtl3 import *
from ..basic.Fu import Fu
from ...lib.basic.en_rdy.ifcs import SendIfcRTL, RecvIfcRTL
from ...lib.opt_type import *


class RetRTL( Fu ):

  def construct( s, DataType, PredicateType, CtrlType,
                 num_inports, num_outports, data_mem_size ):

    super( RetRTL, s ).construct( DataType, PredicateType, CtrlType,
                                     num_inports, num_outports, data_mem_size )

    FuInType    = mk_bits( clog2( num_inports + 1 ) )
    num_entries = 2
    CountType   = mk_bits( clog2( num_entries + 1 ) )

    idx_nbits = clog2( num_inports )

    s.in0     = Wire( FuInType )
    s.in0_idx = Wire( idx_nbits )

    s.in0_idx //= s.in0[0:idx_nbits]
    s.send_out_predicate = Wire( 1 )

    # TODO: declare in0 as wire
    @update
    def comb_logic():

      # For pick input register
      s.in0 @= 0
      for i in range( num_inports ):
        s.recv_in[i].rdy @= b1( 0 )

      s.recv_predicate.rdy @= b1( 0 )
      s.send_out_predicate @= b1( 0 )

      for j in range( num_outports ):
        s.send_out[j].en  @= s.recv_opt.en
        s.send_out[j].msg @= DataType()

      if s.recv_opt.en:
        if s.recv_opt.msg.fu_in[0] != FuInType( 0 ):
          s.in0 @= s.recv_opt.msg.fu_in[0] - FuInType( 1 )
          s.recv_in[s.in0_idx].rdy @= b1( 1 )

        if s.recv_opt.msg.predicate == b1( 1 ):
          s.recv_predicate.rdy @= b1( 1 )

      if s.recv_opt.msg.ctrl == OPT_RET:
        # Branch is only used to set predication rather than delivering value.
        #                             payload,                          predicate, bypass,  delay
        s.send_out[0].msg @= DataType(s.recv_in[s.in0_idx].msg.payload, b1(0),     b1(0),   b1(0))
        if s.recv_in[s.in0_idx].msg.predicate == b1( 0 ):#s.const_zero.payload:
          s.send_out_predicate @= 0
        else:
          s.send_out_predicate @= 1

      else:
        for j in range( num_outports ):
          s.send_out[j].en @= b1( 0 )

      if s.recv_opt.msg.predicate == b1( 1 ):
        s.send_out[0].msg.predicate @= s.send_out_predicate & \
                                       s.recv_predicate.msg.predicate


  def line_trace( s ):
    opt_str = " #"
    if s.recv_opt.en:
      opt_str = OPT_SYMBOL_DICT[s.recv_opt.msg.ctrl]
    out_str = ",".join([str(x.msg) for x in s.send_out])
    recv_str = ",".join([str(x.msg) for x in s.recv_in])
    return f'[recv: {recv_str}] {opt_str}(P{s.recv_opt.msg.predicate}) (const_reg: {s.recv_const.msg}, predicate_reg: {s.recv_predicate.msg}) ] = [out: {out_str}] (s.recv_opt.rdy: {s.recv_opt.rdy}, {OPT_SYMBOL_DICT[s.recv_opt.msg.ctrl]}, send[0].en: {s.send_out[0].en}) '
