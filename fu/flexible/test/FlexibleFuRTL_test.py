"""
==========================================================================
FlexibleFuRTL_test.py
==========================================================================
Test cases for flexible functional unit.

Author : Cheng Tan
  Date : Dec 14, 2019
"""

from pymtl3 import *
from ..FlexibleFuRTL import FlexibleFuRTL
from ...single.AdderRTL import AdderRTL
from ...single.GrantRTL import GrantRTL
from ...single.CompRTL import CompRTL
from ...single.LogicRTL import LogicRTL
from ...single.MemUnitRTL import MemUnitRTL
from ...single.MulRTL import MulRTL
from ...single.PhiRTL import PhiRTL
from ...single.ShifterRTL import ShifterRTL
from ....lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ....lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ....lib.opt_type import *
from ....lib.messages import *

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness( Component ):

  def construct(s, FunctionUnit, FuList, DataType,
                CtrlType,
                data_mem_size, num_inports, num_outports,
                src0_msgs, src1_msgs, ctrl_msgs, sink0_msgs):

    s.src_in0 = TestSrcRTL(DataType, src0_msgs)
    s.src_in1 = TestSrcRTL(DataType, src1_msgs)
    s.src_const = TestSrcRTL(DataType, src1_msgs)
    s.src_opt = TestSrcRTL(CtrlType, ctrl_msgs)
    s.sink_out0 = TestSinkRTL(DataType, sink0_msgs)

    s.dut = FunctionUnit(DataType, CtrlType,
                         num_inports, num_outports, data_mem_size,
                         4, 1, FuList)

    connect(s.src_const.send, s.dut.recv_const)
    connect(s.src_in0.send, s.dut.recv_in[0])
    connect(s.src_in1.send, s.dut.recv_in[1])
    connect(s.src_opt.send, s.dut.recv_opt)
    connect(s.dut.send_out[0], s.sink_out0.recv)

    AddrType = mk_bits(clog2(data_mem_size))
    s.to_mem_raddr = [TestSinkRTL(AddrType, []) for _ in FuList]
    s.from_mem_rdata = [TestSrcRTL( DataType, []) for _ in FuList]
    s.to_mem_waddr = [TestSinkRTL(AddrType, []) for _ in FuList]
    s.to_mem_wdata = [TestSinkRTL(DataType, []) for _ in FuList]
    s.dut.streaming_start_raddr //= 0
    s.dut.streaming_stride //= 0
    s.dut.streaming_end_raddr //= 0

    for i in range(len(FuList)):
      s.to_mem_raddr[i].recv //= s.dut.to_mem_raddr[i]
      s.from_mem_rdata[i].send //= s.dut.from_mem_rdata[i]
      s.to_mem_waddr[i].recv //= s.dut.to_mem_waddr[i]
      s.to_mem_wdata[i].recv //= s.dut.to_mem_wdata[i]
      s.dut.clear[i] //= 0

  def done(s):
    return s.src_in0.done() and s.src_in1.done()   and \
           s.src_opt.done() and s.sink_out0.done()

  def line_trace(s):
    return s.dut.line_trace()

def run_sim(test_harness, max_cycles = 100):
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

def test_flexible_alu():
  FU = FlexibleFuRTL
  FuList = [AdderRTL]
  data_bitwidth = 16
  DataType = mk_data(data_bitwidth, 1)
  PredicateType = mk_predicate(1, 1)
  data_mem_size = 8
  num_inports = 2
  num_outports = 2
  CtrlType = mk_ctrl(num_inports, num_outports)
  FuInType = mk_bits(clog2(num_inports + 1))
  pickRegister = [FuInType(x + 1) for x in range(num_inports)]
  src_in0 =   [DataType(1, 1), DataType(2, 1), DataType(9, 1)]
  src_in1 =   [DataType(2, 1), DataType(3, 0), DataType(1, 1)]
  sink_out0 = [DataType(3, 1), DataType(5, 0), DataType(8, 1)]
  src_opt =   [CtrlType(OPT_ADD, pickRegister),
               CtrlType(OPT_ADD, pickRegister),
               CtrlType(OPT_SUB, pickRegister)]
  th = TestHarness(FU, FuList, DataType, CtrlType,
                   data_mem_size, num_inports, num_outports,
                   src_in0, src_in1, src_opt, sink_out0)
  run_sim(th)

def test_flexible_mul():
  FU            = FlexibleFuRTL
  FuList        = [AdderRTL, MulRTL]
  data_bitwidth = 16
  DataType      = mk_data( data_bitwidth, 1 )
  PredicateType = mk_predicate( 1, 1 )
  data_mem_size = 8
  num_inports   = 2
  num_outports  = 2
  CtrlType      = mk_ctrl(num_inports, num_outports)
  FuInType      = mk_bits(clog2(num_inports + 1))
  pickRegister  = [FuInType(x + 1) for x in range(num_inports)]
  src_in0       = [DataType(1, 1), DataType(2, 1), DataType(9,  1)]
  src_in1       = [DataType(2, 1), DataType(3, 0), DataType(2,  1)]
  sink_out0     = [DataType(2, 1), DataType(6, 0), DataType(18, 1)]
  src_opt       = [CtrlType(OPT_MUL, pickRegister),
                   CtrlType(OPT_MUL, pickRegister),
                   CtrlType(OPT_MUL, pickRegister)]
  th = TestHarness(FU, FuList, DataType, CtrlType,
                   data_mem_size, num_inports, num_outports,
                   src_in0, src_in1, src_opt, sink_out0)
  run_sim( th )

def test_flexible_universal():
  FU            = FlexibleFuRTL
  FuList        = [AdderRTL, MulRTL, LogicRTL, ShifterRTL, PhiRTL, CompRTL, GrantRTL, MemUnitRTL]
  data_bitwidth = 16
  DataType      = mk_data(data_bitwidth, 1)
  PredicateType = mk_predicate(1, 1)
  data_mem_size = 8
  num_inports   = 2
  num_outports  = 2
  CtrlType      = mk_ctrl(num_inports, num_outports)
  FuInType      = mk_bits(clog2(num_inports + 1))
  pickRegister  = [FuInType(x + 1) for x in range(num_inports)]
  src_in0       = [DataType(2, 1), DataType(1, 1), DataType(3, 0)]
  src_in1       = [DataType(2, 1), DataType(0, 0), DataType(2, 1)]
  sink_out0     = [DataType(1, 1), DataType(1, 0), DataType(2, 1)]
  src_opt       = [CtrlType(OPT_EQ ,      pickRegister),
                   CtrlType(OPT_GRT_PRED, pickRegister),
                   CtrlType(OPT_PHI,      pickRegister)]
  th = TestHarness(FU, FuList, DataType, CtrlType,
                   data_mem_size, num_inports, num_outports,
                   src_in0, src_in1, src_opt, sink_out0)
  run_sim(th)
