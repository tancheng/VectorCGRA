"""
==========================================================================
RegisterBankRTL.py
==========================================================================
Register bank between routing crossbar and FU in CGRA tile. It can be
initialized/modeled/parameterized as multiple instances. Each one contains
multiple registers that can be indexed/picked for read/write. Each has
one write port (from routing crossbar, fu crossbar, or const) and two
read ports (one towards FU, one towards routing crossbar).

Each register entry tracks whether it holds an unconsumed token
(https://github.com/tancheng/VectorCGRA/issues/321). Token discipline
applies to "armed" registers, i.e., registers that have been written at
least once since reset; a never-written register keeps the legacy
behavior of always asserting `val` on a configured read, acting as a
default-token source, which existing kernels rely on for liveness (e.g.,
tiles consuming data from their own register cluster that nothing
writes). For an armed register:
- The token bit is set when a token is written.
- A read only asserts `val` while the entry holds an unconsumed token.
- The token is consumed (cleared) when the ctrl step that reads the
  entry completes, signaled via `inport_ctrl_proceed` (the same
  per-step signal the const queue advances on). Within a ctrl step,
  reads are repeatable: FUs may accept the operand several times (e.g.,
  vector-factor replays) or merely snoop it without a val/rdy handshake
  (e.g., VectorAllReduceRTL's base operand), and for
  read_reg_towards=BOTH the tile only lets the step complete once both
  the FU and the routing-crossbar paths have been served.
- A write is rejected (and reported as not-ready via `outport_wr_rdy`)
  while the destination register still holds an unconsumed token, so an
  earlier token can never be silently overwritten by a later iteration.

Author : Cheng Tan
  Date : Feb 6, 2025
"""

from pymtl3 import *
from pymtl3.stdlib.primitive import RegisterFile
from ...lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ...lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ...lib.opt_type import *
from ...lib.util.common import *

from ...lib.util.common import (
  READ_TOWARDS_NOTHING,
  READ_TOWARDS_FU,
  READ_TOWARDS_ROUTING_XBAR,
  READ_TOWARDS_BOTH,
)

class RegisterBankRTL(Component):

  def construct(s, DataType, CtrlType, reg_bank_id, num_registers = 4):

    # Constant
    AddrType = mk_bits(clog2(num_registers))
    s.reg_bank_id = reg_bank_id

    # Interface
    s.inport_opt = InPort(CtrlType)
    # Read path towards the FU.
    s.send_data = SendIfcRTL(DataType)
    # Read path towards the routing crossbar.
    s.send_data_to_xbar = SendIfcRTL(DataType)
    # InPort is enough to expose the data. Recv ifc would complicate
    # the design and handshake.
    s.inport_wdata = [InPort(DataType) for _ in range(3)]
    s.inport_valid = [InPort(mk_bits(1)) for _ in range(3)]
    # Pulses when the current ctrl step completes (i.e., the ctrl memory
    # proceeds to the next ctrl signal); consumes the token of the
    # register read by the completing step.
    s.inport_ctrl_proceed = InPort(mk_bits(1))
    # Indicates whether the destination register of the configured write
    # can currently accept a token (i.e., holds no unconsumed token).
    # The cluster uses it to backpressure the selected write source.
    s.outport_wr_rdy = OutPort(mk_bits(1))
    # Clears all token bookkeeping (token/armed bits) on task switching,
    # so a newly launched task starts from the legacy (unarmed) behavior
    # regardless of what a previous task left behind. Register data
    # itself is preserved, matching the other clearable components.
    s.clear = InPort(mk_bits(1))

    # Component
    s.reg_file = RegisterFile(DataType, num_registers, rd_ports = 1,
                              wr_ports = 1)
    # Bit r indicates whether reg[r] holds an unconsumed token.
    s.token_valid = Wire(num_registers)
    # Bit r indicates whether reg[r] has ever been written ("armed").
    # Token discipline only applies to armed registers; a never-written
    # register keeps the legacy behavior of always asserting `val` on a
    # configured read (acting as a default-token source).
    s.armed = Wire(num_registers)

    # Wires derived from the ctrl signal and the token state.
    s.read_towards_fu = Wire(1)
    s.read_towards_xbar = Wire(1)
    s.read_token_valid = Wire(1)
    s.read_armed = Wire(1)
    s.wr_en = Wire(1)
    # One-hot masks selecting the register whose token bit is set (on a
    # write) or cleared (on the completion of the ctrl step reading it)
    # at the end of this cycle.
    s.token_set_mask = Wire(num_registers)
    s.token_clear_mask = Wire(num_registers)

    @update
    def update_token_status():
      read_towards = s.inport_opt.read_reg_towards[reg_bank_id]
      s.read_towards_fu @= (read_towards == READ_TOWARDS_FU) | \
                           (read_towards == READ_TOWARDS_BOTH)
      s.read_towards_xbar @= (read_towards == READ_TOWARDS_ROUTING_XBAR) | \
                             (read_towards == READ_TOWARDS_BOTH)

      # Token status of the register selected for read/write.
      s.read_token_valid @= 0
      s.read_armed @= 0
      s.outport_wr_rdy @= 0
      for r in range(num_registers):
        if s.inport_opt.read_reg_idx[reg_bank_id] == r:
          s.read_token_valid @= s.token_valid[r]
          s.read_armed @= s.armed[r]
        if s.inport_opt.write_reg_idx[reg_bank_id] == r:
          s.outport_wr_rdy @= ~s.token_valid[r]

    @update
    def access_registers():
      # Initializes signals.
      s.reg_file.raddr[0] @= AddrType()
      s.send_data.msg @= DataType()
      s.send_data_to_xbar.msg @= DataType()
      s.reg_file.waddr[0] @= AddrType()
      s.reg_file.wdata[0] @= DataType()
      s.reg_file.wen[0] @= 0
      s.wr_en @= 0

      read_towards = s.inport_opt.read_reg_towards[reg_bank_id]
      # Reads from register if towards FU (1), routing_xbar (2), or both (3)
      if read_towards > 0:
        s.reg_file.raddr[0] @= s.inport_opt.read_reg_idx[reg_bank_id]
        s.send_data.msg @= s.reg_file.rdata[0]
        s.send_data_to_xbar.msg @= s.reg_file.rdata[0]

      write_reg_from = s.inport_opt.write_reg_from[reg_bank_id]
      if ~s.reset & (write_reg_from > 0):
        # Rejects the write while the destination register still holds an
        # unconsumed token.
        if s.inport_valid[write_reg_from - 1] & s.outport_wr_rdy:
          s.reg_file.waddr[0] @= s.inport_opt.write_reg_idx[reg_bank_id]
          s.reg_file.wdata[0] @= s.inport_wdata[write_reg_from - 1]
          s.reg_file.wen[0] @= 1
          s.wr_en @= 1

    @update
    def update_send_val():
      # An armed register sends only while it holds an unconsumed token;
      # a never-written register keeps the legacy always-valid read
      # behavior (default-token source). Reads are level signals within
      # the current ctrl step (consumption happens on step completion,
      # see update_token_masks), so a consumer may accept or snoop the
      # data multiple times before the step completes.
      s.send_data.val @= ~s.reset & s.read_towards_fu & \
                         (s.read_token_valid | ~s.read_armed)
      s.send_data_to_xbar.val @= ~s.reset & s.read_towards_xbar & \
                                 (s.read_token_valid | ~s.read_armed)

    @update
    def update_token_masks():
      # A write can never target a register that still holds a token
      # (wr_en is gated by outport_wr_rdy) and a consumption only targets
      # a register that holds one, so the two masks never select the same
      # register in the same cycle.
      for r in range(num_registers):
        s.token_set_mask[r] @= \
            s.wr_en & (s.inport_opt.write_reg_idx[reg_bank_id] == r)
        # The completing ctrl step consumes the token it has been reading.
        s.token_clear_mask[r] @= \
            s.inport_ctrl_proceed & \
            (s.read_towards_fu | s.read_towards_xbar) & \
            (s.inport_opt.read_reg_idx[reg_bank_id] == r) & \
            s.token_valid[r]

    @update_ff
    def update_token_valid():
      if s.reset | s.clear:
        s.token_valid <<= 0
        s.armed <<= 0
      else:
        s.token_valid <<= (s.token_valid | s.token_set_mask) & \
                          ~s.token_clear_mask
        # A register becomes (and stays) armed once first written.
        s.armed <<= s.armed | s.token_set_mask

  def line_trace(s):
    inport_opt_str = "inport_opt: " + str(s.inport_opt)
    inport_wdata_str = "inport_wdata: " + str(s.inport_wdata)
    content_str = "content: " + "|".join([str(data) for data in s.reg_file.regs])
    token_str = "token_valid: " + str(s.token_valid) + ", armed: " + str(s.armed)
    send_data_str = "send_data: " + str(s.send_data.msg)
    return f'reg_bank_id: {s.reg_bank_id} || {inport_wdata_str} || {inport_opt_str} || [{content_str}] || [{token_str}] || {send_data_str}'
