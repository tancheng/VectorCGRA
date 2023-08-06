"""
==========================================================================
CGRARTL_test.py
==========================================================================
Translation for CGRAs with different configurations.

Author : Cheng Tan, Yanghui Ou
  Date : July 12, 2023
"""

from pymtl3 import *
from pymtl3.passes.backends.verilog import VerilogTranslationPass
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)

from ...lib.opt_type                import *
from ...lib.messages                import *
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
from ..CGRARTL                      import CGRARTL

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

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
num_fu_in         = 4
DUT               = CGRARTL
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
                    f'CGRARTL' )
  config_model_with_cmdline_opts( dut, cmdline_opts, duts=[] )

