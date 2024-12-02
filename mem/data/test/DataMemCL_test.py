"""
==========================================================================
DataMemCL_test.py
==========================================================================
Test cases for DataMemCL.

Author : Cheng Tan
  Date : Nov 26, 2022
"""


from pymtl3 import *
from ..DataMemCL import DataMemCL
from ....lib.basic.en_rdy.test_sinks import TestSinkRTL
from ....lib.basic.en_rdy.test_srcs import TestSrcRTL
from ....lib.messages import *
from ....lib.opt_type import *


#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness( Component ):

  def construct( s, DataType, AddrType, data_mem_size, read_addr,
                 read_data, write_addr, write_data, preloadData ):

    s.read_addr   = TestSrcRTL ( AddrType, read_addr  )
    s.read_data   = TestSinkRTL( DataType, read_data  )

    s.write_addr  = TestSrcRTL( AddrType, write_addr )
    s.write_data  = TestSrcRTL( DataType, write_data )


    s.dataMem = DataMemCL( DataType, data_mem_size,
                           preload_data = preloadData )

    s.dataMem.recv_raddr[0] //= s.read_addr.send
    s.dataMem.send_rdata[0] //= s.read_data.recv
    s.dataMem.recv_waddr[0] //= s.write_addr.send
    s.dataMem.recv_wdata[0] //= s.write_data.send

  def done( s ):
    return s.read_addr.done() and s.read_data.done()

  def line_trace( s ):
    return s.dataMem.line_trace()

def run_sim( test_harness, max_cycles=10 ):
  test_harness.elaborate()
  test_harness.apply( DefaultPassGroup() )
  test_harness.sim_reset()

  # Run simulation

  ncycles = 0
  print()
  print( "{}:{}".format( ncycles, test_harness.line_trace() ))
  while not test_harness.done() and ncycles < max_cycles:
    test_harness.sim_tick()
    ncycles += 1
    print( "{}:{}".format( ncycles, test_harness.line_trace() ))

  # Check timeout

  assert ncycles < max_cycles

  test_harness.sim_tick()
  test_harness.sim_tick()
  test_harness.sim_tick()

def test_const_queue():
  DataType      = mk_data( 16, 1 )
  data_mem_size = 100
  AddrType      = mk_bits( clog2( data_mem_size) )
  preloadData   = [ DataType(i, 1) for i in range(100) ]

  read_addr     = [ AddrType(2), AddrType(3), AddrType(0), AddrType(12) ]
  read_data     = [ DataType(2, 1), DataType(3, 1), DataType(0, 1), DataType(33, 1) ]
  write_addr    = [ AddrType(12), AddrType(23) ]
  write_data    = [ DataType(33, 1), DataType(44, 1) ]

  th = TestHarness( DataType, AddrType, data_mem_size, read_addr,
                    read_data, write_addr, write_data, preloadData )
  run_sim( th )
