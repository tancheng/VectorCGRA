"""
==========================================================================
CGRATemplateRTL_test.py
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
from ..CGRATemplateRTL import CGRATemplateRTL
from ...lib.basic.en_rdy.test_srcs import TestSrcRTL
from ...lib.messages import *
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

class TestHarness( Component ):

  def construct( s, DUT, FunctionUnit, FuList, DataType, PredicateType,
                 CtrlType, width, height, ctrl_mem_size, data_mem_size,
                 src_opt, ctrl_waddr, tileList, linkList, dataSPM ):

    s.num_tiles = len(tileList)
    AddrType = mk_bits( clog2( ctrl_mem_size ) )

    s.src_opt     = [ TestSrcRTL( CtrlType, src_opt[i] )
                      for i in range( s.num_tiles ) ]
    s.ctrl_waddr  = [ TestSrcRTL( AddrType, ctrl_waddr[i] )
                      for i in range( s.num_tiles ) ]

    s.dut = DUT( DataType, PredicateType, CtrlType, width, height,
                 ctrl_mem_size, data_mem_size, len( src_opt[0] ),
                 len( src_opt[0] ), FunctionUnit, FuList, tileList, linkList, dataSPM )

    for i in range( s.num_tiles ):
      connect( s.src_opt[i].send,     s.dut.recv_wopt[i]  )
      connect( s.ctrl_waddr[i].send,  s.dut.recv_waddr[i] )

  def done( s ):
    done = True
    for i in range( s.num_tiles  ):
      if not s.src_opt[i].done():
        done = False
        break
    return done

  def line_trace( s ):
    return s.dut.line_trace()

class Tile:
  def __init__( s, dimX, dimY ):
    s.disabled = False
    s.dimX = dimX
    s.dimY = dimY
    s.toMem = False
    s.fromMem = False
    s.invalidOutPorts = set()
    s.invalidInPorts = set()
    for i in range( PORT_DIRECTION_COUNTS ):
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

  def getIndex( s, tileList ):
    if s.disabled:
      return -1
    index = 0
    for tile in tileList:
      if tile.dimY < s.dimY and not tile.disabled:
        index += 1
      elif tile.dimY == s.dimY and tile.dimX < s.dimX and not tile.disabled:
        index += 1
    return index

class DataSPM:
  def __init__( s, numOfReadPorts, numOfWritePorts ):
    s.numOfReadPorts = numOfReadPorts
    s.numOfWritePorts = numOfWritePorts

  def getNumOfValidReadPorts( s ):
    return s.numOfReadPorts

  def getNumOfValidWritePorts( s ):
    return s.numOfWritePorts

class Link:
  def __init__( s, srcTile, dstTile, srcPort, dstPort ):
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

  def validatePorts( s ):
    if not s.toMem and not s.fromMem:
      s.srcTile.invalidOutPorts.remove(s.srcPort)
      s.dstTile.invalidInPorts.remove(s.dstPort)
    if s.toMem:
      s.srcTile.toMem = True
    if s.fromMem:
      s.dstTile.fromMem = True


import platform
import pytest

# @pytest.mark.skipif('Linux' not in platform.platform(),
#                     reason="requires linux (gcc)")
# def test_cgra_universal(t_width=2, t_height=2, t_ctrl_mem_size=8, t_data_mem_size=8):
def test_cgra_universal( cmdline_opts, paramCGRA = None):
  num_tile_inports  = 8
  num_tile_outports = 8
  num_xbar_inports  = 10
  num_xbar_outports = 12
  ctrl_mem_size     = paramCGRA.configMemSize if paramCGRA != None else 8
  width             = paramCGRA.rows if paramCGRA != None else 2
  height            = paramCGRA.columns if paramCGRA != None else 2
  RouteType         = mk_bits( clog2( num_xbar_inports + 1 ) )
  AddrType          = mk_bits( clog2( ctrl_mem_size ) )
  num_tiles         = width * height
  # data_mem_size     = paramCGRA != None ? paramCGRA.dataMemSize : 8
  data_mem_size     = 8
  num_fu_in         = 4
  DUT               = CGRATemplateRTL
  FunctionUnit      = FlexibleFuRTL
  # FuList            = [ SeqMulAdderRTL, MemUnitRTL ]#AdderRTL, MulRTL, LogicRTL, ShifterRTL, PhiRTL, CompRTL, BranchRTL, MemUnitRTL ]
  FuList           = [ PhiRTL, AdderRTL, ShifterRTL, MemUnitRTL, SelRTL, CompRTL, SeqMulAdderRTL, RetRTL, MulRTL, LogicRTL, BranchRTL ]
  DataType          = mk_data( 32, 1 )
  PredicateType     = mk_predicate( 1, 1 )
#  DataType         = mk_data( 16, 1 )
  CtrlType          = mk_ctrl( num_fu_in, num_xbar_inports, num_xbar_outports )
  FuInType          = mk_bits( clog2( num_fu_in + 1 ) )
  pickRegister      = [ FuInType( x+1 ) for x in range( num_fu_in ) ]
  src_opt           = [ [ CtrlType( OPT_INC, b1( 0 ), pickRegister, [
                          RouteType(4), RouteType(3), RouteType(2), RouteType(1),
                          RouteType(0), RouteType(0), RouteType(0), RouteType(0),
                          RouteType(5), RouteType(5), RouteType(5), RouteType(5)] ),
                          CtrlType( OPT_INC, b1( 0 ), pickRegister, [
                          RouteType(4),RouteType(3), RouteType(2), RouteType(1),
                          RouteType(0), RouteType(0), RouteType(0), RouteType(0),
                          RouteType(5), RouteType(5), RouteType(5), RouteType(5)] ),
                          CtrlType( OPT_ADD, b1( 0 ), pickRegister, [
                          RouteType(4),RouteType(3), RouteType(2), RouteType(1),
                          RouteType(0), RouteType(0), RouteType(0), RouteType(0),
                          RouteType(5), RouteType(5), RouteType(5), RouteType(5)] ),
                          CtrlType( OPT_ADD, b1( 0 ), pickRegister, [
                          RouteType(4),RouteType(3), RouteType(2), RouteType(1),
                          RouteType(0), RouteType(0), RouteType(0), RouteType(0),
                          RouteType(5), RouteType(5), RouteType(5), RouteType(5)] ),
                          CtrlType( OPT_ADD, b1( 0 ), pickRegister, [
                          RouteType(4),RouteType(3), RouteType(2), RouteType(1),
                          RouteType(0), RouteType(0), RouteType(0), RouteType(0),
                          RouteType(5), RouteType(5), RouteType(5), RouteType(5)] ),
                          CtrlType( OPT_ADD, b1( 0 ), pickRegister, [
                          RouteType(4),RouteType(3), RouteType(2), RouteType(1),
                          RouteType(0), RouteType(0), RouteType(0), RouteType(0),
                          RouteType(5), RouteType(5), RouteType(5), RouteType(5)] ) ]
                          for _ in range( num_tiles ) ]
  ctrl_waddr   = [ [ AddrType( 0 ), AddrType( 1 ), AddrType( 2 ), AddrType( 3 ),
                     AddrType( 4 ), AddrType( 5 ) ] for _ in range( num_tiles ) ]

  dataSPM = None
  tiles = []
  links = None
  if paramCGRA != None:
    tiles = paramCGRA.getValidTiles()
    links = paramCGRA.getValidLinks()
    dataSPM = paramCGRA.dataSPM
  else:
    dataSPM = DataSPM(2, 2)
    for r in range( 2 ):
      tiles.append([])
      for c in range( 2 ):
        tiles[r].append(Tile(c, r))

    links = [ Link(None, None, 0, 0) for _ in range(16) ]

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

  th = TestHarness( DUT, FunctionUnit, FuList, DataType, PredicateType,
                    CtrlType, width, height, ctrl_mem_size, data_mem_size,
                    src_opt, ctrl_waddr, tiles, links, dataSPM )
  th.elaborate()
  th.dut.set_metadata( VerilogTranslationPass.explicit_module_name,
                    f'CGRATemplateRTL' )
  th.dut.set_metadata( VerilogVerilatorImportPass.vl_Wno_list,
                    ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                     'ALWCOMBORDER'] )
  th = config_model_with_cmdline_opts( th, cmdline_opts, duts=['dut'] )

  if paramCGRA != None:
    for tile in tiles:
        if not tile.isDefaultFus():
            targetFuList = []
            for fuType in tile.getAllValidFuTypes():
                targetFuList.append(fuType2RTL[fuType])
            targetTile = "top.dut.tile[" + str(tile.getIndex(tiles)) + "].construct"
            th.set_param(targetTile, FuList=targetFuList)

  run_sim( th )
