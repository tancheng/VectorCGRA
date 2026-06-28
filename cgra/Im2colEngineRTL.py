"""
==========================================================================
Im2colEngineRTL.py
==========================================================================
Packaged im2col engine: wraps the stand-alone Im2colRTL data mover with
a pair of scratchpads and a packet-emit FSM. After running Im2col on a
preloaded input image, it streams the lowered (kH*kW) x (Hout*Wout)
matrix to a CGRA's CPU-facing packet interface as a sequence of
CMD_STORE_REQUEST packets. The (dst_tile, data_addr) destination for
each emitted value is fixed at elaboration time by the dst_tiles /
data_addrs lists.

State machine: IDLE -> IM2COL -> EMIT -> DONE
- IDLE: wait for `start`; pulses Im2col's start on the IDLE->IM2COL edge.
- IM2COL: wait for the embedded Im2col to assert done.
- EMIT: walk out_mem[out_base .. out_base + num_outputs) and emit one
        STORE_REQUEST packet per value via send_pkt.
- DONE: assert `done` and stay here.
"""

from pymtl3 import *

from ..fu.single.Im2colRTL import Im2colRTL
from ..lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ..lib.cmd_type import CMD_STORE_REQUEST
from ..lib.util.data_struct_attr import (kAttrCmd, kAttrCtrl, kAttrCtrlAddr,
                                          kAttrData, kAttrDataAddr, kAttrDst,
                                          kAttrOpaque, kAttrPayload,
                                          kAttrSrcCgraId, kAttrSrcCgraX,
                                          kAttrSrcCgraY, kAttrVcId)
from ..mem.data.DataMemRTL import DataMemRTL


class Im2colEngineRTL(Component):

  def construct(s, DataType, IntraCgraPktType, CgraPayloadType,
                scratch_mem_size,
                in_base, out_base, H, W, kH, kW, stride,
                dst_tiles, data_addrs,
                preload_image):

    Hout = (H - kH) // stride + 1
    Wout = (W - kW) // stride + 1
    num_outputs = kH * kW * Hout * Wout
    assert len(dst_tiles)  == num_outputs
    assert len(data_addrs) == num_outputs

    # Derive widths from the passed-in packet types so the engine stays
    # generic across CGRA configurations.
    ScratchAddrType = mk_bits(clog2(scratch_mem_size))
    TileIdType      = IntraCgraPktType.get_field_type(kAttrDst)
    CgraIdType      = IntraCgraPktType.get_field_type(kAttrSrcCgraId)
    CgraXType       = IntraCgraPktType.get_field_type(kAttrSrcCgraX)
    CgraYType       = IntraCgraPktType.get_field_type(kAttrSrcCgraY)
    OpqType         = IntraCgraPktType.get_field_type(kAttrOpaque)
    VcIdType        = IntraCgraPktType.get_field_type(kAttrVcId)
    PayloadType     = IntraCgraPktType.get_field_type(kAttrPayload)
    CmdType         = PayloadType.get_field_type(kAttrCmd)
    DataAddrType    = PayloadType.get_field_type(kAttrDataAddr)
    CtrlType        = PayloadType.get_field_type(kAttrCtrl)
    CtrlAddrType    = PayloadType.get_field_type(kAttrCtrlAddr)

    IdxType   = mk_bits(max(1, clog2(num_outputs + 1)))
    StateType = mk_bits(2)

    S_IDLE   = StateType(0)
    S_IM2COL = StateType(1)
    S_EMIT   = StateType(2)
    S_DONE   = StateType(3)

    # Public I/O.
    s.start    = InPort(b1)
    s.done     = OutPort(b1)
    s.send_pkt = SendIfcRTL(IntraCgraPktType)

    # Pre-build the input scratchpad preload (image at [in_base, in_base+H*W)).
    preload_full = [DataType(0, 1) for _ in range(scratch_mem_size)]
    for i, v in enumerate(preload_image):
      preload_full[in_base + i] = DataType(v, 1)

    # Sub-components.
    s.im2col  = Im2colRTL(DataType, scratch_mem_size)
    s.in_mem  = DataMemRTL(DataType, scratch_mem_size,
                           rd_ports = 1, wr_ports = 1,
                           preload_data = preload_full)
    s.out_mem = DataMemRTL(DataType, scratch_mem_size,
                           rd_ports = 1, wr_ports = 1)

    connect(s.im2col.to_mem_raddr,   s.in_mem.recv_raddr[0])
    connect(s.im2col.from_mem_rdata, s.in_mem.send_rdata[0])
    connect(s.im2col.to_mem_waddr,   s.out_mem.recv_waddr[0])
    connect(s.im2col.to_mem_wdata,   s.out_mem.recv_wdata[0])

    # Im2col config: bake geometry as constants.
    s.im2col.cfg_in_base  //= ScratchAddrType(in_base)
    s.im2col.cfg_out_base //= ScratchAddrType(out_base)
    s.im2col.cfg_W        //= ScratchAddrType(W)
    s.im2col.cfg_kH       //= ScratchAddrType(kH)
    s.im2col.cfg_kW       //= ScratchAddrType(kW)
    s.im2col.cfg_stride   //= ScratchAddrType(stride)
    s.im2col.cfg_Hout     //= ScratchAddrType(Hout)
    s.im2col.cfg_Wout     //= ScratchAddrType(Wout)

    # FSM state.
    s.state    = Wire(StateType)
    s.emit_idx = Wire(IdxType)

    # Combinational dst/addr lookup (unrolled chain over emit_idx).
    s.cur_dst  = Wire(TileIdType)
    s.cur_addr = Wire(DataAddrType)

    # Per-output constant ROMs as Wire arrays. The verilator translator
    # accepts indexed access into Wire-arrays of bitstructs natively;
    # plain Python lists / tuples of pymtl3-typed values do not translate.
    s.dst_tile_rom  = [Wire(TileIdType)   for _ in range(num_outputs)]
    s.data_addr_rom = [Wire(DataAddrType) for _ in range(num_outputs)]
    for i in range(num_outputs):
      s.dst_tile_rom[i]  //= TileIdType(dst_tiles[i])
      s.data_addr_rom[i] //= DataAddrType(data_addrs[i])

    @update
    def select_dst_and_addr():
      s.cur_dst  @= s.dst_tile_rom[0]
      s.cur_addr @= s.data_addr_rom[0]
      for i in range(num_outputs):
        if s.emit_idx == IdxType(i):
          s.cur_dst  @= s.dst_tile_rom[i]
          s.cur_addr @= s.data_addr_rom[i]

    # Tie off the unused write port on the input scratchpad.
    @update
    def tie_off_in_mem_wr():
      s.in_mem.recv_waddr[0].val @= b1(0)
      s.in_mem.recv_waddr[0].msg @= ScratchAddrType(0)
      s.in_mem.recv_wdata[0].val @= b1(0)
      s.in_mem.recv_wdata[0].msg @= DataType()

    # Forward `start` to Im2col only while we are in IDLE; this gives Im2col
    # a single-cycle pulse on the IDLE->IM2COL transition and prevents the
    # re-trigger that would otherwise happen if start were held through
    # Im2col's S_DONE state.
    @update
    def drive_im2col_start():
      s.im2col.start @= (s.state == S_IDLE) & s.start

    # EMIT-phase packet construction. We pass integer zeros (rather than
    # type constructors like CtrlType()) for the don't-care fields so the
    # verilator translator can encode them as constants -- it can't handle
    # default constructors of bitstructs that contain list-of-bits fields
    # (e.g. the CtrlType.fu_in array) inside behavioral RTLIR.
    @update
    def build_send_pkt():
      s.out_mem.recv_raddr[0].val @= b1(0)
      s.out_mem.recv_raddr[0].msg @= ScratchAddrType(0)
      s.out_mem.send_rdata[0].rdy @= b1(0)
      s.done                      @= b1(0)
      s.send_pkt.val              @= b1(0)

      if s.state == S_EMIT:
        s.out_mem.recv_raddr[0].val @= b1(1)
        s.out_mem.recv_raddr[0].msg @= ScratchAddrType(out_base) + \
                                       zext(s.emit_idx, ScratchAddrType)
        s.out_mem.send_rdata[0].rdy @= s.send_pkt.rdy
        s.send_pkt.val              @= s.out_mem.send_rdata[0].val
        s.send_pkt.msg              @= IntraCgraPktType(
            0,             # src
            s.cur_dst,     # dst
            0, 0,          # src/dst cgra_id
            0, 0,          # src cgra x/y
            0, 0,          # dst cgra x/y
            0,             # opaque
            0,             # vc_id
            PayloadType(
                CmdType(CMD_STORE_REQUEST),
                s.out_mem.send_rdata[0].msg,
                s.cur_addr,
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
        s.emit_idx <<= IdxType(0)
      else:
        if s.state == S_IDLE:
          if s.start:
            s.state    <<= S_IM2COL
            s.emit_idx <<= IdxType(0)
        elif s.state == S_IM2COL:
          if s.im2col.done:
            s.state <<= S_EMIT
        elif s.state == S_EMIT:
          if s.send_pkt.val & s.send_pkt.rdy:
            if s.emit_idx + IdxType(1) >= IdxType(num_outputs):
              s.state <<= S_DONE
            else:
              s.emit_idx <<= s.emit_idx + IdxType(1)
        # S_DONE is terminal until reset.

  def line_trace(s):
    state_map = {0: "IDLE", 1: "IM2COL", 2: "EMIT", 3: "DONE"}
    st = state_map[int(s.state)]
    return (f"engine[{st} emit_idx={int(s.emit_idx)} done={int(s.done)} "
            f"send_val={int(s.send_pkt.val)} send_rdy={int(s.send_pkt.rdy)}] "
            f"|| im2col[{s.im2col.line_trace()}]")
