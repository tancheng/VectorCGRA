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
from ...fu.single.GrantRTL import GrantRTL
from ...fu.single.CompRTL import CompRTL
from ...fu.single.LogicRTL import LogicRTL
from ...fu.single.LoopControlRTL import LoopControlRTL
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
from ...lib.util.common import *


#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, DUT, FunctionUnit, FuList,
                CtrlPktType,
                cgra_id, width, height,
                ctrl_mem_size, data_mem_size_global,
                data_mem_size_per_bank, num_banks_per_cgra,
                num_registers_per_reg_bank,
                src_ctrl_pkt, ctrl_steps,
                mem_access_is_combinational,
                topology, controller2addr_map,
                idTo2d_map, complete_signal_sink_out,
                multi_cgra_rows, multi_cgra_columns, src_query_pkt):

    CgraPayloadType = CtrlPktType.get_field_type(kAttrPayload)
    DataType = CgraPayloadType.get_field_type(kAttrData)
    DataAddrType = mk_bits(clog2(data_mem_size_global))
    s.num_tiles = width * height
    s.src_ctrl_pkt = TestSrcRTL(CtrlPktType, src_ctrl_pkt)
    s.src_query_pkt = TestSrcRTL(CtrlPktType, src_query_pkt)

    s.dut = DUT(CgraPayloadType,
                # CGRA terminals on x/y. Assume in total 4, though this
                # test is for single CGRA.
                multi_cgra_rows, multi_cgra_columns,
                width, height, ctrl_mem_size,
                data_mem_size_global, data_mem_size_per_bank,
                num_banks_per_cgra, num_registers_per_reg_bank,
                ctrl_steps, ctrl_steps,
                mem_access_is_combinational,
                FunctionUnit, FuList, topology,
                controller2addr_map, idTo2d_map,
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

def init_param(topology, FuList = [MemUnitRTL, AdderRTL],
               x_tiles = 2, y_tiles = 2, data_bitwidth = 32,
               test_name = 'default', total_execute_ctrl_count = 1):
  tile_ports = 4
  assert(topology == MESH or topology == KING_MESH)
  if topology == MESH:
    tile_ports = 4
  elif topology == KING_MESH:
    tile_ports = 8
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
  num_rd_tiles = x_tiles + y_tiles - 1
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
                                       num_rd_tiles,
                                       CgraPayloadType)

  IntraCgraPktType = mk_intra_cgra_pkt(num_cgra_columns,
                                       num_cgra_rows,
                                       num_tiles,
                                       CgraPayloadType)

  routing_xbar_code = [TileInType(0) for _ in range(num_routing_outports)]
  fu_in_code = [FuInType(0) for _ in range(num_fu_inports)]
  fu_in_code[0] = FuInType(1)
  fu_xbar_code = [FuOutType(0) for _ in range(num_routing_outports)]
  fu_xbar_code[num_tile_outports] = FuOutType(1)
  read_reg_from_code = [b1(0) for _ in range(num_fu_inports)]
  read_reg_from_code[0] = b1(1)
  read_reg_idx_code = [RegIdxType(0) for _ in range(num_fu_inports)]
  read_reg_idx_code[0] = RegIdxType(2)

  src_ctrl_pkt = []
  complete_signal_sink_out = []
  ctrl_steps = 0
  src_query_pkt = []
  if test_name == 'default':
      '''
      Each tile performs independent INC, without waiting for data from
      neighbours, instead, consuming the data inside their own register
      cluster/file (i.e., `read_reg_from`).
      '''
      src_opt_per_tile = [[
          # Pre-configure per-tile total iteration count. As we only have single `INC` operation,
          # `total_execute_ctrl_count` indicates the `INC` would be run `total_execute_ctrl_count`
          # times, then `COMPLETE` signal is sent back to CPU.
          IntraCgraPktType(0, # src
                           i, # dst
                           cgra_id, # src_cgra_id
                           cgra_id, # dst_cgra_id
                           idTo2d_map[cgra_id][0], # src_cgra_x
                           idTo2d_map[cgra_id][1], # src_cgra_y
                           idTo2d_map[cgra_id][0], # dst_cgra_x
                           idTo2d_map[cgra_id][1], # dst_cgra_y
                           0, # opaque
                           0, # vc_id
                           # Only execute one operation (i.e., `INC`) is enough for this tile.
                           # If this is set more than 1, `INC` would be run multiple times before
                           # `COMPLETE` signal is sent back to CPU.
                           CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(total_execute_ctrl_count))),

          # Pre-configure per-tile config count per iter, i.e., 1, as we only have one `INC` operation.
          IntraCgraPktType(0, # src
                           i, # dst
                           cgra_id, # src_cgra_id
                           cgra_id, # dst_cgra_id
                           idTo2d_map[cgra_id][0], # src_cgra_x
                           idTo2d_map[cgra_id][1], # src_cgra_y
                           idTo2d_map[cgra_id][0], # dst_cgra_x
                           idTo2d_map[cgra_id][1], # dst_cgra_y
                           0, # opaque
                           0, # vc_id
                           # Only execute one operation (i.e., `INC`) is enough for this tile.
                           CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(1))),

          IntraCgraPktType(0, # src
                           i, # dst
                           cgra_id, # src_cgra_id
                           cgra_id, # dst_cgra_id
                           idTo2d_map[cgra_id][0], # src_cgra_x
                           idTo2d_map[cgra_id][1], # src_cgra_y
                           idTo2d_map[cgra_id][0], # dst_cgra_x
                           idTo2d_map[cgra_id][1], # dst_cgra_y
                           0, # opaque
                           0, # vc_id
                           CgraPayloadType(CMD_CONFIG,
                                           ctrl = CtrlType(OPT_INC,
                                                           fu_in_code,
                                                           routing_xbar_code,
                                                           fu_xbar_code,
                                                           read_reg_from = read_reg_from_code,
                                                           read_reg_idx = read_reg_idx_code))),

          IntraCgraPktType(0, # src
                           i, # dst
                           cgra_id, # src_cgra_id
                           cgra_id, # dst_cgra_id
                           idTo2d_map[cgra_id][0], # src_cgra_x
                           idTo2d_map[cgra_id][1], # src_cgra_y
                           idTo2d_map[cgra_id][0], # dst_cgra_x
                           idTo2d_map[cgra_id][1], # dst_cgra_y
                           0, # opaque
                           0, # vc_id
                           CgraPayloadType(CMD_LAUNCH,
                                           ctrl = CtrlType(OPT_NAH)))] for i in range(num_tiles)]

      # vc_id needs to be 1 due to the message might traverse across the date line via ring.
      complete_signal_sink_out = \
          [IntraCgraPktType(i, # src
                            num_tiles, # dst
                            cgra_id, # src_cgra_id
                            cgra_id, # dst_cgra_id
                            idTo2d_map[cgra_id][0], # src_cgra_x
                            idTo2d_map[cgra_id][1], # src_cgra_y
                            idTo2d_map[cgra_id][0], # dst_cgra_x
                            idTo2d_map[cgra_id][1], # dst_cgra_y
                            0, # opaque
                            0, # vc_id
                            CgraPayloadType(CMD_COMPLETE)) for i in range(num_tiles)]

      for opt_per_tile in src_opt_per_tile:
        src_ctrl_pkt.extend(opt_per_tile)
      ctrl_steps = ctrl_mem_size

  elif test_name == 'systolic':
      updated_ctrl_steps = 2
      ctrl_steps = 2
      fu_in_code = [FuInType(x + 1) for x in range(num_fu_inports)]

      # Figure to illustrate details: https://github.com/tancheng/VectorCGRA/blob/master/doc/figures/weight_stationary_systolic_array.png
      activation_tensor_preload_data = [
          [
              # Will be read by tile 6.
              IntraCgraPktType(0, 6, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(1, 1), data_addr = 0)),
              IntraCgraPktType(0, 6, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(2, 1), data_addr = 1)),

              # Will be read by tile 3.
              IntraCgraPktType(0, 3, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(3, 1), data_addr = 2)),
              IntraCgraPktType(0, 3, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(4, 1), data_addr = 3)),
          ]
      ]

      src_opt_pkt = [
          # tile 6
          [
              IntraCgraPktType(0, 6, payload = CgraPayloadType(CMD_CONST, data = DataType(0, 1))),
              IntraCgraPktType(0, 6, payload = CgraPayloadType(CMD_CONST, data = DataType(1, 1))),

              # Pre-configure per-tile config count per iter.
              IntraCgraPktType(0, 6, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(1, 1))),

              # Pre-configure per-tile total config count.
              IntraCgraPktType(0, 6, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(updated_ctrl_steps, 1))),

              # LD_CONST indicates the address is a const.
              IntraCgraPktType(0, 6,
                               payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                         ctrl = CtrlType(OPT_LD_CONST,
                                                                         fu_in_code,
                                                                         [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                          TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                         # Sends to east tiles: [tile 7, tile 8].
                                                                         [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(1),
                                                                          FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

              IntraCgraPktType(0, 6, payload = CgraPayloadType(CMD_LAUNCH))
          ],

          # tile 3
          [
              IntraCgraPktType(0, 3, payload = CgraPayloadType(CMD_CONST, data = DataType(2, 1))),
              IntraCgraPktType(0, 3, payload = CgraPayloadType(CMD_CONST, data = DataType(3, 1))),

              # Pre-configure per-tile config count per iter.
              IntraCgraPktType(0, 3, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(1, 1))),

              # Pre-configure per-tile total config count.
              IntraCgraPktType(0, 3, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(updated_ctrl_steps, 1))),

              # LD_CONST indicates the address is a const.
              IntraCgraPktType(0, 3,
                               payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                         ctrl = CtrlType(OPT_LD_CONST,
                                                                         fu_in_code,
                                                                         [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                          TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                         # Sends to east tiles: [tile 4, tile 5]
                                                                         [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(1),
                                                                          FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

              IntraCgraPktType(0, 3, payload = CgraPayloadType(CMD_LAUNCH))
          ],

          # tile 7
          [
              IntraCgraPktType(0, 7, payload = CgraPayloadType(CMD_CONST, data = DataType(2, 1))),

              # Pre-configure per-tile config count per iter.
              IntraCgraPktType(0, 7, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(1, 1))),

              # Pre-configure per-tile total config count.
              IntraCgraPktType(0, 7, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(updated_ctrl_steps, 1))),

              IntraCgraPktType(0, 7,
                               payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                         ctrl = CtrlType(OPT_MUL_CONST,
                                                                         fu_in_code,
                                                                         # Forward data from west(tile 6) to east (tile 8).
                                                                         [TileInType(0), TileInType(0), TileInType(0), TileInType(3),
                                                                          # Put data from west(tile 6) to first inport of FU, to do OPT_MUL_CONST.
                                                                          TileInType(3), TileInType(0), TileInType(0), TileInType(0)],
                                                                         #              Sends mul to south tile(tile 4).
                                                                         [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0),
                                                                          FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

              IntraCgraPktType(0, 7, payload = CgraPayloadType(CMD_LAUNCH))
          ],

          # tile 4
          [
              IntraCgraPktType(0, 4, payload = CgraPayloadType(CMD_CONST, data = DataType(4, 1))),

              # Pre-configure per-tile config count per iter.
              IntraCgraPktType(0, 4, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(1, 1))),

              # Pre-configure per-tile total config count.
              IntraCgraPktType(0, 4, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(updated_ctrl_steps, 1))),

              IntraCgraPktType(0, 4,
                               payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                         ctrl = CtrlType(OPT_MUL_CONST_ADD,
                                                                         fu_in_code,
                                                                         # Forward data from west(tile 3) to east (tile 5).
                                                                         [TileInType(0), TileInType(0), TileInType(0), TileInType(3),
                                                                          # Put data from west(tile 3) to first inport of FU, to do MUL_CONST (const 4).
                                                                          # Put data from north(tile 7) to third inport to do ADD.
                                                                          TileInType(3), TileInType(0), TileInType(1), TileInType(0)],
                                                                         #              Sends mul_add to south tile(tile 1).
                                                                         [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0),
                                                                          FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

              IntraCgraPktType(0, 4, payload = CgraPayloadType(CMD_LAUNCH))
          ],

          # tile 1
          [
              # Const
              IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_CONST, data = DataType(4, 1))), # 14
              IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_CONST, data = DataType(5, 1))), # 20

              # Pre-configure per-tile config count per iter.
              IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(1, 1))),

              # Pre-configure per-tile total config count.
              IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(updated_ctrl_steps, 1))),

              IntraCgraPktType(0, 1,
                               payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                         ctrl = CtrlType(OPT_STR_CONST,
                                                                         fu_in_code,
                                                                         [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                          # Stores data from north(tile 4).
                                                                          TileInType(1), TileInType(0), TileInType(0), TileInType(0)],
                                                                         [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                          FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

              IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_LAUNCH))
          ],
          
          # tile 8
          [
              IntraCgraPktType(0, 8, payload = CgraPayloadType(CMD_CONST, data = DataType(6, 1))),

              # Pre-configure per-tile config count per iter.
              IntraCgraPktType(0, 8, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(1, 1))),

              # Pre-configure per-tile total config count.
              IntraCgraPktType(0, 8, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(updated_ctrl_steps, 1))),

              IntraCgraPktType(0, 8,
                               payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                         ctrl = CtrlType(OPT_MUL_CONST,
                                                                         fu_in_code,
                                                                         [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                          # Put data from west(tile 7) to first inport of FU, to do OPT_MUL_CONST.
                                                                          TileInType(3), TileInType(0), TileInType(0), TileInType(0)],
                                                                          #             Sends mul to south tile(tile 5).
                                                                         [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0),
                                                                          FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

              IntraCgraPktType(0, 8, payload = CgraPayloadType(CMD_LAUNCH))
          ],

          # tile 5
          [
              IntraCgraPktType(0, 5, payload = CgraPayloadType(CMD_CONST, data = DataType(8, 1))),

              # Pre-configure per-tile config count per iter.
              IntraCgraPktType(0, 5, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(1, 1))),

              # Pre-configure per-tile total config count.
              IntraCgraPktType(0, 5, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(updated_ctrl_steps, 1))),

              IntraCgraPktType(0, 5,
                               payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                         ctrl = CtrlType(OPT_MUL_CONST_ADD,
                                                                         fu_in_code,
                                                                         [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                          # Put data from west(tile 4) to first inport of FU, to do MUL_CONST (const 16).
                                                                          # Put data from north(tile 8) to third inport to do ADD.
                                                                          TileInType(3), TileInType(0), TileInType(1), TileInType(0)],
                                                                          #             Sends mul_add to south tile(tile 2).
                                                                         [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0),
                                                                          FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

              IntraCgraPktType(0, 5, payload = CgraPayloadType(CMD_LAUNCH))
          ],

          # tile 2
          [
              # Const
              IntraCgraPktType(0, 2, payload = CgraPayloadType(CMD_CONST, data = DataType(6, 1))), # 30
              IntraCgraPktType(0, 2, payload = CgraPayloadType(CMD_CONST, data = DataType(7, 1))), # 44

              # Pre-configure per-tile config count per iter.
              IntraCgraPktType(0, 2, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(1, 1))),

              # Pre-configure per-tile total config count.
              IntraCgraPktType(0, 2, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(updated_ctrl_steps, 1))),

              IntraCgraPktType(0, 2,
                               payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                         ctrl = CtrlType(OPT_STR_CONST,
                                                                         fu_in_code,
                                                                         [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                          # Stores data from north(tile 5).
                                                                          TileInType(1), TileInType(0), TileInType(0), TileInType(0)],
                                                                         [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                          FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

              IntraCgraPktType(0, 2, payload = CgraPayloadType(CMD_LAUNCH))
          ]
      ]

      src_query_pkt = \
          [
              IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = 4)),
              IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = 5)),

              IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = 6)),
              IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = 7)),
          ]

      expected_complete_sink_out_pkg = [IntraCgraPktType(payload = CgraPayloadType(CMD_COMPLETE)) for _ in range(8)]
      expected_mem_sink_out_pkt = \
          [
              # tile 1
              IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_RESPONSE, data = DataType(0x0e, 1), data_addr = 4)),
              IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_RESPONSE, data = DataType(0x14, 1), data_addr = 5)),

              # tile 2
              IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_RESPONSE, data = DataType(0x1e, 1), data_addr = 6)),
              IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_RESPONSE, data = DataType(0x2c, 1), data_addr = 7)),
          ]

      for activation in activation_tensor_preload_data:
          src_ctrl_pkt.extend(activation)
      for src_opt in src_opt_pkt:
          src_ctrl_pkt.extend(src_opt)

      complete_signal_sink_out.extend(expected_complete_sink_out_pkg)
      complete_signal_sink_out.extend(expected_mem_sink_out_pkt)

  mem_access_is_combinational = True
  th = TestHarness(DUT, FunctionUnit, FuList,
                   IntraCgraPktType,
                   cgra_id, x_tiles, y_tiles,
                   ctrl_mem_size, data_mem_size_global,
                   data_mem_size_per_bank, num_banks_per_cgra,
                   num_registers_per_reg_bank,
                   src_ctrl_pkt, ctrl_steps,
                   mem_access_is_combinational, topology,
                   controller2addr_map, idTo2d_map, complete_signal_sink_out,
                   num_cgra_rows, num_cgra_columns,
                   src_query_pkt)
  return th

def test_homogeneous_2x2(cmdline_opts):
  topology = "Mesh"
  FuList = [AdderRTL,
            MulRTL,
            LogicRTL,
            ShifterRTL,
            PhiRTL,
            CompRTL,
            GrantRTL,
            MemUnitRTL,
            SelRTL,
            RetRTL,
           ]
  th = init_param(topology, FuList)

  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                       ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                        'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)

def test_homogeneous_2x2_ctrl_count_2(cmdline_opts):
  topology = "Mesh"
  FuList = [AdderRTL,
            MulRTL,
            LogicRTL,
            ShifterRTL,
            PhiRTL,
            CompRTL,
            GrantRTL,
            MemUnitRTL,
            SelRTL,
            RetRTL,
           ]
  th = init_param(topology, FuList, total_execute_ctrl_count = 2)

  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                       ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                        'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)

def test_heterogeneous_king_mesh_2x2(cmdline_opts):
  topology = "KingMesh"
  th = init_param(topology)
  th.set_param("top.dut.tile[1].construct", FuList=[ShifterRTL, AdderRTL, MemUnitRTL])
  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                      ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                       'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)

def test_heterogeneous_with_loop_control(cmdline_opts):
  topology = "KingMesh"
  th = init_param(topology)
  th.set_param("top.dut.tile[1].construct", FuList=[ShifterRTL, AdderRTL, MemUnitRTL, LoopControlRTL])
  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                      ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                       'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)

def test_vector_king_mesh_2x2(cmdline_opts):
  topology = "KingMesh"
  FuList = [AdderRTL,
            MulRTL,
            LogicRTL,
            ShifterRTL,
            PhiRTL,
            CompRTL,
            GrantRTL,
            MemUnitRTL,
            SelRTL,
            VectorMulComboRTL,
            VectorAdderComboRTL]
  data_bitwidth = 64
  th = init_param(topology, FuList, data_bitwidth = data_bitwidth)
  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                      ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                       'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)

def test_vector_mesh_4x4(cmdline_opts):
  topology = "Mesh"
  FuList = [AdderRTL,
            MulRTL,
            LogicRTL,
            ShifterRTL,
            PhiRTL,
            CompRTL,
            GrantRTL,
            MemUnitRTL,
            SelRTL,
            VectorMulComboRTL,
            VectorAdderComboRTL]
  data_bitwidth = 32
  th = init_param(topology, FuList, x_tiles = 4, y_tiles = 4,
                  data_bitwidth = data_bitwidth)
  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                      ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                       'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)

def test_systolic_3x3(cmdline_opts):
  topology = "Mesh"
  FuList = [AdderRTL,
            MulRTL,
            LogicRTL,
            ShifterRTL,
            PhiRTL,
            CompRTL,
            GrantRTL,
            MemUnitRTL,
            SelRTL,
            FpAddRTL,
            FpMulRTL,
            SeqMulAdderRTL,
            VectorMulComboRTL,
            VectorAdderComboRTL]

  data_bitwidth = 32
  th = init_param(topology, FuList, x_tiles = 3, y_tiles = 3,
                  data_bitwidth = data_bitwidth, test_name = 'systolic')
  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                      ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                       'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)
