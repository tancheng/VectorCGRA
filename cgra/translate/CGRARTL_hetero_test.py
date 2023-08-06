"""
==========================================================================
CGRARTL_hetero_test.py
==========================================================================
Test cases for heterogeneous CGRAs.

Author : Cheng Tan, Yanghui Ou
  Date : July 12, 2023
"""

from pymtl3 import *
from pymtl3.passes.backends.verilog import (VerilogTranslationPass,
                                            VerilogVerilatorImportPass)
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)

from ...lib.opt_type                import *
from ...lib.messages                import *
from ...fu.flexible.FlexibleFuRTL   import FlexibleFuRTL
from ...fu.single.AdderRTL          import AdderRTL
from ...fu.single.ShifterRTL        import ShifterRTL
from ...fu.single.MemUnitRTL        import MemUnitRTL
from ..CGRARTL                      import CGRARTL

num_tile_inports  = 4
num_tile_outports = 4
num_xbar_inports  = 6
num_xbar_outports = 8
ctrl_mem_size     = 6
width             = 2
height            = 2
RouteType         = mk_bits( clog2( num_xbar_inports + 1 ) )
AddrType          = mk_bits( clog2( ctrl_mem_size ) )
num_tiles         = width * height
data_mem_size     = 8
DUT               = CGRARTL
num_fu_in         = 4
FunctionUnit      = FlexibleFuRTL
FuList            = [MemUnitRTL, AdderRTL]
DataType          = mk_data( 16, 1 )
PredicateType     = mk_predicate( 1, 1 )
CtrlType          = mk_ctrl( num_fu_in, num_xbar_inports, num_xbar_outports )
FuInType          = mk_bits( clog2( num_fu_in + 1 ) )
pickRegister      = [ FuInType( x+1 ) for x in range( num_fu_in ) ]
src_opt           = [ [ CtrlType( OPT_INC, b1( 0 ), pickRegister, [
                        RouteType(4), RouteType(3), RouteType(2), RouteType(1),
                        RouteType(5), RouteType(5), RouteType(5), RouteType(5)] ),
                        CtrlType( OPT_INC, b1( 0 ), pickRegister, [
                        RouteType(4),RouteType(3), RouteType(2), RouteType(1),
                        RouteType(5), RouteType(5), RouteType(5), RouteType(5)] ),
                        CtrlType( OPT_ADD, b1( 0 ), pickRegister, [
                        RouteType(4),RouteType(3), RouteType(2), RouteType(1),
                        RouteType(5), RouteType(5), RouteType(5), RouteType(5)] ),
                        CtrlType( OPT_STR, b1( 0 ), pickRegister, [
                        RouteType(4),RouteType(3), RouteType(2), RouteType(1),
                        RouteType(5), RouteType(5), RouteType(5), RouteType(5)] ),
                        CtrlType( OPT_ADD, b1( 0 ), pickRegister, [
                        RouteType(4),RouteType(3), RouteType(2), RouteType(1),
                        RouteType(5), RouteType(5), RouteType(5), RouteType(5)] ),
                        CtrlType( OPT_ADD, b1( 0 ), pickRegister, [
                        RouteType(4),RouteType(3), RouteType(2), RouteType(1),
                        RouteType(5), RouteType(5), RouteType(5), RouteType(5)] ) ]
                        for _ in range( num_tiles ) ]

def test_elaborate():
  dut = CGRARTL( DataType, PredicateType, CtrlType, width, height,
                 ctrl_mem_size, data_mem_size, len( src_opt[0] ),
                 FunctionUnit, FuList )
  dut.apply( DefaultPassGroup(linetrace=True) )
  dut.sim_reset()
  dut.sim_tick()
  dut.sim_tick()

# TODO: fix import by either suppressing warnings or address them
def test_translate( cmdline_opts ):
  dut = CGRARTL( DataType, PredicateType, CtrlType, width, height,
                 ctrl_mem_size, data_mem_size, len( src_opt[0] ),
                 FunctionUnit, FuList )
  dut.set_metadata( VerilogTranslationPass.explicit_module_name,
                    f'CGRAHeteroRTL' )
  dut.set_metadata( VerilogVerilatorImportPass.vl_Wno_list,
                    ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                     'ALWCOMBORDER'] )
  config_model_with_cmdline_opts( dut, cmdline_opts, duts=[] )
  # test_harness.dut.config_verilog_import = VerilatorImportConfigs(vl_Wno_list = ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT', 'ALWCOMBORDER'])

