"""
=========================================================================
Crossbar.py
=========================================================================
Data-driven crossbar. Valid data is sent out only when 

Author : Cheng Tan
  Date : August 26, 2023
"""

from pymtl3 import *
from ..lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ..lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ..lib.opt_type import *

class CrossbarRTL(Component):

  def construct(s, DataType, PredicateType, CtrlType,
                num_inports = 5, num_outports = 5, bypass_point = 4,
                id = 0):

    InType = mk_bits(clog2(num_inports + 1))
    s.bypass_point = bypass_point

    # Interface

    s.recv_opt       = RecvIfcRTL( CtrlType )
    s.recv_data      = [ RecvIfcRTL( DataType ) for _ in range( num_inports  ) ]
    s.send_data      = [ SendIfcRTL( DataType ) for _ in range( num_outports ) ]
    s.send_predicate = SendIfcRTL( PredicateType )

    # TODO: should include position information or not
    # s.pos  = InPort( PositionType )

    s.in_dir         = [ Wire( InType ) for _ in range( num_outports ) ]
    s.in_dir_local   = [ Wire( InType ) for _ in range( num_outports ) ]
    s.out_rdy_vector = Wire( num_outports )
    s.recv_predicate_vector = Wire( num_inports )
    # Used to indicate whether the recv_data could be popped.
    s.recv_blocked_vector = Wire( num_inports )
    # received or sent once but there are still some others pending. So the
    # one already done should not proceed the next to avoid overwriting.
    s.recv_but_block_by_others = [ Wire( b1 ) for _ in range( num_inports ) ]
    s.send_but_block_by_others = [ Wire( b1 ) for _ in range( num_outports ) ]

    # Routing logic
    @update
    def update_signal():
      s.out_rdy_vector        @= 0
      s.recv_predicate_vector @= 0
      s.send_predicate.val    @= 0
      s.recv_blocked_vector   @= 0
      s.send_predicate.msg    @= PredicateType()
      for i in range( num_inports ):
        s.recv_data[i].rdy @= 0
      for i in range( num_outports ):
        s.in_dir[i]        @= 0
        s.in_dir_local[i]  @= 0
        s.send_data[i].val @= 0
        s.send_data[i].msg @= DataType()

      # For predication register update. 'predicate' and 'predicate_in' no need
      # to be active at the same time. Specifically, the 'predicate' is for
      # the operation at the current cycle while the 'predicate_in' accumulates
      # the predicate and pushes into the predicate register that will be used
      # in the future.
      if s.recv_opt.msg.predicate:
        s.send_predicate.msg @= PredicateType( b1(0), b1(0) )

      if s.recv_opt.msg.ctrl != OPT_START:
        for i in range( num_inports ):
          # Set predicate once the recv_data is stable (i.e., en == true).
          if s.recv_opt.msg.predicate_in[i] & s.recv_data[i].val:
            s.send_predicate.val @= b1( 1 )
            s.send_predicate.msg.payload @= b1( 1 )
            s.recv_predicate_vector[i] @= s.recv_data[i].msg.predicate

        for i in range( num_inports ):
          s.recv_blocked_vector[i] @= (s.recv_data[i].msg.delay == 1)

          # The predicate_in might not be issued to other ports on the xbar,
          # but it also needs to be drained from the recv_data, otherwise,
          # it would block the recv_data channel/buffer.
          if s.recv_opt.msg.predicate_in[i] & \
             ~s.recv_blocked_vector[i] & \
             ~s.recv_but_block_by_others[i]:
            s.recv_data[i].rdy @= 1

        for i in range( num_outports ):
          s.out_rdy_vector[i] @= s.send_data[i].rdy
          s.in_dir[i]  @= s.recv_opt.msg.outport[i]
          if s.in_dir[i] > 0:
            s.send_data[i].msg.delay @= s.recv_data[s.in_dir_local[i]].msg.delay
          else:
            s.out_rdy_vector[i] @= 1

        for i in range( num_outports ):
          s.in_dir[i]  @= s.recv_opt.msg.outport[i]
          if (s.in_dir[i] > 0) & s.send_data[i].rdy:
            s.in_dir_local[i] @= s.in_dir[i] - 1

            s.recv_data[s.in_dir_local[i]].rdy @= \
                    s.send_data[i].rdy & \
                    ~s.recv_blocked_vector[s.in_dir_local[i]] & \
                    ~s.recv_but_block_by_others[s.in_dir_local[i]] & \
                    ~s.send_but_block_by_others[i]

            s.send_data[i].val @= s.recv_data[s.in_dir_local[i]].val
            if s.send_data[i].val & s.recv_data[s.in_dir_local[i]].rdy:
              s.send_data[i].msg.payload   @= s.recv_data[s.in_dir_local[i]].msg.payload
              s.send_data[i].msg.predicate @= s.recv_data[s.in_dir_local[i]].msg.predicate
              s.send_data[i].msg.bypass    @= s.recv_data[s.in_dir_local[i]].msg.bypass
              s.send_data[i].msg.delay     @= 0
              # The generate one can be send to other tile without buffering,
              # but buffering is still needed when 'other tile' is yourself
              # (i.e., generating output to self input). Here we avoid self
              # connecting by checking whether the inport belongs to FU and
              # outport be towards to remote tiles to eliminate combinational
              # loop.
              if (s.in_dir_local[i] >= s.bypass_point) & (i < s.bypass_point):
                s.send_data[i].msg.bypass @= b1( 1 )
              else:
                s.send_data[i].msg.bypass @= b1( 0 )
          else:
            s.send_data[i].val @= b1( 0 )

      else:
        for i in range( num_outports ):
          s.send_data[i].val @= b1( 0 )
      s.recv_opt.rdy @= reduce_and( s.out_rdy_vector ) & ~reduce_or( s.recv_blocked_vector )
      s.send_predicate.msg.predicate @= reduce_or( s.recv_predicate_vector )

    @update_ff
    def update_blocked_by_others():
      for i in range( num_inports ):
        if reduce_or( s.recv_blocked_vector ) & ~s.recv_blocked_vector[i]:
          s.recv_but_block_by_others[i] <<= 1
        elif ~reduce_or( s.recv_blocked_vector ):
          s.recv_but_block_by_others[i] <<= 0

      for i in range( num_outports ):
        if ~reduce_and( s.out_rdy_vector ) & s.out_rdy_vector[i]:
          s.send_but_block_by_others[i] <<= 1
        elif reduce_and( s.out_rdy_vector ):
          s.send_but_block_by_others[i] <<= 0

  # Line trace
  def line_trace( s ):
    recv_str = "|".join([ str(x.msg) for x in s.recv_data ])
    out_str  = "|".join([ str(x.msg) for x in s.send_data ])
    pred_str = str( s.send_predicate.msg )
    return f"{recv_str} [{s.recv_opt.msg}] {out_str}-xbar.pred:{pred_str}"

