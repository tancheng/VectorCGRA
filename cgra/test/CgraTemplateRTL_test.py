"""
==========================================================================
CgraTemplateRTL_test.py
==========================================================================
Translation for parameterizable CGRA based on the template.

Author : Cheng Tan
  Date : Dec 23, 2022

"""

from pymtl3 import *
from pymtl3.passes.backends.verilog import (VerilogTranslationPass,
                                            VerilogVerilatorImportPass)
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)
from ..CgraTemplateRTL import CgraTemplateRTL
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ...lib.messages import *
from ...lib.cmd_type import *
from ...lib.opt_type import *
from ...lib.util.common import *
from ...fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from ...fu.single.AdderRTL import AdderRTL
from ...fu.single.BranchRTL import BranchRTL
from ...fu.single.CompRTL import CompRTL
from ...fu.single.LogicRTL import LogicRTL
from ...fu.single.MemUnitRTL import MemUnitRTL
from ...fu.single.MulRTL import MulRTL
from ...fu.single.PhiRTL import PhiRTL
from ...fu.single.RetRTL import RetRTL
from ...fu.single.SelRTL import SelRTL
from ...fu.double.SeqMulAdderRTL import SeqMulAdderRTL
from ...fu.single.ShifterRTL import ShifterRTL

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
fuType2RTL["Br"   ] = BranchRTL

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, DUT, FunctionUnit, FuList, DataType, PredicateType,
                CtrlPktType, CtrlSignalType, NocPktType, CmdType,
                ControllerIdType, controller_id, ctrl_mem_size,
                data_mem_size_global, data_mem_size_per_bank,
                num_banks_per_cgra, num_registers_per_reg_bank,
                src_ctrl_pkt, ctrl_steps, TileList,
                LinkList, dataSPM, controller2addr_map, idTo2d_map):

    s.num_tiles = len(TileList)
    s.src_ctrl_pkt = TestSrcRTL(CtrlPktType, src_ctrl_pkt)

    s.dut = DUT(DataType, PredicateType, CtrlPktType, CtrlSignalType,
                NocPktType, CmdType, ControllerIdType,
                # CGRA terminals on x/y. Assume in total 4, though this
                # test is for single CGRA.
                1, 4,
                ctrl_mem_size, data_mem_size_global,
                data_mem_size_per_bank, num_banks_per_cgra,
                num_registers_per_reg_bank,
                ctrl_steps, ctrl_steps, FunctionUnit, FuList,
                TileList, LinkList, dataSPM, controller2addr_map,
                idTo2d_map)

    # Connections
    s.dut.controller_id //= controller_id
    s.src_ctrl_pkt.send //= s.dut.recv_from_cpu_ctrl_pkt

    s.dut.send_to_noc.rdy //= 0
    s.dut.recv_from_noc.val //= 0
    s.dut.recv_from_noc.msg //= NocPktType(0, 0, 0, 0, 0, 0)

  def done(s):
    return s.src_ctrl_pkt.done()

  def line_trace(s):
    return s.dut.line_trace()

class Tile:
  def __init__(s, dimX, dimY):
    s.disabled = False
    s.dimX = dimX
    s.dimY = dimY
    s.toMem = False
    s.fromMem = False
    s.invalidOutPorts = set()
    s.invalidInPorts = set()
    for i in range(PORT_DIRECTION_COUNTS):
      s.invalidOutPorts.add(i)
      s.invalidInPorts.add(i)

  def getInvalidInPorts(s):
    return s.invalidInPorts

  def getInvalidOutPorts(s):
    return s.invalidOutPorts

  def hasToMem(s):
    return s.toMem

  def hasFromMem(s):
    return s.fromMem

  def getIndex(s, TileList):
    if s.disabled:
      return -1
    index = 0
    for tile in TileList:
      if tile.dimY < s.dimY and not tile.disabled:
        index += 1
      elif tile.dimY == s.dimY and tile.dimX < s.dimX and not tile.disabled:
        index += 1
    return index

class DataSPM:
  def __init__(s, numOfReadPorts, numOfWritePorts):
    s.numOfReadPorts = numOfReadPorts
    s.numOfWritePorts = numOfWritePorts

  def getNumOfValidReadPorts(s):
    return s.numOfReadPorts

  def getNumOfValidWritePorts(s):
    return s.numOfWritePorts

class Link:
  def __init__(s, srcTile, dstTile, srcPort, dstPort):
    s.srcTile = srcTile
    s.dstTile = dstTile
    s.srcPort = srcPort
    s.dstPort = dstPort
    s.disabled = False
    s.toMem = False
    s.fromMem = False
    s.memPort = -1

  def getMemReadPort(s):
      return s.memPort

  def getMemWritePort(s):
      return s.memPort

  def isToMem(s):
    return s.toMem

  def isFromMem(s):
    return s.fromMem

  def validatePorts(s):
    if not s.toMem and not s.fromMem:
      s.srcTile.invalidOutPorts.remove(s.srcPort)
      s.dstTile.invalidInPorts.remove(s.dstPort)
    if s.toMem:
      s.srcTile.toMem = True
    if s.fromMem:
      s.dstTile.fromMem = True


import platform
import pytest

def test_cgra_universal(cmdline_opts, paramCGRA = None):
  num_tile_inports  = 8
  num_tile_outports = 8
  num_fu_inports = 4
  num_fu_outports = 2
  num_routing_outports = num_tile_outports + num_fu_inports
  ctrl_mem_size = paramCGRA.configMemSize if paramCGRA != None else 6
  width = paramCGRA.rows if paramCGRA != None else 2
  height = paramCGRA.columns if paramCGRA != None else 2
  data_mem_size_global = 512
  data_mem_size_per_bank = 32
  num_banks_per_cgra = 2
  num_terminals = 4
  num_ctrl_actions = 6
  num_ctrl_operations = 64
  num_registers_per_reg_bank = 16
  TileInType = mk_bits(clog2(num_tile_inports + 1))
  FuInType = mk_bits(clog2(num_fu_inports + 1))
  FuOutType = mk_bits(clog2(num_fu_outports + 1))
  addr_nbits = clog2(data_mem_size_global)
  AddrType = mk_bits(addr_nbits)
  CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
  num_tiles = width * height
  DUT = CgraTemplateRTL
  FunctionUnit = FlexibleFuRTL
  # FuList = [MemUnitRTL, AdderRTL]
  FuList = [PhiRTL, AdderRTL, ShifterRTL, MemUnitRTL, SelRTL, CompRTL, SeqMulAdderRTL, RetRTL, MulRTL, LogicRTL, BranchRTL]
  data_nbits = 32
  DataType = mk_data(data_nbits, 1)
  PredicateType = mk_predicate(1, 1)

  CmdType = mk_bits(4)
  ControllerIdType = mk_bits(clog2(num_terminals))
  controller_id = 1
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

  CtrlPktType = \
      mk_intra_cgra_pkt(width * height,
                        num_ctrl_actions,
                        ctrl_mem_size,
                        num_ctrl_operations,
                        num_fu_inports,
                        num_fu_outports,
                        num_tile_inports,
                        num_tile_outports,
                        num_registers_per_reg_bank,
                        data_nbits)
  CtrlSignalType = \
      mk_separate_reg_ctrl(num_ctrl_operations,
                           num_fu_inports,
                           num_fu_outports,
                           num_tile_inports,
                           num_tile_outports,
                           num_registers_per_reg_bank)

  NocPktType = mk_multi_cgra_noc_pkt(ncols = num_terminals,
                                     nrows = 1,
                                     addr_nbits = addr_nbits,
                                     data_nbits = data_nbits,
                                     predicate_nbits = 1)
  pick_register = [FuInType(x + 1) for x in range(num_fu_inports)]
  tile_in_code = [TileInType(max(4 - x, 0)) for x in range(num_routing_outports)]
  fu_out_code  = [FuOutType(x % 2) for x in range(num_routing_outports)]
  src_opt_per_tile = [[
                # src dst vc_id opq cmd_type    addr operation predicate
      CtrlPktType(0,  i,  0,    0,  CMD_CONFIG, 0,   OPT_INC,  b1(0),
                  pick_register, tile_in_code, fu_out_code),
      # This last one is for launching kernel.
      CtrlPktType(0,  i,  0,    0,  CMD_LAUNCH, 0,   OPT_ADD, b1(0),
                  pick_register, tile_in_code, fu_out_code)
      ] for i in range(num_tiles)]

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
    dataSPM = DataSPM(2, 2)
    for r in range(2):
      tiles.append([])
      for c in range(2):
        tiles[r].append(Tile(c, r))

    links = [Link(None, None, 0, 0) for _ in range(16)]

    links[0].srcTile = None
    links[0].dstTile = tiles[0][0]
    links[0].srcPort = 0
    links[0].dstPort = PORT_WEST
    links[0].fromMem = True
    links[0].memPort = 0
    links[0].validatePorts()

    links[1].srcTile = tiles[0][0]
    links[1].dstTile = None
    links[1].srcPort = PORT_WEST
    links[1].dstPort = 0
    links[1].toMem = True
    links[1].memPort = 0
    links[1].validatePorts()

    links[2].srcTile = None
    links[2].dstTile = tiles[1][0]
    links[2].srcPort = 1
    links[2].dstPort = PORT_WEST
    links[2].fromMem = True
    links[2].memPort = 1
    links[2].validatePorts()

    links[3].srcTile = tiles[1][0]
    links[3].dstTile = None
    links[3].srcPort = PORT_WEST
    links[3].dstPort = 1
    links[3].toMem = True
    links[3].memPort = 1
    links[3].validatePorts()

    links[4].srcTile = tiles[0][0]
    links[4].dstTile = tiles[0][1]
    links[4].srcPort = PORT_EAST
    links[4].dstPort = PORT_WEST
    links[4].validatePorts()

    links[5].srcTile = tiles[0][1]
    links[5].dstTile = tiles[0][0]
    links[5].srcPort = PORT_WEST
    links[5].dstPort = PORT_EAST
    links[5].validatePorts()

    links[6].srcTile = tiles[1][0]
    links[6].dstTile = tiles[1][1]
    links[6].srcPort = PORT_EAST
    links[6].dstPort = PORT_WEST
    links[6].validatePorts()

    links[7].srcTile = tiles[1][1]
    links[7].dstTile = tiles[1][0]
    links[7].srcPort = PORT_WEST
    links[7].dstPort = PORT_EAST
    links[7].validatePorts()

    links[8].srcTile = tiles[0][0]
    links[8].dstTile = tiles[1][0]
    links[8].srcPort = PORT_NORTH
    links[8].dstPort = PORT_SOUTH
    links[8].validatePorts()

    links[9].srcTile = tiles[1][0]
    links[9].dstTile = tiles[0][0]
    links[9].srcPort = PORT_SOUTH
    links[9].dstPort = PORT_NORTH
    links[9].validatePorts()

    links[10].srcTile = tiles[0][1]
    links[10].dstTile = tiles[1][1]
    links[10].srcPort = PORT_NORTH
    links[10].dstPort = PORT_SOUTH
    links[10].validatePorts()

    links[11].srcTile = tiles[1][1]
    links[11].dstTile = tiles[0][1]
    links[11].srcPort = PORT_SOUTH
    links[11].dstPort = PORT_NORTH
    links[11].validatePorts()

    links[12].srcTile = tiles[0][0]
    links[12].dstTile = tiles[1][1]
    links[12].srcPort = PORT_NORTHEAST
    links[12].dstPort = PORT_SOUTHWEST
    links[12].validatePorts()

    links[13].srcTile = tiles[1][1]
    links[13].dstTile = tiles[0][0]
    links[13].srcPort = PORT_SOUTHWEST
    links[13].dstPort = PORT_NORTHEAST
    links[13].validatePorts()

    links[14].srcTile = tiles[0][1]
    links[14].dstTile = tiles[1][0]
    links[14].srcPort = PORT_NORTHWEST
    links[14].dstPort = PORT_SOUTHEAST
    links[14].validatePorts()

    links[15].srcTile = tiles[1][0]
    links[15].dstTile = tiles[0][1]
    links[15].srcPort = PORT_SOUTHEAST
    links[15].dstPort = PORT_NORTHWEST
    links[15].validatePorts()

    def handleReshape( t_tiles ):
      tiles = []
      for row in t_tiles:
        for t in row:
          tiles.append(t)
      return tiles

    tiles = handleReshape(tiles)

  th = TestHarness(DUT, FunctionUnit, FuList, DataType, PredicateType,
                   CtrlPktType, CtrlSignalType, NocPktType, CmdType,
                   ControllerIdType, controller_id,
                   ctrl_mem_size, data_mem_size_global,
                   data_mem_size_per_bank, num_banks_per_cgra,
                   num_registers_per_reg_bank,
                   src_ctrl_pkt, ctrl_mem_size, tiles, links, dataSPM,
                   controller2addr_map, idTo2d_map)

  th.elaborate()
  th.dut.set_metadata(VerilogTranslationPass.explicit_module_name,
                      f'CgraTemplateRTL')
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                      ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                       'ALWCOMBORDER'])
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
