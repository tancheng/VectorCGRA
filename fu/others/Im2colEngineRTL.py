"""
==========================================================================
Im2colEngineRTL.py
==========================================================================
Runtime-programmable im2col (image-to-column) engine. Reads a
single-channel input image resident in a local input scratchpad and
streams the lowered (kH*kW) x (Hout*Wout) column matrix into the
enclosing CGRA's shared data memory as a sequence of CMD_STORE_REQUEST
packets on `send_pkt`.

Configuration model (mirrors CMD_DMA_CONFIG_* convention): the CPU
sends one CMD per geometry parameter before firing CMD_IM2COL_LAUNCH.
Each config CMD is consumed by the engine while it sits in S_IDLE and
latched into the corresponding register. CMD_IM2COL_LAUNCH triggers the
IDLE -> READ transition, at which point Hout / Wout are precomputed.

  CMD_IM2COL_H                (data)      -> cfg_H
  CMD_IM2COL_W                (data)      -> cfg_W
  CMD_IM2COL_KH               (data)      -> cfg_kH
  CMD_IM2COL_KW               (data)      -> cfg_kW
  CMD_IM2COL_LOG2_STRIDE      (data)      -> cfg_log2_stride
  CMD_IM2COL_DST_SRAM_BASE    (data_addr) -> cfg_dst_sram_base_addr
  CMD_IM2COL_LAUNCH                        -> start processing

The image always sits at offset 0 of the engine's private in_mem
scratchpad -- since nothing outside the engine addresses in_mem, there
is no benefit to exposing an input base address.

Stride is passed as log2(stride) so that (H - kH) / stride can be
implemented as `>> log2_stride`; pymtl3's Verilog translator does not
support integer `//`. This restricts stride to powers of two (1, 2,
4, ...).

Emit convention: output i (0-based, ox innermost -> oy -> kx -> ky) is
stored to shared data_mem addr (dst_sram_base_addr + i).

Note on packet dst_tile: CMD_STORE_REQUEST packets are routed by the
CGRA controller using the payload.data_addr field alone (see
ControllerRTL.update_sending_to_noc_msg); the packet's dst_tile is
ignored on this path. The engine emits dst=0 for its store packets.

State machine: IDLE -> READ -> EMIT -> DONE
  IDLE: hold rdy=1; latch config on each CONFIG cmd, transition on LAUNCH.
  READ: assert the read on in_mem at in_addr(oy, ox, ky, kx).
  EMIT: hold the incoming data, drive send_pkt. On send_pkt fire,
        advance the nested loop counters and either loop back to READ
        or transition to DONE.
  DONE: assert `done` and stay here until reset.
"""

from pymtl3 import *

from ...lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ...lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ...lib.cmd_type import (CMD_IM2COL_DST_SRAM_BASE, CMD_IM2COL_H,
                              CMD_IM2COL_KH, CMD_IM2COL_KW,
                              CMD_IM2COL_LAUNCH, CMD_IM2COL_LOG2_STRIDE,
                              CMD_IM2COL_W, CMD_STORE_REQUEST)
from ...lib.util.data_struct_attr import kAttrCmd, kAttrDataAddr, kAttrPayload
from ...mem.data.DataMemRTL import DataMemRTL


class Im2colEngineRTL(Component):

  def construct(s, DataType, IntraCgraPktType, CgraPayloadType,
                scratch_mem_size,
                preload_image):

    # Derive widths from the passed-in packet types so the engine stays
    # generic across CGRA configurations.
    ScratchAddrType = mk_bits(clog2(scratch_mem_size))
    PayloadType     = IntraCgraPktType.get_field_type(kAttrPayload)
    CmdType         = PayloadType.get_field_type(kAttrCmd)
    DataAddrType    = PayloadType.get_field_type(kAttrDataAddr)

    # emit_idx must fit any valid destination offset within data_mem.
    IdxType   = DataAddrType
    StateType = mk_bits(2)

    S_IDLE = StateType(0)
    S_READ = StateType(1)
    S_EMIT = StateType(2)
    S_DONE = StateType(3)

    # Public I/O.
    s.recv_cmd_pkt = RecvIfcRTL(IntraCgraPktType)
    s.done         = OutPort(b1)
    s.send_pkt     = SendIfcRTL(IntraCgraPktType)

    # Input scratchpad: image preloaded starting at addr 0. Real deploys
    # would fill this via DMA/CPU writes prior to LAUNCH; the preload is
    # a modeling convenience for tests.
    preload_full = [DataType(0, 1) for _ in range(scratch_mem_size)]
    for i, v in enumerate(preload_image):
      preload_full[i] = DataType(v, 1)

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

    # Runtime config registers, latched by the corresponding CMD.
    s.cfg_H                    = Wire(ScratchAddrType)
    s.cfg_W                    = Wire(ScratchAddrType)
    s.cfg_kH                   = Wire(ScratchAddrType)
    s.cfg_kW                   = Wire(ScratchAddrType)
    s.cfg_log2_stride          = Wire(ScratchAddrType)
    s.cfg_dst_sram_base_addr   = Wire(DataAddrType)
    # Precomputed on LAUNCH so the S_EMIT loop-advance can compare
    # against a plain register instead of redoing (H-kH)>>log2_stride
    # each cycle.
    s.cfg_Hout = Wire(ScratchAddrType)
    s.cfg_Wout = Wire(ScratchAddrType)

    # Combinational address computation. Narrowing casts keep pymtl3's
    # AST analyzer happy on binop-result narrowing.
    s.in_row  = Wire(ScratchAddrType)
    s.in_col  = Wire(ScratchAddrType)
    s.in_addr = Wire(ScratchAddrType)

    @update
    def comb_in_addr():
      # ox*stride and oy*stride are shifts because stride is stored as
      # its log2 (Verilog translator has no `//` but supports `>>`/`<<`).
      # Image is assumed to live at in_mem[0..); no base offset.
      s.in_row  @= ScratchAddrType((s.oy << s.cfg_log2_stride) + s.ky)
      s.in_col  @= ScratchAddrType((s.ox << s.cfg_log2_stride) + s.kx)
      s.in_addr @= ScratchAddrType(s.in_row * s.cfg_W + s.in_col)

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

      # Config/launch cmds are accepted only while idle.
      s.recv_cmd_pkt.rdy @= (s.state == S_IDLE)

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
                s.cfg_dst_sram_base_addr + zext(s.emit_idx, DataAddrType),
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
          if s.recv_cmd_pkt.val:
            cmd = s.recv_cmd_pkt.msg.payload.cmd
            # data field carries numeric config values; take the low
            # ScratchAddrType.nbits bits.
            data_lo = trunc(s.recv_cmd_pkt.msg.payload.data.payload,
                            ScratchAddrType)
            # data_addr field carries SRAM offsets directly.
            data_addr = s.recv_cmd_pkt.msg.payload.data_addr

            if   cmd == CmdType(CMD_IM2COL_H):
              s.cfg_H            <<= data_lo
            elif cmd == CmdType(CMD_IM2COL_W):
              s.cfg_W            <<= data_lo
            elif cmd == CmdType(CMD_IM2COL_KH):
              s.cfg_kH           <<= data_lo
            elif cmd == CmdType(CMD_IM2COL_KW):
              s.cfg_kW           <<= data_lo
            elif cmd == CmdType(CMD_IM2COL_LOG2_STRIDE):
              s.cfg_log2_stride  <<= data_lo
            elif cmd == CmdType(CMD_IM2COL_DST_SRAM_BASE):
              s.cfg_dst_sram_base_addr <<= data_addr
            elif cmd == CmdType(CMD_IM2COL_LAUNCH):
              # Precompute Hout/Wout from the currently-latched config.
              s.cfg_Hout <<= ScratchAddrType(
                  ((s.cfg_H - s.cfg_kH) >> s.cfg_log2_stride) + 1)
              s.cfg_Wout <<= ScratchAddrType(
                  ((s.cfg_W - s.cfg_kW) >> s.cfg_log2_stride) + 1)
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
            # walks the flat output index monotonically. This lets the
            # store addr be a simple dst_sram_base_addr + emit_idx sum.
            if s.ox + ScratchAddrType(1) < s.cfg_Wout:
              s.ox    <<= s.ox + ScratchAddrType(1)
              s.state <<= S_READ
            elif s.oy + ScratchAddrType(1) < s.cfg_Hout:
              s.ox    <<= ScratchAddrType(0)
              s.oy    <<= s.oy + ScratchAddrType(1)
              s.state <<= S_READ
            elif s.kx + ScratchAddrType(1) < s.cfg_kW:
              s.ox    <<= ScratchAddrType(0)
              s.oy    <<= ScratchAddrType(0)
              s.kx    <<= s.kx + ScratchAddrType(1)
              s.state <<= S_READ
            elif s.ky + ScratchAddrType(1) < s.cfg_kH:
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
