#=========================================================================
# Unit testing for AddFNRTL PyMTL wrapper module
#=========================================================================

from pymtl3 import *
from pymtl3.stdlib.test_utils import run_test_vector_sim, TestVectorSimulator
from pymtl3.passes.backends.verilog import *

import hypothesis
from hypothesis import given
from hypothesis import strategies as st
from hypothesis import settings

#from HardFloat.AddFNRTL import AddFN
#from HardFloat.converter_funcs import floatToFN, fNToFloat
from ..FPaddRTL import FPadd
from ...pymtl3_hardfloat.HardFloat.converter_funcs import floatToFN, fNToFloat

import random

# ========================================================================
round_near_even   = 0b000
round_minMag      = 0b001
round_min         = 0b010
round_max         = 0b011
round_near_maxMag = 0b100
round_odd         = 0b110

# =================== Format of floating point number ====================
# bin('0b' + '0' + '00000' + '0000000000')
#      bin   sign   expon     significand
# ========================================================================

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
def run_tv_test( dut, test_vectors, precision, tolerance ):

  # Define input/output functions
  def tv_in( dut, tv ):
    dut.rhs_0 @= tv[2]
    dut.rhs_1 @= tv[3]

  def tv_out( dut, tv ):
    test_out = fNToFloat(tv[4], precision=precision)
    actual_out = fNToFloat(dut.out, precision=precision)

    assert abs(test_out - actual_out) < tolerance

  # Run the test
  dut.elaborate()

  dut.set_metadata( VerilogTranslationImportPass.enable, True )

  dut.apply( VerilogPlaceholderPass() )
  dut = VerilogTranslationImportPass()( dut )

  sim = TestVectorSimulator( dut, test_vectors, tv_in, tv_out )
  sim.run_test()

# ====================== Tests for half-precision ========================

def test_addF16_ones():

  expWidth = 5
  sigWidth = 11
  precision = expWidth + sigWidth
  tolerance = 0.001

  a = 1.0
  b = 1.0
  out = a + b

  a = floatToFN(a, precision=precision)
  b = floatToFN(b, precision=precision)
  out = floatToFN(out, precision=precision)

  run_tv_test( FPadd(), [[0, 0, a, b, out]],  precision, tolerance)

