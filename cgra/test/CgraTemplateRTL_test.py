"""
==========================================================================
CgraTemplateRTL_test.py
==========================================================================
Translation for parameterizable CGRA based on the template.

Author : Cheng Tan
  Date : Dec 23, 2022

"""

from pymtl3.passes.backends.verilog import (VerilogTranslationPass,
                                            VerilogVerilatorImportPass)
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)

from ..CgraTemplateRTL import CgraTemplateRTL
from ...fu.double.SeqMulAdderRTL import SeqMulAdderRTL
from ...fu.flexible.FlexibleFuRTL import FlexibleFuRTL
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
from ...lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ...lib.messages import *
from ...lib.opt_type import *
from ...lib.util.common import *
from ...lib.util.cgra.Tile import Tile
from ...lib.util.cgra.DataSPM import DataSPM
from ...lib.util.cgra.cgra_helper import get_links

fuType2RTL = {}
fuType2RTL["Phi"  ] = PhiRTL
fuType2RTL["Add"  ] = AdderRTL
fuType2RTL["Shift"] = ShifterRTL
fuType2RTL["Ld"   ] = MemUnitRTL
fuType2RTL["St"   ] = MemUnitRTL
fuType2RTL["Sel"  ] = SelRTL
fuType2RTL["Cmp"  ] = CompRTL
fuType2RTL["MAC"  ] = SeqMulAdderRTL
fuType2RTL["Ret"  ] = RetRTL
fuType2RTL["Mul"  ] = MulRTL
fuType2RTL["Logic"] = LogicRTL
fuType2RTL["Grant"] = GrantRTL

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, DUT, FunctionUnit, FuList,
                CtrlPktType,
                cgra_id, ctrl_mem_size,
                data_mem_size_global, data_mem_size_per_bank,
                num_banks_per_cgra, num_registers_per_reg_bank,
                src_ctrl_pkt, ctrl_steps,
                mem_access_is_combinational,
                TileList, LinkList, dataSPM,
                controller2addr_map, idTo2d_map,
                complete_signal_sink_out):

    CgraPayloadType = CtrlPktType.get_field_type(kAttrPayload)
    DataAddrType = mk_bits(clog2(data_mem_size_global))
    s.num_tiles = len(TileList)
    s.src_ctrl_pkt = TestSrcRTL(CtrlPktType, src_ctrl_pkt)
    s.complete_signal_sink_out = TestSinkRTL(CtrlPktType, complete_signal_sink_out)

    s.dut = DUT(CgraPayloadType,
                # CGRA terminals on x/y. Assume in total 4, though this
                # test is for single CGRA.
                1, 4,
                None, None,
                ctrl_mem_size, data_mem_size_global,
                data_mem_size_per_bank, num_banks_per_cgra,
                num_registers_per_reg_bank,
                ctrl_steps, ctrl_steps,
                mem_access_is_combinational,
                FunctionUnit, FuList,
                TileList, LinkList, dataSPM, controller2addr_map,
                idTo2d_map, is_multi_cgra = False)

    # Connections
    s.dut.cgra_id //= cgra_id
    s.src_ctrl_pkt.send //= s.dut.recv_from_cpu_pkt
    s.complete_signal_sink_out.recv //= s.dut.send_to_cpu_pkt

    # Connects memory address upper and lower bound for each CGRA.
    s.dut.address_lower //= DataAddrType(controller2addr_map[cgra_id][0])
    s.dut.address_upper //= DataAddrType(controller2addr_map[cgra_id][1])

  def done(s):
    return s.src_ctrl_pkt.done() and s.complete_signal_sink_out.done()

  def line_trace(s):
    return s.dut.line_trace()

def test_cgra_universal(cmdline_opts, paramCGRA = None):
  num_tile_inports  = 8
  num_tile_outports = 8
  num_fu_inports = 4
  num_fu_outports = 2
  num_routing_outports = num_tile_outports + num_fu_inports
  ctrl_mem_size = paramCGRA.configMemSize if paramCGRA != None else 8
  width = paramCGRA.rows if paramCGRA != None else 2
  height = paramCGRA.columns if paramCGRA != None else 2
  data_mem_size_global = 512
  data_mem_size_per_bank = 32
  num_banks_per_cgra = 2
  num_cgra_columns = 4
  num_cgra_rows = 1
  num_cgras = num_cgra_columns * num_cgra_rows
  num_registers_per_reg_bank = 16
  RegIdxType = mk_bits(clog2(num_registers_per_reg_bank))
  TileInType = mk_bits(clog2(num_tile_inports + 1))
  FuInType = mk_bits(clog2(num_fu_inports + 1))
  FuOutType = mk_bits(clog2(num_fu_outports + 1))
  addr_nbits = clog2(data_mem_size_global)
  num_tiles = width * height
  DUT = CgraTemplateRTL
  FunctionUnit = FlexibleFuRTL
  # FuList = [MemUnitRTL, AdderRTL]
  FuList = [PhiRTL, AdderRTL, ShifterRTL, MemUnitRTL, SelRTL, CompRTL, SeqMulAdderRTL, RetRTL, MulRTL, LogicRTL, GrantRTL]
  data_nbits = 32
  DataType = mk_data(data_nbits, 1)
  PredicateType = mk_predicate(1, 1)

  DataAddrType = mk_bits(addr_nbits)
  ControllerIdType = mk_bits(clog2(num_cgras))
  cgra_id = 0
  controller2addr_map = {
          0: [0, 3],
          1: [4, 7],
          2: [8, 11],
          3: [12, 15],
  }

  idTo2d_map = {
          0: [0, 0],
          1: [1, 0],
          2: [2, 0],
          3: [3, 0],
  }

  cgra_id_nbits = 2
  data_nbits = 32
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
                                       width,
                                       CgraPayloadType)

  IntraCgraPktType = mk_intra_cgra_pkt(num_cgra_columns,
                                       num_cgra_rows,
                                       num_tiles,
                                       CgraPayloadType)

  tile_in_code = [TileInType(0) for x in range(num_routing_outports)]
  # Note that we still need to set FU inport, and `INC` requires one input.
  fu_in_code = [FuInType(0) for _ in range(num_fu_inports)]
  fu_in_code[0] = FuInType(1)
  fu_out_code  = [FuOutType(0) for x in range(num_routing_outports)]
  # Note that we still need to set FU xbar, and `INC` requires one output.
  fu_out_code[num_tile_outports] = FuOutType(1)
  read_reg_from_code = [b1(0) for _ in range(num_fu_inports)]
  read_reg_from_code[0] = b1(1)
  read_reg_idx_code = [RegIdxType(0) for _ in range(num_fu_inports)]
  read_reg_idx_code[0] = RegIdxType(2)

  '''
  Each tile performs independent INC, without waiting for data from
  neighbours, instead, consuming the data inside their own register
  cluster/file (i.e., `read_reg_from`).
  '''
  src_opt_per_tile = [[
      # Pre-configure per-tile total config count. As we only have single `INC` operation,
      # we set it as one, which would trigger `COMPLETE` signal be sent back to CPU.
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
                       # Only execute one operation (i.e., store) is enough for this tile.
                       # If this is set more than 1, no `COMPLETE` signal would be set back to CPU.
                       CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(1))),

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
                                                       tile_in_code,
                                                       fu_out_code,
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

  src_ctrl_pkt = []
  for opt_per_tile in src_opt_per_tile:
    src_ctrl_pkt.extend(opt_per_tile)

  dataSPM = None
  tiles = []
  links = None
  if paramCGRA != None:
    tiles = paramCGRA.getValidTiles()
    links = paramCGRA.getValidLinks()
    dataSPM = paramCGRA.dataSPM
  else:
    for r in range(height):
      tiles.append([])
      for c in range(width):
        tiles[r].append(Tile(c, r))
    # Assumes first column tiles are connected to memory.
    dataSPM = DataSPM(width, width)

    links = get_links(tiles)

    def handleReshape( t_tiles ):
      tiles = []
      for row in t_tiles:
        for t in row:
          tiles.append(t)
      return tiles

    tiles = handleReshape(tiles)

  # Non-combinational memory access to improve the timing and P&R.
  mem_access_is_combinational = False
  th = TestHarness(DUT, FunctionUnit, FuList,
                   IntraCgraPktType,
                   cgra_id,
                   ctrl_mem_size, data_mem_size_global,
                   data_mem_size_per_bank, num_banks_per_cgra,
                   num_registers_per_reg_bank,
                   src_ctrl_pkt, ctrl_mem_size,
                   mem_access_is_combinational, tiles, links, dataSPM,
                   controller2addr_map, idTo2d_map, complete_signal_sink_out)

  th.elaborate()
  th.dut.set_metadata(VerilogTranslationPass.explicit_module_name,
                      f'CgraTemplateRTL')
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                      ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                       'ALWCOMBORDER', 'CMPCONST'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])

  if paramCGRA != None:
    for tile in tiles:
        if not tile.isDefaultFus():
            targetFuList = []
            for fuType in tile.getAllValidFuTypes():
                targetFuList.append(fuType2RTL[fuType])
            targetTile = "top.dut.tile[" + str(tile.getIndex(tiles)) + "].construct"
            th.set_param(targetTile, FuList=targetFuList)

  run_sim(th)
