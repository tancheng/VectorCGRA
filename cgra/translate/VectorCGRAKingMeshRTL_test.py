"""
==========================================================================
VectorCGRAKingMeshRTL_test.py
==========================================================================
Test cases for CGRAs with different configurations.

Author : Cheng Tan
  Date : April 1, 2023
"""


from pymtl3 import *
from pymtl3.passes.backends.verilog import (VerilogTranslationPass,
                                            VerilogVerilatorImportPass)
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)
from ..CGRAKingMeshRTL import CGRAKingMeshRTL
from ...fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from ...fu.single.AdderRTL import AdderRTL
from ...fu.single.BranchRTL import BranchRTL
from ...fu.single.CompRTL import CompRTL
from ...fu.single.LogicRTL import LogicRTL
from ...fu.single.MemUnitRTL import MemUnitRTL
from ...fu.single.MulRTL import MulRTL
from ...fu.single.PhiRTL import PhiRTL
from ...fu.single.SelRTL import SelRTL
from ...fu.single.ShifterRTL import ShifterRTL
from ...fu.vector.VectorAdderComboRTL import VectorAdderComboRTL
from ...fu.vector.VectorMulComboRTL import VectorMulComboRTL
from ...lib.basic.en_rdy.test_srcs import TestSrcRTL
from ...lib.messages import *
from ...lib.opt_type import *


#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness( Component ):

  def construct( s, DUT, FunctionUnit, fu_list, DataType, PredicateType,
                 CtrlType, width, height, ctrl_mem_size, data_mem_size,
                 src_opt, ctrl_waddr):

    s.num_tiles = width * height
    AddrType = mk_bits( clog2( ctrl_mem_size ) )

    s.src_opt     = [ TestSrcRTL( CtrlType, src_opt[i] )
                      for i in range( s.num_tiles ) ]
    s.ctrl_waddr  = [ TestSrcRTL( AddrType, ctrl_waddr[i] )
                      for i in range( s.num_tiles ) ]

    s.dut = DUT( DataType, PredicateType, CtrlType, width, height,
                 ctrl_mem_size, data_mem_size, len( src_opt[0] ),
                 len( src_opt[0] ), FunctionUnit, fu_list )

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

def test_homo_4x4( cmdline_opts ):
  num_tile_inports  = 8
  num_tile_outports = 8
  num_xbar_inports  = 10
  num_xbar_outports = 12
  ctrl_mem_size     = 6
  width         = 4
  height        = 4
  RouteType     = mk_bits( clog2( num_xbar_inports + 1 ) )
  AddrType      = mk_bits( clog2( ctrl_mem_size ) )
  num_tiles     = width * height
  data_mem_size = 8
  num_fu_in     = 4
  DUT           = CGRAKingMeshRTL
  FunctionUnit  = FlexibleFuRTL
  # FuList        = [MemUnitRTL, AdderRTL]
  vector_list        = [ AdderRTL, MulRTL, LogicRTL, ShifterRTL, PhiRTL, CompRTL, BranchRTL, MemUnitRTL, SelRTL, VectorMulComboRTL, VectorAdderComboRTL ]
  scalar_list   = [ AdderRTL, MulRTL, LogicRTL, ShifterRTL, PhiRTL, CompRTL, BranchRTL, MemUnitRTL, SelRTL ]
  DataType      = mk_data( 64, 1 )
  PredicateType = mk_predicate( 1, 1 )
  CtrlType      = mk_ctrl( num_fu_in, num_xbar_inports, num_xbar_outports )
  FuInType      = mk_bits( clog2( num_fu_in + 1 ) )
  pickRegister  = [ FuInType( x+1 ) for x in range( num_fu_in ) ]
  src_opt       = [[ CtrlType( OPT_INC, b1( 0 ), pickRegister, [
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
  ctrl_waddr   = [[ AddrType( 0 ), AddrType( 1 ), AddrType( 2 ), AddrType( 3 ),
                    AddrType( 4 ), AddrType( 5 ) ] for _ in range( num_tiles ) ]
  th = TestHarness( DUT, FunctionUnit, vector_list, DataType, PredicateType,
                    CtrlType, width, height, ctrl_mem_size, data_mem_size,
                    src_opt, ctrl_waddr )
  for row in range( height ):
    for col in range( width ):
      idx = col + row * height
      if row % 2 == 0 and col % 2 == 1 or row % 2 == 1 and col % 2 == 0:
        print( f' - set tile[{idx}] to vector')
        th.set_param( f'top.dut.tile[{idx}].construct', FuList=vector_list  )
      else:
        print( f' - set tile[{idx}] to scalar')
        th.set_param( f'top.dut.tile[{idx}].construct', FuList=scalar_list  )

  th.elaborate()
  th.dut.set_metadata( VerilogTranslationPass.explicit_module_name,
                    f'VectorCGRAKingMeshRTL_{width}x{height}' )
  # th.dut.set_metadata( VerilogVerilatorImportPass.vl_Wno_list,
  #                   ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
  #                    'ALWCOMBORDER'] )
  # th = config_model_with_cmdline_opts( th, cmdline_opts, duts=['dut'] )

  run_sim( th, cmdline_opts, duts=['dut'] )

