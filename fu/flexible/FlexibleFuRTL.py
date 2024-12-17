"""
==========================================================================
FlexibleFuRTL.py
==========================================================================
A flexible functional unit whose functionality can be parameterized.

Author : Cheng Tan
  Date : Dec 24, 2019

"""
import json

from py_markdown_table.markdown_table import markdown_table
from pymtl3 import *

from tile.TileRTL_constant import tile_port_direction_dict
from ...fu.single.MemUnitRTL import MemUnitRTL
from ...fu.single.AdderRTL  import AdderRTL
from ...lib.basic.en_rdy.ifcs import SendIfcRTL, RecvIfcRTL
from ...lib.opt_type import *


class FlexibleFuRTL( Component ):

  def construct( s, DataType, PredicateType, CtrlType,
                 num_inports, num_outports, data_mem_size, FuList ):#=[MemUnitRTL,AdderRTL] ):

    # Constant
    s.fu_list_size = len( FuList )
    num_entries = 2
    CountType = mk_bits( clog2( num_entries + 1 ) )
    AddrType = mk_bits( clog2( data_mem_size ) )

    # Interface
    s.recv_in        = [ RecvIfcRTL( DataType ) for _ in range( num_inports  ) ]
    s.recv_in_count  = [ InPort( CountType ) for _ in range( num_inports  ) ]
    s.recv_predicate = RecvIfcRTL( PredicateType )
    s.recv_const     = RecvIfcRTL( DataType )
    s.recv_opt       = RecvIfcRTL( CtrlType )
    s.send_out       = [ SendIfcRTL( DataType ) for _ in range( num_outports ) ]

    s.to_mem_raddr   = [ SendIfcRTL( AddrType ) for _ in range( s.fu_list_size ) ]
    s.from_mem_rdata = [ RecvIfcRTL( DataType ) for _ in range( s.fu_list_size ) ]
    s.to_mem_waddr   = [ SendIfcRTL( AddrType ) for _ in range( s.fu_list_size ) ]
    s.to_mem_wdata   = [ SendIfcRTL( DataType ) for _ in range( s.fu_list_size ) ]

    # Components
    s.fu = [ FuList[i]( DataType, PredicateType, CtrlType, num_inports, num_outports,
                        data_mem_size ) for i in range( s.fu_list_size ) ]

    s.fu_recv_const_rdy_vector     = Wire( s.fu_list_size )
    s.fu_recv_predicate_rdy_vector = Wire( s.fu_list_size )
    s.fu_recv_opt_rdy_vector       = Wire( s.fu_list_size )
    s.fu_recv_in_rdy_vector        = [ Wire( s.fu_list_size ) for i in range( num_inports ) ]

    # Connection
    for i in range( len( FuList ) ):
      s.to_mem_raddr[i]   //= s.fu[i].to_mem_raddr
      s.from_mem_rdata[i] //= s.fu[i].from_mem_rdata
      s.to_mem_waddr[i]   //= s.fu[i].to_mem_waddr
      s.to_mem_wdata[i]   //= s.fu[i].to_mem_wdata

    @update
    def comb_logic():

      for j in range( num_outports ):
        s.send_out[j].en  @= b1( 0 )
        s.send_out[j].msg @= DataType()

      for i in range( s.fu_list_size ):

        # const connection
        s.fu[i].recv_const.msg @= s.recv_const.msg
        s.fu[i].recv_const.en  @= s.recv_const.en
        # s.recv_const.rdy       @= s.recv_const.rdy | s.fu[i].recv_const.rdy
        s.fu_recv_const_rdy_vector[i] @= s.fu[i].recv_const.rdy

        for j in range( num_inports):
          s.fu[i].recv_in_count[j] @= s.recv_in_count[j]

        # opt connection
        s.fu[i].recv_opt.msg @= s.recv_opt.msg
        s.fu[i].recv_opt.en  @= s.recv_opt.en
        # s.recv_opt.rdy       @= s.fu[i].recv_opt.rdy | s.recv_opt.rdy
        s.fu_recv_opt_rdy_vector[i] @= s.fu[i].recv_opt.rdy

        # Note that the predication for a combined FU should be identical/shareable,
        # which means the computation in different basic block cannot be combined.
        s.fu[i].recv_opt.msg.predicate @= s.recv_opt.msg.predicate
        s.fu[i].recv_predicate.en      @= s.recv_predicate.en
        # s.recv_predicate.rdy           @= s.fu[i].recv_predicate.rdy | s.recv_predicate.rdy
        s.fu_recv_predicate_rdy_vector[i] @= s.fu[i].recv_predicate.rdy
        s.fu[i].recv_predicate.msg     @= s.recv_predicate.msg

        # send_out connection
        for j in range( num_outports ):
          if s.fu[i].send_out[j].en:
            s.send_out[j].msg     @= s.fu[i].send_out[j].msg
            s.send_out[j].en      @= s.fu[i].send_out[j].en
          s.fu[i].send_out[j].rdy @= s.send_out[j].rdy

      s.recv_const.rdy     @= reduce_or( s.fu_recv_const_rdy_vector )
      s.recv_predicate.rdy @= reduce_or( s.fu_recv_predicate_rdy_vector )
      s.recv_opt.rdy       @= reduce_or( s.fu_recv_opt_rdy_vector )

      for j in range( num_inports ):
        s.recv_in[j].rdy @= b1( 0 )

      # recv_in connection
      for port in range( num_inports ):
        for i in range( s.fu_list_size ):
          s.fu[i].recv_in[port].msg @= s.recv_in[port].msg
          s.fu[i].recv_in[port].en  @= s.recv_in[port].en
          # s.recv_in[j].rdy       @= s.fu[i].recv_in[j].rdy | s.recv_in[j].rdy
          s.fu_recv_in_rdy_vector[port][i] @= s.fu[i].recv_in[port].rdy
        s.recv_in[port].rdy @= reduce_or( s.fu_recv_in_rdy_vector[port] )


  def line_trace( s ):
    opt_str = " #"
    if s.recv_opt.en:
      opt_str = OPT_SYMBOL_DICT[s.recv_opt.msg.ctrl]

    out_md = markdown_table([x.msg.__dict__ for x in s.send_out]).set_params(quote=False).get_markdown()

    recv_data = [x.msg.__dict__ for x in s.recv_in]
    recv_list = []
    for idx, data in enumerate(recv_data):
      port_direction = tile_port_direction_dict[idx]
      dict_with_direction = {"port_direction": port_direction}
      dict_with_direction.update(data)
      recv_list.append(dict_with_direction)
    recv_md = markdown_table(recv_list).set_params(quote=False).get_markdown()

    return (f'## class: {s.__class__.__name__}\n'
            f'- recv:'
            f'{recv_md}\n'
            f'- opt ({opt_str}):\n'
            f'  (P{s.recv_opt.msg.predicate})\n'
            f'  const: {str(s.recv_const.msg.__dict__)}\n'
            f'  en: {s.recv_const.en}\n'
            f'===>\n'
            f'- out:'
            f'{out_md}\n'
            f'- recv_opt.rdy: {s.recv_opt.rdy}\n'
            f'- recv_in[0].rdy: {s.recv_in[0].rdy}\n'
            f'- recv_in[1].rdy: {s.recv_in[1].rdy}\n'
            f'- recv_predicate.msg: {str(s.recv_predicate.msg.__dict__)}\n'
            f'- opt: {OPT_SYMBOL_DICT[s.recv_opt.msg.ctrl]}\n'
            f'- recv_opt.en: {s.recv_opt.en}\n'
            f'- send[0].en: {s.send_out[0].en}\n')

