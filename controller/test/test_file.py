from pymtl3 import *
from pymtl3.stdlib.primitive import Reg
from pymtl3.stdlib.test_utils import run_sim
from pymtl3.passes.backends.verilog import VerilogTranslationPass
from pymtl3.passes.backends.verilog.import_ import VerilogVerilatorImportPass
from pymtl3.passes.backends.verilog import (VerilogVerilatorImportPass)
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)

class MinimalRegisterTest( Component ):
    def construct( s ):
        s.count = Reg( Bits8 )
        s.count_out = OutPort( Bits8 )
        s.count_in = OutPort( Bits8 )
        
        # Wire outputs for debugging
        s.count_out //= s.count.out
        
        @update_ff
        def counter_ff():
            if s.reset:
                s.count.in_ <<= 0
                s.count_in <<= 0
            else:
                s.count.in_ <<= s.count.out + 1
                s.count_in <<= s.count.out + 1
    
    def line_trace( s ):
        return f"in:{s.count.in_} out:{s.count.out}"

def test_minimal_register():
    dut = MinimalRegisterTest()
    
    # Test with PyMTL3 simulation first
    print("=== PyMTL3 Simulation ===")
    dut.elaborate()
    dut.apply( DefaultPassGroup() )
    dut.sim_reset()
    
    for cycle in range(8):
        print(f"Cycle {cycle}: {dut.line_trace()}")
        dut.sim_tick()
    
    # Test with Verilog translation
    print("\n=== Verilog Translation Test ===")
    dut2 = MinimalRegisterTest()
    dut2.elaborate()
    
    # Add Verilog translation warnings suppression
    dut2.set_metadata( VerilogVerilatorImportPass.vl_Wno_list, 
                      ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT'] )
    
    # Apply Verilog translation and import
    dut2.apply( VerilogTranslationPass() )
    dut2.apply( VerilogVerilatorImportPass() )
    
    dut2.sim_reset()
    
    for cycle in range(8):
        print(f"Cycle {cycle}: {dut2.line_trace()}")
        dut2.sim_tick()

if __name__ == "__main__":
    test_minimal_register()