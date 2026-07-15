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
- A write targeting a register that still holds an unconsumed token, or
  that is being read by the current ctrl step, is accepted into a
  one-entry write skid buffer (if free) and committed into the register
  file once this cannot disturb an in-flight read, so an earlier token
  can never be silently overwritten and a register being read stays
  stable until the step completes — while a producer whose destination
  register is being read by its own ctrl step (same-register
  read-modify-write, e.g. an accumulator, or `NOT $0 -> $0, SOUTH`
  under backpressure, see issues #281/#286) can still complete its
  write handshake and let the step finish. Only while the skid buffer
  is occupied are writes backpressured (via `outport_wr_rdy`).

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
    s.send_data_to_fu = SendIfcRTL(DataType)
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
    # Indicates whether the configured write can be accepted this cycle
    # (directly or into the skid buffer). The cluster uses it to
    # backpressure the selected write source.
    s.outport_wr_rdy = OutPort(mk_bits(1))
    # Clears all token bookkeeping (token/armed/skid state) on task
    # switching, so a newly launched task starts from the legacy
    # (unarmed) behavior regardless of what a previous task left behind.
    # Register data itself is preserved, matching the other clearable
    # components.
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
    # Write skid buffer (one entry; the bank has one write port, so at
    # most one write can be blocked at a time). A write that cannot land
    # directly is accepted ("parked") here and committed into the
    # register file once that cannot disturb an in-flight read. This is
    # what allows an operation to read and write the same register
    # within one ctrl step (e.g., an accumulator, or `NOT $0 -> $0,
    # SOUTH` under backpressure — see issues #281/#286): the producer's
    # write handshake completes immediately via the skid, so the step
    # can finish and release the old token, while the register keeps
    # the old value stable for any re-reads until the step completes.
    s.skid_valid = Wire(1)
    s.skid_data = Wire(DataType)
    s.skid_idx = Wire(AddrType)

    # Wires derived from the ctrl signal and the token state.
    s.read_towards_fu = Wire(1)
    s.read_towards_xbar = Wire(1)
    s.read_token_valid = Wire(1)
    s.read_armed = Wire(1)
    # Token status of the configured write target and of the skid
    # entry's target.
    s.wr_target_token = Wire(1)
    s.skid_target_token = Wire(1)
    # The current ctrl step is reading the write target / the skid
    # entry's target. A register being read must stay stable until the
    # step completes (reads are level signals), so such writes park in
    # the skid and commit exactly when the step completes.
    s.wr_target_read = Wire(1)
    s.skid_target_read = Wire(1)
    # The skid entry commits into the register file this cycle.
    s.skid_commit = Wire(1)
    # A write is accepted from the selected source this cycle...
    s.wr_accept = Wire(1)
    # ...and lands directly in the register file...
    s.wr_en = Wire(1)
    # ...or is parked in the skid buffer.
    s.skid_park = Wire(1)
    # Write data selected from the configured source.
    s.wr_sel_data = Wire(DataType)
    # One-hot masks selecting the register whose token bit is set (on a
    # direct write or a skid commit) or cleared (on the completion of
    # the ctrl step reading it) at the end of this cycle.
    s.token_set_mask = Wire(num_registers)
    s.token_clear_mask = Wire(num_registers)

    @update
    def update_token_status():
      read_towards = s.inport_opt.read_reg_towards[reg_bank_id]
      s.read_towards_fu @= (read_towards == READ_TOWARDS_FU) | \
                           (read_towards == READ_TOWARDS_BOTH)
      s.read_towards_xbar @= (read_towards == READ_TOWARDS_ROUTING_XBAR) | \
                             (read_towards == READ_TOWARDS_BOTH)

      # Token status of the registers selected for read/write and of the
      # skid entry's target.
      s.read_token_valid @= 0
      s.read_armed @= 0
      s.wr_target_token @= 0
      s.skid_target_token @= 0
      for r in range(num_registers):
        if s.inport_opt.read_reg_idx[reg_bank_id] == r:
          s.read_token_valid @= s.token_valid[r]
          s.read_armed @= s.armed[r]
        if s.inport_opt.write_reg_idx[reg_bank_id] == r:
          s.wr_target_token @= s.token_valid[r]
        if s.skid_idx == r:
          s.skid_target_token @= s.token_valid[r]

      s.wr_target_read @= (s.read_towards_fu | s.read_towards_xbar) & \
          (s.inport_opt.read_reg_idx[reg_bank_id] == \
           s.inport_opt.write_reg_idx[reg_bank_id])
      s.skid_target_read @= (s.read_towards_fu | s.read_towards_xbar) & \
          (s.inport_opt.read_reg_idx[reg_bank_id] == s.skid_idx)

      # The parked write drains into the register file as soon as this
      # cannot disturb an in-flight read: if the current step reads the
      # skid's target, the commit happens exactly when that step
      # completes (its new token atomically replaces the one the step
      # consumes); otherwise it happens once the target holds no token.
      s.skid_commit @= s.skid_valid & \
          ((s.skid_target_read & s.inport_ctrl_proceed) | \
           (~s.skid_target_read & ~s.skid_target_token))

      # A write is accepted whenever the skid buffer is free: it lands
      # directly in the register file if that cannot disturb anything,
      # and parks in the skid otherwise. Occupied skid -> not ready.
      # Keeping this a pure function of registered state means the
      # producer's rdy never combinationally depends on any consumer's
      # readiness (in particular not on skid_commit, which derives from
      # inport_ctrl_proceed and would otherwise close a loop through
      # the FU's rdy chain), and it also guarantees a direct write can
      # never collide with a skid commit on the single write port.
      s.outport_wr_rdy @= ~s.skid_valid

    @update
    def access_registers():
      # Initializes signals.
      s.reg_file.raddr[0] @= AddrType()
      s.send_data_to_fu.msg @= DataType()
      s.send_data_to_xbar.msg @= DataType()
      s.reg_file.waddr[0] @= AddrType()
      s.reg_file.wdata[0] @= DataType()
      s.reg_file.wen[0] @= 0
      s.wr_accept @= 0
      s.wr_en @= 0
      s.skid_park @= 0
      s.wr_sel_data @= DataType()

      read_towards = s.inport_opt.read_reg_towards[reg_bank_id]
      # Reads from register if towards FU (1), routing_xbar (2), or both (3)
      if read_towards > 0:
        s.reg_file.raddr[0] @= s.inport_opt.read_reg_idx[reg_bank_id]
        s.send_data_to_fu.msg @= s.reg_file.rdata[0]
        s.send_data_to_xbar.msg @= s.reg_file.rdata[0]

      write_reg_from = s.inport_opt.write_reg_from[reg_bank_id]
      if ~s.reset & (write_reg_from > 0):
        s.wr_sel_data @= s.inport_wdata[write_reg_from - 1]
        # Accepts the write if the skid buffer is free; a write is never
        # lost or overwritten.
        if s.inport_valid[write_reg_from - 1] & s.outport_wr_rdy:
          s.wr_accept @= 1
          # Lands directly if that cannot disturb an in-flight read: the
          # target holds no token and is not being read by the current
          # step (a register being read must stay stable until the step
          # completes), or the reading step completes this very cycle
          # (the write lands at the step boundary; a consumed token is
          # atomically replaced since set wins over clear). Otherwise
          # parks in the skid buffer.
          if (~s.wr_target_token & ~s.wr_target_read) | \
             (s.wr_target_read & s.inport_ctrl_proceed):
            s.wr_en @= 1
          else:
            s.skid_park @= 1

      # The skid commit owns the single write port when it fires; a
      # direct write never coincides with it (a commit implies the skid
      # is occupied, and outport_wr_rdy rejects all writes while it is).
      if s.skid_commit:
        s.reg_file.waddr[0] @= s.skid_idx
        s.reg_file.wdata[0] @= s.skid_data
        s.reg_file.wen[0] @= 1
      elif s.wr_en:
        s.reg_file.waddr[0] @= s.inport_opt.write_reg_idx[reg_bank_id]
        s.reg_file.wdata[0] @= s.wr_sel_data
        s.reg_file.wen[0] @= 1

    @update
    def update_send_val():
      # An armed register sends only while it holds an unconsumed token;
      # a never-written register keeps the legacy always-valid read
      # behavior (default-token source). Reads are level signals within
      # the current ctrl step (consumption happens on step completion,
      # see update_token_masks), so a consumer may accept or snoop the
      # data multiple times before the step completes.
      s.send_data_to_fu.val @= ~s.reset & s.read_towards_fu & \
                         (s.read_token_valid | ~s.read_armed)
      s.send_data_to_xbar.val @= ~s.reset & s.read_towards_xbar & \
                                 (s.read_token_valid | ~s.read_armed)

    @update
    def update_token_masks():
      # The set and clear masks can select the same register in one
      # cycle: when a write lands or a skid commit fires on step
      # completion for the register the step was reading, the new token
      # atomically replaces the consumed one (set wins in
      # update_token_valid).
      for r in range(num_registers):
        s.token_set_mask[r] @= \
            (s.wr_en & (s.inport_opt.write_reg_idx[reg_bank_id] == r)) | \
            (s.skid_commit & (s.skid_idx == r))
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
        s.skid_valid <<= 0
      else:
        # Set wins over clear: a write or skid commit coinciding with
        # the consumption of the same register's token (on step
        # completion) installs the new token.
        s.token_valid <<= (s.token_valid & ~s.token_clear_mask) | \
                          s.token_set_mask
        # A register becomes (and stays) armed once first written.
        s.armed <<= s.armed | s.token_set_mask

        # Parking and committing are mutually exclusive (parking requires
        # a free skid, committing an occupied one).
        if s.skid_park:
          s.skid_valid <<= 1
          s.skid_data <<= s.wr_sel_data
          s.skid_idx <<= s.inport_opt.write_reg_idx[reg_bank_id]
        elif s.skid_commit:
          s.skid_valid <<= 0

  def line_trace(s):
    inport_opt_str = "inport_opt: " + str(s.inport_opt)
    inport_wdata_str = "inport_wdata: " + str(s.inport_wdata)
    content_str = "content: " + "|".join([str(data) for data in s.reg_file.regs])
    token_str = "token_valid: " + str(s.token_valid) + ", armed: " + str(s.armed) + \
                ", skid: " + (f"reg[{int(s.skid_idx)}]={s.skid_data}" if s.skid_valid else "-")
    send_data_to_fu_str = "send_data_to_fu: " + str(s.send_data_to_fu.msg)
    return f'reg_bank_id: {s.reg_bank_id} || {inport_wdata_str} || {inport_opt_str} || [{content_str}] || [{token_str}] || {send_data_to_fu_str}'
