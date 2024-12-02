#=========================================================================
# Unit testing for AddFNRTL PyMTL wrapper module
#=========================================================================


from pymtl3 import *
from pymtl3.stdlib.test_utils import run_test_vector_sim, TestVectorSimulator
from pymtl3.passes.backends.verilog import *
from hypothesis import given
from hypothesis import settings
from hypothesis import strategies as st
from ..ALUgenMACRTL import ALUgenMAC
import hypothesis
import random


# =========================== Helper functions ===========================
def abs( x ):
  if(x < 0):
    return -x
  else:
    return x

def get_rand( low, high, precision ):
  val = round(random.uniform(low, high), precision)
  while abs(val) < 1:
    val = round(random.uniform(low, high), precision)

  return val
# ========================================================================

#-------------------------------------------------------------------------
# TestVectorSimulator test
#-------------------------------------------------------------------------
def run_tv_test( dut, test_vectors, tolerance ):

  # Define input/output functions
  def tv_in( dut, tv ):
    dut.rhs_0  @= tv[0]
    dut.rhs_1  @= tv[1]
    dut.rhs_1b @= tv[2]
    dut.rhs_2  @= tv[3]

  def tv_out( dut, tv ):
    test_out = tv[4]
    actual_out = dut.lhs_0

    assert abs(test_out - actual_out) <= tolerance

  # Run the test
  dut.elaborate()

  dut.set_metadata( VerilogTranslationImportPass.enable, True )

  dut.apply( VerilogPlaceholderPass() )
  dut = VerilogTranslationImportPass()( dut )

  sim = TestVectorSimulator( dut, test_vectors, tv_in, tv_out )
  sim.run_test()

# ====================== Tests ========================
#          b0 b1 b2 b3 b4 b5
# A + B     0  0  ?  0  0  0
# A − B     1  0  ?  0  0  0
# A < B     1  1  0  0  0  0
# A ≥ B     1  1  1  0  0  0
# A > B     0  1  0  1  0  0
# A ≤ B     0  1  1  1  0  0
# A · B     0  0  ?  0  1  0
# A · B + C 0  0  ?  0  1  1

def test_add_ones(cmdline_opts):
  tolerance = 0.00

  a = 1.0
  b = 1.0
  c = 99
  out = a + b

  run_tv_test( ALUgenMAC(), [[a, b, c, 0, out]], tolerance)

def test_sub(cmdline_opts):
  tolerance = 0.00

  a = 15
  b = 9
  c = 99
  out = a - b

  run_tv_test( ALUgenMAC(), [[a, b, c, 1, out]], tolerance)

def test_gte(cmdline_opts):
  tolerance = 0.00

  a = 14
  b = 14
  c = 99
  out = 1

  run_tv_test( ALUgenMAC(), [[a, b, c, 7, out]], tolerance)

def test_mul(cmdline_opts):
  tolerance = 0.00

  a = 10
  b = 135
  c = 99
  out = a * b

  run_tv_test( ALUgenMAC(), [[a, b, c, 16, out]], tolerance)

def test_mac(cmdline_opts):
  tolerance = 0.00

  a = 10
  b = 135
  c = 99
  out = a * b + c

  run_tv_test( ALUgenMAC(), [[a, b, c, 48, out]], tolerance)

