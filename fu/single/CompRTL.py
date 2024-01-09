"""
==========================================================================
CompRTL.py
==========================================================================
Functional unit for performing comparison.

Author : Cheng Tan
  Date : December 2, 2019

"""

from pymtl3             import *
from ...lib.ifcs import SendIfcRTL, RecvIfcRTL
from ...lib.opt_type    import *
from ..basic.Fu         import Fu

class CompRTL( Fu ):

  def construct( s, DataType, PredicateType, CtrlType,
                 num_inports, num_outports, data_mem_size ):

    super( CompRTL, s ).construct( DataType, PredicateType, CtrlType,
                                   num_inports, num_outports,
                                   data_mem_size )

    s.const_one  = DataType(1, 0)
    FuInType     = mk_bits( clog2( num_inports + 1 ) )
    num_entries  = 2
    CountType    = mk_bits( clog2( num_entries + 1 ) )

    # data:      s.recv_in[0]
    # reference: s.recv_in[1] (or recv_const)

    # TODO: declare in0 and in1 as wires
    s.in0 = Wire( FuInType )
    s.in1 = Wire( FuInType )

    idx_nbits = clog2( num_inports )
    s.in0_idx = Wire( idx_nbits )
    s.in1_idx = Wire( idx_nbits )

    s.in0_idx //= s.in0[0:idx_nbits]
    s.in1_idx //= s.in1[0:idx_nbits]

    @update
    def read_reg():

      # For pick input register
      s.in0 @= FuInType( 0 )
      s.in1 @= FuInType( 0 )
      for i in range( num_inports ):
        s.recv_in[i].rdy @= b1( 0 )
      s.recv_predicate.rdy @= b1( 0 )
      if s.recv_opt.en:
        if s.recv_opt.msg.fu_in[0] != FuInType( 0 ):
          s.in0 @= s.recv_opt.msg.fu_in[0] - FuInType( 1 )
          s.recv_in[s.in0_idx].rdy @= b1( 1 )
        if s.recv_opt.msg.fu_in[1] != FuInType( 0 ):
          s.in1 @= s.recv_opt.msg.fu_in[1] - FuInType( 1 )
          s.recv_in[s.in1_idx].rdy @= b1( 1 )
        if s.recv_opt.msg.predicate == b1( 1 ):
          s.recv_predicate.rdy @= b1( 1 )

      predicate = s.recv_in[s.in0_idx].msg.predicate & s.recv_in[s.in1_idx].msg.predicate
      s.send_out[0].msg @= s.const_one

      for j in range( num_outports ):
        s.send_out[j].en @= s.recv_opt.en

      if s.recv_opt.msg.ctrl == OPT_EQ:
        if s.recv_in[s.in0_idx].msg.payload == s.recv_in[s.in1_idx].msg.payload:
          s.send_out[0].msg @= s.const_one
          s.send_out[0].msg.predicate @= predicate
        else:
          s.send_out[0].msg @= s.const_zero
          s.send_out[0].msg.predicate @= predicate
        if s.recv_opt.en & ( (s.recv_in_count[s.in0_idx] == 0) | \
                             (s.recv_in_count[s.in1_idx] == 0) ):
          s.recv_in[s.in0_idx].rdy @= b1( 0 )
          s.recv_in[s.in1_idx].rdy @= b1( 0 )
          s.send_out[0].msg.predicate @= b1( 0 )

      elif s.recv_opt.msg.ctrl == OPT_EQ_CONST:
        if s.recv_in[s.in0_idx].msg.payload == s.recv_const.msg.payload:
          s.send_out[0].msg @= s.const_one
          s.send_out[0].msg.predicate @= b1( 1 )
        else:
          s.send_out[0].msg @= s.const_zero
          s.send_out[0].msg.predicate @= b1( 1 )

      elif s.recv_opt.msg.ctrl == OPT_LT:
        if s.recv_in[s.in0_idx].msg.payload < s.recv_in[s.in1_idx].msg.payload:
          s.send_out[0].msg @= s.const_one
          s.send_out[0].msg.predicate @= predicate
        else:
          s.send_out[0].msg @= s.const_zero
          s.send_out[0].msg.predicate @= predicate
        if s.recv_opt.en & ( (s.recv_in_count[s.in0_idx] == 0) | \
                             (s.recv_in_count[s.in1_idx] == 0) ):
          s.recv_in[s.in0_idx].rdy @= b1( 0 )
          s.recv_in[s.in1_idx].rdy @= b1( 0 )

      else:
        for j in range( num_outports ):
          s.send_out[j].en @= b1( 0 )

      # TODO: and -> &
      if s.recv_opt.msg.predicate == b1( 1 ):
        s.send_out[0].msg.predicate @= s.send_out[0].msg.predicate & \
                                       s.recv_predicate.msg.predicate
