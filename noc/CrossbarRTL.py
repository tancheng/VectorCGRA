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

  def construct(s,
                DataType,
                PredicateType,
                CtrlType,
                num_inports = 5,
                num_outports = 5,
                num_cgras = 4,
                num_tiles = 4,
                ctrl_mem_size = 6,
                outport_towards_local_base_id = 4):

    InType = mk_bits(clog2(num_inports + 1))
    num_index = num_inports if num_inports != 1 else 2
    NumInportType = mk_bits(clog2(num_index))
    PrologueCountType = mk_bits(clog2(PROLOGUE_MAX_COUNT + 1))
    CtrlAddrType = mk_bits(clog2(ctrl_mem_size))

    # Interface
    s.recv_opt = RecvIfcRTL(CtrlType)
    s.recv_data = [RecvIfcRTL(DataType) for _ in range(num_inports)]
    s.recv_data_msg = [Wire(DataType) for _ in range(num_inports)]
    s.recv_data_val = [Wire(b1) for _ in range(num_inports)]
    for i in range(num_inports):
      s.recv_data_msg[i] //= s.recv_data[i].msg
      s.recv_data_val[i] //= s.recv_data[i].val

    s.crossbar_outport = [InPort(InType) for _ in range(num_outports)]
    s.send_data = [SendIfcRTL(DataType) for _ in range(num_outports)]

    s.in_dir = [Wire(InType) for _ in range(num_outports)]
    s.in_dir_local = [Wire(NumInportType) for _ in range(num_outports)]
    s.send_rdy_vector = Wire(num_outports)
    s.recv_valid_vector = Wire(num_outports)
    s.recv_required_vector = Wire(num_inports)
    s.send_required_vector = Wire(num_outports)

    s.cgra_id = InPort(mk_bits(max(1, clog2(num_cgras))))
    s.tile_id = InPort(mk_bits(clog2(num_tiles + 1)))
    s.crossbar_id = InPort(b1)
    s.compute_done = InPort(b1)

    s.ctrl_addr_inport = InPort(CtrlAddrType)

    # Prologue-related wires and registers, which are used to indicate
    # whether the prologue steps have already been satisfied.
    s.prologue_allowing_vector = Wire(num_outports)
    s.recv_valid_or_prologue_allowing_vector = Wire(num_outports)
    s.prologue_counter = [[Wire(PrologueCountType) for _ in range(num_inports)] for _ in range(ctrl_mem_size)]
    s.prologue_counter_next = [[Wire(PrologueCountType) for _ in range(num_inports)] for _ in range(ctrl_mem_size)]
    s.prologue_count_inport = [[InPort(PrologueCountType) for _ in range(num_inports)] for _ in range(ctrl_mem_size)]
    # Wiki of "Workaround for sv2v Flattening Multi‐dimensional Arrays into One‐dimensional Vectors"
    # https://github.com/tancheng/VectorCGRA/wiki/Workaround-for-sv2v-Flattening-Multi%E2%80%90dimensional-Arrays-into-One%E2%80%90dimensional-Vectors
    s.prologue_count_wire = [[Wire(PrologueCountType) for _ in range(num_inports)] for _ in range(ctrl_mem_size)]

    for addr in range(ctrl_mem_size):
      for i in range(num_inports):
        s.prologue_count_inport[addr][i] //= s.prologue_count_wire[addr][i]

    # Routing logic
    @update
    def update_signal():
      for i in range(num_inports):
        s.recv_data[i].rdy @= 0
      for i in range(num_outports):
        s.send_data[i].val @= 0
        s.send_data[i].msg @= DataType()
      s.recv_opt.rdy @= 0

      if s.recv_opt.val & (s.recv_opt.msg.operation != OPT_START):
        for i in range(num_inports):
          s.recv_data[i].rdy @= reduce_and(s.recv_valid_vector) & \
                                reduce_and(s.send_rdy_vector) & \
                                s.recv_required_vector[i]

        for i in range(num_outports):
          s.send_data[i].val @= reduce_and(s.recv_valid_vector) & \
                                s.send_required_vector[i]
          if reduce_and(s.recv_valid_vector) & \
             s.send_required_vector[i]:
            s.send_data[i].msg.payload @= s.recv_data_msg[s.in_dir_local[i]].payload
            s.send_data[i].msg.predicate @= s.recv_data_msg[s.in_dir_local[i]].predicate

        s.recv_opt.rdy @= reduce_and(s.send_rdy_vector) & \
                          reduce_and(s.recv_valid_or_prologue_allowing_vector)

    @update_ff
    def update_prologue_counter():
      if s.reset:
        for addr in range(ctrl_mem_size):
          for i in range(num_inports):
            s.prologue_counter[addr][i] <<= 0
      else:
        for addr in range(ctrl_mem_size):
          for i in range(num_inports):
            s.prologue_counter[addr][i] <<= s.prologue_counter_next[addr][i]

    @update
    def update_prologue_counter_next():
      # Nested-loop to update the prologue counter, to avoid dynamic indexing to
      # work-around Yosys issue: https://github.com/tancheng/VectorCGRA/issues/148
      for addr in range(ctrl_mem_size):
        for i in range(num_inports):
          s.prologue_counter_next[addr][i] @= s.prologue_counter[addr][i]
          for j in range(num_outports):
            if s.recv_opt.rdy & \
              (s.in_dir[j] > 0) & \
              (s.in_dir_local[j] == i) & \
              (addr == s.ctrl_addr_inport) & \
              (s.prologue_counter[addr][i] < s.prologue_count_wire[addr][i]):
              s.prologue_counter_next[addr][i] @= s.prologue_counter[addr][i] + 1

    @update
    def update_prologue_allowing_vector():
      s.prologue_allowing_vector @= 0
      for i in range(num_outports):
        if s.in_dir[i] > 0:
          # Records whether the prologue steps have already been satisfied.
          s.prologue_allowing_vector[i] @= \
            (s.prologue_counter[s.ctrl_addr_inport][s.in_dir_local[i]] < \
             s.prologue_count_wire[s.ctrl_addr_inport][s.in_dir_local[i]])
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
        # The `num_inports` indicates the number of outports that go to other tiles.
        # Specifically, if the compute already done, we shouldn't care the ones
        # (i.e., i >= num_inports) go to the FU's inports. In other words, we skip
        # the rdy checking on the FU's inports (connecting from crossbar_outport) if
        # the compute is already completed.
        if (s.in_dir[i] > 0) & \
           (~s.compute_done | (i < outport_towards_local_base_id)):
          s.send_rdy_vector[i] @= s.send_data[i].rdy
        else:
          s.send_rdy_vector[i] @= 1

    @update
    def update_valid_vector():
      s.recv_valid_vector @= 0
      for i in range(num_outports):
        if s.in_dir[i] > 0:
          s.recv_valid_vector[i] @= s.recv_data_val[s.in_dir_local[i]]
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
    return f"{recv_str} [{s.recv_opt.msg}] {out_str}"

