"""
==========================================================================
VectorAdderCombRTL.py
==========================================================================
Multiple parallelly combined adders to enable vectorization.
The result is same for both multi-FU and combo. The vectorized
addition is still useful for a[0:3]++ (i.e., vec_add_inc) and
a[0:3]+b (i.e., vec_add_const) at different vectorization
granularities.

Author : Cheng Tan
  Date : March 28, 2022

"""

from pymtl3             import *
from pymtl3.stdlib.ifcs import SendIfcRTL, RecvIfcRTL
from .VectorAdderRTL    import VectorAdderRTL
from ...lib.opt_type    import *

class VectorAdderComboRTL( Component ):

  def construct( s, DataType, PredicateType, CtrlType,
                 num_inports, num_outports, data_mem_size,
                 vector_factor = 4, data_bandwidth = 16 ):

    # Constants
    assert(data_bandwidth % vector_factor == 0)
    sub_bw       = data_bandwidth // vector_factor
    num_entries  = 4
    CountType    = mk_bits( clog2( num_entries + 1 ) )

    # Interface
    s.recv_in        = [ RecvIfcRTL( DataType ) for _ in range( num_inports ) ]
    s.recv_in_count  = [ InPort( CountType ) for _ in range( num_inports ) ]
    s.recv_const     = RecvIfcRTL( DataType )
    s.recv_predicate = RecvIfcRTL( PredicateType )
    s.recv_opt       = RecvIfcRTL( CtrlType )
    s.send_out       = [ SendIfcRTL( DataType ) for _ in range( num_outports ) ]
    s.initial_carry_in  = InPort( b1 )
    s.initial_carry_out = OutPort( b1 )

    # Components
    s.Fu = [ VectorAdderRTL( sub_bw, CtrlType, 2, 1, data_mem_size )
             for _ in range( vector_factor ) ]

    # Connection: for carry-in/out
    s.Fu[0].carry_in = s.initial_carry_in # b1( 0 )
    for i in range( 1, vector_factor ):
      s.Fu[i].carry_in //= s.Fu[i-1].carry_out
    s.initial_carry_out //= s.Fu[vector_factor-1].carry_out

    # Connection: split into vectorized FUs
    for i in range( vector_factor ):
      s.recv_in[0].msg.payload[i*sub_bw:(i+1)*sub_bw] //= s.Fu[i].recv_in[0].msg[0:sub_bw]
      s.recv_in[1].msg.payload[i*sub_bw:(i+1)*sub_bw] //= s.Fu[i].recv_in[1].msg[0:sub_bw]
      s.recv_const.msg.payload[i*sub_bw:(i+1)*sub_bw] //= s.Fu[i].recv_const.msg[0:sub_bw]

      s.Fu[i].send_out[0].msg[0:sub_bw] //= s.send_out[0].msg.payload[i*sub_bw:(i+1)*sub_bw]

    # Redundant interfaces for MemUnit
    AddrType         = mk_bits( clog2( data_mem_size ) )
    s.to_mem_raddr   = SendIfcRTL( AddrType )
    s.from_mem_rdata = RecvIfcRTL( DataType )
    s.to_mem_waddr   = SendIfcRTL( AddrType )
    s.to_mem_wdata   = SendIfcRTL( DataType )

    @s.update
    def update_signal():
      s.recv_in[0].rdy  = s.send_out[0].rdy
      s.recv_in[1].rdy  = s.send_out[0].rdy

      for i in range( vector_factor ):
        s.Fu[i].recv_opt.en = s.recv_opt.en

        # Note that the predication for a combined FU should be identical/shareable,
        # which means the computation in different basic block cannot be combined.
        # s.Fu[i].recv_opt.msg.predicate = s.recv_opt.msg.predicate

        # Connect count
        s.Fu[i].recv_in_count[0] = s.recv_in_count[0]
        s.Fu[i].recv_in_count[1] = s.recv_in_count[1]

      s.recv_opt.rdy    = s.send_out[0].rdy

      s.send_out[0].en  = s.recv_in[0].en   and s.recv_in[1].en   and\
                          s.recv_opt.en

    FuInType = mk_bits( clog2( num_inports + 1 ) )

    @s.update
    def update_opt():

      for i in range( vector_factor ):
        s.Fu[i].recv_opt.msg.fu_in[0] = FuInType(1)
        s.Fu[i].recv_opt.msg.fu_in[1] = FuInType(2)

      s.recv_predicate.rdy = b1( 0 )
      if s.recv_opt.msg.predicate == b1( 1 ):
        s.recv_predicate.rdy = b1( 1 )

      if s.recv_opt.msg.ctrl == OPT_VEC_ADD or\
         s.recv_opt.msg.ctrl == OPT_ADD:
        for i in range( vector_factor ):
          s.Fu[i].recv_opt.msg.ctrl = OPT_ADD
        s.send_out[0].msg.predicate = s.recv_in[0].msg.predicate and s.recv_in[1].msg.predicate

      elif s.recv_opt.msg.ctrl == OPT_VEC_SUB or\
           s.recv_opt.msg.ctrl == OPT_SUB:
        for i in range( vector_factor ):
          s.Fu[i].recv_opt.msg.ctrl = OPT_SUB
        s.send_out[0].msg.predicate = s.recv_in[0].msg.predicate and s.recv_in[1].msg.predicate

      elif s.recv_opt.msg.ctrl == OPT_VEC_ADD_CONST or\
           s.recv_opt.msg.ctrl == OPT_ADD_CONST:
        for i in range( vector_factor ):
          s.Fu[i].recv_opt.msg.ctrl = OPT_ADD_CONST
        s.send_out[0].msg.predicate = s.recv_in[0].msg.predicate

      elif s.recv_opt.msg.ctrl == OPT_VEC_SUB_CONST or\
           s.recv_opt.msg.ctrl == OPT_SUB_CONST:
        for i in range( vector_factor ):
          s.Fu[i].recv_opt.msg.ctrl = OPT_SUB_CONST
        s.send_out[0].msg.predicate = s.recv_in[0].msg.predicate

      if s.recv_opt.msg.ctrl == OPT_VEC_ADD_CONST or\
         s.recv_opt.msg.ctrl == OPT_VEC_SUB_CONST or\
         s.recv_opt.msg.ctrl == OPT_ADD_CONST or\
         s.recv_opt.msg.ctrl == OPT_SUB_CONST:
        s.recv_const.rdy = s.recv_opt.en

  def line_trace( s ):
    return str(s.recv_in[0].msg) + OPT_SYMBOL_DICT[s.recv_opt.msg.ctrl] + str(s.recv_in[1].msg) + " -> " + str(s.send_out[0].msg)
    # return s.Fu[0].line_trace() + " ; " + s.Fu[1].line_trace() + " ; " +\
    #        s.Fu[2].line_trace() + " ; " + s.Fu[3].line_trace()
