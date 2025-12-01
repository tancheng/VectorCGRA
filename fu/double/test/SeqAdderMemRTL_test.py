"""
==========================================================================
SeqAdderMemRTL_test.py
==========================================================================
Test cases for Adder + MemUnit sequential combo functional unit.
This tests the fix for issue #214: MemUnit is not fusible.

Author : Cheng Tan
  Date : December 2, 2024
"""

from pymtl3 import *
from ..SeqAdderMemRTL import SeqAdderMemRTL
from ....lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ....lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ....lib.messages import *
from ....lib.opt_type import *

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, FunctionUnit, DataType, CtrlType,
                num_inports, num_outports, data_mem_size,
                src0_msgs, src1_msgs, src2_msgs,
                ctrl_msgs, sink_msgs, mem_data):

    AddrType = mk_bits(clog2(data_mem_size))

    s.src_in0   = TestSrcRTL(DataType, src0_msgs)
    s.src_in1   = TestSrcRTL(DataType, src1_msgs)
    s.src_in2   = TestSrcRTL(DataType, src2_msgs)
    s.src_const = TestSrcRTL(DataType, src1_msgs)  # const for add offset
    s.src_opt   = TestSrcRTL(CtrlType, ctrl_msgs)
    s.sink_out  = TestSinkRTL(DataType, sink_msgs)

    s.dut = FunctionUnit(DataType, CtrlType,
                         num_inports, num_outports, data_mem_size)

    # Simple memory model for testing
    s.mem_data = mem_data
    s.mem_raddr_pending = Wire(1)
    s.mem_raddr_val = Wire(AddrType)

    connect(s.src_in0.send,    s.dut.recv_in[0])
    connect(s.src_in1.send,    s.dut.recv_in[1])
    connect(s.src_in2.send,    s.dut.recv_in[2])
    connect(s.src_const.send,  s.dut.recv_const)
    connect(s.src_opt.send,    s.dut.recv_opt)
    connect(s.dut.send_out[0], s.sink_out.recv)

    @update
    def mem_read_logic():
      # Memory read address handling
      s.dut.to_mem_raddr.rdy @= 1
      s.dut.from_mem_rdata.val @= s.mem_raddr_pending
      s.dut.from_mem_rdata.msg @= DataType(0, 1)
      if s.mem_raddr_pending:
        addr = int(s.mem_raddr_val)
        if addr < len(s.mem_data):
          s.dut.from_mem_rdata.msg @= s.mem_data[addr]

    @update_ff
    def mem_read_pending():
      if s.reset:
        s.mem_raddr_pending <<= 0
        s.mem_raddr_val <<= AddrType(0)
      else:
        if s.dut.to_mem_raddr.val & s.dut.to_mem_raddr.rdy:
          s.mem_raddr_pending <<= 1
          s.mem_raddr_val <<= s.dut.to_mem_raddr.msg
        elif s.dut.from_mem_rdata.val & s.dut.from_mem_rdata.rdy:
          s.mem_raddr_pending <<= 0

    @update
    def mem_write_logic():
      # Memory write (not used in this test but need to connect)
      s.dut.to_mem_waddr.rdy @= 1
      s.dut.to_mem_wdata.rdy @= 1

  def done(s):
    return s.src_in0.done() and s.src_opt.done() and s.sink_out.done()

  def line_trace(s):
    return s.dut.line_trace()

def run_sim(test_harness, max_cycles=50):
  test_harness.elaborate()
  test_harness.apply(DefaultPassGroup())
  test_harness.sim_reset()

  # Run simulation
  ncycles = 0
  print()
  print("{}:{}".format(ncycles, test_harness.line_trace()))
  while not test_harness.done() and ncycles < max_cycles:
    test_harness.sim_tick()
    ncycles += 1
    print("{}:{}".format(ncycles, test_harness.line_trace()))

  # Check timeout
  assert ncycles < max_cycles

  test_harness.sim_tick()
  test_harness.sim_tick()
  test_harness.sim_tick()

def test_adder_mem_basic():
  """
  Test that memory interfaces are correctly propagated through combo FU.
  This verifies the fix for issue #214.
  """
  FU            = SeqAdderMemRTL
  DataType      = mk_data(16, 1)
  PredicateType = mk_predicate(1, 1)
  num_inports   = 4
  num_outports  = 2
  CtrlType      = mk_ctrl(num_inports, num_outports)
  data_mem_size = 16

  # Memory contents: mem[0]=100, mem[1]=200, mem[2]=300, mem[3]=400
  mem_data = [DataType(100, 1), DataType(200, 1), DataType(300, 1), DataType(400, 1)]

  # Test: Add base address + const offset, then load
  # Input: base_addr=0, const_offset=2 -> should load mem[2]=300
  src_in0  = [DataType(0, 1)]  # Base address
  src_in1  = [DataType(2, 1)]  # Const offset (will be added)
  src_in2  = [DataType(0, 1)]  # Unused

  # Expected: addr = 0 + 2 = 2, mem[2] = 300
  sink_out = [DataType(300, 1)]
  src_opt  = [CtrlType(OPT_ADD_CONST_LD)]

  th = TestHarness(FU, DataType, CtrlType,
                   num_inports, num_outports, data_mem_size,
                   src_in0, src_in1, src_in2, src_opt,
                   sink_out, mem_data)
  run_sim(th)

def test_contains_mem_unit_attribute():
  """
  Test that the SeqAdderMemRTL has the contains_mem_unit attribute set.
  """
  assert hasattr(SeqAdderMemRTL, 'contains_mem_unit')
  assert SeqAdderMemRTL.contains_mem_unit == True
