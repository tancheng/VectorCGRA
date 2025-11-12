"""
==========================================================================
MemUnitRTL_test.py
==========================================================================
Test cases for functional unit.

Author : Cheng Tan
  Date : November 27, 2019
"""

from pymtl3 import *

from ..MemUnitRTL import MemUnitRTL
from ....lib.messages import *
from ....lib.opt_type import *
from ....lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ....lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ....mem.data.DataMemCL import DataMemCL
from ....mem.data.DataMemRTL import DataMemRTL

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------
# TODO: connect recv_const

class TestHarness(Component):

  def construct(s, FunctionUnit, DataUnit, DataType,
                ConfigType, num_inports, num_outports, data_mem_size,
                src0_msgs, src1_msgs, src_const_msgs, ctrl_msgs,
                sink_msgs):

    s.src_in0 = TestSrcRTL(DataType, src0_msgs)
    s.src_in1 = TestSrcRTL(DataType, src1_msgs)
    s.src_const = TestSrcRTL(DataType, src_const_msgs)
    s.src_opt = TestSrcRTL(ConfigType, ctrl_msgs)
    s.sink_out = TestSinkRTL(DataType, sink_msgs)

    s.dut = FunctionUnit(DataType, ConfigType,
                         num_inports, num_outports, data_mem_size)
    s.data_mem = DataUnit(DataType, data_mem_size)

    connect(s.dut.to_mem_raddr,   s.data_mem.recv_raddr[0])
    connect(s.dut.from_mem_rdata, s.data_mem.send_rdata[0])
    connect(s.dut.to_mem_waddr,   s.data_mem.recv_waddr[0])
    connect(s.dut.to_mem_wdata,   s.data_mem.recv_wdata[0])

    connect(s.src_in0.send, s.dut.recv_in[0])
    connect(s.src_in1.send, s.dut.recv_in[1])
    connect(s.src_const.send, s.dut.recv_const)
    connect(s.src_opt.send, s.dut.recv_opt)
    connect(s.dut.send_out[0], s.sink_out.recv)

  def done(s):
    return s.src_in0.done() and s.src_in1.done() and \
           s.src_opt.done() and s.sink_out.done()

  def line_trace(s):
    return s.data_mem.line_trace() + ' || ' + s.dut.line_trace()

def run_sim(test_harness, max_cycles = 20):
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

def test_Mem():
  FU = MemUnitRTL
  DataUnit = DataMemRTL
  DataType = mk_data(16, 1)
  PredicateType = mk_predicate(1, 1)
  data_mem_size = 8
  num_inports = 2
  num_outports = 1
  ConfigType = mk_ctrl(num_inports, num_outports)
  FuInType = mk_bits(clog2( num_inports + 1))
  pickRegister = [FuInType(x + 1) for x in range(num_inports)]
  src_in0 =   [DataType(1, 1), DataType(3, 1), DataType(3, 1), DataType(3, 1)] # addr
  src_in1 =   [                DataType(9, 1)                                ] # data
  src_const = [DataType(0, 1)]
  sink_out =  [DataType(0, 0), DataType(9, 1), DataType(9, 1)]
  src_opt =   [ConfigType(OPT_LD,  pickRegister),
               ConfigType(OPT_STR, pickRegister),
               ConfigType(OPT_LD,  pickRegister),
               ConfigType(OPT_LD,  pickRegister)]
  th = TestHarness(FU, DataUnit, DataType, ConfigType,
                   num_inports, num_outports, data_mem_size,
                   src_in0, src_in1, src_const, src_opt,
                   sink_out)
  run_sim(th)

def test_PseudoMem():
  FU = MemUnitRTL
  DataUnit = DataMemCL
  DataType = mk_data(16, 1)
  PredicateType = mk_predicate(1, 1)
  data_mem_size = 8
  num_inports = 2
  num_outports = 1
  ConfigType = mk_ctrl(num_inports, num_outports)
  FuInType = mk_bits(clog2(num_inports + 1))
  pickRegister = [FuInType(x + 1) for x in range(num_inports)]
  src_in0 =   [DataType(1, 1), DataType(0, 1),                 DataType(0, 1)                ]
  src_in1 =   [                DataType(9, 1)                                                ]
  src_const = [                                DataType(0, 1),                 DataType(1, 1)]
  sink_out =  [DataType(0, 0),                 DataType(9, 1), DataType(9, 1), DataType(0, 0)]
  src_opt =   [ConfigType(OPT_LD,       pickRegister),
               ConfigType(OPT_STR,      pickRegister),
               ConfigType(OPT_LD_CONST, pickRegister),
               ConfigType(OPT_LD,       pickRegister),
               ConfigType(OPT_LD_CONST, pickRegister)]
  th = TestHarness(FU, DataUnit, DataType, ConfigType,
                   num_inports, num_outports, data_mem_size, src_in0,
                   src_in1, src_const, src_opt, sink_out)
  run_sim(th)

