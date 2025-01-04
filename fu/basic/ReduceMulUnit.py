'''
==========================================================================
ReduceMulUnit.py
==========================================================================
A parameterized reduce integer multiply unit that calculates the product
of N inputs. This unit simply has a chain of multipliers. A potentially
more optimized implementation could use a tree of multipliers instead of a
chain.

This unit assumes no overflow.

Author : Yanghui Ou
  Date : Jul 30, 2023
'''

from pymtl3 import *

class ReduceMulUnit( Component ):

  def construct( s, DataType, num_inputs ):
    # Local parameter
    s.DataType   = DataType
    s.num_inputs = num_inputs

    # Interface
    s.in_ = [ InPort( s.DataType ) for _ in range( s.num_inputs ) ]
    s.out = OutPort( s.DataType )

    # Components
    s.partial_sum = [ Wire( s.DataType ) for _ in range( s.num_inputs ) ]

    @update
    def up_sum():
      s.partial_sum[0] @= s.in_[0]
      for i in range( 1, s.num_inputs ):
        s.partial_sum[i] @= s.partial_sum[i-1] * s.in_[i]

    s.out //= s.partial_sum[s.num_inputs-1]

  def line_trace( s ):
    in_trace = '*'.join([str(p) for p in s.in_])
    return f'{s.in_trace}(){s.out}'

