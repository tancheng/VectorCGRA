'''
==========================================================================
ExclusiveDivRTL_test.py
==========================================================================

Author: Jiajun Qin
  Date: June 2, 2025
'''


from pymtl3 import *
from pymtl3.passes.backends.verilog import VerilogTranslationPass
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)
from ..CompRTL import CompRTL
from ..MemUnitRTL import MemUnitRTL
from ..MulRTL import MulRTL
from ..ExclusiveDivRTL import ExclusiveDivRTL
from ....lib.messages import *
from ....lib.opt_type import *

data_bitwidth = 32
DataType      = mk_data( data_bitwidth, 1 )
PredicateType = mk_predicate( 1, 1 )
num_inports   = 4
num_outports  = 2
ConfigType = mk_ctrl(4, 2)
data_mem_size = 8
latency       = 4

def test_elaborate(cmdline_opts):
  dut = ExclusiveDivRTL( DataType, ConfigType,
                 num_inports, num_outports, data_mem_size,
                 latency = latency, data_bitwidth = data_bitwidth)
  dut = config_model_with_cmdline_opts(dut, cmdline_opts, duts = [])

# TODO: fix import by either suppressing warnings or address them
def test_translate( cmdline_opts ):
  dut = ExclusiveDivRTL( DataType, ConfigType,
                 num_inports, num_outports, data_mem_size,
                 latency = latency, data_bitwidth = data_bitwidth)
  dut.set_metadata( VerilogTranslationPass.explicit_module_name,
                    f'ExclusiveDivRTL' )
  config_model_with_cmdline_opts( dut, cmdline_opts, duts=[] )

