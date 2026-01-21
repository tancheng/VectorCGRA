"""
==========================================================================
LoopCounterRTL.py
==========================================================================
Test cases for functional unit LoopCounter.

Author : Shangkun Li
  Date : January 21, 2026
"""

from pymtl3 import *
from ..LoopCounterRTL import LoopCounterRTL
from ....lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ....lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ....lib.messages import *
from ....lib.opt_type import *

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):
    def construct(s, FunctionUnit, DataType, CtrlType,
                  num_inports, num_outports,
                  data_mem_size, ctrl_mem_size,
                  src_const, src_opt, sink_out):
        s.src_const = TestSrcRTL(DataType, src_const)
        s.src_opt = TestSrcRTL(CtrlType, src_opt)
        s.sink_out = TestSinkRTL(DataType, sink_out)
        
        s.dut = FunctionUnit(DataType, CtrlType, num_inports, num_outports,
                            data_mem_size, ctrl_mem_size)
        
        connect(s.src_const.send, s.dut.recv_const)
        connect(s.src_opt.send, s.dut.recv_opt)
        connect(s.dut.send_out[0], s.sink_out.recv)
    
    def done(s):
        return s.src_const.done() and s.src_opt.done() and s.sink_out.done()
    
    def line_trace(s):
        return s.dut.line_trace()

def run_sim(test_harness, max_cycles = 100):
  test_harness.elaborate()
  test_harness.apply(DefaultPassGroup())
  test_harness.sim_reset()

  # Run simulation
  ncycles = 0
  print()
  print("{}:{}".format( ncycles, test_harness.line_trace()))
  while not test_harness.done() and ncycles < max_cycles:
    test_harness.sim_tick()
    ncycles += 1
    print("{}:{}".format( ncycles, test_harness.line_trace()))

  # Check timeout
  assert ncycles < max_cycles

  test_harness.sim_tick()
  test_harness.sim_tick()
  test_harness.sim_tick()
  
#-------------------------------------------------------------------------
# Test cases
#-------------------------------------------------------------------------

def test_loop_counter_basic():
    """Test basic counter: for(i=0; i<5; i++)"""
    
    num_inports = 4
    num_outports = 2
    data_mem_size = 8
    ctrl_mem_size = 8
    DataType = mk_data(32, 1)
    CtrlType = mk_ctrl(num_inports, num_outports, num_inports, num_outports)
    
    # Configuration constants: lower=0, upper=5, step=1
    src_const = [
        DataType(0, 1),   # lower_bound = 0
        DataType(5, 1),   # upper_bound = 5
        DataType(1, 1),   # step = 1
    ]
    
    # Operations: keeps executing OPT_LOOP_COUNT
    src_opt = [CtrlType(OPT_LOOP_COUNT)] * 10
    
    # Expected output: 0,1,2,3,4 (pred=1), then 5,5,5... (pred=0)
    sink_out = [
        DataType(0, 1),   # i=0, predicate=1
        DataType(1, 1),   # i=1, predicate=1
        DataType(2, 1),   # i=2, predicate=1
        DataType(3, 1),   # i=3, predicate=1
        DataType(4, 1),   # i=4, predicate=1
        DataType(5, 0),   # i=5>=upper, predicate=0
        DataType(5, 0),   # stays at 5, pred=0
        DataType(5, 0),
        DataType(5, 0),
        DataType(5, 0),
    ]
    
    th = TestHarness(LoopCounterRTL, DataType, CtrlType,
                     num_inports, num_outports,
                     data_mem_size, ctrl_mem_size,
                     src_const, src_opt, sink_out)
    
    run_sim(th)
    
def test_loop_counter_with_step():
    """Test counter with step: for(i=0; i<10; i+=2)"""
    
    num_inports = 4
    num_outports = 2
    data_mem_size = 8
    ctrl_mem_size = 8
    DataType = mk_data(32, 1)
    CtrlType = mk_ctrl(num_inports, num_outports, num_inports, num_outports)
    
    src_const = [
        DataType(0, 1),
        DataType(10, 1),
        DataType(2, 1),
    ]
    
    src_opt = [CtrlType(OPT_LOOP_COUNT)] * 8
    
    sink_out = [
        DataType(0, 1),
        DataType(2, 1),
        DataType(4, 1),
        DataType(6, 1),
        DataType(8, 1),
        DataType(10, 0),
        DataType(10, 0),
        DataType(10, 0),
    ]
    
    th = TestHarness(LoopCounterRTL, DataType, CtrlType,
                     num_inports, num_outports,
                     data_mem_size, ctrl_mem_size,
                     src_const, src_opt, sink_out)
    
    run_sim(th)
        
        
