"""
==========================================================================
ConstQueueDynamicRTL_test.py
==========================================================================
Test cases for constant queue with regs.

Author : Yuqi Sun
  Date : Jan 11, 2025
"""
from ....lib.basic.val_rdy.SinkRTL import SinkRTL
from ..ConstQueueDynamicRTL import ConstQueueDynamicRTL
# from ....lib.basic.en_rdy.test_sinks import TestSinkRTL
# from ....lib.basic.en_rdy.test_srcs import TestSrcRTL
from ....lib.basic.val_rdy.SourceRTL import SourceRTL
from ....lib.messages import *

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, MemUnit, DataType, const_mem_size, src_const):
    s.src_const_pkt = SourceRTL(DataType, src_const)
    # s.read_data = SinkRTL(DataType, read_data)

    s.const_queue = MemUnit(DataType, const_mem_size)
    s.src_const_pkt.send //= s.const_queue.recv_const

  def line_trace(s):
    return s.const_queue.line_trace()


def run_sim(test_harness):
  test_harness.elaborate()
  test_harness.apply(DefaultPassGroup())
  test_harness.sim_reset()

  # assert 1 < 2
  print(test_harness.line_trace())
  # Run simulation
  test_harness.sim_tick()
  test_harness.sim_tick()
  test_harness.sim_tick()
  test_harness.sim_tick()
  test_harness.sim_tick()
  test_harness.sim_tick()
  test_harness.sim_tick()
  test_harness.sim_tick()
  test_harness.sim_tick()
  test_harness.sim_tick()
  test_harness.sim_tick()
  test_harness.sim_tick()
  print(test_harness.line_trace())

def test_const_queue():
  MemUnit = ConstQueueDynamicRTL
  DataType = mk_data(4, 1)
  const_mem_size = 8
  src_const = [DataType(9, 1), DataType(8, 1), DataType(7, 1), DataType(6, 1),
               DataType(5, 1), DataType(4, 1), DataType(3, 1), DataType(2, 1),
               DataType(1, 1), DataType(-1, 1)]
  src_const = [DataType(9, 1), DataType(8, 1), DataType(7, 1)]
  # read_data = [DataType(2, 1), DataType(3, 1), DataType(0, 1), DataType(13, 1)]
  th = TestHarness(MemUnit, DataType, const_mem_size, src_const)
  run_sim(th)

