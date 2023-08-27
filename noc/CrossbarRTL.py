"""
=========================================================================
Crossbar.py
=========================================================================
Data-driven crossbar. Valid data is sent out only when 

Author : Cheng Tan
  Date : August 26, 2023
"""

from pymtl3 import *

from ..lib.ifcs     import SendIfcRTL, RecvIfcRTL
from ..lib.opt_type import *

class CrossbarRTL( Component ):

  def construct( s, DataType, PredicateType, CtrlType,
                 num_inports=5, num_outports=5, bypass_point=4, id=0 ):

    InType     = mk_bits( clog2( num_inports + 1 ) )
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
    s.recv_blocked_by_others = [ Wire( b1 ) for _ in range( num_inports ) ]
    s.send_blocked_by_others = [ Wire( b1 ) for _ in range( num_outports ) ]

    # Routing logic
    @update
    def update_signal():
      s.out_rdy_vector        @= 0
      s.recv_predicate_vector @= 0
      s.send_predicate.en     @= 0
      s.recv_blocked_vector   @= 0
      s.send_predicate.msg    @= PredicateType()
      for i in range( num_inports ):
        s.recv_data[i].rdy @= 0
      for i in range( num_outports ):
        s.in_dir[i]        @= 0
        s.in_dir_local[i]  @= 0
        s.send_data[i].en  @= 0
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
          if s.recv_opt.msg.predicate_in[i] & s.recv_data[i].en:
            s.send_predicate.en @= b1( 1 )
            s.send_predicate.msg.payload @= b1( 1 )
            s.recv_predicate_vector[i] @= s.recv_data[i].msg.predicate

        for i in range( num_inports ):
          s.recv_blocked_vector[i] @= (s.recv_data[i].msg.delay == 1)

        for i in range( num_outports ):
          s.out_rdy_vector[i] @= s.send_data[i].rdy
          s.in_dir[i]  @= s.recv_opt.msg.outport[i]
          if s.in_dir[i] == 0:
            s.out_rdy_vector[i] @= 1
          else:
            s.send_data[i].msg.delay @= s.recv_data[s.in_dir_local[i]].msg.delay

        for i in range( num_outports ):
          s.in_dir[i]  @= s.recv_opt.msg.outport[i]
          if s.in_dir[i] > 0:
            s.in_dir_local[i] @= s.in_dir[i] - 1
          if (s.in_dir[i] > 0) & s.send_data[i].rdy:
            s.in_dir_local[i] @= s.in_dir[i] - 1
            # s.recv_data[s.in_dir_local[i]].rdy @= \
            #         s.send_data[i].rdy & \
            #         ~reduce_or( s.recv_blocked_vector ) & \
            #         reduce_and( s.out_rdy_vector )

            # s.recv_data[s.in_dir_local[i]].rdy @= \
            #         s.send_data[i].rdy & \
            #         ~s.recv_blocked_by_others[i]

            # s.recv_data[s.in_dir_local[i]].rdy @= \
            #         s.send_data[i].rdy & \
            #         ~s.recv_blocked_vector[s.in_dir_local[i]] & \
            #         ~s.recv_blocked_by_others[s.in_dir_local[i]]

            s.recv_data[s.in_dir_local[i]].rdy @= \
                    s.send_data[i].rdy & \
                    ~s.recv_blocked_vector[s.in_dir_local[i]] & \
                    ~s.recv_blocked_by_others[s.in_dir_local[i]] & \
                    ~s.send_blocked_by_others[i]
            print("check s.send_blocked_by_others[", i, "]: ",
                  s.send_blocked_by_others[i])


            s.send_data[i].en @= s.recv_data[s.in_dir_local[i]].en
            if s.send_data[i].en & s.recv_data[s.in_dir_local[i]].rdy:
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
            s.send_data[i].en  @= b1( 0 )

      else:
        for i in range( num_outports ):
          s.send_data[i].en @= b1( 0 )
      s.recv_opt.rdy @= reduce_and( s.out_rdy_vector ) & ~reduce_or( s.recv_blocked_vector )
      s.send_predicate.msg.predicate @= reduce_or( s.recv_predicate_vector )
      # print()
      # for i in range( num_inports ):
      #   print("[comb] check reduce_or(recv_block): ",
      #         reduce_or( s.recv_blocked_vector ),
      #         "; s.recv_blocked_vector[", i, "]: ",
      #         s.recv_blocked_vector[i],
      #         "; s.recv_blocked_by_others[", i, "]: ",
      #         s.recv_blocked_by_others[i] )



    @update_ff
    def update_blocked_by_others():
      for i in range( num_inports ):
        # s.recv_blocked_by_others[i] <<= reduce_or( s.recv_blocked_vector )
        if reduce_or( s.recv_blocked_vector ) & ~s.recv_blocked_vector[i]:
          s.recv_blocked_by_others[i] <<= 1
        elif ~reduce_or( s.recv_blocked_vector ):
          s.recv_blocked_by_others[i] <<= 0
        # print("[update_ff] check reduce_or(recv_block): ",
        #       reduce_or( s.recv_blocked_vector ),
        #       "; s.recv_blocked_vector[", i, "]: ",
        #       s.recv_blocked_vector[i],
        #       "; s.recv_blocked_by_others[", i, "]: ",
        #       s.recv_blocked_by_others[i] )

      for i in range( num_outports ):
        # s.recv_blocked_by_others[i] <<= reduce_or( s.recv_blocked_vector )
        if ~reduce_and( s.out_rdy_vector ) & s.out_rdy_vector[i]:
          s.send_blocked_by_others[i] <<= 1
        elif reduce_and( s.out_rdy_vector ):
          s.send_blocked_by_others[i] <<= 0


  # Line trace
  def line_trace( s ):
    recv_str = "|".join([ str(x.msg) for x in s.recv_data ])
    out_str  = "|".join([ str(x.msg) for x in s.send_data ])
    pred_str = str( s.send_predicate.msg )
    return f"{recv_str} [{s.recv_opt.msg}] {out_str}-xbar.pred:{pred_str}"

