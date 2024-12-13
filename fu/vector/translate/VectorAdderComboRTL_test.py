'''
==========================================================================
VectorAdderComboRTL_test.py
==========================================================================

Author: Yanghui Ou
  Date: July 11, 2023
'''


from pymtl3 import *
from pymtl3.passes.backends.verilog import VerilogTranslationPass
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)

from ..VectorAdderComboRTL          import VectorAdderComboRTL
from ....lib.opt_type               import *
from ....lib.messages               import *

DataType      = mk_data( 64, 1 )
PredicateType = mk_predicate( 1, 1 )
num_inports   = 4
CtrlType      = mk_ctrl( num_fu_in = num_inports )
num_outports  = 2
data_mem_size = 8

def test_elaborate():
  dut = VectorAdderComboRTL( DataType, PredicateType, CtrlType,
                             num_inports, num_outports, data_mem_size )
  dut.apply( DefaultPassGroup(linetrace=True) )
  dut.sim_reset()
  dut.sim_tick()
  dut.sim_tick()

# TODO: fix import by either suppressing warnings or address them
def test_translate( cmdline_opts ):
  dut = VectorAdderComboRTL( DataType, PredicateType, CtrlType,
                             num_inports, num_outports, data_mem_size )
  dut.set_metadata( VerilogTranslationPass.explicit_module_name,
                    f'VectorAdderComboRTL' )
  config_model_with_cmdline_opts( dut, cmdline_opts, duts=[] )

