'''
==========================================================================
TileVectorRTL_test.py
==========================================================================

Author: Yanghui Ou
  Date: July 11, 2023
'''
from pymtl3 import *
from pymtl3.passes.backends.verilog import VerilogTranslationPass
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)

from ...lib.opt_type                      import *
from ...lib.messages                      import *
from ...fu.triple.ThreeMulAdderShifterRTL import ThreeMulAdderShifterRTL
from ...fu.flexible.FlexibleFuRTL         import FlexibleFuRTL
from ...fu.vector.VectorMulComboRTL       import VectorMulComboRTL
from ...fu.vector.VectorAdderComboRTL     import VectorAdderComboRTL
from ...fu.vector.VectorAllReduceRTL      import VectorAllReduceRTL
from ...fu.single.AdderRTL                import AdderRTL
from ...fu.single.MemUnitRTL              import MemUnitRTL
from ...fu.single.MulRTL                  import MulRTL
from ...fu.single.SelRTL                  import SelRTL
from ...fu.single.ShifterRTL              import ShifterRTL
from ...fu.single.LogicRTL                import LogicRTL
from ...fu.single.PhiRTL                  import PhiRTL
from ...fu.single.CompRTL                 import CompRTL
from ...fu.single.BranchRTL               import BranchRTL
from ...fu.triple.ThreeMulAdderShifterRTL import ThreeMulAdderShifterRTL
from ...mem.ctrl.CtrlMemRTL               import CtrlMemRTL
from ..TileRTL                            import TileRTL

num_connect_inports  = 4
num_connect_outports = 4
num_fu_inports       = 4
num_fu_outports      = 2
num_xbar_inports     = num_fu_outports + num_connect_inports
num_xbar_outports    = num_fu_inports + num_connect_outports
ctrl_mem_size        = 3
data_mem_size        = 8
num_fu_in            = 4

RouteType     = mk_bits( clog2( num_xbar_inports + 1 ) )
AddrType      = mk_bits( clog2( ctrl_mem_size ) )
DUT           = TileRTL
FunctionUnit  = FlexibleFuRTL
# FuList        = [ AdderRTL, BranchRTL, MemUnitRTL, VectorMulComboRTL, VectorAdderComboRTL, VectorAdderComboRTL, VectorAdderComboRTL, VectorAdderComboRTL, VectorAdderComboRTL, VectorAdderComboRTL, VectorAdderComboRTL, VectorAdderComboRTL ]
FuList        = [ AdderRTL, MulRTL, LogicRTL, ShifterRTL, PhiRTL, CompRTL, BranchRTL, MemUnitRTL, SelRTL, VectorMulComboRTL, VectorAdderComboRTL ]#, VectorAllReduceRTL ]
#  FuList       = [AdderRTL]
#  FuList      = [ThreeMulAdderShifterRTL]
DataType      = mk_data( 64, 1 )
PredicateType = mk_predicate( 1, 1 )
CtrlType      = mk_ctrl( num_fu_in, num_xbar_inports, num_xbar_outports )
FuInType      = mk_bits( clog2( num_fu_in + 1 ) )
pickRegister  = [ FuInType( x+1 ) for x in range( num_fu_in ) ]
opt_waddr     = [ AddrType( 0 ), AddrType( 1 ), AddrType( 2 ) ]

src_opt       = [ CtrlType( OPT_NAH, b1( 0 ), pickRegister, [
                  RouteType(0), RouteType(0), RouteType(0), RouteType(0),
                  RouteType(4), RouteType(3), RouteType(0), RouteType(0)] ),
                  CtrlType( OPT_ADD, b1( 0 ), pickRegister, [
                  RouteType(0), RouteType(0), RouteType(0), RouteType(5),
                  RouteType(4), RouteType(1), RouteType(0), RouteType(0)] ),
                  CtrlType( OPT_SUB, b1( 0 ), pickRegister, [
                  RouteType(5), RouteType(0), RouteType(0), RouteType(5),
                  RouteType(0), RouteType(0), RouteType(0), RouteType(0)] ) ]

def test_elaborate():
  dut = TileRTL( DataType, PredicateType, CtrlType, ctrl_mem_size,
                 data_mem_size, len(src_opt), num_fu_inports,
                 num_fu_outports, 4, 4, FunctionUnit, FuList )
  dut.apply( DefaultPassGroup(linetrace=True) )
  dut.sim_reset()
  dut.sim_tick()
  dut.sim_tick()

# TODO: fix import by either suppressing warnings or address them
def test_translate( cmdline_opts ):
  dut = TileRTL( DataType, PredicateType, CtrlType, ctrl_mem_size,
                       data_mem_size, len(src_opt), num_fu_inports,
                       num_fu_outports, 4, 4, FunctionUnit, FuList )
  dut.set_metadata( VerilogTranslationPass.explicit_module_name,
                    f'TileVectorRTL' )
  config_model_with_cmdline_opts( dut, cmdline_opts, duts=[] )

