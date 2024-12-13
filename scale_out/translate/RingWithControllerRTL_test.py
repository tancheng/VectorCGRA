"""
=========================================================================
RingWithControllerRTL_test.py
=========================================================================
Test for RingControllerRTL with CGRA message.

Author : Cheng Tan
  Date : Dec 3, 2024
"""


from pymtl3 import *
from ...lib.messages import *
from ...lib.opt_type import *
from ...lib.basic.en_rdy.test_sinks import TestSinkRTL
from ...lib.basic.en_rdy.test_srcs import TestSrcRTL
from ..RingWithControllerRTL import RingWithControllerRTL
from pymtl3.stdlib.test_utils import config_model_with_cmdline_opts
from pymtl3.passes.backends.verilog import (VerilogTranslationPass,
                                            VerilogVerilatorImportPass)


#-------------------------------------------------------------------------
# TestHarness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, RingPktType, CGRADataType, CGRAAddrType, num_terminals,
                src_msgs, sink_msgs):

    s.num_terminals = num_terminals
    s.srcs = [TestSrcRTL(CGRADataType, src_msgs[i])
              for i in range(num_terminals)]
    s.dut = RingWithControllerRTL(RingPktType, CGRADataType,
                                  CGRAAddrType, num_terminals)
    s.sinks = [TestSinkRTL(CGRADataType, sink_msgs[i])
               for i in range(num_terminals)]

    # Connections
    for i in range (s.dut.num_terminals):
      s.srcs[i].send //= s.dut.recv_from_master[i]
      s.dut.send_to_master[i] //= s.sinks[i].recv

  def done(s):
    for i in range(s.num_terminals):
      if not s.srcs[i].done() or not s.sinks[i].done():
        return False
    return True 

  def line_trace(s):
    return s.dut.line_trace()

#-------------------------------------------------------------------------
# run_rtl_sim
#-------------------------------------------------------------------------

def run_sim(test_harness, max_cycles=20):

  # Create a simulator
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


#=========================================================================
# Test cases
#=========================================================================

# class RingWithController_Tests:
# 
#   @classmethod
#   def setup_class(cls):
#     cls.DutType = RingWithControllerRTL
# 
#   def _test_ring_data(s, translation = ''):
#     DataType = mk_data(32, 1)
#     num_terminals = 4
#     RingPktType = mk_ring_multi_cgra_pkt(num_terminals,
#                                          payload_nbits = 32,
#                                          predicate_nbits = 1)
#     src_data = [
#                 [],
#                 [],
#                 [DataType(7, 1, 1), DataType(2, 1), DataType(3, 1)],
#                 [DataType(7, 1, 1), DataType(2, 1), DataType(3, 1)]
#                ]
# 
#     sink_data = [
#                  [],
#                  [],
#                  [DataType(7, 1, 1), DataType(2, 1), DataType(3, 1)],
#                  [DataType(7, 1, 1), DataType(2, 1), DataType(3, 1)]
#                 ]
# 
#     ctrl_mem_size = 4
#     AddrType = mk_bits(clog2(ctrl_mem_size))
# 
#     th = TestHarness(RingPktType, DataType, AddrType, num_terminals,
#                      src_data, sink_data)
#     cmdline_opts={'dump_vcd': False, 'test_verilog': translation,
#                   'dump_vtb': False}
#     run_sim(th, cmdline_opts)
# 
#   def test_ring_data(self):
#     self._test_ring_data('zeros')

data_nbits = 32
predicate_nbits = 1
DataType = mk_data(data_nbits, predicate_nbits)
num_terminals = 4
ctrl_mem_size = 4
addr_nbits = clog2(ctrl_mem_size)
AddrType = mk_bits(addr_nbits)
RingPktType = mk_ring_multi_cgra_pkt(num_terminals,
                                     addr_nbits = addr_nbits,
                                     data_nbits = data_nbits,
                                     predicate_nbits = predicate_nbits)
src_data = [
            [],
            [DataType(7, 1, 1), DataType(8, 1), DataType(9, 1)],
            [DataType(1, 1, 1), DataType(2, 1), DataType(3, 1)],
            []
           ]

sink_data = [
             [],
             [],
             # The expected data is received in an interleaved way.
             [DataType(1, 0, 0), DataType(7, 0, 0), DataType(2, 0, 0), DataType(8, 0, 0), DataType(3, 0, 0), DataType(9, 0, 0)],
             []
            ]

def test_simple(cmdline_opts):
  th = TestHarness(RingPktType, DataType, AddrType, num_terminals,
                   src_data, sink_data)
  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                      ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                       'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts=['dut'])
  run_sim(th)


