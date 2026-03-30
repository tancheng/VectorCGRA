"""
==========================================================================
GepRTL_test.py
==========================================================================
Test cases for GEP (GetElementPtr) functional unit.

Author : Shangkun Li
  Date : March 31, 2026
"""

import pytest
from itertools import product
from pymtl3 import *
from ..GepRTL import GepRTL
from ....lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ....lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ....lib.opt_type import *
from ....lib.cmd_type import *
from ....lib.messages import *
from ....mem.const.ConstQueueRTL import ConstQueueRTL

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, FunctionUnit, IntraCgraPktType, DataType, ConfigType,
                CgraPayloadType,
                num_inports, num_outports, data_mem_size,
                src0_msgs, src1_msgs, src2_msgs,
                src_const, ctrl_msgs, src_from_ctrl,
                sink_msgs):

    s.src_in0 = TestSrcRTL(DataType, src0_msgs)
    s.src_in1 = TestSrcRTL(DataType, src1_msgs)
    s.src_in2 = TestSrcRTL(DataType, src2_msgs)
    s.src_opt = TestSrcRTL(ConfigType, ctrl_msgs)
    s.src_from_ctrl = TestSrcRTL(CgraPayloadType, src_from_ctrl)
    s.sink_out = TestSinkRTL(DataType, sink_msgs)

    s.const_queue = ConstQueueRTL(DataType, src_const)
    s.dut = FunctionUnit(IntraCgraPktType, num_inports, num_outports)

    connect(s.src_in0.send, s.dut.recv_in[0])
    connect(s.src_in1.send, s.dut.recv_in[1])
    connect(s.src_in2.send, s.dut.recv_in[2])
    connect(s.dut.recv_const, s.const_queue.send_const)
    connect(s.src_opt.send, s.dut.recv_opt)
    connect(s.src_from_ctrl.send, s.dut.recv_from_ctrl_mem)
    connect(s.dut.send_out[0], s.sink_out.recv)

  def done(s):
    return s.src_in0.done() and s.src_in1.done() and \
           s.src_opt.done() and s.sink_out.done()

  def line_trace(s):
    return s.dut.line_trace()

def run_sim(test_harness, max_cycles = 40):
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

#-------------------------------------------------------------------------
# Helper to build common types
#-------------------------------------------------------------------------

def make_types(data_nbits=32, num_inports=4, num_outports=1,
               data_mem_size=8, ctrl_mem_size=8):
  DataType = mk_data(data_nbits, 1)
  ConfigType = mk_ctrl(num_inports, num_outports)
  FuInType = mk_bits(clog2(num_inports + 1))
  DataAddrType = mk_bits(clog2(data_mem_size))
  CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
  CgraPayloadType = mk_cgra_payload(DataType, DataAddrType, ConfigType, CtrlAddrType)
  IntraCgraPktType = mk_intra_cgra_pkt(1, 1, 1, CgraPayloadType)
  return DataType, ConfigType, FuInType, CgraPayloadType, IntraCgraPktType

#-------------------------------------------------------------------------
# Test cases: 1D GEP
#-------------------------------------------------------------------------

@pytest.mark.parametrize(
  'base, index',
  product(range(0, 100, 40), range(0, 20, 4))
)
def test_gep_1d(base, index):
  """OPT_GEP: result = base(in0) + index(in1)"""
  num_inports = 4
  num_outports = 1
  data_mem_size = 8
  DataType, ConfigType, FuInType, CgraPayloadType, IntraCgraPktType = \
      make_types(num_inports=num_inports, num_outports=num_outports)

  src_in0 =   [DataType(base, 1)]
  src_in1 =   [DataType(index, 1)]
  src_in2 =   [DataType(0, 0)]
  src_const = [DataType(0, 1)]
  sink_out =  [DataType(base + index, 1)]
  # fu_in[0]=1 -> in0(base), fu_in[1]=2 -> in1(index)
  src_opt =   [ConfigType(OPT_GEP,
               [FuInType(1), FuInType(2), FuInType(0), FuInType(0)])]
  src_from_ctrl = []

  th = TestHarness(GepRTL, IntraCgraPktType, DataType, ConfigType,
                   CgraPayloadType,
                   num_inports, num_outports, data_mem_size,
                   src_in0, src_in1, src_in2, src_const, src_opt,
                   src_from_ctrl, sink_out)
  run_sim(th)


def test_gep_1d_const():
  """OPT_GEP_CONST: result = base(const) + index(in0)"""
  num_inports = 4
  num_outports = 1
  data_mem_size = 8
  DataType, ConfigType, FuInType, CgraPayloadType, IntraCgraPktType = \
      make_types(num_inports=num_inports, num_outports=num_outports)

  base_addr = 1000
  index_vals = [4, 8, 12]
  src_in0 =   [DataType(v, 1) for v in index_vals]
  src_in1 =   []
  src_in2 =   []
  src_const = [DataType(base_addr, 1)] * len(index_vals)
  sink_out =  [DataType(base_addr + v, 1) for v in index_vals]
  src_opt =   [ConfigType(OPT_GEP_CONST,
               [FuInType(1), FuInType(0), FuInType(0), FuInType(0)])] * len(index_vals)
  src_from_ctrl = []

  th = TestHarness(GepRTL, IntraCgraPktType, DataType, ConfigType,
                   CgraPayloadType,
                   num_inports, num_outports, data_mem_size,
                   src_in0, src_in1, src_in2, src_const, src_opt,
                   src_from_ctrl, sink_out)
  run_sim(th)


#-------------------------------------------------------------------------
# Test cases: 2D GEP
#-------------------------------------------------------------------------

def test_gep_2d():
  """OPT_GEP_2D: result = base(in0) + index0(in1) * stride + index1(in2)
  Simulates A[i][j] where A has 10 elements per row.
  Memory is element-addressed for now, so stride = 10 (elements, not bytes).
  """
  num_inports = 4
  num_outports = 1
  data_mem_size = 8
  DataType, ConfigType, FuInType, CgraPayloadType, IntraCgraPktType = \
      make_types(num_inports=num_inports, num_outports=num_outports)

  base_addr = 2000
  stride = 10  # 10 elements per row (element-granular addressing)

  # Test A[0][0], A[1][3], A[2][7]
  test_cases = [
    (0, 0),  # offset = 0*10 + 0 = 0
    (1, 3),  # offset = 1*10 + 3 = 13
    (2, 7),  # offset = 2*10 + 7 = 27
  ]

  src_in0 =   [DataType(base_addr, 1)] * len(test_cases)
  src_in1 =   [DataType(i, 1) for i, j in test_cases]
  src_in2 =   [DataType(j, 1) for i, j in test_cases]
  src_const = [DataType(0, 1)]
  sink_out =  [DataType(base_addr + i * stride + j, 1) for i, j in test_cases]
  # fu_in[0]=1 -> in0(base), fu_in[1]=2 -> in1(index0), fu_in[2]=3 -> in2(index1)
  src_opt =   [ConfigType(OPT_GEP_2D,
               [FuInType(1), FuInType(2), FuInType(3), FuInType(0)])] * len(test_cases)
  # Pre-configure stride via CMD before execution.
  src_from_ctrl = [
    CgraPayloadType(CMD_CONFIG_GEP_STRIDE, DataType(stride, 1), 0, ConfigType(0), 0),
  ]

  th = TestHarness(GepRTL, IntraCgraPktType, DataType, ConfigType,
                   CgraPayloadType,
                   num_inports, num_outports, data_mem_size,
                   src_in0, src_in1, src_in2, src_const, src_opt,
                   src_from_ctrl, sink_out)
  run_sim(th)


def test_gep_2d_const():
  """OPT_GEP_2D_CONST: result = base(const) + index0(in0) * stride + index1(in1)
  Simulates A[i][j] where A has 8 elements per row.
  Memory is element-addressed for now, so stride = 8 (elements, not bytes).
  Base address comes from const_queue.
  """
  num_inports = 4
  num_outports = 1
  data_mem_size = 8
  DataType, ConfigType, FuInType, CgraPayloadType, IntraCgraPktType = \
      make_types(num_inports=num_inports, num_outports=num_outports)

  base_addr = 4000
  stride = 8  # 8 elements per row (element-granular addressing)

  # Test A[0][0], A[1][2], A[3][5]
  test_cases = [
    (0, 0),  # offset = 0*8 + 0 = 0
    (1, 2),  # offset = 1*8 + 2 = 10
    (3, 5),  # offset = 3*8 + 5 = 29
  ]

  src_in0 =   [DataType(i, 1) for i, j in test_cases]
  src_in1 =   [DataType(j, 1) for i, j in test_cases]
  src_in2 =   [DataType(0, 0)] * len(test_cases)
  src_const = [DataType(base_addr, 1)] * len(test_cases)
  sink_out =  [DataType(base_addr + i * stride + j, 1) for i, j in test_cases]
  # fu_in[0]=1 -> in0(index0), fu_in[1]=2 -> in1(index1)
  src_opt =   [ConfigType(OPT_GEP_2D_CONST,
               [FuInType(1), FuInType(2), FuInType(0), FuInType(0)])] * len(test_cases)
  # Pre-configure stride via CMD.
  src_from_ctrl = [
    CgraPayloadType(CMD_CONFIG_GEP_STRIDE, DataType(stride, 1), 0, ConfigType(0), 0),
  ]

  th = TestHarness(GepRTL, IntraCgraPktType, DataType, ConfigType,
                   CgraPayloadType,
                   num_inports, num_outports, data_mem_size,
                   src_in0, src_in1, src_in2, src_const, src_opt,
                   src_from_ctrl, sink_out)
  run_sim(th)


#-------------------------------------------------------------------------
# Test predicate propagation
#-------------------------------------------------------------------------

def test_gep_predicate():
  """Test that predicates propagate correctly through GEP."""
  num_inports = 4
  num_outports = 1
  data_mem_size = 8
  DataType, ConfigType, FuInType, CgraPayloadType, IntraCgraPktType = \
      make_types(num_inports=num_inports, num_outports=num_outports)

  # Predicate=0 on one input should result in predicate=0 output.
  src_in0 =   [DataType(100, 1), DataType(200, 0)]
  src_in1 =   [DataType(10,  0), DataType(20,  1)]
  src_in2 =   [DataType(0,   0), DataType(0,   0)]
  src_const = [DataType(0, 1)]
  sink_out =  [DataType(110, 0), DataType(220, 0)]
  src_opt =   [
    ConfigType(OPT_GEP, [FuInType(1), FuInType(2), FuInType(0), FuInType(0)]),
    ConfigType(OPT_GEP, [FuInType(1), FuInType(2), FuInType(0), FuInType(0)]),
  ]
  src_from_ctrl = []

  th = TestHarness(GepRTL, IntraCgraPktType, DataType, ConfigType,
                   CgraPayloadType,
                   num_inports, num_outports, data_mem_size,
                   src_in0, src_in1, src_in2, src_const, src_opt,
                   src_from_ctrl, sink_out)
  run_sim(th)
