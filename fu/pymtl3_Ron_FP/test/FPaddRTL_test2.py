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
#from ...pymtl3_hardfloat.HardFloat.converter_funcs import floatToFN, fNToFloat

import random

import math

# this is for standard 16,32,64,128 bit things
exp_width      = [5, 8, 11, 15]
mantissa_width = [10, 23, 52, 112]

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
# This file contains the declaration of two functions:
#
# floatToStd( x, precision ): converts a floating point number to the
# IEEE-754 format
#
# stdToFloat( x, precision ): converts a number in IEEE-754 format to
# a floating point number
#
# NOTE: precision works as follows: half (16), single (32), double (64),
# and quadruple (128)
# ========================================================================


# ========================== Helper functions ============================
# Function to properly handle trailing values that start with 0
def decConv( dec ):
  num = 0
  index = 0

  while(dec[index] == '0'):
    num = num + 1
    index = index + 1

  return int(dec) * 10**(-num)

# Function for converting decimal to binary
def float_bin(number, places = 3):
  whole, dec = str(number).split(".")
  whole = int(whole)

  if(int(dec) != 0):
    dec = decConv( dec )
  else:
    dec = int(dec)

  print(dec)

  res = bin(whole).lstrip("0b") + "."

  for x in range(places):
    whole, dec = str((decimal_converter(dec)) * 2).split(".")

    if(int(dec) != 0):
      dec = decConv( dec )
    else:
      dec = int(dec)

    res += whole

  return res

def decimal_converter(num):
  while num > 1:
      num /= 10
  return num

get_bin = lambda x, n: format(x, 'b').zfill(n)
# ========================================================================

# ========= Floating-point number to IEEE-754 format converter ===========
def floatToFN( f, *, precision=None, exp_nbits=None, sig_nbits=None ):

  if precision is None:
    assert exp_nbits is not None and sig_nbits is not None, "Either precision or exp_nbits/sig_nbits should be None"
    precision = exp_nbits + sig_nbits + 1
  else:
    assert exp_nbits is None and sig_nbits is None, "Either precision or exp_nbits/sig_nbits should be None"
    assert precision in [16,32,64,128], "only support standard half/single/double precision"
    i = int(math.log2(precision)) - 4
    exp_nbits = exp_width[i]
    sig_nbits = mantissa_width[i]

  if math.isnan(f): return (((1<<exp_nbits)-1) << sig_nbits) + 1
  if f == float("inf"): return ((1<<exp_nbits)-1) << sig_nbits
  if f == float("-inf"): return (1 << (exp_nbits+sig_nbits)) | (((1<<exp_nbits)-1) << sig_nbits)
  if f == 0: return 0

  if f < 0:
    sign = 1
    f = -f
  else:
    sign = 0

  bias = (1 << (exp_nbits-1))-1
  zero_exp = -((1 << (exp_nbits-1))-1)
  one_exp  = 1 << (exp_nbits-1)

  exponent = math.floor( math.log( f, 2 ) )

  # one_exp <= exp, too big, +-inf
  if exponent >= one_exp:
    return (sign << (exp_nbits+sig_nbits)) | (((1<<exp_nbits)-1)<<sig_nbits)

  # exp < zero_exp-sig_nbits, too small, zero
  if exponent < zero_exp - sig_nbits:
    return 0

  # zero_exp-sig_nbits <= exp <= zero_exp, leading 0
  if exponent <= zero_exp:
    ret_exp = 0
    tmp = f/(2**(zero_exp + 1))

  # the last case is zero_exp < exp < one_exp, leading one
  else:
    ret_exp = exponent + bias
    tmp = f/(2**(exponent)) - 1

  ret_sig = 0
  for i in range(sig_nbits):
    tmp *= 2
    ret_sig <<= 1
    if tmp >= 1:
      ret_sig += 1
      tmp -= 1
  return (sign << (exp_nbits+sig_nbits)) | (ret_exp << sig_nbits) | ret_sig

# ========================================================================

# ========= IEEE-754 format to Floating-point number converter ===========
def fNToFloat( n, *, precision=None, exp_nbits=None, sig_nbits=None ):
  if precision is None:
    assert exp_nbits is not None and sig_nbits is not None, "Either precision or exp_nbits/sig_nbits should be None"
    precision = exp_nbits + sig_nbits + 1
  else:
    assert exp_nbits is None and sig_nbits is None, "Either precision or exp_nbits/sig_nbits should be None"
    assert precision in [16,32,64,128], "only support standard half/single/double precision"
    i = int(math.log2(precision)) - 4
    exp_nbits = exp_width[i]
    sig_nbits = mantissa_width[i]

  n = int(n)
  assert 0 <= n < 2**precision, f"{hex(n)} has more than {precision} bits"

  # Split the bitmask into three parts
  sign_raw     = n >> (precision-1)
  exp_raw      = (n >> sig_nbits) & ((1<<exp_nbits)-1)
  mantissa_raw = n & ((1<<sig_nbits)-1)

  # Calculate the real exp
  exp = exp_raw - ((1<<(exp_nbits-1))-1)

  if exp_raw == 0:
    # the exponent of exp_raw==0 is actually 1, as the leading digit is
    # zero instead of one according to IEEE754
    return ((-1)**sign_raw) * mantissa_raw * (2.0**(exp - sig_nbits + 1))
  elif exp_raw < ((1<<exp_nbits)-1):
    return ((-1)**sign_raw) * ( mantissa_raw * (2.0**(exp - sig_nbits)) + 2**exp )
  else:
    if mantissa_raw == 0:
      if sign_raw:  return float("-inf")
      return float("inf")
    return float("nan")

# ========================================================================
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

