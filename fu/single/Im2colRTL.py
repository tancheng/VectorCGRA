"""
==========================================================================
Im2colRTL.py
==========================================================================
Stand-alone im2col (image-to-column) data mover. Reads an HxW single-
channel input image from one memory port and writes the lowered
(kH*kW) x (Hout*Wout) column matrix to a second memory port. Scalar
32-bit data, no padding.

Output layout (row-major flat):
  out[ky*kW + kx][oy*Wout + ox] = in[oy*stride + ky][ox*stride + kx]

The caller drives configuration ports and pulses `start`; `done` rises
once the entire matrix has been emitted. Configuration ports must be
held stable while the engine is running.
"""

from pymtl3 import *
from ...lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ...lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL


class Im2colRTL(Component):

  def construct(s, DataType, data_mem_size = 64):

    AddrType  = mk_bits(clog2(data_mem_size))
    StateType = mk_bits(2)

    S_IDLE  = StateType(0)
    S_READ  = StateType(1)
    S_WRITE = StateType(2)
    S_DONE  = StateType(3)

    # Configuration inputs (held stable while running).
    s.cfg_in_base  = InPort(AddrType)
    s.cfg_out_base = InPort(AddrType)
    s.cfg_W        = InPort(AddrType)
    s.cfg_kH       = InPort(AddrType)
    s.cfg_kW       = InPort(AddrType)
    s.cfg_stride   = InPort(AddrType)
    s.cfg_Hout     = InPort(AddrType)
    s.cfg_Wout     = InPort(AddrType)

    # Control.
    s.start = InPort(b1)
    s.done  = OutPort(b1)

    # Memory ports (input/output scratchpads live in the test harness).
    s.to_mem_raddr   = SendIfcRTL(AddrType)
    s.from_mem_rdata = RecvIfcRTL(DataType)
    s.to_mem_waddr   = SendIfcRTL(AddrType)
    s.to_mem_wdata   = SendIfcRTL(DataType)

    # State.
    s.state    = Wire(StateType)
    s.oy       = Wire(AddrType)
    s.ox       = Wire(AddrType)
    s.ky       = Wire(AddrType)
    s.kx       = Wire(AddrType)
    s.data_reg = Wire(DataType)

    # Combinational address computation.
    s.in_row   = Wire(AddrType)
    s.in_col   = Wire(AddrType)
    s.in_addr  = Wire(AddrType)
    s.out_row  = Wire(AddrType)
    s.out_col  = Wire(AddrType)
    s.out_addr = Wire(AddrType)
    s.patches  = Wire(AddrType)  # Hout * Wout

    @update
    def comb_addr():
      # AddrType(...) narrows the wider product/sum back to AddrType.nbits.
      # Slicing a BinOp expression directly trips pymtl3's AST analyzer,
      # so we wrap rather than slice.
      s.patches  @= AddrType(s.cfg_Hout * s.cfg_Wout)
      s.in_row   @= AddrType(s.oy * s.cfg_stride + s.ky)
      s.in_col   @= AddrType(s.ox * s.cfg_stride + s.kx)
      s.in_addr  @= AddrType(s.cfg_in_base + s.in_row * s.cfg_W + s.in_col)
      s.out_row  @= AddrType(s.ky * s.cfg_kW + s.kx)
      s.out_col  @= AddrType(s.oy * s.cfg_Wout + s.ox)
      s.out_addr @= AddrType(s.cfg_out_base + s.out_row * s.patches + s.out_col)

    @update
    def comb_io():
      s.to_mem_raddr.val   @= b1(0)
      s.to_mem_raddr.msg   @= AddrType(0)
      s.from_mem_rdata.rdy @= b1(0)
      s.to_mem_waddr.val   @= b1(0)
      s.to_mem_waddr.msg   @= AddrType(0)
      s.to_mem_wdata.val   @= b1(0)
      s.to_mem_wdata.msg   @= DataType()
      s.done               @= b1(0)

      if s.state == S_READ:
        s.to_mem_raddr.val   @= b1(1)
        s.to_mem_raddr.msg   @= s.in_addr
        s.from_mem_rdata.rdy @= b1(1)
      elif s.state == S_WRITE:
        s.to_mem_waddr.val @= b1(1)
        s.to_mem_waddr.msg @= s.out_addr
        s.to_mem_wdata.val @= b1(1)
        s.to_mem_wdata.msg @= s.data_reg
      elif s.state == S_DONE:
        s.done @= b1(1)

    @update_ff
    def seq():
      if s.reset:
        s.state    <<= S_IDLE
        s.oy       <<= AddrType(0)
        s.ox       <<= AddrType(0)
        s.ky       <<= AddrType(0)
        s.kx       <<= AddrType(0)
        s.data_reg <<= DataType()
      else:
        if s.state == S_IDLE:
          if s.start:
            s.oy    <<= AddrType(0)
            s.ox    <<= AddrType(0)
            s.ky    <<= AddrType(0)
            s.kx    <<= AddrType(0)
            s.state <<= S_READ

        elif s.state == S_READ:
          if s.to_mem_raddr.rdy & s.from_mem_rdata.val:
            s.data_reg <<= s.from_mem_rdata.msg
            s.state    <<= S_WRITE

        elif s.state == S_WRITE:
          if s.to_mem_waddr.rdy & s.to_mem_wdata.rdy:
            # Nested-loop counter advance (kx -> ky -> ox -> oy).
            if s.kx + AddrType(1) < s.cfg_kW:
              s.kx    <<= s.kx + AddrType(1)
              s.state <<= S_READ
            elif s.ky + AddrType(1) < s.cfg_kH:
              s.kx    <<= AddrType(0)
              s.ky    <<= s.ky + AddrType(1)
              s.state <<= S_READ
            elif s.ox + AddrType(1) < s.cfg_Wout:
              s.kx    <<= AddrType(0)
              s.ky    <<= AddrType(0)
              s.ox    <<= s.ox + AddrType(1)
              s.state <<= S_READ
            elif s.oy + AddrType(1) < s.cfg_Hout:
              s.kx    <<= AddrType(0)
              s.ky    <<= AddrType(0)
              s.ox    <<= AddrType(0)
              s.oy    <<= s.oy + AddrType(1)
              s.state <<= S_READ
            else:
              s.state <<= S_DONE

        elif s.state == S_DONE:
          if s.start:
            s.state <<= S_IDLE

  def line_trace(s):
    state_map = {0: "IDLE", 1: "READ", 2: "WRITE", 3: "DONE"}
    st = state_map[int(s.state)]
    return (f"[{st}] oy={int(s.oy)} ox={int(s.ox)} "
            f"ky={int(s.ky)} kx={int(s.kx)} "
            f"in_addr={int(s.in_addr)} out_addr={int(s.out_addr)} "
            f"data_reg={s.data_reg} done={int(s.done)}")
