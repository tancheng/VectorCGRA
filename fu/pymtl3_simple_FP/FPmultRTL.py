#=========================================================================
# Wrapper for HardFloat's addition and subtraction module
#=========================================================================

from pymtl3 import *
from pymtl3.passes.backends.verilog import *

class FPmult( VerilogPlaceholder, Component ):

  # Constructor

  def construct( s, expWidth = 5, sigWidth = 11 ):

    # Interface
    #input logic clk,
    #input logic rst,
    #//Inputs
    #input logic [15:0] rhs_0,
    #input logic [15:0] rhs_1,
    #//Outputs
    #output logic [15:0] lhs_0
    s.clk = InPort() # unused
    s.rst = InPort() # unused
    s.rhs_0 = InPort(16)
    s.rhs_1 = InPort(16)
    s.lhs_0 = OutPort(16)

    # Configurations

    # Configurations

    from os import path
    srcdir = path.dirname(__file__) + path.sep + 'svsrc' + path.sep

    s.set_metadata( VerilogPlaceholderPass.src_file, srcdir + 'FPmult.sv' )
    s.set_metadata( VerilogPlaceholderPass.top_module, 'FPmult_plain' )
    s.set_metadata( VerilogPlaceholderPass.v_include, [ srcdir ] )
    #s.set_metadata( VerilogPlaceholderPass.v_libs, [
    #  srcdir + 'HardFloat_primitives.v',
    #  srcdir + 'isSigNaNRecFN.v',
    #  srcdir + 'HardFloat_rawFN.v',
    #])
    s.set_metadata( VerilogPlaceholderPass.has_clk, False )
    s.set_metadata( VerilogPlaceholderPass.has_reset, False )

    s.set_metadata( VerilogVerilatorImportPass.vl_Wno_list, ['WIDTH'] )
