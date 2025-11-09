"""
==========================================================================
LoopControlRTL_test.py
==========================================================================
Test cases for functional unit LoopControl.

Author : Shiran Guo
  Date : November 7, 2025
"""

from pymtl3 import *
from ..LoopControlRTL import LoopControlRTL
from ....lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ....lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ....lib.messages import DataType, CtrlType
from ....lib.opt_type import OptType, OPT_ADD, OPT_SUB, OPT_MUL, OPT_DIV  # Replace with actual used names

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, FunctionUnit, DataType, CtrlType,
                num_inports, num_outports, data_mem_size, 
                src_parent_valid, src_start, src_end, src_step, src_opt, 
                sink_index, sink_valid):

    s.src_parent_valid = TestSrcRTL(DataType, src_parent_valid)
    s.src_start = TestSrcRTL(DataType, src_start)
    s.src_end = TestSrcRTL(DataType, src_end)
    s.src_step = TestSrcRTL(DataType, src_step)
    s.src_opt = TestSrcRTL(CtrlType, src_opt)
    s.sink_index = TestSinkRTL(DataType, sink_index)
    s.sink_valid = TestSinkRTL(DataType, sink_valid)

    s.dut = FunctionUnit(DataType, CtrlType, num_inports,
                         num_outports, data_mem_size)

    s.src_parent_valid.send //= s.dut.recv_in[0]
    s.src_start.send //= s.dut.recv_in[1]
    s.src_end.send //= s.dut.recv_in[2]
    s.src_step.send //= s.dut.recv_in[3]
    s.src_opt.send //= s.dut.recv_opt
    s.dut.send_out[0] //= s.sink_index.recv
    s.dut.send_out[1] //= s.sink_valid.recv

  def done(s):
    return s.src_parent_valid.done() and s.sink_index.done() and s.sink_valid.done()

  def line_trace(self):
    return self.dut.line_trace()

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

def test_loop_control_basic():
  """Test basic loop control: for i in range(0, 5, 1)"""
  FU = LoopControlRTL
  DataType = mk_data(32, 1)
  num_inports = 4  # parent_valid, start, end, step
  num_outports = 2
  CtrlType = mk_ctrl(num_inports, num_outports)
  data_mem_size = 8
  FuInType = mk_bits(clog2(num_inports + 1))
  pickRegister = [FuInType(x + 1) for x in range(num_inports)]
  
  # Loop: for i = 0; i < 5; i += 1
  num_iterations = 5
  # Provide enough inputs for the loop iterations plus the final check
  src_parent_valid = [DataType(1, 1) for _ in range(num_iterations + 1)]
  src_start = [DataType(0, 1) for _ in range(num_iterations + 1)]
  src_end = [DataType(5, 1) for _ in range(num_iterations + 1)]
  src_step = [DataType(1, 1) for _ in range(num_iterations + 1)]
  src_opt = [CtrlType(OPT_LOOP_CONTROL, pickRegister) for _ in range(num_iterations + 1)]
  
  # Expected outputs:
  # Iteration 0: index=0, valid=1
  # Iteration 1: index=1, valid=1
  # Iteration 2: index=2, valid=1
  # Iteration 3: index=3, valid=1
  # Iteration 4: index=4, valid=1
  # Iteration 5: index=5, valid=0 (loop ends, but still produces output)
  sink_index = [DataType(i, 1) for i in range(num_iterations)] + [DataType(num_iterations, 0)]
  sink_valid = [DataType(1, 1) for _ in range(num_iterations)] + [DataType(0, 1)]
  
  th = TestHarness(FU, DataType, CtrlType, num_inports,
                   num_outports, data_mem_size, 
                   src_parent_valid, src_start, src_end, src_step, src_opt,
                   sink_index, sink_valid)
  run_sim(th)

def test_loop_control_step():
  """Test loop control with step: for i in range(0, 10, 2)"""
  FU = LoopControlRTL
  DataType = mk_data(32, 1)
  num_inports = 4  # parent_valid, start, end, step
  num_outports = 2
  CtrlType = mk_ctrl(num_inports, num_outports)
  data_mem_size = 8
  FuInType = mk_bits(clog2(num_inports + 1))
  pickRegister = [FuInType(x + 1) for x in range(num_inports)]
  
  # Loop: for i = 0; i < 10; i += 2
  # Now with configurable step=2!
  num_iterations = 5  # 0, 2, 4, 6, 8
  src_parent_valid = [DataType(1, 1) for _ in range(num_iterations + 1)]
  src_start = [DataType(0, 1) for _ in range(num_iterations + 1)]
  src_end = [DataType(10, 1) for _ in range(num_iterations + 1)]
  src_step = [DataType(2, 1) for _ in range(num_iterations + 1)]  # step = 2
  src_opt = [CtrlType(OPT_LOOP_CONTROL, pickRegister) for _ in range(num_iterations + 1)]
  
  # Expected outputs with step=2: 0, 2, 4, 6, 8, then 10 (invalid)
  expected_indices = [0, 2, 4, 6, 8]
  sink_index = [DataType(i, 1) for i in expected_indices] + [DataType(10, 0)]
  sink_valid = [DataType(1, 1) for _ in range(num_iterations)] + [DataType(0, 1)]
  
  th = TestHarness(FU, DataType, CtrlType, num_inports,
                   num_outports, data_mem_size, 
                   src_parent_valid, src_start, src_end, src_step, src_opt,
                   sink_index, sink_valid)
  run_sim(th)

def test_loop_control_nested():
  """Test nested loop scenario - outer loop valid controls inner loop"""
  FU = LoopControlRTL
  DataType = mk_data(32, 1)
  num_inports = 4  # parent_valid, start, end, step
  num_outports = 2
  CtrlType = mk_ctrl(num_inports, num_outports)
  data_mem_size = 8
  FuInType = mk_bits(clog2(num_inports + 1))
  pickRegister = [FuInType(x + 1) for x in range(num_inports)]
  
  # Inner loop: for j = 0; j < 3; j++
  num_iterations = 3
  src_parent_valid = [DataType(1, 1) for _ in range(num_iterations + 1)]
  src_start = [DataType(0, 1) for _ in range(num_iterations + 1)]
  src_end = [DataType(3, 1) for _ in range(num_iterations + 1)]
  src_step = [DataType(1, 1) for _ in range(num_iterations + 1)]
  src_opt = [CtrlType(OPT_LOOP_CONTROL, pickRegister) for _ in range(num_iterations + 1)]
  
  sink_index = [DataType(i, 1) for i in range(num_iterations)] + [DataType(num_iterations, 0)]
  sink_valid = [DataType(1, 1) for _ in range(num_iterations)] + [DataType(0, 1)]
  
  th = TestHarness(FU, DataType, CtrlType, num_inports,
                   num_outports, data_mem_size, 
                   src_parent_valid, src_start, src_end, src_step, src_opt,
                   sink_index, sink_valid)
  run_sim(th)

if __name__ == "__main__":
  test_loop_control_basic()
