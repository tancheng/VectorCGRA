"""
==========================================================================
ConstQueueDynamicRTL_test.py
==========================================================================
Test cases for constant queue with regs.

Author : Yuqi Sun
  Date : Jan 11, 2025
"""
from ..ConstQueueDynamicRTL import ConstQueueDynamicRTL
from ....lib.basic.val_rdy.SinkRTL import SinkRTL
from ....lib.basic.val_rdy.SourceRTL import SourceRTL
from ....lib.messages import *


#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, MemUnit, DataType, const_mem_size, src_const, read_data):
    s.src_const_pkt = SourceRTL(DataType, src_const)
    s.read_data = SinkRTL(DataType, read_data)

    s.const_queue = MemUnit(DataType, const_mem_size)
    s.src_const_pkt.send //= s.const_queue.recv_const
    s.read_data.recv //= s.const_queue.send_const

  def done(self):
    return self.src_const_pkt.done()

  def line_trace(s):
    return s.const_queue.line_trace(verbosity = 1)

def run_sim(test_harness, max_cycles = 20):
  test_harness.elaborate()
  test_harness.apply(DefaultPassGroup(linetrace = True))
  test_harness.sim_reset()

  ncycles = 0
  while not test_harness.done() and ncycles < max_cycles:
    test_harness.sim_tick()
    ncycles += 1

  for i in range(10):
    test_harness.sim_tick()


def test_const_num_lt_mem():
  MemUnit = ConstQueueDynamicRTL
  DataType = mk_data(4, 1)
  const_mem_size = 8

  # The number of source const is less than the memory size.
  src_const = [DataType(9, 1), DataType(8, 1), DataType(7, 1)]
  read_data = [DataType(9, 1), DataType(8, 1), DataType(7, 1), DataType(9, 1), DataType(8, 1)]
  th = TestHarness(MemUnit, DataType, const_mem_size, src_const, read_data)
  run_sim(th)

def test_const_num_gt_mem():
  MemUnit = ConstQueueDynamicRTL
  DataType = mk_data(4, 1)
  const_mem_size = 8

  # The number of source const is more than the memory size.
  src_const = [DataType(9, 1), DataType(8, 1), DataType(7, 1), DataType(6, 1),
               DataType(5, 1), DataType(4, 1), DataType(3, 1), DataType(2, 1),
               DataType(1, 1)]
  read_data = [DataType(9, 1), DataType(8, 1), DataType(7, 1), DataType(6, 1),
               DataType(5, 1), DataType(4, 1), DataType(3, 1), DataType(2, 1),
               DataType(9, 1), DataType(8, 1), DataType(7, 1), DataType(6, 1),
               DataType(5, 1), DataType(4, 1), DataType(3, 1), DataType(2, 1)]
  th = TestHarness(MemUnit, DataType, const_mem_size, src_const, read_data)
  run_sim(th)

def test_const_loop():
  MemUnit = ConstQueueDynamicRTL
  DataType = mk_data(4, 1)
  const_mem_size = 8

  # The number of source const is less than the memory size.
  src_const = [DataType(9, 1)]
  read_data = [DataType(9, 1), DataType(9, 1), DataType(9, 1), DataType(9, 1)]
  th = TestHarness(MemUnit, DataType, const_mem_size, src_const, read_data)
  run_sim(th)
