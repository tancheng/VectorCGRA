"""
==========================================================================
VectorAllReduceRTL.py
==========================================================================
AllReduce functional unit.

Author : Cheng Tan
  Date : April 23, 2022

"""

from pymtl3             import *
from pymtl3.stdlib.ifcs import SendIfcRTL, RecvIfcRTL
from ...lib.opt_type    import *

class VectorAllReduceRTL( Component ):

  def construct( s, DataType, PredicateType, CtrlType,
                 num_inports, num_outports, data_mem_size,
                 num_lanes = 4, data_bandwidth = 16 ):

    # Constants
    assert(data_bandwidth % num_lanes == 0)
    # currently only support 4 due to the shift logic
    assert(num_lanes % 4 == 0)
    num_entries  = 4
    CountType    = mk_bits( clog2( num_entries + 1 ) )
    sub_bw       = data_bandwidth // num_lanes
    s.const_zero = DataType(0, 0)

    # Interface
    s.recv_in        = [ RecvIfcRTL( DataType ) for _ in range( num_inports ) ]
    s.recv_in_count  = [ InPort( CountType ) for _ in range( num_inports ) ]
    s.recv_const     = RecvIfcRTL( DataType )
    s.recv_predicate = RecvIfcRTL( PredicateType )
    s.recv_opt       = RecvIfcRTL( CtrlType )
    s.send_out       = [ SendIfcRTL( DataType ) for _ in range( num_outports ) ]
    TempDataType     = mk_bits( data_bandwidth )
    s.temp_result    = [ Wire( TempDataType ) for _ in range( num_lanes ) ]

    # Redundant interfaces for MemUnit
    AddrType         = mk_bits( clog2( data_mem_size ) )
    s.to_mem_raddr   = SendIfcRTL( AddrType )
    s.from_mem_rdata = RecvIfcRTL( DataType )
    s.to_mem_waddr   = SendIfcRTL( AddrType )
    s.to_mem_wdata   = SendIfcRTL( DataType )

    @s.update
    def update_result():
      # Connection: split data into vectorized wires
      for i in range( num_lanes ):
        s.temp_result[i] = TempDataType( 0 )
        s.temp_result[i][0:sub_bw] = s.recv_in[0].msg.payload[i*sub_bw:(i+1)*sub_bw]


      if s.recv_opt.msg.ctrl == OPT_VEC_REDUCE_ADD:
        s.send_out[0].msg.payload[0:data_bandwidth] = TempDataType( 0 )
        for i in range( num_lanes ):
          s.send_out[0].msg.payload[0:data_bandwidth] += s.temp_result[i]
      elif s.recv_opt.msg.ctrl == OPT_VEC_REDUCE_MUL:
        s.send_out[0].msg.payload[0:data_bandwidth] = TempDataType( 1 )
        for i in range( num_lanes ):
          s.send_out[0].msg.payload[0:data_bandwidth] *= s.temp_result[i]

    @s.update
    def update_signal():
      for i in range( num_inports ):
        s.recv_in[i].rdy  = b1( 0 )

      s.recv_in[0].rdy  = s.send_out[0].rdy
      # s.recv_in[1].rdy  = s.send_out[0].rdy
      s.recv_opt.rdy    = s.send_out[0].rdy
      s.send_out[0].en  = s.recv_in[0].en and\
                          s.recv_opt.en

    @s.update
    def update_predicate():
      s.recv_predicate.rdy = b1( 0 )
      if s.recv_opt.msg.predicate == b1( 1 ):
        s.recv_predicate.rdy = b1( 1 )
      if s.recv_opt.msg.ctrl == OPT_VEC_REDUCE_ADD:
        s.send_out[0].msg.predicate = s.recv_in[0].msg.predicate

    @s.update
    def update_mem():
      s.to_mem_waddr.en    = b1( 0 )
      s.to_mem_wdata.en    = b1( 0 )
      s.to_mem_wdata.msg   = s.const_zero
      s.to_mem_waddr.msg   = AddrType( 0 )
      s.to_mem_raddr.msg   = AddrType( 0 )
      s.to_mem_raddr.en    = b1( 0 )
      s.from_mem_rdata.rdy = b1( 0 )

  def line_trace( s ):
    return str(s.recv_in[0].msg) + OPT_SYMBOL_DICT[s.recv_opt.msg.ctrl] + " -> " + str(s.send_out[0].msg)
    # return s.Fu[0].line_trace() + " ; " + s.Fu[1].line_trace() + " ; " +\
    #       s.Fu[2].line_trace() + " ; " + s.Fu[3].line_trace() + " ; " +\
    #       s.Fu[4].line_trace() + " ; " + s.Fu[5].line_trace() + " ; " +\
    #       s.Fu[6].line_trace() + " ; " + s.Fu[7].line_trace()
