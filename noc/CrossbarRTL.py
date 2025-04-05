"""
=========================================================================
CrossbarSeparate.py
=========================================================================
Data-driven crossbar. Valid data is sent out only when all the input
channels have pending data.

Author : Cheng Tan
  Date : Nov 29, 2024
"""

from pymtl3 import *
from ..lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ..lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ..lib.opt_type import *
from ..lib.util.common import *

class CrossbarRTL(Component):

  def construct(s, DataType, PredicateType, CtrlType, num_inports = 5,
                num_outports = 5, num_tiles = 4):

    InType = mk_bits(clog2(num_inports + 1))
    num_index = num_inports if num_inports != 1 else 2
    NumInportType = mk_bits(clog2(num_index))
    PrologueCountType = mk_bits(clog2(PROLOGUE_MAX_COUNT + 1))

    # Interface
    s.recv_opt = RecvIfcRTL(CtrlType)
    s.recv_data = [RecvIfcRTL(DataType) for _ in range(num_inports)]
    s.crossbar_outport = [InPort(InType) for _ in range(num_outports)]
    s.send_data = [SendIfcRTL(DataType) for _ in range(num_outports)]

    s.send_predicate = SendIfcRTL(PredicateType)

    s.in_dir = [Wire(InType) for _ in range(num_outports)]
    s.in_dir_local = [Wire(NumInportType) for _ in range(num_outports)]
    s.send_rdy_vector = Wire(num_outports)
    s.recv_predicate_vector = Wire(num_inports)
    s.recv_valid_vector = Wire(num_outports)
    s.recv_required_vector = Wire(num_inports)
    s.send_required_vector = Wire(num_outports)

    s.tile_id = InPort(mk_bits(clog2(num_tiles + 1)))
    s.crossbar_id = InPort(b1)

    # Prologue-related wires and registers, which are used to indicate
    # whether the prologue steps have already been satisfied.
    s.prologue_allowing_vector = Wire(num_outports)
    s.recv_valid_or_prologue_allowing_vector = Wire(num_outports)
    s.prologue_counter = [Wire(PrologueCountType) for _ in range(num_inports)]
    s.prologue_count_inport = [InPort(PrologueCountType) for _ in range(num_inports)]

    # Routing logic
    @update
    def update_signal():
      # s.out_rdy_vector @= 0
      s.recv_predicate_vector @= 0
      s.send_predicate.val @= 0
      # s.recv_blocked_vector @= 0
      s.send_predicate.msg @= PredicateType()
      for i in range(num_inports):
        s.recv_data[i].rdy @= 0
      for i in range(num_outports):
        s.send_data[i].val @= 0
        s.send_data[i].msg @= DataType()
      s.recv_opt.rdy @= 0

      # For predication register update. 'predicate' and 'predicate_in' no need
      # to be active at the same time. Specifically, the 'predicate' is for
      # the operation at the current cycle while the 'predicate_in' accumulates
      # the predicate and pushes into the predicate register that will be used
      # in the future.
      if s.recv_opt.msg.predicate:
        s.send_predicate.msg @= PredicateType(b1(0), b1(0))

      if s.recv_opt.val & (s.recv_opt.msg.ctrl != OPT_START):
        for i in range(num_inports):
          # Set predicate once the recv_data is stable (i.e., en == true).
          # FIXME: Let's re-think the predicate support in next PR.
          if s.recv_opt.msg.routing_predicate_in[i]:
            s.send_predicate.val @= b1(1)
            s.send_predicate.msg.payload @= b1(1)
            s.recv_predicate_vector[i] @= s.recv_data[i].msg.predicate

        for i in range(num_inports):
          s.recv_data[i].rdy @= reduce_and(s.recv_valid_vector) & \
                                reduce_and(s.send_rdy_vector) & \
                                s.recv_required_vector[i]

        for i in range(num_outports):
          s.send_data[i].val @= reduce_and(s.recv_valid_vector) & \
                                s.send_required_vector[i]
                                # FIXME: Valid shouldn't depend on rdy.
                                # reduce_and(s.send_rdy_vector) & \
          if reduce_and(s.recv_valid_vector) & \
             s.send_required_vector[i]:
             # reduce_and(s.send_rdy_vector) & \
            s.send_data[i].msg.payload @= s.recv_data[s.in_dir_local[i]].msg.payload
            s.send_data[i].msg.predicate @= s.recv_data[s.in_dir_local[i]].msg.predicate

        s.send_predicate.msg.predicate @= reduce_or(s.recv_predicate_vector)
        # s.recv_opt.rdy @= reduce_and(s.send_rdy_vector) & reduce_and(s.recv_valid_vector)
        s.recv_opt.rdy @= reduce_and(s.send_rdy_vector) & \
                          reduce_and(s.recv_valid_or_prologue_allowing_vector)

    @update_ff
    def update_prologue_counter():
      if s.reset:
        for i in range(num_inports):
          s.prologue_counter[i] <<= 0
      elif s.recv_opt.rdy:
        for i in range(num_outports):
          if (s.in_dir[i] > 0) & \
             (s.prologue_counter[s.in_dir_local[i]] < s.prologue_count_inport[s.in_dir_local[i]]):
            s.prologue_counter[s.in_dir_local[i]] <<= s.prologue_counter[s.in_dir_local[i]] + 1

    @update
    def update_prologue_allowing_vector():
      s.prologue_allowing_vector @= 0
      for i in range(num_outports):
        if s.in_dir[i] > 0:
          # Records whether the prologue steps have already been satisfied.
          s.prologue_allowing_vector[i] @= \
              (s.prologue_counter[s.in_dir_local[i]] < \
               s.prologue_count_inport[s.in_dir_local[i]])
        else:
          s.prologue_allowing_vector[i] @= 1

    @update
    def update_prologue_or_valid_vector():
      s.recv_valid_or_prologue_allowing_vector @= 0
      for i in range(num_outports):
        s.recv_valid_or_prologue_allowing_vector[i] @= \
            s.recv_valid_vector[i] | s.prologue_allowing_vector[i]

    @update
    def update_in_dir_vector():

      for i in range(num_outports):
        s.in_dir[i] @= 0
        s.in_dir_local[i] @= 0

      for i in range(num_outports):
        s.in_dir[i] @= s.crossbar_outport[i]
        if s.in_dir[i] > 0:
          s.in_dir_local[i] @= trunc(s.in_dir[i] - 1, NumInportType)

    @update
    def update_rdy_vector():
      s.send_rdy_vector @= 0
      for i in range(num_outports):
        if s.in_dir[i] > 0:
          s.send_rdy_vector[i] @= s.send_data[i].rdy
        else:
          s.send_rdy_vector[i] @= 1

    @update
    def update_valid_vector():
      s.recv_valid_vector @= 0
      for i in range(num_outports):
        if s.in_dir[i] > 0:
          s.recv_valid_vector[i] @= s.recv_data[s.in_dir_local[i]].val
        else:
          s.recv_valid_vector[i] @= 1

    @update
    def update_recv_required_vector():
      for i in range(num_inports):
        s.recv_required_vector[i] @= 0

      for i in range(num_outports):
        if s.in_dir[i] > 0:
          s.recv_required_vector[s.in_dir_local[i]] @= 1

    @update
    def update_send_required_vector():

      for i in range(num_outports):
        s.send_required_vector[i] @= 0

      for i in range(num_outports):
        if s.in_dir[i] > 0:
          s.send_required_vector[i] @= 1


  # Line trace
  def line_trace(s):
    recv_str = "|".join([str(x.msg) for x in s.recv_data])
    out_str  = "|".join([str(x.msg) for x in s.send_data])
    pred_str = str(s.send_predicate.msg)
    return f"{recv_str} [{s.recv_opt.msg}] {out_str}-xbar.pred:{pred_str}"

