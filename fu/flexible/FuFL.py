"""
=========================================================================
FuFL.py
=========================================================================
A functional unit implemented in functional level for verification of the CL
and RTL designs.

Author : Cheng Tan
  Date : April 8, 2020
"""


from pymtl3 import *
from ...lib.opt_type import *
from ...lib.messages import *


#------------------------------------------------------------------------
# Assuming that the elements in FuDFG are already ordered well.
#------------------------------------------------------------------------

def FuFL( DataType, input_a, input_b, opt ):
  out_list = []
  for i in range( len( input_a ) ):
    if( opt[i].operation == OPT_ADD):
      out_list.append(DataType(input_a[i].payload + input_b[i].payload))
    elif( opt[i].operation == OPT_SUB):
      out_list.append(DataType(input_a[i].payload - input_b[i].payload))
    elif( opt[i].operation == OPT_MUL):
      out_list.append(DataType(input_a[i].payload * input_b[i].payload))
  return out_list

