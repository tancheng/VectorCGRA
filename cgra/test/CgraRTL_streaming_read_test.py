"""
==========================================================================
CgraRTL_fir_test.py
==========================================================================
Test cases for CGRA with crossbar-based data memory and ring-based control
memory of each tile.

Author : Cheng Tan
  Date : Aug 30, 2025
"""

from pymtl3.passes.backends.verilog import (VerilogVerilatorImportPass)
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)

from ..CgraRTL import CgraRTL
from ...fu.double.SeqMulAdderRTL import SeqMulAdderRTL
from ...fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from ...fu.float.FpAddRTL import FpAddRTL
from ...fu.float.FpMulRTL import FpMulRTL
from ...fu.quadra.FourIncCmpNotGrantRTL import FourIncCmpNotGrantRTL
from ...fu.single.AdderRTL import AdderRTL
from ...fu.single.GrantRTL import GrantRTL
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
from ...fu.vector.VectorAllReduceRTL import VectorAllReduceRTL
from ...lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ...lib.messages import *
from ...lib.opt_type import *


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
                src_ctrl_pkt, 
                src_data_south_boundary,
                src_data_west_boundary,
                sink_out_south_boundary,
                kCtrlCountPerIter, kTotalCtrlSteps,
                mem_access_is_combinational,
                has_ctrl_ring,
                controller2addr_map, idTo2d_map,
                multi_cgra_rows, multi_cgra_columns):

    CgraPayloadType = CtrlPktType.get_field_type(kAttrPayload)
    DataType = CgraPayloadType.get_field_type(kAttrData)
    DataAddrType = mk_bits(clog2(data_mem_size_global))
    s.num_tiles = width * height
    s.src_ctrl_pkt = TestSrcRTL(CtrlPktType, src_ctrl_pkt)
    s.src_data_south_boundary = TestSrcRTL(DataType, src_data_south_boundary)
    s.src_data_west_boundary = TestSrcRTL(DataType, src_data_west_boundary)

    s.dut = DUT(CgraPayloadType,
                # CGRA terminals on x/y. Assume in total 4, though this
                # test is for single CGRA.
                multi_cgra_rows, multi_cgra_columns,
                width, height, ctrl_mem_size,
                data_mem_size_global, data_mem_size_per_bank,
                num_banks_per_cgra, num_registers_per_reg_bank,
                kCtrlCountPerIter, kTotalCtrlSteps,
                mem_access_is_combinational,
                FunctionUnit, FuList, "KingMesh",
                controller2addr_map, idTo2d_map,
                is_multi_cgra = False,
                has_ctrl_ring = has_ctrl_ring)

    s.has_ctrl_ring = has_ctrl_ring

    s.sink_out_south_boundary = TestSinkRTL(DataType, sink_out_south_boundary)

    # Connections
    s.dut.cgra_id //= cgra_id
    s.dut.recv_from_cpu_pkt //= s.src_ctrl_pkt.send

    # Connects memory address upper and lower bound for each CGRA.
    s.dut.address_lower //= DataAddrType(controller2addr_map[cgra_id][0])
    s.dut.address_upper //= DataAddrType(controller2addr_map[cgra_id][1])

    for tile_col in range(width):
      s.dut.send_data_on_boundary_north[tile_col].rdy //= 0
      s.dut.recv_data_on_boundary_north[tile_col].val //= 0
      s.dut.recv_data_on_boundary_north[tile_col].msg //= DataType()

      if tile_col == 0:
        # Uses tile 0 to receive input data and send output results.
        s.dut.send_data_on_boundary_south[tile_col] //= s.sink_out_south_boundary.recv
        s.dut.recv_data_on_boundary_south[tile_col] //= s.src_data_south_boundary.send
      else:
        s.dut.send_data_on_boundary_south[tile_col].rdy //= 0
        s.dut.recv_data_on_boundary_south[tile_col].val //= 0
        s.dut.recv_data_on_boundary_south[tile_col].msg //= DataType()

    for tile_row in range(height):
      if tile_row == 0:
        # Uses tile 0 to receive input data and send output results.
        s.dut.send_data_on_boundary_west[tile_row].rdy //= 0
        s.dut.recv_data_on_boundary_west[tile_row] //= s.src_data_west_boundary.send
      else:
        s.dut.send_data_on_boundary_west[tile_row].rdy //= 0
        s.dut.recv_data_on_boundary_west[tile_row].val //= 0
        s.dut.recv_data_on_boundary_west[tile_row].msg //= DataType()
   
      s.dut.send_data_on_boundary_east[tile_row].rdy //= 0
      s.dut.recv_data_on_boundary_east[tile_row].val //= 0
      s.dut.recv_data_on_boundary_east[tile_row].msg //= DataType()
    s.dut.send_to_cpu_pkt.rdy //= 0

  def done(s):
    if not s.has_ctrl_ring:
      return True
    return (s.src_ctrl_pkt.done() and s.sink_out_south_boundary.done())

  def line_trace(s):
    return s.dut.line_trace()

# Common configurations/setups.
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
          FourIncCmpNotGrantRTL,
         ]
x_tiles = 2
y_tiles = 2
data_bitwidth = 32
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
num_cgra_columns = 1
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
fu_xbar_code = [FuOutType(0) for _ in range(num_routing_outports)]
write_reg_from_code = [b2(0) for _ in range(num_fu_inports)]
# 2 indicates the FU xbar port (instead of const queue or routing xbar port).
write_reg_from_code[0] = b2(2)
read_reg_from_code = [b1(0) for _ in range(num_fu_inports)]
read_reg_from_code[0] = b1(1)
read_reg_idx_code = [RegIdxType(0) for _ in range(num_fu_inports)]

fu_in_code = [FuInType(x + 1) for x in range(num_fu_inports)]

preload_data = [
    [
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(10, 1), data_addr = 0)),
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(11, 1), data_addr = 1)),
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(12, 1), data_addr = 2)),
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(13, 1), data_addr = 3)),
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(14, 1), data_addr = 4)),
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(15, 1), data_addr = 5)),
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(16, 1), data_addr = 6)),
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(17, 1), data_addr = 7)),
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(18, 1), data_addr = 8)),
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(19, 1), data_addr = 9)),
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(20, 1), data_addr = 10)),
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(21, 1), data_addr = 11)),
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(22, 1), data_addr = 12)),
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(23, 1), data_addr = 13)),
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(24, 1), data_addr = 14)),
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(25, 1), data_addr = 15)),
    ]
]

def sim_streaming_ld(cmdline_opts, mem_access_is_combinational, has_ctrl_ring):
  kCtrlCountPerIter = 3 
  kTotalCtrlSteps = 3
  src_ctrl_pkt = []
  src_opt_pkt = [
      # tile 0
      [
          # Streaming start addr.
          IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONFIG_STREAMING_LD_START_ADDR, data = DataType(2, 1))),

          # Streaming stride.
          IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONFIG_STREAMING_LD_STRIDE, data = DataType(2, 1))),

          # Streaming start addr.
          IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONFIG_STREAMING_LD_END_ADDR, data = DataType(8, 1))),

          # NAH.
          IntraCgraPktType(0, 0,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                     ctrl = CtrlType(OPT_NAH,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),
          # Streaming LD.
          IntraCgraPktType(0, 0,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                     ctrl = CtrlType(OPT_STREAM_LD,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                      # LD results routing to South.
                                                                     [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),
          # ADD operation to test whether streaming will block the FU.
          IntraCgraPktType(0, 0,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                     ctrl = CtrlType(OPT_ADD,
                                                                     fu_in_code,
                                                                      # Performs ADD using data from boundary South and West of tile 0.
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(2), TileInType(3), TileInType(0), TileInType(0)],
                                                                      # Sends the result to boundary South of tile 0.
                                                                     [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),
          # Launch the tile.
          IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_LAUNCH))
      ]
  ]

  src_data_south_boundary = [DataType(3, 1)]
  src_data_west_boundary = [DataType(5, 1)]
                             # Streaming LD result                                               ADD result    
  sink_out_south_boundary = [DataType(12, 1), DataType(14, 1), DataType(16, 1), DataType(18, 1), DataType(8, 1)]

  for activation in preload_data:
      src_ctrl_pkt.extend(activation)
  for src_opt in src_opt_pkt:
      src_ctrl_pkt.extend(src_opt)

  th = TestHarness(DUT, FunctionUnit, FuList,
                   IntraCgraPktType,
                   cgra_id, x_tiles, y_tiles,
                   ctrl_mem_size, data_mem_size_global,
                   data_mem_size_per_bank, num_banks_per_cgra,
                   num_registers_per_reg_bank,
                   src_ctrl_pkt,
                   src_data_south_boundary,
                   src_data_west_boundary,
                   sink_out_south_boundary,
                   kCtrlCountPerIter, kTotalCtrlSteps,
                   mem_access_is_combinational,
                   has_ctrl_ring,
                   controller2addr_map, idTo2d_map, 
                   num_cgra_rows, num_cgra_columns)

  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                       ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                        'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)

def test_streaming_ld_combinational_mem_access(cmdline_opts):
  sim_streaming_ld(cmdline_opts, mem_access_is_combinational = True, has_ctrl_ring = True)

def test_streaming_ld_non_combinational_mem_access(cmdline_opts):
  sim_streaming_ld(cmdline_opts, mem_access_is_combinational = False, has_ctrl_ring = True)
