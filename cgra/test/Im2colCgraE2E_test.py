"""
==========================================================================
Im2colCgraE2E_test.py
==========================================================================
End-to-end tests that wire the Im2colToCgraBridge in front of the 3x3
weight-stationary systolic CGRA from CgraRTL_test.test_systolic_3x3.

The bridge runs Im2col on a small preloaded image, emits the lowered
matrix as a sequence of CMD_STORE_REQUEST packets into the CGRA's
CPU-facing packet interface, and then yields the packet bus to the
ordinary systolic configuration / launch stream.

Two tests:

  test_im2col_to_systolic_3x3
      Smoke test of the bridge wiring. Picks an image so the lowered
      matrix matches the original systolic activations [1,2,3,4] and
      asserts on the original [14,20,30,44] outputs.

  test_im2col_conv1d_to_systolic_3x3
      A real conv1d through the pipeline. The systolic PE weights are
      derived from filter coefficients and the expected memory contents
      come from a Python golden conv. The test passes iff the full
      image -> im2col -> bridge -> systolic matmul -> memory pipeline
      computes the conv correctly.

L/F/A/W mapping (conv as matmul through this systolic):
  L : lowered matrix, shape (kH*kW) x (Hout*Wout).
  F : filter bank,    shape (K) x (kH*kW), K = number of output channels.
  A : systolic input matrix, indexed [time][input_row]. The two feeder
      tiles (tile 6 and tile 3) each stream one column of A over time:
        A[t][0] = L[0][t]  (tile 6 streams)
        A[t][1] = L[1][t]  (tile 3 streams)
  W : systolic PE weights, indexed [input_row][output_col]. With 2 input
      rows and 2 output cols laid out across tiles 7/8/4/5:
        W[0][0] = tile 7    W[0][1] = tile 8
        W[1][0] = tile 4    W[1][1] = tile 5
      and W[i][k] = F[k][i].

The systolic computes Q[t][k] = sum_i A[t][i] * W[i][k] = O[k][t] where
O = F . L is the conv output. Memory sinks then store:
  addr 4,5 = O[0][0..1]   (output channel 0 over the spatial axis)
  addr 6,7 = O[1][0..1]   (output channel 1)
"""

from pymtl3 import *
from pymtl3.passes.backends.verilog import VerilogVerilatorImportPass
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)

from ..CgraRTL import CgraRTL
from ..Im2colToCgraBridge import Im2colToCgraBridge
from ...fu.double.SeqMulAdderRTL import SeqMulAdderRTL
from ...fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from ...fu.float.FpAddRTL import FpAddRTL
from ...fu.float.FpMulRTL import FpMulRTL
from ...fu.single.AdderRTL import AdderRTL
from ...fu.single.CompRTL import CompRTL
from ...fu.single.GrantRTL import GrantRTL
from ...fu.single.LogicRTL import LogicRTL
from ...fu.single.MemUnitRTL import MemUnitRTL
from ...fu.single.MulRTL import MulRTL
from ...fu.single.PhiRTL import PhiRTL
from ...fu.single.SelRTL import SelRTL
from ...fu.single.ShifterRTL import ShifterRTL
from ...fu.vector.VectorAdderComboRTL import VectorAdderComboRTL
from ...fu.vector.VectorMulComboRTL import VectorMulComboRTL
from ...lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ...lib.cmd_type import *
from ...lib.messages import *
from ...lib.opt_type import *
from ...lib.util.common import *


#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, FuList, IntraCgraPktType, CgraPayloadType, DataType,
                cgra_id, width, height,
                ctrl_mem_size, data_mem_size_global,
                data_mem_size_per_bank, num_banks_per_cgra,
                num_registers_per_reg_bank,
                src_ctrl_pkt, ctrl_steps,
                mem_access_is_combinational,
                topology, controller2addr_map,
                idTo2d_map, complete_signal_sink_out,
                multi_cgra_rows, multi_cgra_columns, src_query_pkt,
                bridge_image, bridge_geom, bridge_dst_tiles,
                bridge_data_addrs, bridge_scratch_mem_size):

    DataAddrType = mk_bits(clog2(data_mem_size_global))
    s.num_tiles = width * height
    s.src_ctrl_pkt  = TestSrcRTL(IntraCgraPktType, src_ctrl_pkt)
    s.src_query_pkt = TestSrcRTL(IntraCgraPktType, src_query_pkt)

    s.bridge = Im2colToCgraBridge(
        DataType, IntraCgraPktType, CgraPayloadType,
        bridge_scratch_mem_size,
        bridge_geom['in_base'],  bridge_geom['out_base'],
        bridge_geom['H'],        bridge_geom['W'],
        bridge_geom['kH'],       bridge_geom['kW'],
        bridge_geom['stride'],
        bridge_dst_tiles,        bridge_data_addrs,
        bridge_image)

    s.dut = CgraRTL(CgraPayloadType,
                    multi_cgra_rows, multi_cgra_columns,
                    width, height, ctrl_mem_size,
                    data_mem_size_global, data_mem_size_per_bank,
                    num_banks_per_cgra, num_registers_per_reg_bank,
                    ctrl_steps, ctrl_steps,
                    mem_access_is_combinational,
                    FlexibleFuRTL, FuList, topology,
                    controller2addr_map, idTo2d_map,
                    is_multi_cgra = False)

    cmp_fn = lambda a, b: (a.payload.data == b.payload.data and
                           a.payload.cmd  == b.payload.cmd)
    s.complete_signal_sink_out = TestSinkRTL(IntraCgraPktType,
                                             complete_signal_sink_out,
                                             cmp_fn = cmp_fn)

    s.dut.cgra_id //= cgra_id
    s.complete_signal_sink_out.recv //= s.dut.send_to_cpu_pkt

    complete_count_value = sum(1 for pkt in complete_signal_sink_out
                               if pkt.payload.cmd == CMD_COMPLETE)
    CompleteCountType = mk_bits(clog2(complete_count_value + 1))
    s.complete_count = Wire(CompleteCountType)

    # One-cycle start pulse for the bridge after reset.
    s.bridge_started = Wire(b1)

    @update
    def drive_bridge_start():
      s.bridge.start @= ~s.bridge_started

    @update_ff
    def update_bridge_started():
      if s.reset:
        s.bridge_started <<= b1(0)
      else:
        s.bridge_started <<= b1(1)

    # Three-way packet arbiter into recv_from_cpu_pkt: bridge (preload)
    # first, then the ordinary systolic ctrl stream, then queries.
    @update
    def issue_pkt():
      s.dut.recv_from_cpu_pkt.val @= b1(0)
      s.dut.recv_from_cpu_pkt.msg @= IntraCgraPktType()
      s.bridge.send_pkt.rdy       @= b1(0)
      s.src_ctrl_pkt.send.rdy     @= b1(0)
      s.src_query_pkt.send.rdy    @= b1(0)

      if ~s.bridge.done:
        s.dut.recv_from_cpu_pkt.val @= s.bridge.send_pkt.val
        s.dut.recv_from_cpu_pkt.msg @= s.bridge.send_pkt.msg
        s.bridge.send_pkt.rdy       @= s.dut.recv_from_cpu_pkt.rdy
      elif (s.complete_count >= complete_count_value) & \
           ~s.src_ctrl_pkt.send.val:
        s.dut.recv_from_cpu_pkt.val @= s.src_query_pkt.send.val
        s.dut.recv_from_cpu_pkt.msg @= s.src_query_pkt.send.msg
        s.src_query_pkt.send.rdy    @= s.dut.recv_from_cpu_pkt.rdy
      else:
        s.dut.recv_from_cpu_pkt.val @= s.src_ctrl_pkt.send.val
        s.dut.recv_from_cpu_pkt.msg @= s.src_ctrl_pkt.send.msg
        s.src_ctrl_pkt.send.rdy     @= s.dut.recv_from_cpu_pkt.rdy

    @update_ff
    def update_complete_count():
      if s.reset:
        s.complete_count <<= 0
      else:
        if s.complete_signal_sink_out.recv.val & \
           s.complete_signal_sink_out.recv.rdy & \
           (s.complete_count < complete_count_value):
          s.complete_count <<= s.complete_count + CompleteCountType(1)

    s.dut.address_lower //= DataAddrType(controller2addr_map[cgra_id][0])
    s.dut.address_upper //= DataAddrType(controller2addr_map[cgra_id][1])

    for tile_col in range(width):
      s.dut.send_data_on_boundary_north[tile_col].rdy //= 0
      s.dut.recv_data_on_boundary_north[tile_col].val //= 0
      s.dut.recv_data_on_boundary_north[tile_col].msg //= DataType()

      s.dut.send_data_on_boundary_south[tile_col].rdy //= 0
      s.dut.recv_data_on_boundary_south[tile_col].val //= 0
      s.dut.recv_data_on_boundary_south[tile_col].msg //= DataType()

    for tile_row in range(height):
      s.dut.send_data_on_boundary_west[tile_row].rdy //= 0
      s.dut.recv_data_on_boundary_west[tile_row].val //= 0
      s.dut.recv_data_on_boundary_west[tile_row].msg //= DataType()

      s.dut.send_data_on_boundary_east[tile_row].rdy //= 0
      s.dut.recv_data_on_boundary_east[tile_row].val //= 0
      s.dut.recv_data_on_boundary_east[tile_row].msg //= DataType()

  def done(s):
    return (s.src_ctrl_pkt.done() and s.src_query_pkt.done()
            and s.complete_signal_sink_out.done())

  def line_trace(s):
    return s.bridge.line_trace() + ' || ' + s.dut.line_trace()


#-------------------------------------------------------------------------
# Build the systolic config (minus the activation preload, which the
# bridge supplies) and the matching expected outputs.
#-------------------------------------------------------------------------

def build_systolic_packets(IntraCgraPktType, CgraPayloadType, CtrlType,
                           DataType, TileInType, FuInType, FuOutType,
                           updated_ctrl_steps, pe_weights, expected_outputs):
  """Build the systolic config / launch / query packet streams.

  pe_weights      : dict mapping tile id (7, 4, 8, 5) to its MUL_CONST weight.
  expected_outputs: dict mapping addr (4, 5, 6, 7) to expected stored value.
  """
  fu_in_code = [FuInType(x + 1) for x in range(4)]
  ZX = TileInType(0)
  Z2 = FuOutType(0)

  def cfg(tile, opt, routing, fu_xbar):
    return IntraCgraPktType(0, tile,
        payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                  ctrl = CtrlType(opt, fu_in_code,
                                                  routing, fu_xbar)))

  def header(tile, consts):
    pkts = []
    for c in consts:
      pkts.append(IntraCgraPktType(0, tile,
          payload = CgraPayloadType(CMD_CONST, data = DataType(c, 1))))
    pkts.append(IntraCgraPktType(0, tile,
        payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER,
                                  data = DataType(1, 1))))
    pkts.append(IntraCgraPktType(0, tile,
        payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT,
                                  data = DataType(updated_ctrl_steps, 1))))
    return pkts

  src_opt_pkt = [
      header(6, [0, 1]) + [
          cfg(6, OPT_LD_CONST, [ZX]*8,
              [Z2, Z2, Z2, FuOutType(1), Z2, Z2, Z2, Z2]),
          IntraCgraPktType(0, 6, payload = CgraPayloadType(CMD_LAUNCH)),
      ],
      header(3, [2, 3]) + [
          cfg(3, OPT_LD_CONST, [ZX]*8,
              [Z2, Z2, Z2, FuOutType(1), Z2, Z2, Z2, Z2]),
          IntraCgraPktType(0, 3, payload = CgraPayloadType(CMD_LAUNCH)),
      ],
      header(7, [pe_weights[7]]) + [
          cfg(7, OPT_MUL_CONST,
              [ZX, ZX, ZX, TileInType(3), TileInType(3), ZX, ZX, ZX],
              [Z2, FuOutType(1), Z2, Z2, Z2, Z2, Z2, Z2]),
          IntraCgraPktType(0, 7, payload = CgraPayloadType(CMD_LAUNCH)),
      ],
      header(4, [pe_weights[4]]) + [
          cfg(4, OPT_MUL_CONST_ADD,
              [ZX, ZX, ZX, TileInType(3),
               TileInType(3), ZX, TileInType(1), ZX],
              [Z2, FuOutType(1), Z2, Z2, Z2, Z2, Z2, Z2]),
          IntraCgraPktType(0, 4, payload = CgraPayloadType(CMD_LAUNCH)),
      ],
      header(1, [4, 5]) + [
          cfg(1, OPT_STR_CONST,
              [ZX, ZX, ZX, ZX, TileInType(1), ZX, ZX, ZX],
              [Z2]*8),
          IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_LAUNCH)),
      ],
      header(8, [pe_weights[8]]) + [
          cfg(8, OPT_MUL_CONST,
              [ZX, ZX, ZX, ZX, TileInType(3), ZX, ZX, ZX],
              [Z2, FuOutType(1), Z2, Z2, Z2, Z2, Z2, Z2]),
          IntraCgraPktType(0, 8, payload = CgraPayloadType(CMD_LAUNCH)),
      ],
      header(5, [pe_weights[5]]) + [
          cfg(5, OPT_MUL_CONST_ADD,
              [ZX, ZX, ZX, ZX,
               TileInType(3), ZX, TileInType(1), ZX],
              [Z2, FuOutType(1), Z2, Z2, Z2, Z2, Z2, Z2]),
          IntraCgraPktType(0, 5, payload = CgraPayloadType(CMD_LAUNCH)),
      ],
      header(2, [6, 7]) + [
          cfg(2, OPT_STR_CONST,
              [ZX, ZX, ZX, ZX, TileInType(1), ZX, ZX, ZX],
              [Z2]*8),
          IntraCgraPktType(0, 2, payload = CgraPayloadType(CMD_LAUNCH)),
      ],
  ]

  query_pkt = [
      IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = 4)),
      IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = 5)),
      IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = 6)),
      IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = 7)),
  ]

  expected_complete = [IntraCgraPktType(
                           payload = CgraPayloadType(CMD_COMPLETE))
                       for _ in range(8)]
  expected_mem = [
      IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_RESPONSE,
                                                 data = DataType(expected_outputs[addr], 1),
                                                 data_addr = addr))
      for addr in (4, 5, 6, 7)
  ]

  flat = []
  for group in src_opt_pkt:
    flat.extend(group)
  return flat, query_pkt, expected_complete + expected_mem


#-------------------------------------------------------------------------
# Tests
#-------------------------------------------------------------------------

def test_im2col_to_systolic_3x3(cmdline_opts):
  topology              = "Mesh"
  x_tiles               = 3
  y_tiles               = 3
  data_bitwidth         = 32
  ctrl_mem_size         = 6
  data_mem_size_global  = 128
  data_mem_size_per_bank = 16
  num_banks_per_cgra    = 2
  num_cgra_columns      = 4
  num_cgra_rows         = 1
  num_cgras             = num_cgra_columns * num_cgra_rows
  num_registers_per_reg_bank = 16
  num_tile_inports      = 4   # Mesh
  num_tile_outports     = 4
  num_fu_inports        = 4
  num_fu_outports       = 2
  num_tiles             = x_tiles * y_tiles
  num_rd_tiles          = x_tiles + y_tiles - 1
  per_cgra_data_size    = data_mem_size_global // num_cgras
  updated_ctrl_steps    = 2
  ctrl_steps            = 2

  FuList = [AdderRTL, MulRTL, LogicRTL, ShifterRTL, PhiRTL, CompRTL,
            GrantRTL, MemUnitRTL, SelRTL, FpAddRTL, FpMulRTL,
            SeqMulAdderRTL, VectorMulComboRTL, VectorAdderComboRTL]

  DataAddrType = mk_bits(clog2(data_mem_size_global))
  CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
  DataType     = mk_data(data_bitwidth, 1)
  # Width must accommodate tile inports AND register-bank inports
  # (mk_ctrl was widened upstream when read-from-reg routing was added).
  TileInType   = mk_bits(clog2(num_tile_inports + num_fu_inports + 1))
  FuInType     = mk_bits(clog2(num_fu_inports + 1))
  FuOutType    = mk_bits(clog2(num_fu_outports + 1))

  CtrlType = mk_ctrl(num_fu_inports, num_fu_outports,
                     num_tile_inports, num_tile_outports,
                     num_registers_per_reg_bank)
  CgraPayloadType = mk_cgra_payload(DataType, DataAddrType,
                                    CtrlType, CtrlAddrType)
  IntraCgraPktType = mk_intra_cgra_pkt(num_cgra_columns, num_cgra_rows,
                                       num_tiles, CgraPayloadType)

  cgra_id = 0
  controller2addr_map = {i: [i * per_cgra_data_size,
                             (i + 1) * per_cgra_data_size - 1]
                         for i in range(num_cgras)}
  idTo2d_map = {0: [0, 0], 1: [1, 0], 2: [2, 0], 3: [3, 0]}

  # Bridge inputs: image + geometry chosen so lowered matrix == [1,2,3,4],
  # i.e. the same activation values the original systolic test preloads.
  bridge_image = [1, 3, 2, 4]
  bridge_geom = dict(in_base = 0, out_base = 16,
                     H = 1, W = 4, kH = 1, kW = 2, stride = 2)
  bridge_dst_tiles  = [6, 6, 3, 3]
  bridge_data_addrs = [0, 1, 2, 3]
  bridge_scratch_mem_size = 64

  # Original systolic weights and expected outputs (verbatim from
  # CgraRTL_test.test_systolic_3x3).
  pe_weights       = {7: 2, 4: 4, 8: 6, 5: 8}
  expected_outputs = {4: 0x0e, 5: 0x14, 6: 0x1e, 7: 0x2c}

  src_ctrl_pkt, src_query_pkt, complete_signal_sink_out = \
      build_systolic_packets(IntraCgraPktType, CgraPayloadType, CtrlType,
                             DataType, TileInType, FuInType, FuOutType,
                             updated_ctrl_steps, pe_weights, expected_outputs)

  th = TestHarness(FuList, IntraCgraPktType, CgraPayloadType, DataType,
                   cgra_id, x_tiles, y_tiles,
                   ctrl_mem_size, data_mem_size_global,
                   data_mem_size_per_bank, num_banks_per_cgra,
                   num_registers_per_reg_bank,
                   src_ctrl_pkt, ctrl_steps,
                   True, topology,
                   controller2addr_map, idTo2d_map,
                   complete_signal_sink_out,
                   num_cgra_rows, num_cgra_columns, src_query_pkt,
                   bridge_image, bridge_geom, bridge_dst_tiles,
                   bridge_data_addrs, bridge_scratch_mem_size)

  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                      ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                       'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)


#-------------------------------------------------------------------------
# Software golden 1D conv.
#-------------------------------------------------------------------------

def golden_conv1d(image, filters, stride):
  """1D convolution with K output channels and a kW filter per channel.

  image   : list of W ints (single-channel 1D signal).
  filters : list of K filter lists, each of length kW.
  stride  : int.
  Returns a list of K lists, each of length Wout.
  """
  W = len(image)
  K = len(filters)
  kW = len(filters[0])
  Wout = (W - kW) // stride + 1
  out = [[0] * Wout for _ in range(K)]
  for k in range(K):
    for ox in range(Wout):
      for kx in range(kW):
        out[k][ox] += image[ox * stride + kx] * filters[k][kx]
  return out


def test_im2col_conv1d_to_systolic_3x3(cmdline_opts):
  """End-to-end 1D conv: image -> im2col -> systolic matmul -> conv output.

  Computes conv1d(image, filters, stride=1) where image is length 3 and
  there are 2 output channels with 1x2 filters. The lowered matrix is
  shape 2 (kH*kW) x 2 (Wout), and the systolic array (configured as a
  2x2 matmul A x W) multiplies it against the filter weights, yielding
  output[k][ox] at memory addrs:
    addr 4 = output[0][0]   addr 5 = output[0][1]
    addr 6 = output[1][0]   addr 7 = output[1][1]
  """
  # Conv inputs.
  image   = [1, 2, 3]            # H=1, W=3
  filters = [[1, 1], [2, 1]]     # 2 filters of size 1x2 (kH=1, kW=2)
  stride  = 1
  H, W, kH, kW = 1, 3, 1, 2

  # Python golden.
  expected = golden_conv1d(image, filters, stride)
  assert expected == [[3, 5], [4, 7]]
  expected_outputs = {4: expected[0][0], 5: expected[0][1],
                      6: expected[1][0], 7: expected[1][1]}

  # Systolic PE weights derived from the filter coefficients.
  # See file docstring for the L/F/A/W mapping:
  #   tile 7 = F[0][0]  (filter 0, position 0)
  #   tile 4 = F[0][1]  (filter 0, position 1)
  #   tile 8 = F[1][0]
  #   tile 5 = F[1][1]
  pe_weights = {7: filters[0][0], 4: filters[0][1],
                8: filters[1][0], 5: filters[1][1]}

  # CGRA / mesh parameters (mirror test_im2col_to_systolic_3x3).
  topology              = "Mesh"
  x_tiles               = 3
  y_tiles               = 3
  data_bitwidth         = 32
  ctrl_mem_size         = 6
  data_mem_size_global  = 128
  data_mem_size_per_bank = 16
  num_banks_per_cgra    = 2
  num_cgra_columns      = 4
  num_cgra_rows         = 1
  num_cgras             = num_cgra_columns * num_cgra_rows
  num_registers_per_reg_bank = 16
  num_tile_inports      = 4
  num_tile_outports     = 4
  num_fu_inports        = 4
  num_fu_outports       = 2
  num_tiles             = x_tiles * y_tiles
  per_cgra_data_size    = data_mem_size_global // num_cgras
  updated_ctrl_steps    = 2
  ctrl_steps            = 2

  FuList = [AdderRTL, MulRTL, LogicRTL, ShifterRTL, PhiRTL, CompRTL,
            GrantRTL, MemUnitRTL, SelRTL, FpAddRTL, FpMulRTL,
            SeqMulAdderRTL, VectorMulComboRTL, VectorAdderComboRTL]

  DataAddrType = mk_bits(clog2(data_mem_size_global))
  CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
  DataType     = mk_data(data_bitwidth, 1)
  # Width must accommodate tile inports AND register-bank inports
  # (mk_ctrl was widened upstream when read-from-reg routing was added).
  TileInType   = mk_bits(clog2(num_tile_inports + num_fu_inports + 1))
  FuInType     = mk_bits(clog2(num_fu_inports + 1))
  FuOutType    = mk_bits(clog2(num_fu_outports + 1))

  CtrlType = mk_ctrl(num_fu_inports, num_fu_outports,
                     num_tile_inports, num_tile_outports,
                     num_registers_per_reg_bank)
  CgraPayloadType = mk_cgra_payload(DataType, DataAddrType,
                                    CtrlType, CtrlAddrType)
  IntraCgraPktType = mk_intra_cgra_pkt(num_cgra_columns, num_cgra_rows,
                                       num_tiles, CgraPayloadType)

  cgra_id = 0
  controller2addr_map = {i: [i * per_cgra_data_size,
                             (i + 1) * per_cgra_data_size - 1]
                         for i in range(num_cgras)}
  idTo2d_map = {0: [0, 0], 1: [1, 0], 2: [2, 0], 3: [3, 0]}

  src_ctrl_pkt, src_query_pkt, complete_signal_sink_out = \
      build_systolic_packets(IntraCgraPktType, CgraPayloadType, CtrlType,
                             DataType, TileInType, FuInType, FuOutType,
                             updated_ctrl_steps, pe_weights, expected_outputs)

  # Bridge: feed the natural conv image; im2col lowers it on the fly.
  # The lowered matrix (kH*kW x Wout = 2 x 2) flattens row-major to
  #   [I[0], I[1], I[1], I[2]] = [1, 2, 2, 3]
  # which the bridge then writes into tile-6 mem (addrs 0..1) and
  # tile-3 mem (addrs 2..3), exactly the layout the systolic expects.
  bridge_image = image
  bridge_geom = dict(in_base = 0, out_base = 16,
                     H = H, W = W, kH = kH, kW = kW, stride = stride)
  bridge_dst_tiles  = [6, 6, 3, 3]
  bridge_data_addrs = [0, 1, 2, 3]
  bridge_scratch_mem_size = 64

  th = TestHarness(FuList, IntraCgraPktType, CgraPayloadType, DataType,
                   cgra_id, x_tiles, y_tiles,
                   ctrl_mem_size, data_mem_size_global,
                   data_mem_size_per_bank, num_banks_per_cgra,
                   num_registers_per_reg_bank,
                   src_ctrl_pkt, ctrl_steps,
                   True, topology,
                   controller2addr_map, idTo2d_map,
                   complete_signal_sink_out,
                   num_cgra_rows, num_cgra_columns, src_query_pkt,
                   bridge_image, bridge_geom, bridge_dst_tiles,
                   bridge_data_addrs, bridge_scratch_mem_size)

  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                      ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                       'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)
