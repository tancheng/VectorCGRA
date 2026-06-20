"""
==========================================================================
Im2colRTL_test.py
==========================================================================
Tests the stand-alone Im2colRTL data mover. The harness wires the DUT to
two DataMemRTL scratchpads (one preloaded with the input image, one
empty for the lowered output matrix) and verifies the post-run output
memory contents against a software golden im2col.
"""

from pymtl3 import *
from pymtl3.stdlib.test_utils import config_model_with_cmdline_opts

from ..Im2colRTL import Im2colRTL
from ....lib.messages import mk_data
from ....mem.data.DataMemRTL import DataMemRTL


#-------------------------------------------------------------------------
# Software golden
#-------------------------------------------------------------------------

def golden_im2col(image, H, W, kH, kW, stride):
  Hout = (H - kH) // stride + 1
  Wout = (W - kW) // stride + 1
  out = [0] * (kH * kW * Hout * Wout)
  for oy in range(Hout):
    for ox in range(Wout):
      for ky in range(kH):
        for kx in range(kW):
          row = ky * kW + kx
          col = oy * Wout + ox
          out[row * (Hout * Wout) + col] = image[(oy * stride + ky) * W +
                                                 (ox * stride + kx)]
  return out, Hout, Wout


#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, DataType, data_mem_size, preload_image):

    AddrType = mk_bits(clog2(data_mem_size))

    s.dut = Im2colRTL(DataType, data_mem_size)

    s.in_mem = DataMemRTL(DataType, data_mem_size,
                          rd_ports = 1, wr_ports = 1,
                          preload_data = preload_image)
    s.out_mem = DataMemRTL(DataType, data_mem_size,
                           rd_ports = 1, wr_ports = 1)

    connect(s.dut.to_mem_raddr,   s.in_mem.recv_raddr[0])
    connect(s.dut.from_mem_rdata, s.in_mem.send_rdata[0])
    connect(s.dut.to_mem_waddr,   s.out_mem.recv_waddr[0])
    connect(s.dut.to_mem_wdata,   s.out_mem.recv_wdata[0])

    # Unused output-memory read port and input-memory write port are
    # tied off so RegisterFile sees a stable, deasserted request.
    @update
    def tie_off_unused():
      s.out_mem.recv_raddr[0].val @= b1(0)
      s.out_mem.recv_raddr[0].msg @= AddrType(0)
      s.out_mem.send_rdata[0].rdy @= b1(0)
      s.in_mem.recv_waddr[0].val  @= b1(0)
      s.in_mem.recv_waddr[0].msg  @= AddrType(0)
      s.in_mem.recv_wdata[0].val  @= b1(0)
      s.in_mem.recv_wdata[0].msg  @= DataType()

  def line_trace(s):
    return f"{s.dut.line_trace()} || in_mem[{s.in_mem.line_trace()}] || out_mem[{s.out_mem.line_trace()}]"


#-------------------------------------------------------------------------
# Simulation driver
#-------------------------------------------------------------------------

def run_im2col(image, H, W, kH, kW, stride, in_base, out_base,
               data_mem_size = 64, max_cycles = 500, cmdline_opts = None):

  DataType = mk_data(32, 1)
  AddrType = mk_bits(clog2(data_mem_size))

  expected, Hout, Wout = golden_im2col(image, H, W, kH, kW, stride)

  # Build preload list: image at [in_base, in_base+H*W), zeros elsewhere.
  preload = [DataType(0, 1) for _ in range(data_mem_size)]
  for i, v in enumerate(image):
    preload[in_base + i] = DataType(v, 1)

  th = TestHarness(DataType, data_mem_size, preload)
  if cmdline_opts is not None:
    th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  th.apply(DefaultPassGroup())
  th.sim_reset()

  # Drive configuration; assert start for one cycle.
  th.dut.cfg_in_base  @= AddrType(in_base)
  th.dut.cfg_out_base @= AddrType(out_base)
  th.dut.cfg_W        @= AddrType(W)
  th.dut.cfg_kH       @= AddrType(kH)
  th.dut.cfg_kW       @= AddrType(kW)
  th.dut.cfg_stride   @= AddrType(stride)
  th.dut.cfg_Hout     @= AddrType(Hout)
  th.dut.cfg_Wout     @= AddrType(Wout)
  th.dut.start        @= b1(1)
  th.sim_tick()
  th.dut.start        @= b1(0)

  ncycles = 1
  print()
  print(f"{ncycles}: {th.line_trace()}")
  while int(th.dut.done) == 0 and ncycles < max_cycles:
    th.sim_tick()
    ncycles += 1
    print(f"{ncycles}: {th.line_trace()}")

  assert ncycles < max_cycles, "im2col timed out"

  # One extra tick so the final write commits into the output reg_file.
  th.sim_tick()

  # Compare output-memory contents against software golden.
  out_len = kH * kW * Hout * Wout
  actual = [int(th.out_mem.reg_file.regs[out_base + i].payload)
            for i in range(out_len)]
  assert actual == expected, (
    f"im2col mismatch:\n  expected={expected}\n  actual={actual}")

  return th, ncycles


#-------------------------------------------------------------------------
# Tests
#-------------------------------------------------------------------------

def test_im2col_4x4_k2_s1(cmdline_opts):
  # Classic small case: 4x4 image, 2x2 kernel, stride 1 -> 3x3 output grid
  # and a 4x9 lowered matrix.
  image = list(range(16))
  run_im2col(image, H=4, W=4, kH=2, kW=2, stride=1,
             in_base=0, out_base=16, data_mem_size=64,
             cmdline_opts=cmdline_opts)


def test_im2col_4x4_k2_s2(cmdline_opts):
  # Stride 2: 4x4 / 2x2 / s2 -> 2x2 output, 4x4 lowered matrix.
  image = [i * 2 + 1 for i in range(16)]
  run_im2col(image, H=4, W=4, kH=2, kW=2, stride=2,
             in_base=0, out_base=16, data_mem_size=64,
             cmdline_opts=cmdline_opts)


def test_im2col_5x5_k3_s1(cmdline_opts):
  # 5x5 / 3x3 / s1 -> 3x3 output, 9x9 lowered matrix (81 elements).
  image = list(range(25))
  run_im2col(image, H=5, W=5, kH=3, kW=3, stride=1,
             in_base=0, out_base=32, data_mem_size=128,
             cmdline_opts=cmdline_opts)
