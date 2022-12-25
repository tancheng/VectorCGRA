"""
==========================================================================
CGRATemplateRTL_test.py
==========================================================================
Translation for parameterizable CGRA based on the template.

Author : Cheng Tan
  Date : Dec 23, 2022

"""

from pymtl3 import *
from pymtl3.stdlib.test             import TestSinkCL
from pymtl3.stdlib.test.test_srcs   import TestSrcRTL

from ...lib.opt_type                import *
from ...lib.messages                import *
from ...lib.common                  import *

from ...fu.flexible.FlexibleFuRTL   import FlexibleFuRTL
from ...fu.single.AdderRTL          import AdderRTL
from ...fu.single.MemUnitRTL        import MemUnitRTL
from ...fu.single.MulRTL            import MulRTL
from ...fu.single.SelRTL            import SelRTL
from ...fu.single.ShifterRTL        import ShifterRTL
from ...fu.single.LogicRTL          import LogicRTL
from ...fu.single.PhiRTL            import PhiRTL
from ...fu.single.CompRTL           import CompRTL
from ...fu.double.SeqMulAdderRTL    import SeqMulAdderRTL
from ...fu.single.BranchRTL         import BranchRTL
from ..CGRATemplateRTL              import CGRATemplateRTL

from pymtl3.passes.backends.verilog import TranslationImportPass

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness( Component ):

  def construct( s, DUT, FunctionUnit, FuList, DataType, PredicateType,
                 CtrlType, width, height, ctrl_mem_size, data_mem_size,
                 src_opt, ctrl_waddr, tileList, linkList ):

    s.num_tiles = width * height
    AddrType = mk_bits( clog2( ctrl_mem_size ) )

    s.src_opt     = [ TestSrcRTL( CtrlType, src_opt[i] )
                      for i in range( s.num_tiles ) ]
    s.ctrl_waddr  = [ TestSrcRTL( AddrType, ctrl_waddr[i] )
                      for i in range( s.num_tiles ) ]

    s.dut = DUT( DataType, PredicateType, CtrlType, width, height,
                 ctrl_mem_size, data_mem_size, len( src_opt[0] ),
                 FunctionUnit, FuList, tileList, linkList )

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
  def __init__( s, posX, posY ):
    s.disabled = False
    s.posX = posX
    s.posY = posY
    s.hasToMem = False
    s.hasFromMem = False
    s.invalidOutPorts = set()
    s.invalidInPorts = set()
    for i in range( DIRECTION_COUNTS ):
      s.invalidOutPorts.add(i)
      s.invalidInPorts.add(i)

  def getIndex( s, tileList ):
    if s.disabled:
      return -1
    index = 0
    for tile in tileList:
      if tile.posY < s.posY and not tile.disabled:
        index += 1
      elif tile.posY == s.posY and tile.posX < s.posX and not tile.disabled:
        index += 1
    return index

class Link:
  def __init__( s, srcTile, dstTile, srcPort, dstPort ):
    s.srcTile = srcTile
    s.dstTile = dstTile
    s.srcPort = srcPort
    s.dstPort = dstPort
    s.disabled = False
    s.isToMem = False
    s.isFromMem = False

  def validatePorts( s ):
    if not s.isToMem and not s.isFromMem:
      s.srcTile.invalidOutPorts.remove(s.srcPort)
      s.dstTile.invalidInPorts.remove(s.dstPort)
    if s.isToMem:
      s.srcTile.hasToMem = True
    if s.isFromMem:
      s.dstTile.hasFromMem = True

def run_sim( test_harness, max_cycles=10 ):
  test_harness.elaborate()
  test_harness.dut.verilog_translate_import = True
  test_harness.dut.config_verilog_import = VerilatorImportConfigs(vl_Wno_list             =         ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT', 'ALWCOMBORDER'])
  test_harness = TranslationImportPass()(test_harness)
  test_harness.apply( SimulationPass() )
  test_harness.sim_reset()

  # Run simulation
  ncycles = 0
  print()
  print( "{}:{}".format( ncycles, test_harness.line_trace() ))
  while not test_harness.done() and ncycles < max_cycles:
    test_harness.tick()
    ncycles += 1
    print( "{}:{}".format( ncycles, test_harness.line_trace() ))

  # Check timeout
  assert ncycles < max_cycles

  test_harness.tick()
  test_harness.tick()
  test_harness.tick()

import platform
import pytest

@pytest.mark.skipif('Linux' not in platform.platform(),
                    reason="requires linux (gcc)")
def test_cgra_universal():
  num_tile_inports  = 8
  num_tile_outports = 8
  num_xbar_inports  = 10
  num_xbar_outports = 12
  ctrl_mem_size     = 6
  width             = 2
  height            = 2
  RouteType         = mk_bits( clog2( num_xbar_inports + 1 ) )
  AddrType          = mk_bits( clog2( ctrl_mem_size ) )
  num_tiles         = width * height
  data_mem_size     = 8
  num_fu_in         = 4
  DUT               = CGRATemplateRTL
  FunctionUnit      = FlexibleFuRTL
  FuList            = [ SeqMulAdderRTL, MemUnitRTL ]#AdderRTL, MulRTL, LogicRTL, ShifterRTL, PhiRTL, CompRTL, BranchRTL, MemUnitRTL ]
  DataType          = mk_data( 32, 1 )
  PredicateType     = mk_predicate( 1, 1 )
#  FuList           = [ SeqMulAdderRTL, AdderRTL, MulRTL, LogicRTL, ShifterRTL, PhiRTL, CompRTL, BranchRTL, MemUnitRTL ]
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
                          CtrlType( OPT_STR, b1( 0 ), pickRegister, [
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

  tiles = []
  for y in range( 2 ):
    tiles.append([])
    for x in range( 2 ):
      tiles[y].append(Tile(x, y))

  links = [ Link(None, None, 0, 0) for _ in range(16) ]
  
  links[0].srcTile = None
  links[0].dstTile = tiles[0][0]
  links[0].srcPort = 0
  links[0].dstPort = WEST
  links[0].isFromMem = True
  links[0].validatePorts()

  links[1].srcTile = tiles[0][0]
  links[1].dstTile = None
  links[1].srcPort = WEST
  links[1].dstPort = 0
  links[1].isToMem = True
  links[1].validatePorts()

  links[2].srcTile = None
  links[2].dstTile = tiles[1][0]
  links[2].srcPort = 1
  links[2].dstPort = WEST
  links[2].isFromMem = True
  links[2].validatePorts()

  links[3].srcTile = tiles[1][0]
  links[3].dstTile = None
  links[3].srcPort = WEST
  links[3].dstPort = 1
  links[3].isToMem = True
  links[3].validatePorts()

  links[4].srcTile = tiles[0][0]
  links[4].dstTile = tiles[0][1]
  links[4].srcPort = EAST
  links[4].dstPort = WEST
  links[4].validatePorts()

  links[5].srcTile = tiles[0][1]
  links[5].dstTile = tiles[0][0]
  links[5].srcPort = WEST
  links[5].dstPort = EAST
  links[5].validatePorts()

  links[6].srcTile = tiles[1][0]
  links[6].dstTile = tiles[1][1]
  links[6].srcPort = EAST
  links[6].dstPort = WEST
  links[6].validatePorts()

  links[7].srcTile = tiles[1][1]
  links[7].dstTile = tiles[1][0]
  links[7].srcPort = WEST
  links[7].dstPort = EAST
  links[7].validatePorts()

  links[8].srcTile = tiles[0][0]
  links[8].dstTile = tiles[1][0]
  links[8].srcPort = NORTH
  links[8].dstPort = SOUTH
  links[8].validatePorts()

  links[9].srcTile = tiles[1][0]
  links[9].dstTile = tiles[0][0]
  links[9].srcPort = SOUTH
  links[9].dstPort = NORTH
  links[9].validatePorts()

  links[10].srcTile = tiles[0][1]
  links[10].dstTile = tiles[1][1]
  links[10].srcPort = NORTH
  links[10].dstPort = SOUTH
  links[10].validatePorts()

  links[11].srcTile = tiles[1][1]
  links[11].dstTile = tiles[0][1]
  links[11].srcPort = SOUTH
  links[11].dstPort = NORTH
  links[11].validatePorts()

  links[12].srcTile = tiles[0][0]
  links[12].dstTile = tiles[1][1]
  links[12].srcPort = NORTHEAST
  links[12].dstPort = SOUTHWEST
  links[12].validatePorts()

  links[13].srcTile = tiles[1][1]
  links[13].dstTile = tiles[0][0]
  links[13].srcPort = SOUTHWEST
  links[13].dstPort = NORTHEAST
  links[13].validatePorts()

  links[14].srcTile = tiles[0][1]
  links[14].dstTile = tiles[1][0]
  links[14].srcPort = NORTHWEST
  links[14].dstPort = SOUTHEAST
  links[14].validatePorts()

  links[15].srcTile = tiles[1][0]
  links[15].dstTile = tiles[0][1]
  links[15].srcPort = SOUTHEAST
  links[15].dstPort = NORTHWEST
  links[15].validatePorts()

  def handleReshape( t_tiles, t_links ):
    tiles = []
    for row in t_tiles:
      for t in row:
        tiles.append(t)
    return tiles, t_links

  def validate( t_tiles, t_links ):
    pass

  tileList, linkList = handleReshape(tiles, links)
  validate( tiles, links )

  print("done assemble links", links)

  th = TestHarness( DUT, FunctionUnit, FuList, DataType, PredicateType,
                    CtrlType, width, height, ctrl_mem_size, data_mem_size,
                    src_opt, ctrl_waddr, tileList, linkList )
  run_sim( th )

