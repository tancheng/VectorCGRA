"""
==========================================================================
FlexibleFu_test.py
==========================================================================
Test cases for flexible functional unit.

Author : Cheng Tan
  Date : Dec 14, 2019
"""


from pymtl3 import *
from hypothesis import strategies as st
from ..FlexibleFuRTL import FlexibleFuRTL
from ..FuFL import *
from ...single.AdderRTL import AdderRTL
from ...single.GrantRTL import GrantRTL
from ...single.CompRTL import CompRTL
from ...single.LogicRTL import LogicRTL
from ...single.MemUnitRTL import MemUnitRTL
from ...single.MulRTL import MulRTL
from ...single.NahRTL import NahRTL
from ...single.PhiRTL import PhiRTL
from ...single.ShifterRTL import ShifterRTL
from ....lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ....lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ....lib.opt_type import *
from ....lib.messages import *
import hypothesis

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness( Component ):

  def construct( s, FunctionUnit, FuList, DataType, PredicateType, CtrlType,
                 data_bitwidth,
                 src0_msgs, src1_msgs, ctrl_msgs, sink0_msgs ):
    data_mem_size = 8
    num_inports   = 2
    num_outports  = 2

    s.src_in0       = TestSrcRTL (DataType,      src0_msgs    )
    s.src_in1       = TestSrcRTL (DataType,      src1_msgs    )
    s.src_const     = TestSrcRTL (DataType,      src1_msgs    )
    s.src_opt       = TestSrcRTL (CtrlType,      ctrl_msgs    )
    s.sink_out0     = TestSinkRTL(DataType,      sink0_msgs   )

    s.dut = FunctionUnit(DataType, PredicateType, CtrlType,
                         data_bitwidth,
                         num_inports, num_outports, data_mem_size,
                         4, 1, FuList )

    connect(s.src_const.send,     s.dut.recv_const    )
    connect(s.src_in0.send,       s.dut.recv_in[0]    )
    connect(s.src_in1.send,       s.dut.recv_in[1]    )
    connect(s.src_opt.send,       s.dut.recv_opt      )
    connect(s.dut.send_out[0],    s.sink_out0.recv    )

    AddrType = mk_bits(clog2(data_mem_size))
    s.to_mem_raddr   = [TestSinkRTL(AddrType, []) for _ in FuList]
    s.from_mem_rdata = [TestSrcRTL (DataType, []) for _ in FuList]
    s.to_mem_waddr   = [TestSinkRTL(AddrType, []) for _ in FuList]
    s.to_mem_wdata   = [TestSinkRTL(DataType, []) for _ in FuList]

    for i in range(s.dut.fu_list_size):
      s.to_mem_raddr[i].recv   //= s.dut.to_mem_raddr[i]
      s.from_mem_rdata[i].send //= s.dut.from_mem_rdata[i]
      s.to_mem_waddr[i].recv   //= s.dut.to_mem_waddr[i]
      s.to_mem_wdata[i].recv   //= s.dut.to_mem_wdata[i]
      s.dut.clear[i].clear //= 0

  def done(s):
    return s.src_in0.done() and s.src_in1.done() and \
           s.src_opt.done() and s.sink_out0.done()

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


func_opt = {AdderRTL : OPT_ADD,
            NahRTL   : OPT_ADD,
            MulRTL   : OPT_MUL}

@st.composite
def inputs_strat(draw, functions):
  input_a = draw(st.integers(0, 8), label="input_a")
  input_b = draw(st.integers(0, 8), label="input_b")
  opt = draw(st.sampled_from([func_opt[function] for function in functions]))
  return input_a, input_b, opt

@hypothesis.settings(deadline=None, max_examples = 50)
@hypothesis.given(
  functions = st.sampled_from([[AdderRTL], [AdderRTL, MulRTL]]),
  inputs = st.data(),
)
def test_hypothesis(functions, inputs):
  FU = FlexibleFuRTL
  input_list = inputs.draw(
    st.lists(inputs_strat(functions), max_size = 4),
    label = "functions"
  )
  src_a, src_b, src_opt = [], [], []
  data_bitwidth = 16
  DataType      = mk_data(data_bitwidth, 1)
  PredicateType = mk_predicate(1, 1)
  num_inports   = 2
  CtrlType      = mk_ctrl(num_inports)
  FuInType      = mk_bits(clog2(num_inports + 1))
  pickRegister  = [FuInType(x + 1) for x in range(num_inports)]
  for value in input_list:
    src_a.append  (DataType(value[0]))
    src_b.append  (DataType(value[1]))
    src_opt.append(CtrlType(value[2], pickRegister))
  sink_out      = FuFL(DataType, src_a, src_b, src_opt)
  th = TestHarness(FU, functions, DataType, PredicateType, CtrlType,
                   data_bitwidth,
                   src_a, src_b, src_opt, sink_out)
  run_sim(th)

