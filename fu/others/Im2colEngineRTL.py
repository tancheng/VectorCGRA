"""
==========================================================================
Im2colEngineRTL.py
==========================================================================
Merged im2col (image-to-column) engine. Reads an HxW single-channel input
image from a local input scratchpad and streams the lowered
(kH*kW) x (Hout*Wout) column matrix into the enclosing CGRA's shared
data memory as a sequence of CMD_STORE_REQUEST packets on `send_pkt`.
The engine writes output i to CGRA data_mem addr i (i.e. the lowered
matrix occupies data_mem[0 .. num_outputs)); the consumer configures
its LD_CONST addresses accordingly.

Note on packet dst_tile: CMD_STORE_REQUEST packets are routed by the
CGRA controller using the payload.data_addr field alone (see
ControllerRTL.update_sending_to_noc_msg); the packet's dst_tile is
ignored on this path. The engine therefore emits dst=0 unconditionally,
and does not take a dst_tiles list.

Relative to the previous split:
  Im2colRTL       = stand-alone im2col data mover, wrote its output to
                    a caller-supplied output scratchpad memory port.
  Im2colEngineRTL = wrapped that data mover in a private in_mem /
                    out_mem scratchpad pair plus a follow-on emit FSM
                    that drained out_mem into CMD_STORE_REQUEST packets.

This file collapses both into one component: on each S_READ we compute
the current in_mem address, and on the returned data we form the store
packet directly. There is no output scratchpad -- values are computed
and emitted in lock-step so the CGRA's shared data_mem is the only
buffer needed.

The input scratchpad is kept: the caller preloads the image into it at
construct time so the engine has a stable local buffer to walk during
im2col (modeling the "image already resident in a nearby SPM" boundary
condition).

State machine: IDLE -> READ -> EMIT -> DONE
  IDLE: wait for `start`.
  READ: assert the read on in_mem at in_addr(ky, kx, oy, ox).
  EMIT: hold the incoming data, drive send_pkt with
        (data_addr = emit_idx, data). On send_pkt fire, advance the
        nested loop counters (ox innermost, then oy, kx, ky) and
        either loop back to READ or transition to DONE. The loop order
        is chosen so emit_idx (the flat output counter) monotonically
        walks 0 -> num_outputs, which is why we can use emit_idx as
        the SRAM address directly.
  DONE: assert `done` and stay here until reset.
"""

from pymtl3 import *

from ...lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ...lib.cmd_type import CMD_STORE_REQUEST
from ...lib.util.data_struct_attr import kAttrCmd, kAttrDataAddr, kAttrPayload
from ...mem.data.DataMemRTL import DataMemRTL


class Im2colEngineRTL(Component):

  def construct(s, DataType, IntraCgraPktType, CgraPayloadType,
                scratch_mem_size,
                in_base, H, W, kH, kW, stride,
                preload_image):

    Hout = (H - kH) // stride + 1
    Wout = (W - kW) // stride + 1
    num_outputs = kH * kW * Hout * Wout

    # Derive widths from the passed-in packet types so the engine stays
    # generic across CGRA configurations.
    ScratchAddrType = mk_bits(clog2(scratch_mem_size))
    PayloadType     = IntraCgraPktType.get_field_type(kAttrPayload)
    CmdType         = PayloadType.get_field_type(kAttrCmd)
    DataAddrType    = PayloadType.get_field_type(kAttrDataAddr)

    IdxType   = mk_bits(max(1, clog2(num_outputs + 1)))
    StateType = mk_bits(2)

    S_IDLE = StateType(0)
    S_READ = StateType(1)
    S_EMIT = StateType(2)
    S_DONE = StateType(3)

    # Public I/O.
    s.start    = InPort(b1)
    s.done     = OutPort(b1)
    s.send_pkt = SendIfcRTL(IntraCgraPktType)

    # Pre-build the input scratchpad preload (image at [in_base, in_base+H*W)).
    preload_full = [DataType(0, 1) for _ in range(scratch_mem_size)]
    for i, v in enumerate(preload_image):
      preload_full[in_base + i] = DataType(v, 1)

    s.in_mem = DataMemRTL(DataType, scratch_mem_size,
                          rd_ports = 1, wr_ports = 1,
                          preload_data = preload_full)

    # FSM state.
    s.state    = Wire(StateType)
    s.oy       = Wire(ScratchAddrType)
    s.ox       = Wire(ScratchAddrType)
    s.ky       = Wire(ScratchAddrType)
    s.kx       = Wire(ScratchAddrType)
    s.emit_idx = Wire(IdxType)
    s.data_reg = Wire(DataType)

    # Combinational address computation. Narrowing casts (ScratchAddrType(...))
    # prevent pymtl3's AST analyzer from tripping on binop-result slices.
    s.in_row  = Wire(ScratchAddrType)
    s.in_col  = Wire(ScratchAddrType)
    s.in_addr = Wire(ScratchAddrType)

    @update
    def comb_in_addr():
      s.in_row  @= ScratchAddrType(s.oy * stride + s.ky)
      s.in_col  @= ScratchAddrType(s.ox * stride + s.kx)
      s.in_addr @= ScratchAddrType(in_base + s.in_row * W + s.in_col)

    # Tie off the unused write port on the input scratchpad.
    @update
    def tie_off_in_mem_wr():
      s.in_mem.recv_waddr[0].val @= b1(0)
      s.in_mem.recv_waddr[0].msg @= ScratchAddrType(0)
      s.in_mem.recv_wdata[0].val @= b1(0)
      s.in_mem.recv_wdata[0].msg @= DataType()

    # Read + emit datapath. Pass integer zeros (rather than type
    # constructors like CtrlType()) for the don't-care fields so the
    # verilator translator can encode them as constants -- it can't
    # handle default constructors of bitstructs that contain list-of-bits
    # fields (e.g. the CtrlType.fu_in array) inside behavioral RTLIR.
    @update
    def drive_read_and_emit():
      s.in_mem.recv_raddr[0].val @= b1(0)
      s.in_mem.recv_raddr[0].msg @= ScratchAddrType(0)
      s.in_mem.send_rdata[0].rdy @= b1(0)

      s.send_pkt.val @= b1(0)
      s.done         @= b1(0)

      if s.state == S_READ:
        s.in_mem.recv_raddr[0].val @= b1(1)
        s.in_mem.recv_raddr[0].msg @= s.in_addr
        s.in_mem.send_rdata[0].rdy @= b1(1)

      if s.state == S_EMIT:
        s.send_pkt.val @= b1(1)
        s.send_pkt.msg @= IntraCgraPktType(
            0,             # src
            0,             # dst (unused for STORE_REQUEST -- controller
                           # routes by payload.data_addr)
            0, 0,          # src/dst cgra_id
            0, 0,          # src cgra x/y
            0, 0,          # dst cgra x/y
            0,             # opaque
            0,             # vc_id
            PayloadType(
                CmdType(CMD_STORE_REQUEST),
                s.data_reg,
                zext(s.emit_idx, DataAddrType),   # SRAM addr = emit_idx
                0,         # ctrl (zero)
                0,         # ctrl_addr
            ),
        )
      else:
        s.send_pkt.msg @= IntraCgraPktType(
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
            PayloadType(0, 0, 0, 0, 0),
        )

      if s.state == S_DONE:
        s.done @= b1(1)

    # FSM transitions.
    @update_ff
    def fsm():
      if s.reset:
        s.state    <<= S_IDLE
        s.oy       <<= ScratchAddrType(0)
        s.ox       <<= ScratchAddrType(0)
        s.ky       <<= ScratchAddrType(0)
        s.kx       <<= ScratchAddrType(0)
        s.emit_idx <<= IdxType(0)
        s.data_reg <<= DataType()
      else:
        if s.state == S_IDLE:
          if s.start:
            s.state    <<= S_READ
            s.oy       <<= ScratchAddrType(0)
            s.ox       <<= ScratchAddrType(0)
            s.ky       <<= ScratchAddrType(0)
            s.kx       <<= ScratchAddrType(0)
            s.emit_idx <<= IdxType(0)

        elif s.state == S_READ:
          if s.in_mem.recv_raddr[0].rdy & s.in_mem.send_rdata[0].val:
            s.data_reg <<= s.in_mem.send_rdata[0].msg
            s.state    <<= S_EMIT

        elif s.state == S_EMIT:
          if s.send_pkt.val & s.send_pkt.rdy:
            # Loop order (ox -> oy -> kx -> ky, ox innermost) so emit_idx
            # walks the flat output index (row = ky*kW+kx, col =
            # oy*Wout+ox, flat = row*Hout*Wout + col) monotonically.
            # This lets data_addr_const be indexed by emit_idx directly
            # without an intermediate LUT.
            if s.ox + ScratchAddrType(1) < ScratchAddrType(Wout):
              s.ox    <<= s.ox + ScratchAddrType(1)
              s.state <<= S_READ
            elif s.oy + ScratchAddrType(1) < ScratchAddrType(Hout):
              s.ox    <<= ScratchAddrType(0)
              s.oy    <<= s.oy + ScratchAddrType(1)
              s.state <<= S_READ
            elif s.kx + ScratchAddrType(1) < ScratchAddrType(kW):
              s.ox    <<= ScratchAddrType(0)
              s.oy    <<= ScratchAddrType(0)
              s.kx    <<= s.kx + ScratchAddrType(1)
              s.state <<= S_READ
            elif s.ky + ScratchAddrType(1) < ScratchAddrType(kH):
              s.ox    <<= ScratchAddrType(0)
              s.oy    <<= ScratchAddrType(0)
              s.kx    <<= ScratchAddrType(0)
              s.ky    <<= s.ky + ScratchAddrType(1)
              s.state <<= S_READ
            else:
              s.state <<= S_DONE
            s.emit_idx <<= s.emit_idx + IdxType(1)
        # S_DONE is terminal until reset.

  def line_trace(s):
    state_map = {0: "IDLE", 1: "READ", 2: "EMIT", 3: "DONE"}
    st = state_map[int(s.state)]
    return (f"engine[{st} emit_idx={int(s.emit_idx)} "
            f"oy={int(s.oy)} ox={int(s.ox)} ky={int(s.ky)} kx={int(s.kx)} "
            f"done={int(s.done)} "
            f"send_val={int(s.send_pkt.val)} send_rdy={int(s.send_pkt.rdy)}] "
            f"in_addr={int(s.in_addr)} data_reg={s.data_reg}")
