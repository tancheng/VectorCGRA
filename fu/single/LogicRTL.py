"""
==========================================================================
LogicRTL.py
==========================================================================
Functional Unit for logic computation in a CGRA tile.

Author : Cheng Tan
  Date : November 28, 2019

"""

from pymtl3             import *
from ...lib.ifcs import SendIfcRTL, RecvIfcRTL
from ...lib.opt_type    import *
from ..basic.Fu         import Fu

class LogicRTL( Fu ):

  def construct( s, DataType, PredicateType, CtrlType,
                 num_inports, num_outports, data_mem_size ):

    super( LogicRTL, s ).construct( DataType, PredicateType, CtrlType,
                                    num_inports, num_outports, data_mem_size )

    FuInType    = mk_bits( clog2( num_inports + 1 ) )
    num_entries = 2
    CountType   = mk_bits( clog2( num_entries + 1 ) )

    # TODO: declare in0 and in1 as wire
    s.in0 = Wire( FuInType )
    s.in1 = Wire( FuInType )

    idx_nbits = clog2( num_inports )
    s.in0_idx = Wire( idx_nbits )
    s.in1_idx = Wire( idx_nbits )

    s.in0_idx //= s.in0[0:idx_nbits]
    s.in1_idx //= s.in1[0:idx_nbits]

    @update
    def comb_logic():

      # For pick input register
      s.in0 @= 0
      s.in1 @= 0
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

      s.send_out[0].msg.predicate @= s.recv_in[s.in0_idx].msg.predicate & \
                                     s.recv_in[s.in1_idx].msg.predicate
      for j in range( num_outports ):
        s.send_out[j].en @= s.recv_opt.en
      if s.recv_opt.msg.ctrl == OPT_OR:
        s.send_out[0].msg.payload @= s.recv_in[s.in0_idx].msg.payload | s.recv_in[s.in1_idx].msg.payload
      elif s.recv_opt.msg.ctrl == OPT_AND:
        s.send_out[0].msg.payload @= s.recv_in[s.in0_idx].msg.payload & s.recv_in[s.in1_idx].msg.payload
      elif s.recv_opt.msg.ctrl == OPT_NOT:
        s.send_out[0].msg.payload @= ~ s.recv_in[s.in0_idx].msg.payload
      elif s.recv_opt.msg.ctrl == OPT_XOR:
        s.send_out[0].msg.payload @= s.recv_in[s.in0_idx].msg.payload ^ s.recv_in[s.in1_idx].msg.payload
      else:
        for j in range( num_outports ):
          s.send_out[j].en @= b1( 0 )

      if ( (s.recv_opt.msg.ctrl == OPT_OR) | (s.recv_opt.msg.ctrl == OPT_AND) | \
           (s.recv_opt.msg.ctrl == OPT_XOR) ) & s.recv_opt.en & \
           ( (s.recv_in_count[s.in0_idx] == 0) | (s.recv_in_count[s.in1_idx] == 0) ):
        s.recv_in[s.in0_idx].rdy @= b1( 0 )
        s.recv_in[s.in1_idx].rdy @= b1( 0 )
        s.send_out[0].msg.predicate @= b1( 0 )

      if s.recv_opt.msg.predicate == b1( 1 ):
        s.send_out[0].msg.predicate @= s.send_out[0].msg.predicate & \
                                       s.recv_predicate.msg.predicate
