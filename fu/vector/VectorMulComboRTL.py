"""
==========================================================================
VectorMulCombRTL.py
==========================================================================
Multiple parallelly combined multipliers to enable vectorization.
The result is same for both multi-FU and combo.
The vectorized Mul works at different vectorization granularities.

Author : Cheng Tan
  Date : April 17, 2022

"""

from pymtl3             import *
from pymtl3.stdlib.ifcs import SendIfcRTL, RecvIfcRTL
from .VectorMulRTL      import VectorMulRTL
from ...lib.opt_type    import *

class VectorMulComboRTL( Component ):

  def construct( s, DataType, PredicateType, CtrlType,
                 num_inports, num_outports, data_mem_size,
                 num_lanes = 4, data_bandwidth = 64 ):

    # Constants
    assert(data_bandwidth % num_lanes == 0)
    # currently only support 4 due to the shift logic
    assert(num_lanes % 4 == 0)
    s.const_zero = DataType(0, 0)
    num_entries  = 2
    CountType    = mk_bits( clog2( num_entries + 1 ) )
    # By default 16-bit indicates both input and output. For a Mul,
    # if output is no longer than 16-bit, it means the
    # input is no longer than 8-bit. Here, the sub_bw is by default
    # 4, which will be times by 2 to make it 8-bit to compensate
    # the longer output in the subFU.
    sub_bw       = data_bandwidth // num_lanes
    sub_bw_2     = 2 * data_bandwidth // num_lanes
    sub_bw_3     = 3 * data_bandwidth // num_lanes
    sub_bw_4     = 4 * data_bandwidth // num_lanes

    # Interface
    s.recv_in        = [ RecvIfcRTL( DataType ) for _ in range( num_inports ) ]
    s.recv_in_count  = [ InPort( CountType ) for _ in range( num_inports ) ]
    s.recv_const     = RecvIfcRTL( DataType )
    s.recv_predicate = RecvIfcRTL( PredicateType )
    s.recv_opt       = RecvIfcRTL( CtrlType )
    s.send_out       = [ SendIfcRTL( DataType ) for _ in range( num_outports ) ]
    TempDataType     = mk_bits( data_bandwidth )
    s.temp_result    = [ Wire( TempDataType ) for _ in range( num_lanes ) ]

    # Components
    s.Fu = [ VectorMulRTL( sub_bw, CtrlType, 4, 2, data_mem_size )
             for _ in range( num_lanes ) ]

    # Redundant interfaces for MemUnit
    s.initial_carry_in  = InPort( b1 )
    s.initial_carry_out = OutPort( b1 )
    AddrType         = mk_bits( clog2( data_mem_size ) )
    s.to_mem_raddr   = SendIfcRTL( AddrType )
    s.from_mem_rdata = RecvIfcRTL( DataType )
    s.to_mem_waddr   = SendIfcRTL( AddrType )
    s.to_mem_wdata   = SendIfcRTL( DataType )


    @s.update
    def update_input_output():

      s.send_out[0].en = s.recv_in[0].en and\
                         s.recv_in[1].en and\
                         s.recv_opt.en

      if s.recv_opt.msg.ctrl == OPT_VEC_MUL:

        s.send_out[0].msg.payload[0:data_bandwidth] = TempDataType( 0 )

        # Connection: split into vectorized FUs
        s.Fu[0].recv_in[0].msg[0:sub_bw] = s.recv_in[0].msg.payload[0:sub_bw]
        s.Fu[0].recv_in[1].msg[0:sub_bw] = s.recv_in[1].msg.payload[0:sub_bw]
        s.Fu[1].recv_in[0].msg[0:sub_bw] = s.recv_in[0].msg.payload[sub_bw:sub_bw_2]
        s.Fu[1].recv_in[1].msg[0:sub_bw] = s.recv_in[1].msg.payload[sub_bw:sub_bw_2]
        s.Fu[2].recv_in[0].msg[0:sub_bw] = s.recv_in[0].msg.payload[sub_bw_2:sub_bw_3]
        s.Fu[2].recv_in[1].msg[0:sub_bw] = s.recv_in[1].msg.payload[sub_bw_2:sub_bw_3]
        s.Fu[3].recv_in[0].msg[0:sub_bw] = s.recv_in[0].msg.payload[sub_bw_3:sub_bw_4]
        s.Fu[3].recv_in[1].msg[0:sub_bw] = s.recv_in[1].msg.payload[sub_bw_3:sub_bw_4]

        for i in range( num_lanes ):

          s.temp_result[i] = TempDataType( 0 )
          s.temp_result[i][0:sub_bw_2] = s.Fu[i].send_out[0].msg[0:sub_bw_2]
  
          s.send_out[0].msg.payload[0:data_bandwidth] = s.send_out[0].msg.payload[0:data_bandwidth] + (s.temp_result[i] << (sub_bw * i));
          # s.send_out[0].msg.payload[sub_bw*i:sub_bw*(i+1)] = s.Fu[i].send_out[0].msg[0:sub_bw];

      elif s.recv_opt.msg.ctrl == OPT_MUL: # with highest precision

        s.Fu[0].recv_in[0].msg[0:sub_bw] = s.recv_in[0].msg.payload[0:sub_bw]
        s.Fu[0].recv_in[1].msg[0:sub_bw] = s.recv_in[1].msg.payload[0:sub_bw]
        s.Fu[1].recv_in[0].msg[0:sub_bw] = s.recv_in[0].msg.payload[0:sub_bw]
        s.Fu[1].recv_in[1].msg[0:sub_bw] = s.recv_in[1].msg.payload[sub_bw:sub_bw_2] 
        s.Fu[2].recv_in[0].msg[0:sub_bw] = s.recv_in[0].msg.payload[sub_bw:sub_bw_2] 
        s.Fu[2].recv_in[1].msg[0:sub_bw] = s.recv_in[1].msg.payload[0:sub_bw]
        s.Fu[3].recv_in[0].msg[0:sub_bw] = s.recv_in[0].msg.payload[sub_bw:sub_bw_2] 
        s.Fu[3].recv_in[1].msg[0:sub_bw] = s.recv_in[1].msg.payload[sub_bw:sub_bw_2] 
    
        for i in range( num_lanes ):
          s.temp_result[i] = TempDataType( 0 )
          s.temp_result[i][0:sub_bw_2] = s.Fu[i].send_out[0].msg[0:sub_bw_2]
  
        s.send_out[0].msg.payload[0:data_bandwidth] = s.temp_result[0] + (s.temp_result[1] << sub_bw) + (s.temp_result[2] << sub_bw) + (s.temp_result[3] << (sub_bw*2))

      else:
        for j in range( num_outports ):
          s.send_out[j].en = b1( 0 )


    @s.update
    def update_signal():
      s.recv_in[0].rdy  = s.send_out[0].rdy
      s.recv_in[1].rdy  = s.send_out[0].rdy

      for i in range( num_lanes ):
        s.Fu[i].recv_opt.en = s.recv_opt.en

        # Note that the predication for a combined FU should be identical/shareable,
        # which means the computation in different basic block cannot be combined.
        # s.Fu[i].recv_opt.msg.predicate = s.recv_opt.msg.predicate

        # Connect count
        s.Fu[i].recv_in_count[0] = s.recv_in_count[0]
        s.Fu[i].recv_in_count[1] = s.recv_in_count[1]

      s.recv_opt.rdy    = s.send_out[0].rdy

    FuInType = mk_bits( clog2( num_inports + 1 ) )

    @s.update
    def update_opt():

      for i in range( num_lanes ):
        s.Fu[i].recv_opt.msg.fu_in[0] = FuInType(1)
        s.Fu[i].recv_opt.msg.fu_in[1] = FuInType(2)

      s.recv_predicate.rdy = b1( 0 )
      if s.recv_opt.msg.predicate == b1( 1 ):
        s.recv_predicate.rdy = b1( 1 )

      if s.recv_opt.msg.ctrl == OPT_VEC_MUL or\
         s.recv_opt.msg.ctrl == OPT_MUL:
        for i in range( num_lanes ):
          s.Fu[i].recv_opt.msg.ctrl = OPT_MUL
        s.send_out[0].msg.predicate = s.recv_in[0].msg.predicate and s.recv_in[1].msg.predicate

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
    return str(s.recv_in[0].msg) + OPT_SYMBOL_DICT[s.recv_opt.msg.ctrl] + str(s.recv_in[1].msg) + " -> " + str(s.send_out[0].msg)
    # return s.Fu[0].line_trace() + " ; " + s.Fu[1].line_trace() + " ; " +\
    #       s.Fu[2].line_trace() + " ; " + s.Fu[3].line_trace() + " ; " +\
    #       s.Fu[4].line_trace() + " ; " + s.Fu[5].line_trace() + " ; " +\
    #       s.Fu[6].line_trace() + " ; " + s.Fu[7].line_trace()
