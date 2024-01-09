"""
==========================================================================
ALUgenMAC2nd.py
==========================================================================
Floating point add unit.

Author : Yanghui Ou & Ron Jokai
  Date : Jan 6, 2024
"""

from pymtl3                                import *
from ...lib.ifcs                           import SendIfcRTL, RecvIfcRTL
from ...lib.opt_type                       import *
from ..basic.Fu                            import Fu
from ..pymtl3_Ron_fixed.ALUgenMACRTL       import ALUgenMAC

class ALUgenMAC2nd( Fu ):
  def construct( s, DataType, PredicateType, CtrlType,
                 num_inports, num_outports, data_mem_size):
    super( ALUgenMAC2nd, s ).construct( DataType, PredicateType, CtrlType,
                                   num_inports, num_outports,
                                   data_mem_size )

    # Local parameters
    assert DataType.get_field_type( 'payload' ).nbits == 16

    num_entries = 3
    FuInType    = mk_bits( clog2( num_inports + 1 ) )
    CountType   = mk_bits( clog2( num_entries + 1 ) )

    # Components
    s.fALU = ALUgenMAC()
    s.fALU.rhs_2 //= lambda:   0 if s.recv_opt.msg.ctrl == OPT_ADD     else \
                             ( 1 if s.recv_opt.msg.ctrl == OPT_SUB     else \
                             ( 3 if s.recv_opt.msg.ctrl == OPT_LT      else \
                             ( 7 if s.recv_opt.msg.ctrl == OPT_GTE     else \
                             (10 if s.recv_opt.msg.ctrl == OPT_GT      else \
                             (14 if s.recv_opt.msg.ctrl == OPT_LTE     else \
                             (16 if s.recv_opt.msg.ctrl == OPT_MUL     else \
                             (48 if s.recv_opt.msg.ctrl == OPT_MUL_ADD else 0)))))))

    # Wires
    s.in0 = Wire( FuInType )
    s.in1 = Wire( FuInType )
    s.in2 = Wire( FuInType )

    idx_nbits = clog2( num_inports )
    s.in0_idx = Wire( idx_nbits )
    s.in1_idx = Wire( idx_nbits )
    s.in2_idx = Wire( idx_nbits )

    s.in0_idx //= s.in0[0:idx_nbits]
    s.in1_idx //= s.in1[0:idx_nbits]
    s.in2_idx //= s.in2[0:idx_nbits]

    @update
    def comb_logic():

      # For pick input register
      s.in0 @= 0
      s.in1 @= 0
      s.in2 @= 0
      for i in range( num_inports ):
        s.recv_in[i].rdy @= b1( 0 )

      for i in range( num_outports ):
        s.send_out[i].en  @= s.recv_opt.en
        s.send_out[i].msg @= DataType()

      s.recv_predicate.rdy @= b1( 0 )

      if s.recv_opt.en:
        if s.recv_opt.msg.fu_in[0] != 0:
          s.in0 @= zext(s.recv_opt.msg.fu_in[0] - 1, FuInType)
          s.recv_in[s.in0_idx].rdy @= b1( 1 )
        if s.recv_opt.msg.fu_in[1] != 0:
          s.in1 @= zext(s.recv_opt.msg.fu_in[1] - 1, FuInType)
          s.recv_in[s.in1_idx].rdy @= b1( 1 )
        if s.recv_opt.msg.fu_in[2] != 0:
          s.in2 @= zext(s.recv_opt.msg.fu_in[2] - 1, FuInType)
          s.recv_in[s.in2_idx].rdy @= b1( 1 )
        if s.recv_opt.msg.predicate == b1( 1 ):
          s.recv_predicate.rdy @= b1( 1 )

      s.send_out[0].msg.predicate @= s.recv_in[s.in0_idx].msg.predicate & \
                                     s.recv_in[s.in1_idx].msg.predicate & \
                                     s.recv_in[s.in2_idx].msg.predicate

      # TODO RJ Here we need to block predicate propagation for the third port if ctrl != MAC.
      #if s.recv_opt.msg.ctrl == OPT_FADD:
      s.fALU.rhs_0  @= s.recv_in[s.in0_idx].msg.payload
      s.fALU.rhs_1  @= s.recv_in[s.in1_idx].msg.payload
      s.fALU.rhs_1b @= s.recv_in[s.in2_idx].msg.payload
      s.send_out[0].msg.predicate @= s.recv_in[s.in0_idx].msg.predicate & \
                                     s.recv_in[s.in1_idx].msg.predicate & \
                                     s.recv_in[s.in2_idx].msg.predicate
      if s.recv_opt.en & ( (s.recv_in_count[s.in0_idx] == 0) | \
                           (s.recv_in_count[s.in1_idx] == 0) | \
                           (s.recv_in_count[s.in2_idx] == 0) ):
        s.recv_in[s.in0_idx].rdy @= b1( 0 )
        s.recv_in[s.in1_idx].rdy @= b1( 0 )
        s.recv_in[s.in2_idx].rdy @= b1( 0 )
        s.send_out[0].msg.predicate @= b1( 0 )

      #elif s.recv_opt.msg.ctrl == OPT_FADD_CONST:
      #  s.fadd.rhs_0 @= s.recv_in[s.in0_idx].msg.payload
      #  s.fadd.rhs_1 @= s.recv_const.msg.payload
      #  s.send_out[0].msg.predicate @= s.recv_in[s.in0_idx].msg.predicate

      #elif s.recv_opt.msg.ctrl == OPT_FINC:
      #  s.fadd.rhs_0 @= s.recv_in[s.in0_idx].msg.payload
      #  s.fadd.rhs_1 @= s.FLOATING_ONE
      #  s.send_out[0].msg.predicate @= s.recv_in[s.in0_idx].msg.predicate

      #elif s.recv_opt.msg.ctrl == OPT_FSUB:
      #  s.fadd.rhs_0 @= s.recv_in[s.in0_idx].msg.payload
      #  s.fadd.rhs_1 @= s.recv_in[s.in1_idx].msg.payload
      #  s.send_out[0].msg.predicate @= s.recv_in[s.in0_idx].msg.predicate
      #  if s.recv_opt.en & ( (s.recv_in_count[s.in0_idx] == 0) | \
      #                       (s.recv_in_count[s.in1_idx] == 0) ):
      #    s.recv_in[s.in0_idx].rdy @= b1( 0 )
      #    s.recv_in[s.in1_idx].rdy @= b1( 0 )
      #    s.send_out[0].msg.predicate @= b1( 0 )
      #else:
      #  for j in range( num_outports ):
      #    s.send_out[j].en @= b1( 0 )

      if s.recv_opt.msg.predicate == b1( 1 ):
        s.send_out[0].msg.predicate @= s.send_out[0].msg.predicate & \
                                       s.recv_predicate.msg.predicate

      s.send_out[0].msg.payload @= s.fALU.lhs_0

