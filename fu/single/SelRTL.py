"""
==========================================================================
SelRTL.py
==========================================================================
Functional unit Select for CGRA tile.

Author : Cheng Tan
  Date : May 23, 2020
"""


from pymtl3 import *
from ...lib.basic.en_rdy.ifcs import SendIfcRTL, RecvIfcRTL
from ...lib.opt_type import *


class SelRTL( Component ):

  def construct( s, DataType, PredicateType, CtrlType,
                 num_inports, num_outports, data_mem_size=4 ):

    # Constant
    AddrType         = mk_bits( clog2( data_mem_size ) )
    s.const_zero     = DataType(0, 0)
    s.true           = DataType(1, 1)
    FuInType         = mk_bits( clog2( num_inports + 1 ) )
    num_entries      = 2
    CountType        = mk_bits( clog2( num_entries + 1 ) )

    # Interface
    s.recv_in        = [ RecvIfcRTL( DataType ) for _ in range( num_inports ) ]
    s.recv_in_count  = [ InPort( CountType ) for _ in range( num_inports ) ]
    s.recv_predicate = RecvIfcRTL( PredicateType )
    s.recv_const     = RecvIfcRTL( DataType )
    s.recv_opt       = RecvIfcRTL( CtrlType )
    s.send_out       = [ SendIfcRTL( DataType ) for _ in range( num_outports ) ]

    # Redundant interfaces for MemUnit
    s.to_mem_raddr   = SendIfcRTL( AddrType )
    s.from_mem_rdata = RecvIfcRTL( DataType )
    s.to_mem_waddr   = SendIfcRTL( AddrType )
    s.to_mem_wdata   = SendIfcRTL( DataType )
    # s.initial_carry_in  = InPort( b1 )
    # s.initial_carry_out = OutPort( b1 )

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

    # Components
    s.recv_rdy_vector = Wire( num_outports )

    @update
    def update_mem():
      s.to_mem_waddr.en    @= b1( 0 )
      s.to_mem_wdata.en    @= b1( 0 )
      s.to_mem_wdata.msg   @= s.const_zero
      s.to_mem_waddr.msg   @= AddrType( 0 )
      s.to_mem_raddr.msg   @= AddrType( 0 )
      s.to_mem_raddr.en    @= b1( 0 )
      s.from_mem_rdata.rdy @= b1( 0 )

    # TODO: declare in0 in1 in2 as wires
    @update
    def comb_logic():

      # For pick input register, Selector needs at least 3 inputs
      s.in0 @= FuInType( 0 )
      s.in1 @= FuInType( 0 )
      s.in2 @= FuInType( 0 )
      for i in range( num_inports ):
        s.recv_in[i].rdy @= b1( 0 )

      s.recv_predicate.rdy @= b1( 0 )
      for i in range( num_outports ):
        s.send_out[i].en  @= 0
        s.send_out[i].msg @= DataType()

      if s.recv_opt.en:
        if s.recv_opt.msg.fu_in[0] != FuInType( 0 ):
          s.in0 @= s.recv_opt.msg.fu_in[0] - FuInType( 1 )
          s.recv_in[s.in0_idx].rdy @= b1( 1 )
        if s.recv_opt.msg.fu_in[1] != FuInType( 0 ):
          s.in1 @= s.recv_opt.msg.fu_in[1] - FuInType( 1 )
          s.recv_in[s.in1_idx].rdy @= b1( 1 )
        if s.recv_opt.msg.fu_in[2] != FuInType( 0 ):
          s.in2 @= s.recv_opt.msg.fu_in[2] - FuInType( 1 )
          s.recv_in[s.in2_idx].rdy @= b1( 1 )
        if s.recv_opt.msg.predicate == b1( 1 ):
          s.recv_predicate.rdy @= b1( 1 )

      for j in range( num_outports ):
        # s.recv_const.rdy @= s.send_out[j].rdy | s.recv_const.rdy
        # s.recv_opt.rdy @= s.send_out[j].rdy | s.recv_opt.rdy
        s.recv_rdy_vector[j] @= s.send_out[j].rdy
      s.recv_const.rdy @= reduce_or( s.recv_rdy_vector )
      s.recv_opt.rdy   @= reduce_or( s.recv_rdy_vector )

      for j in range( num_outports ):
        s.send_out[j].en @= s.recv_opt.en
      if s.recv_opt.msg.ctrl == OPT_SEL:
        if s.recv_in[s.in0_idx].msg.payload == s.true.payload:
          s.send_out[0].msg @= s.recv_in[s.in1_idx].msg
        else:
          s.send_out[0].msg @= s.recv_in[s.in2_idx].msg
        if s.recv_opt.en & ( (s.recv_in_count[s.in0_idx] == 0) | \
                             (s.recv_in_count[s.in1_idx] == 0) | \
                             (s.recv_in_count[s.in2_idx] == 0) ):
          s.recv_in[s.in0_idx].rdy @= b1( 0 )
          s.recv_in[s.in1_idx].rdy @= b1( 0 )
          s.recv_in[s.in2_idx].rdy @= b1( 0 )
          s.send_out[0].msg.predicate @= b1( 0 )
      else:
        for j in range( num_outports ):
          s.send_out[j].en @= b1( 0 )

      if s.recv_opt.msg.predicate == b1( 1 ):
        s.send_out[0].msg.predicate @= s.send_out[0].msg.predicate & \
                                       s.recv_predicate.msg.predicate

  def line_trace( s ):
    opt_str = " #"
    if s.recv_opt.en:
      opt_str = OPT_SYMBOL_DICT[s.recv_opt.msg.ctrl]
    out_str = ",".join([str(x.msg) for x in s.send_out])
    recv_str = ",".join([str(x.msg) for x in s.recv_in])
    return f'[recv: {recv_str}] {opt_str}(P{s.recv_opt.msg.predicate}) (const_reg: {s.recv_const.msg}, predicate_reg: {s.recv_predicate.msg}) ] = [out: {out_str}] (s.recv_opt.rdy: {s.recv_opt.rdy}, {OPT_SYMBOL_DICT[s.recv_opt.msg.ctrl]}, send[0].en: {s.send_out[0].en}) '
