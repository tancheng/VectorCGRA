#=========================================================================
# Wrapper for HardFloat's addition and subtraction module
#=========================================================================

from pymtl3 import *
from pymtl3.passes.backends.verilog import *

class AluGenMacWrapperRTL( VerilogPlaceholder, Component ):

  # Constructor

  def construct( s ):

    # Interface
    #input logic signed [15:0] rhs_0,
    #input logic signed [15:0] rhs_1,
    #input logic signed [15:0] rhs_1b,
    #input logic [5:0] rhs_2,
    #output logic signed [15:0] lhs_0
    s.rhs_0  = InPort(16)
    s.rhs_1  = InPort(16)
    s.rhs_1b = InPort(16)
    s.rhs_2  = InPort(6)
    s.lhs_0  = OutPort(16)

    from os import path
    srcdir = path.dirname(__file__) + path.sep + 'svsrc' + path.sep

    s.set_metadata( VerilogPlaceholderPass.src_file, srcdir + 'ALUgenMAC.sv' )
    s.set_metadata( VerilogPlaceholderPass.top_module, 'ALUgenMAC' )
    s.set_metadata( VerilogPlaceholderPass.v_include, [ srcdir ] )
    #s.set_metadata( VerilogPlaceholderPass.v_libs, [
    #  srcdir + 'HardFloat_primitives.v',
    #  srcdir + 'isSigNaNRecFN.v',
    #  srcdir + 'HardFloat_rawFN.v',
    #])
    s.set_metadata( VerilogPlaceholderPass.has_clk, False )
    s.set_metadata( VerilogPlaceholderPass.has_reset, False )

    s.set_metadata( VerilogVerilatorImportPass.vl_Wno_list, ['WIDTH'] )

