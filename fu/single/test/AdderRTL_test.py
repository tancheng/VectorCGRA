"""
==========================================================================
AluRTL_test.py
==========================================================================
Test cases for all functional units.

Author : Cheng Tan
  Date : November 27, 2019
"""

from pymtl3 import *
from ..AdderRTL import AdderRTL
from ....lib.basic.val_rdy.SourceRTL import SourceRTL as ValRdyTestSrcRTL
from ....lib.basic.val_rdy.SinkRTL import SinkRTL as ValRdyTestSinkRTL
from ....lib.messages import *
from ....lib.opt_type import *
from ....mem.const.ConstQueueRTL import ConstQueueRTL

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, FunctionUnit, IntraCgraPktType, DataType, ConfigType,
                num_inports, num_outports, data_mem_size,
                src0_msgs, src1_msgs, src_const,
                ctrl_msgs, sink_msgs):

    s.src_in0 = ValRdyTestSrcRTL(DataType, src0_msgs)
    s.src_in1 = ValRdyTestSrcRTL(DataType, src1_msgs)
    s.src_opt = ValRdyTestSrcRTL(ConfigType, ctrl_msgs)
    s.sink_out = ValRdyTestSinkRTL(DataType, sink_msgs)

    s.const_queue = ConstQueueRTL(DataType, src_const)
    s.dut = FunctionUnit(IntraCgraPktType, num_inports, num_outports)

    connect(s.src_in0.send, s.dut.recv_in[0])
    connect(s.src_in1.send, s.dut.recv_in[1])
    connect(s.dut.recv_const, s.const_queue.send_const)
    connect(s.src_opt.send, s.dut.recv_opt)
    connect(s.dut.send_out[0], s.sink_out.recv)

  def done(s):
    return s.src_in0.done() and \
           s.src_opt.done() and \
           s.sink_out.done()

  def line_trace(s):
    return s.dut.line_trace()

def run_sim(test_harness, max_cycles = 20):
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

def test_alu():
  FU = AdderRTL
  DataType = mk_data(16, 1)
  PredType = mk_predicate(1, 1)
  num_inports = 2
  num_outports = 1
  ConfigType = mk_ctrl(num_inports, num_outports)
  FuInType = mk_bits(clog2(num_inports + 1))
  
  data_mem_size = 8
  ctrl_mem_size = 8
  DataAddrType  = mk_bits(clog2(data_mem_size))
  CtrlAddrType  = mk_bits(clog2(ctrl_mem_size))
  CgraPayloadType = mk_cgra_payload(DataType, DataAddrType, ConfigType, CtrlAddrType)
  IntraCgraPktType = mk_intra_cgra_pkt(1, 1, 1, CgraPayloadType)

  pickRegister  = [FuInType(x + 1) for x in range(num_inports)]
  src_in0       = [DataType(1, 1), DataType(7, 1), DataType(4, 1)]
  src_in1       = [                DataType(3, 0),                 DataType(1, 1)]
  src_const     = [DataType(5, 1),                 DataType(2, 1), DataType(7, 1)]
  sink_out      = [DataType(6, 1), DataType(4, 0), DataType(6, 1)]
  src_opt       = [ConfigType(OPT_ADD_CONST, pickRegister),
                   ConfigType(OPT_SUB,       pickRegister),
                   ConfigType(OPT_ADD_CONST, pickRegister)]

  th = TestHarness(FU, IntraCgraPktType, DataType, ConfigType, num_inports,
                   num_outports, data_mem_size, src_in0, src_in1,
                   src_const, src_opt, sink_out)
  run_sim(th)

