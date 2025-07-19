"""
==========================================================================
CgraRTL_test.py
==========================================================================
Test cases for CGRA with crossbar-based data memory and ring-based control
memory of each tile.

Author : Cheng Tan
  Date : Dec 22, 2024
"""

from pymtl3.passes.backends.verilog import (VerilogVerilatorImportPass)
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)

from ..CgraRTL import CgraRTL
from ...fu.double.SeqMulAdderRTL import SeqMulAdderRTL
from ...fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from ...fu.float.FpAddRTL import FpAddRTL
from ...fu.float.FpMulRTL import FpMulRTL
from ...fu.single.AdderRTL import AdderRTL
from ...fu.single.BranchRTL import BranchRTL
from ...fu.single.CompRTL import CompRTL
from ...fu.single.LogicRTL import LogicRTL
from ...fu.single.MemUnitRTL import MemUnitRTL
from ...fu.single.MulRTL import MulRTL
from ...fu.single.PhiRTL import PhiRTL
from ...fu.single.RetRTL import RetRTL
from ...fu.single.SelRTL import SelRTL
from ...fu.single.ShifterRTL import ShifterRTL
from ...fu.vector.VectorAdderComboRTL import VectorAdderComboRTL
from ...fu.vector.VectorMulComboRTL import VectorMulComboRTL
from ...lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ...lib.messages import *
from ...lib.opt_type import *


#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, DUT, FunctionUnit, FuList, DataType, PredicateType,
                CtrlPktType, CgraPayloadType, CtrlSignalType, NocPktType,
                ControllerIdType, cgra_id, width, height,
                ctrl_mem_size, data_mem_size_global,
                data_mem_size_per_bank, num_banks_per_cgra,
                num_registers_per_reg_bank,
                src_ctrl_pkt, ctrl_count_per_iter, total_ctrl_steps,
                controller2addr_map,
                idTo2d_map, complete_signal_sink_out,
                multi_cgra_rows, multi_cgra_columns, src_query_pkt):

    DataAddrType = mk_bits(clog2(data_mem_size_global))
    s.num_tiles = width * height
    s.src_ctrl_pkt = TestSrcRTL(CtrlPktType, src_ctrl_pkt)
    s.src_query_pkt = TestSrcRTL(CtrlPktType, src_query_pkt)

    s.dut = DUT(DataType, PredicateType, CtrlPktType, CgraPayloadType,
                CtrlSignalType, NocPktType, ControllerIdType,
                # CGRA terminals on x/y. Assume in total 4, though this
                # test is for single CGRA.
                multi_cgra_rows, multi_cgra_columns,
                width, height, ctrl_mem_size,
                data_mem_size_global, data_mem_size_per_bank,
                num_banks_per_cgra, num_registers_per_reg_bank,
                ctrl_count_per_iter, total_ctrl_steps, FunctionUnit,
                FuList, "Mesh", controller2addr_map, idTo2d_map,
                is_multi_cgra = False)

    cmp_fn = lambda a, b : a.payload.data == b.payload.data and a.payload.cmd == b.payload.cmd
    s.complete_signal_sink_out = TestSinkRTL(CtrlPktType, complete_signal_sink_out, cmp_fn = cmp_fn)

    # Connections
    s.dut.cgra_id //= cgra_id
    s.complete_signal_sink_out.recv //= s.dut.send_to_cpu_pkt

    complete_count_value = \
            sum(1 for pkt in complete_signal_sink_out \
                if pkt.payload.cmd == CMD_COMPLETE)

    CompleteCountType = mk_bits(clog2(complete_count_value + 1))
    s.complete_count = Wire(CompleteCountType)

    @update
    def conditional_issue_ctrl_or_query():
      s.dut.recv_from_cpu_pkt.val @= s.src_ctrl_pkt.send.val
      s.dut.recv_from_cpu_pkt.msg @= s.src_ctrl_pkt.send.msg
      s.src_ctrl_pkt.send.rdy @= 0
      s.src_query_pkt.send.rdy @= 0
      if (s.complete_count >= complete_count_value) & \
         ~s.src_ctrl_pkt.send.val:
        s.dut.recv_from_cpu_pkt.val @= s.src_query_pkt.send.val
        s.dut.recv_from_cpu_pkt.msg @= s.src_query_pkt.send.msg
        s.src_query_pkt.send.rdy @= s.dut.recv_from_cpu_pkt.rdy
      else:
        s.src_ctrl_pkt.send.rdy @= s.dut.recv_from_cpu_pkt.rdy

    @update_ff
    def update_complete_count():
      if s.reset:
        s.complete_count <<= 0
      else:
        if s.complete_signal_sink_out.recv.val & s.complete_signal_sink_out.recv.rdy & \
           (s.complete_count < complete_count_value):
          s.complete_count <<= s.complete_count + CompleteCountType(1)

    # Connects memory address upper and lower bound for each CGRA.
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
    return s.dut.line_trace()

def test_homogeneous_4x4_fir(cmdline_opts):
  FuList = [AdderRTL,
            MulRTL,
            LogicRTL,
            ShifterRTL,
            PhiRTL,
            CompRTL,
            BranchRTL,
            MemUnitRTL,
            SelRTL,
            RetRTL,
           ]
  x_tiles = 4
  y_tiles = 4
  data_bitwidth = 32
  tile_ports = 4
  num_tile_inports  = tile_ports
  num_tile_outports = tile_ports
  num_fu_inports = 4
  num_fu_outports = 2
  num_routing_outports = num_tile_outports + num_fu_inports
  ctrl_mem_size = 6
  # data_mem_size_global = 4096
  # data_mem_size_per_bank = 32
  # num_banks_per_cgra = 24
  data_mem_size_global = 128
  data_mem_size_per_bank = 16
  num_banks_per_cgra = 2
  num_cgra_columns = 4
  num_cgra_rows = 1
  num_cgras = num_cgra_columns * num_cgra_rows
  num_ctrl_operations = 64
  num_registers_per_reg_bank = 16
  TileInType = mk_bits(clog2(num_tile_inports + 1))
  FuInType = mk_bits(clog2(num_fu_inports + 1))
  FuOutType = mk_bits(clog2(num_fu_outports + 1))
  addr_nbits = clog2(data_mem_size_global)
  num_tiles = x_tiles * y_tiles
  per_cgra_data_size = int(data_mem_size_global / num_cgras)

  DUT = CgraRTL
  FunctionUnit = FlexibleFuRTL

  DataAddrType = mk_bits(addr_nbits)
  RegIdxType = mk_bits(clog2(num_registers_per_reg_bank))
  DataType = mk_data(data_bitwidth, 1)
  PredicateType = mk_predicate(1, 1)
  ControllerIdType = mk_bits(max(1, clog2(num_cgras)))
  cgra_id = 0
  controller2addr_map = {}
  # 0: [0,    1023]
  # 1: [1024, 2047]
  # 2: [2048, 3071]
  # 3: [3072, 4095]
  for i in range(num_cgras):
    controller2addr_map[i] = [i * per_cgra_data_size,
                              (i + 1) * per_cgra_data_size - 1]
  idTo2d_map = {
          0: [0, 0],
          1: [1, 0],
          2: [2, 0],
          3: [3, 0],
  }

  cgra_id_nbits = clog2(num_cgras)
  addr_nbits = clog2(data_mem_size_global)
  predicate_nbits = 1

  CtrlType = mk_ctrl(num_fu_inports,
                     num_fu_outports,
                     num_tile_inports,
                     num_tile_outports,
                     num_registers_per_reg_bank)
  
  CtrlAddrType = mk_bits(clog2(ctrl_mem_size))

  CgraPayloadType = mk_cgra_payload(DataType,
                                    DataAddrType,
                                    CtrlType,
                                    CtrlAddrType)

  InterCgraPktType = mk_inter_cgra_pkt(num_cgra_columns,
                                       num_cgra_rows,
                                       num_tiles,
                                       CgraPayloadType)

  IntraCgraPktType = mk_intra_cgra_pkt(num_cgra_columns,
                                       num_cgra_rows,
                                       num_tiles,
                                       CgraPayloadType)

  routing_xbar_code = [TileInType(0) for _ in range(num_routing_outports)]
  fu_xbar_code = [FuOutType(0) for _ in range(num_routing_outports)]
  write_reg_from_code = [b2(0) for _ in range(num_fu_inports)]
  # 2 indicates the FU xbar port (instead of const queue or routing xbar port).
  write_reg_from_code[0] = b2(2)
  read_reg_from_code = [b1(0) for _ in range(num_fu_inports)]
  read_reg_from_code[0] = b1(1)
  read_reg_idx_code = [RegIdxType(0) for _ in range(num_fu_inports)]

  src_ctrl_pkt = []
  complete_signal_sink_out = []
  src_query_pkt = []
  ctrl_count_per_iter = 4
  total_ctrl_steps = 8
  fu_in_code = [FuInType(x + 1) for x in range(num_fu_inports)]

  # TODO: make loop bound be parameterizable.
  # FIR kernel demo.
  '''
  // data = [10, 11, 12, 13, 14, 15, 0, ...] (two banks, each has 16 32-bit elements)
  // &input = 0 (addr)
  // &coeff = 2 (addr)
  // &sum = 11(st_const)'s const = 16 (addr)
  // 0(phi_const)'const = int i = 2
  // 1(phi_const)'const = 3

  int i = 2;
  int sum = 3;
  for (int i = 2; i < 4; ++i) {
    sum += input[i] * coeff[i];
  }

  // expected sum = 171 (0xab)
  '''

  # Corresponding DFG:
  # TODO: Need to support grant predicate operations, and
  # connect that with operation 1(phi_const).
  # https://github.com/tancheng/VectorCGRA/issues/149, and
  # fine-grained prologue is needed:
  # https://github.com/tancheng/VectorCGRA/issues/156.
  '''
         0(phi_const) <--┐
         /     |     \   |
       2(+)   4(+)    8(+)
      /    \           |
    3(ld) 5(ld)       9(cmp)
      \    /           
       6(x)            
         |             
       7(+) <---┐      
         |  \   |      
     11(st)  1(phi_const)
  '''

  # Corresponding mapping:
  '''
       ↑ Y
  (0,3)|       🔳
  (0,2)|    ...
  (0,1)| 🔳
  (0,0)+--------→ X
       (1,0)(2,0)(3,0)
  ===================================================
  cycle 0:
  [    🔳            🔳            🔳            🔳 ]

  [ 0(phi_const) →   🔳            🔳            🔳 ]
      ↓ ↺
  [    🔳            🔳            🔳            🔳 ]

  [    7(+)   ───→   🔳            🔳            🔳 ]
        ↺
  ---------------------------------------------------
  cycle 1:
  [    🔳            🔳            🔳            🔳 ]

  [ 2(+ const)  ← 8(+ const)       🔳            🔳 ]
        ↺            ↓
  [ 4(+ const)       🔳            🔳            🔳 ]
        ↺
  [ 11(st_const) ←  1(phi_const)   🔳            🔳 ]

  ---------------------------------------------------
  cycle 2:
  [    🔳            🔳            🔳            🔳 ]

  [   3(ld)          🔳            🔳            🔳 ]
        ↓
  [   5(ld)         9(cmp)         🔳            🔳 ]
        ↺             ↺
  [    🔳            🔳            🔳            🔳 ]

  ---------------------------------------------------
  cycle 3:
  [    🔳            🔳            🔳            🔳 ]

  [    🔳            🔳            🔳            🔳 ]

  [   6(x)           🔳            🔳            🔳 ]
        ↓
  [    🔳            🔳            🔳            🔳 ]

  ---------------------------------------------------
  '''

  preload_data = [
      [
          IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(10, 1), data_addr = 0)),
          IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(11, 1), data_addr = 1)),
          IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(12, 1), data_addr = 2)),
          IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(13, 1), data_addr = 3)),
          IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(14, 1), data_addr = 4)),
          IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(15, 1), data_addr = 5)),
      ]
  ]

  src_opt_pkt = [
      # tile 0
      [
          # Store address.
          IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONST, data = DataType(16, 1))),

          # Pre-configure per-tile config count per iter.
          IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(ctrl_count_per_iter, 1))),

          # Pre-configure per-tile total config count.
          IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(total_ctrl_steps, 1))),

          # ADD.
          IntraCgraPktType(0, 0,
                            payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                      ctrl = CtrlType(OPT_ADD, 0,
                                                                      fu_in_code,
                                                                      [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(1), TileInType(4), TileInType(0), TileInType(0)],
                                                                      # Sends to east tile: tile 1; and self reg.
                                                                      [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(1),
                                                                       FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                      write_reg_from = write_reg_from_code))),

          # STORE_CONST, indicating the address is a const.
          IntraCgraPktType(0, 0,
                            payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                      ctrl = CtrlType(OPT_STR_CONST, 0,
                                                                      fu_in_code,
                                                                      [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                      [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                      read_reg_from = read_reg_from_code))),
          # NAH.
          IntraCgraPktType(0, 0,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                     ctrl = CtrlType(OPT_NAH, 0,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),
          # NAH.
          IntraCgraPktType(0, 0,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 3,
                                                     ctrl = CtrlType(OPT_NAH, 0,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

          # Pre-configure the prologue count for both operation and routing.
          IntraCgraPktType(0, 0,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 0,
                                                     data = DataType(1, 1))),
          IntraCgraPktType(0, 0,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 0,
                                                     ctrl = CtrlType(routing_xbar_outport = [
                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                     data = DataType(1, 1))),
          IntraCgraPktType(0, 0,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 0,
                                                     ctrl = CtrlType(routing_xbar_outport = [
                                                        TileInType(3), TileInType(0), TileInType(0), TileInType(0),
                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                     data = DataType(1, 1))),
          IntraCgraPktType(0, 0,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU_CROSSBAR, ctrl_addr = 0,
                                                     ctrl = CtrlType(fu_xbar_outport = [
                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]),
                                                     data = DataType(1, 1))),

          # Launch the tile.
          IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_LAUNCH))
      ],

      # tile 1
      [
          # Const for PHI_CONST.
          IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_CONST, data = DataType(3, 1))),

          # Pre-configure per-tile config count per iter.
          IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(ctrl_count_per_iter, 1))),

          # Pre-configure per-tile total config count.
          IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(total_ctrl_steps, 1))),

          # NAH.
          IntraCgraPktType(0, 1,
                            payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                      ctrl = CtrlType(OPT_NAH, 0,
                                                                      fu_in_code,
                                                                      [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                      [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

          # PHI_CONST.
          IntraCgraPktType(0, 1,
                            payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                      ctrl = CtrlType(OPT_PHI_CONST, 0,
                                                                      fu_in_code,
                                                                      [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(3), TileInType(0), TileInType(0), TileInType(0)],
                                                                      # Sends to west tile: tile 0.
                                                                      [FuOutType(0), FuOutType(0), FuOutType(1), FuOutType(0),
                                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),
          # NAH.
          IntraCgraPktType(0, 1,
                            payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                      ctrl = CtrlType(OPT_NAH, 0,
                                                                      fu_in_code,
                                                                      [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                      [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),
          # NAH.
          IntraCgraPktType(0, 1,
                            payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 3,
                                                      ctrl = CtrlType(OPT_NAH, 0,
                                                                      fu_in_code,
                                                                      [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                      [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),
          IntraCgraPktType(0, 1,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 0,
                                                     ctrl = CtrlType(routing_xbar_outport = [
                                                        TileInType(2), TileInType(0), TileInType(0), TileInType(0),
                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                     data = DataType(1, 1))),

          # Launch the tile.
          IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_LAUNCH))
      ],

      # tile 4
      [
          # Const for ADD_CONST.
          IntraCgraPktType(0, 4, payload = CgraPayloadType(CMD_CONST, data = DataType(2, 1))),

          # Pre-configure per-tile config count per iter.
          IntraCgraPktType(0, 4, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(ctrl_count_per_iter, 1))),

          # Pre-configure per-tile total config count.
          IntraCgraPktType(0, 4, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(total_ctrl_steps, 1))),

          # NAH.
          IntraCgraPktType(0, 4,
                            payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                      ctrl = CtrlType(OPT_NAH, 0,
                                                                      fu_in_code,
                                                                      [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                      [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

          # ADD_CONST.
          IntraCgraPktType(0, 4,
                            payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                      ctrl = CtrlType(OPT_ADD_CONST, 0,
                                                                      fu_in_code,
                                                                      [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(1), TileInType(0), TileInType(0), TileInType(0)],
                                                                      # Sends to self reg.
                                                                      [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                       FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                      write_reg_from = write_reg_from_code))),
          # LD.
          IntraCgraPktType(0, 4,
                            payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                      ctrl = CtrlType(OPT_LD, 0,
                                                                      fu_in_code,
                                                                      [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                      # Sends to self reg. Needs to be another register cluster to
                                                                      # avoid conflict with ADD_CONST.
                                                                      [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                       FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0)],
                                                                      write_reg_from = [b2(0), b2(2), b2(0), b2(0)],
                                                                      read_reg_from = read_reg_from_code))),
          # MUL.
          IntraCgraPktType(0, 4,
                            payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 3,
                                                      ctrl = CtrlType(OPT_MUL, 0,
                                                                      fu_in_code,
                                                                      [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(1), TileInType(0), TileInType(0), TileInType(0)],
                                                                      # Sends to south tile: tile 0.
                                                                      [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0),
                                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                      read_reg_from = [b1(0), b1(1), b1(0), b1(0)]))),

          # Launch the tile.
          IntraCgraPktType(0, 4, payload = CgraPayloadType(CMD_LAUNCH))
      ],

      # tile 5
      [
          # Const for CMP.
          IntraCgraPktType(0, 5, payload = CgraPayloadType(CMD_CONST, data = DataType(4, 1))),

          # Pre-configure per-tile config count per iter.
          IntraCgraPktType(0, 5, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(ctrl_count_per_iter, 1))),

          # Pre-configure per-tile total config count.
          IntraCgraPktType(0, 5, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(total_ctrl_steps, 1))),

          # NAH.
          IntraCgraPktType(0, 5,
                            payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                      ctrl = CtrlType(OPT_NAH, 0,
                                                                      fu_in_code,
                                                                      [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                      [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

          # NAH.
          IntraCgraPktType(0, 5,
                            payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                      ctrl = CtrlType(OPT_NAH, 0,
                                                                      fu_in_code,
                                                                      [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                      [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

          # CMP.
          IntraCgraPktType(0, 5,
                            payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                      ctrl = CtrlType(OPT_EQ_CONST, 0,
                                                                      fu_in_code,
                                                                      [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(1), TileInType(0), TileInType(0), TileInType(0)],
                                                                      # FIXME: Sends result to self reg for now.
                                                                      [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                       FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                      write_reg_from = [b2(2), b2(0), b2(0), b2(0)]))),

          # NAH.
          IntraCgraPktType(0, 5,
                            payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 3,
                                                      ctrl = CtrlType(OPT_NAH, 0,
                                                                      fu_in_code,
                                                                      [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                      [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

          # Launch the tile.
          IntraCgraPktType(0, 5, payload = CgraPayloadType(CMD_LAUNCH))
      ],

      # tile 8
      [
          # Const for PHI_CONST.
          IntraCgraPktType(0, 8, payload = CgraPayloadType(CMD_CONST, data = DataType(2, 1))),
          # Const for ADD_CONST.
          IntraCgraPktType(0, 8, payload = CgraPayloadType(CMD_CONST, data = DataType(0, 1))),

          # Pre-configure per-tile config count per iter.
          IntraCgraPktType(0, 8, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(ctrl_count_per_iter, 1))),

          # Pre-configure per-tile total config count.
          IntraCgraPktType(0, 8, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(total_ctrl_steps, 1))),

          # PHI_CONST.
          IntraCgraPktType(0, 8,
                            payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                      ctrl = CtrlType(OPT_PHI_CONST, 0,
                                                                      fu_in_code,
                                                                      [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(4), TileInType(0), TileInType(0), TileInType(0)],
                                                                      [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(1),
                                                                       FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                      write_reg_from = write_reg_from_code))),

          # ADD_CONST.
          IntraCgraPktType(0, 8,
                            payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                      ctrl = CtrlType(OPT_ADD_CONST, 0,
                                                                      fu_in_code,
                                                                      [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                      # Sends to self reg.
                                                                      [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                       FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0)],
                                                                      # 2 indicates the FU xbar port (instead of const queue or routing xbar port).
                                                                      write_reg_from = [b2(0), b2(2), b2(0), b2(0)],
                                                                      read_reg_from = read_reg_from_code))),
          # LD.
          IntraCgraPktType(0, 8,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                     ctrl = CtrlType(OPT_LD, 0,
                                                                     # The first 2 indicates the first operand is from the second inport,
                                                                     # which is actually from the second register cluster rather than the
                                                                     # inport channel, indicated by the `read_reg_from_code`.
                                                                     [FuInType(2), FuInType(0), FuInType(0), FuInType(0)],
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     # Sends to south tile: tile 4.
                                                                     [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                     read_reg_from = [b1(0), b1(1), b1(0), b1(0)]))),
          # NAH.
          IntraCgraPktType(0, 8,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 3,
                                                     ctrl = CtrlType(OPT_NAH, 0,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

          # Skips first time incoming from east tile via routing xbar.
          IntraCgraPktType(0, 8,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 0,
                                                     ctrl = CtrlType(routing_xbar_outport = [
                                                        TileInType(3), TileInType(0), TileInType(0), TileInType(0),
                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                     data = DataType(1, 1))),

          # Launch the tile.
          IntraCgraPktType(0, 8, payload = CgraPayloadType(CMD_LAUNCH))
      ],

      # tile 9
      [
          # Const for ADD_CONST.
          IntraCgraPktType(0, 9, payload = CgraPayloadType(CMD_CONST, data = DataType(1, 1))),

          # Pre-configure per-tile config count per iter.
          IntraCgraPktType(0, 9, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(ctrl_count_per_iter, 1))),

          # Pre-configure per-tile total config count.
          IntraCgraPktType(0, 9, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(total_ctrl_steps, 1))),

          # NAH.
          IntraCgraPktType(0, 9,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                     ctrl = CtrlType(OPT_NAH, 0,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

          # ADD_CONST.
          IntraCgraPktType(0, 9,
                            payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                      ctrl = CtrlType(OPT_ADD_CONST, 0,
                                                                      fu_in_code,
                                                                      [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                       TileInType(3), TileInType(0), TileInType(0), TileInType(0)],
                                                                      # Sends to west tile: tile8.
                                                                      [FuOutType(0), FuOutType(1), FuOutType(1), FuOutType(0),
                                                                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),
          # NAH.
          IntraCgraPktType(0, 9,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                     ctrl = CtrlType(OPT_NAH, 0,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),
          # NAH.
          IntraCgraPktType(0, 9,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 3,
                                                     ctrl = CtrlType(OPT_NAH, 0,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

          # Launch the tile.
          IntraCgraPktType(0, 9, payload = CgraPayloadType(CMD_LAUNCH))
      ]
  ]

  src_query_pkt = \
      [
          IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = 16)),
      ]

  expected_complete_sink_out_pkg = [IntraCgraPktType(payload = CgraPayloadType(CMD_COMPLETE)) for _ in range(6)]
  expected_mem_sink_out_pkt = \
      [
          IntraCgraPktType(dst = 16, payload = CgraPayloadType(CMD_LOAD_RESPONSE, data = DataType(0xab, 1), data_addr = 16)),
      ]

  for activation in preload_data:
      src_ctrl_pkt.extend(activation)
  for src_opt in src_opt_pkt:
      src_ctrl_pkt.extend(src_opt)

  complete_signal_sink_out.extend(expected_complete_sink_out_pkg)
  complete_signal_sink_out.extend(expected_mem_sink_out_pkt)

  th = TestHarness(DUT, FunctionUnit, FuList, DataType, PredicateType,
                   IntraCgraPktType, CgraPayloadType, CtrlType, InterCgraPktType,
                   ControllerIdType, cgra_id, x_tiles, y_tiles,
                   ctrl_mem_size, data_mem_size_global,
                   data_mem_size_per_bank, num_banks_per_cgra,
                   num_registers_per_reg_bank,
                   src_ctrl_pkt, ctrl_count_per_iter, total_ctrl_steps,
                   controller2addr_map, idTo2d_map, complete_signal_sink_out,
                   num_cgra_rows, num_cgra_columns,
                   src_query_pkt)

  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                       ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                        'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)

