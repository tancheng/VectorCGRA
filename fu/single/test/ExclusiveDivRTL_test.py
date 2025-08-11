"""
==========================================================================
ExclusiveDivRTL_test.py
==========================================================================
Test cases for Divider.

Author : Jiajun Qin
  Date : May 2, 2025
"""

import pytest
import hypothesis
from hypothesis import strategies as st
from itertools import product
from pymtl3 import *
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)
from ..ExclusiveDivRTL import ExclusiveDivRTL
from ....lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ....lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ....lib.messages import *
from ....lib.opt_type import *
from ....mem.const.ConstQueueRTL import ConstQueueRTL

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, FunctionUnit, DataType, PredicateType, ConfigType,
                num_inports, num_outports, data_mem_size,
                src0_msgs, src1_msgs, src_const, ctrl_msgs,
                sink_msgs):

    s.src_in0 = TestSrcRTL(DataType, src0_msgs)
    s.src_in1 = TestSrcRTL(DataType, src1_msgs)
    s.src_in2 = TestSrcRTL(DataType, src1_msgs)
    s.src_opt = TestSrcRTL(ConfigType, ctrl_msgs)
    s.sink_out = TestSinkRTL(DataType, sink_msgs)

    s.const_queue = ConstQueueRTL(DataType, src_const)
    s.dut = FunctionUnit(DataType, PredicateType, ConfigType,
                         num_inports, num_outports, data_mem_size)

    connect(s.src_in0.send, s.dut.recv_in[0])
    connect(s.src_in1.send, s.dut.recv_in[1])
    connect(s.src_in2.send, s.dut.recv_in[2])
    connect(s.dut.recv_const, s.const_queue.send_const)
    connect(s.src_opt.send, s.dut.recv_opt)
    connect(s.dut.send_out[0], s.sink_out.recv)

  def done(s):
    return s.sink_out.done()

  def line_trace(s):
    return s.dut.line_trace()

def test_mul():
  FU = ExclusiveDivRTL
  DataType = mk_data(32, 1)
  PredicateType = mk_predicate(1, 1)
  num_inports = 4
  num_outports = 2
  ConfigType = mk_ctrl(num_inports, num_outports)
  FuInType = mk_bits(clog2(num_inports + 1))
  data_mem_size = 8
  PredType      = mk_predicate(1, 1)
  src_in0       = [DataType(4, 1), DataType(7, 1), DataType(12, 1)]
  src_in1       = [DataType(3, 0), DataType(3, 0), DataType( 3, 0)]
  src_const     = [DataType(1, 1),                 DataType( 2, 1)]
  sink_out      = [DataType(1, 0), DataType(2, 0), DataType( 4, 0)] 
  pick_register = [FuInType(x + 1) for x in range(num_inports)]
  src_opt       = [ConfigType(OPT_DIV, pick_register),
                   ConfigType(OPT_DIV, pick_register),
                   ConfigType(OPT_DIV, pick_register)]
  th = TestHarness(FU, DataType, PredicateType, ConfigType,
                   num_inports, num_outports, data_mem_size,
                   src_in0, src_in1, src_const, src_opt,
                   sink_out)
  run_sim(th)
