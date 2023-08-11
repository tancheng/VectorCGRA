"""
==========================================================================
FpMulRTL_test.py
==========================================================================
Test cases for floating-point muliplier.

Author : Cheng Tan
  Date : August 10, 2023

"""

from pymtl3                       import *
from pymtl3.stdlib.test_utils     import (run_sim,
                                          config_model_with_cmdline_opts)
from ....lib.test_sinks           import TestSinkRTL
from ....lib.test_srcs            import TestSrcRTL
from ....lib.opt_type             import *
from ....lib.messages             import *
from ....mem.const.ConstQueueRTL  import ConstQueueRTL
from ..FpMulRTL                   import FpMulRTL

from ...pymtl3_hardfloat.HardFloat.converter_funcs import (floatToFN,
                                                           fNToFloat)

round_near_even   = 0b000

def test_elaborate( cmdline_opts ):
  DataType      = mk_data( 16, 1 )
  PredicateType = mk_predicate( 1, 1 )
  ConfigType    = mk_ctrl()
  data_mem_size = 8
  num_inports   = 2
  num_outports  = 1
  FuInType      = mk_bits( clog2( num_inports + 1 ) )
  pickRegister  = [ FuInType( x+1 ) for x in range( num_inports ) ]
  src_in0       = [ DataType(2, 1), DataType(7, 1), DataType(4, 1) ]
  src_in1       = [ DataType(1, 1), DataType(3, 1), DataType(1, 1) ]
  src_predicate = [ PredicateType(1, 0), PredicateType(1, 0), PredicateType(1, 1) ]
  src_const     = [ DataType(5, 1), DataType(0, 0),  DataType(7, 1) ]
  sink_out      = [ DataType(10, 0), DataType(21, 0), DataType(28, 1) ]
  src_opt       = [ ConfigType( OPT_MUL_CONST, b1( 1 ), pickRegister ),
                    ConfigType( OPT_MUL,       b1( 1 ), pickRegister ),
                    ConfigType( OPT_MUL_CONST, b1( 1 ), pickRegister ) ]
  dut = FpMulRTL( DataType, PredicateType, ConfigType, num_inports,
                  num_outports, data_mem_size, exp_nbits=4, sig_nbits=11 )
  dut = config_model_with_cmdline_opts( dut, cmdline_opts, duts=[] )

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness( Component ):

  def construct( s, FunctionUnit, DataType, PredicateType, ConfigType,
                 num_inports, num_outports, data_mem_size,
                 src0_msgs, src1_msgs, src_predicate, src_const,
                 ctrl_msgs, sink_msgs ):

    s.src_in0       = TestSrcRTL( DataType,      src0_msgs     )
    s.src_in1       = TestSrcRTL( DataType,      src1_msgs     )
    s.src_predicate = TestSrcRTL( PredicateType, src_predicate )
    s.src_opt       = TestSrcRTL( ConfigType,    ctrl_msgs     )
    s.sink_out      = TestSinkRTL( DataType,     sink_msgs     )

    s.const_queue = ConstQueueRTL( DataType, src_const )
    s.dut = FunctionUnit( DataType, PredicateType, ConfigType,
                          num_inports, num_outports, data_mem_size )

    for i in range( num_inports ):
      s.dut.recv_in_count[i] //= 1

    connect( s.src_in0.send,       s.dut.recv_in[0]         )
    connect( s.src_in1.send,       s.dut.recv_in[1]         )
    connect( s.src_predicate.send, s.dut.recv_predicate     )
    connect( s.dut.recv_const,     s.const_queue.send_const )
    connect( s.src_opt.send,       s.dut.recv_opt           )
    connect( s.dut.send_out[0],    s.sink_out.recv          )

  def done( s ):
    return s.src_in0.done() and s.src_in1.done() and \
           s.src_opt.done() and s.sink_out.done()

  def line_trace( s ):
    return s.dut.line_trace()

def mk_float_to_bits_fn( DataType, exp_nbits = 4, sig_nbits = 11 ):
  return lambda f_value, predicate: (
      DataType( floatToFN( f_value,
                           precision = 1 + exp_nbits + sig_nbits ),
                predicate ) )

def test_mul():
  FU            = FpMulRTL
  exp_nbits     = 4
  sig_nbits     = 11
  DataType      = mk_data( 1 + exp_nbits + sig_nbits, 1 )
  f2b           = mk_float_to_bits_fn( DataType, exp_nbits, sig_nbits )
  PredicateType = mk_predicate( 1, 1 )
  ConfigType    = mk_ctrl()
  data_mem_size = 8
  num_inports   = 2
  num_outports  = 1
  FuInType      = mk_bits( clog2( num_inports + 1 ) )
  pickRegister  = [ FuInType( x+1 ) for x in range( num_inports ) ]
  src_in0       = [ f2b(2.2, 1), f2b(7.7, 1), f2b(4.4, 1) ]
  src_in1       = [ f2b(1.1, 1), f2b(3.3, 1), f2b(1.1, 1) ]
  src_predicate = [ PredicateType(1, 0), PredicateType(1, 0), PredicateType(1, 1) ]
  src_const     = [ f2b(5.5, 1),  f2b(0, 0),  f2b(7.7, 1) ]
  sink_out      = [ f2b(12.1, 0), f2b(25.4, 0), f2b(33.88, 1) ] # 25.41 -> 25.4
  src_opt       = [ ConfigType( OPT_FMUL_CONST, b1( 1 ), pickRegister ),
                    ConfigType( OPT_FMUL,       b1( 1 ), pickRegister ),
                    ConfigType( OPT_FMUL_CONST, b1( 1 ), pickRegister ) ]
  th = TestHarness( FU, DataType, PredicateType, ConfigType,
                    num_inports, num_outports, data_mem_size,
                    src_in0, src_in1, src_predicate, src_const, src_opt,
                    sink_out )
  run_sim( th )

