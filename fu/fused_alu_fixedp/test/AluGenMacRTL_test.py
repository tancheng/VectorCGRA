"""
==========================================================================
AluGenMacFuRTL_test.py
==========================================================================

Author : RJ
  Date : Jan 6, 2024
"""

from pymtl3 import *
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)
from ..AluGenMacRTL import AluGenMacRTL
from ....lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ....lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ....lib.messages import *
from ....lib.opt_type import *
from ....mem.const.ConstQueueRTL import ConstQueueRTL

def test_elaborate( cmdline_opts ):
  DataType      = mk_data( 16, 1 )
  PredType      = mk_predicate( 1, 1 )
  ConfigType    = mk_ctrl(3, 3, 1)
  data_mem_size = 8
  ctrl_mem_size = 8
  DataAddrType  = mk_bits(clog2(data_mem_size))
  CtrlAddrType  = mk_bits(clog2(ctrl_mem_size))
  CgraPayloadType = mk_cgra_payload(DataType, DataAddrType, ConfigType, CtrlAddrType)
  IntraCgraPktType = mk_intra_cgra_pkt(1, 1, 1, CgraPayloadType)
  num_inports   = 3
  num_outports  = 1
  FuInType      = mk_bits(clog2(num_inports + 1))
  pick_register = [FuInType(x + 1) for x in range(num_inports) ]
  src_in0       = [DataType(1, 1), DataType(7, 1), DataType(4,  1)]
  src_in1       = [DataType(2, 1), DataType(3, 1), DataType(1,  1)]
  src_in2       = [DataType(2, 1), DataType(3, 1), DataType(1,  1)]
  src_const     = [DataType(5, 1), DataType(0, 0), DataType(7,  1)]
  sink_out      = [DataType(6, 0), DataType(4, 0), DataType(11, 1)]
  src_opt       = [ConfigType(OPT_ADD_CONST, pick_register),
                   ConfigType(OPT_SUB,       pick_register),
                   ConfigType(OPT_ADD_CONST, pick_register)]
  dut = AluGenMacRTL(IntraCgraPktType, num_inports, num_outports)
  dut = config_model_with_cmdline_opts(dut, cmdline_opts, duts = [])

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness( Component ):

  def construct(s, FunctionUnit, IntraCgraPktType, DataType, ConfigType,
                num_inports, num_outports, data_mem_size,
                src0_msgs, src1_msgs, src2_msgs, src_const,
                ctrl_msgs, sink_msgs):

    s.src_in0  = TestSrcRTL (DataType,   src0_msgs)
    s.src_in1  = TestSrcRTL (DataType,   src1_msgs)
    s.src_in2  = TestSrcRTL (DataType,   src2_msgs)
    s.src_opt  = TestSrcRTL (ConfigType, ctrl_msgs)
    s.sink_out = TestSinkRTL(DataType,  sink_msgs)

    s.const_queue = ConstQueueRTL(DataType, src_const)
    s.dut = FunctionUnit(IntraCgraPktType, num_inports, num_outports)

    connect(s.src_in0.send,    s.dut.recv_in[0]        )
    connect(s.src_in1.send,    s.dut.recv_in[1]        )
    connect(s.src_in2.send,    s.dut.recv_in[2]        )
    connect(s.dut.recv_const,  s.const_queue.send_const)
    connect(s.src_opt.send,    s.dut.recv_opt          )
    connect(s.dut.send_out[0], s.sink_out.recv         )

  def done(s):
    return s.src_in0.done() and s.src_in1.done() and \
           s.src_opt.done() and s.sink_out.done()

  def line_trace(s):
    return s.dut.line_trace()

def test_add_basic(cmdline_opts):
  FU            = AluGenMacRTL
  exp_nbits     = 4
  sig_nbits     = 11
  DataType      = mk_data(16, 1)
  PredType      = mk_predicate(1, 1)
  ConfigType    = mk_ctrl(3, 3, 1)
  data_mem_size = 8
  ctrl_mem_size = 8
  DataAddrType  = mk_bits(clog2(data_mem_size))
  CtrlAddrType  = mk_bits(clog2(ctrl_mem_size))
  CgraPayloadType = mk_cgra_payload(DataType, DataAddrType, ConfigType, CtrlAddrType)
  IntraCgraPktType = mk_intra_cgra_pkt(1, 1, 1, CgraPayloadType)
  num_inports   = 3
  num_outports  = 1
  FuInType      = mk_bits(clog2(num_inports + 1))
  pick_register = [FuInType(x + 1) for x in range(num_inports) ]
  src_in0       = [DataType(1, 1), DataType(2, 1), DataType(3, 1), DataType(3, 1), DataType(3, 1),DataType(3, 1), DataType( 4, 1), DataType( 3, 1)]
  src_in1       = [DataType(1, 1), DataType(2, 1), DataType(3, 1), DataType(3, 1), DataType(3, 1),DataType(3, 1), DataType( 5, 1), DataType( 3, 1)]
  src_in2       = [DataType(1, 1), DataType(2, 1), DataType(3, 1), DataType(3, 1), DataType(3, 1),DataType(3, 1), DataType( 3, 1), DataType( 3, 1)]
  src_const     = [DataType(1, 1), DataType(2, 1), DataType(3, 1)]
  sink_out      = [DataType(2, 1), DataType(0, 1), DataType(0, 1), DataType(1, 1), DataType(0, 1),DataType(1, 1), DataType(20, 1), DataType(12, 1)]
  src_opt       = [ConfigType(OPT_ADD,     pick_register),
                   ConfigType(OPT_SUB,     pick_register),
                   ConfigType(OPT_LT,      pick_register),
                   ConfigType(OPT_LTE,     pick_register),
                   ConfigType(OPT_GT,      pick_register),
                   ConfigType(OPT_GTE,     pick_register),
                   ConfigType(OPT_MUL,     pick_register),
                   ConfigType(OPT_MUL_ADD, pick_register)]
  th = TestHarness(FU, IntraCgraPktType, DataType, ConfigType,
                  num_inports, num_outports, data_mem_size,
                  src_in0, src_in1, src_in2, src_const, src_opt,
                  sink_out)
  run_sim(th)
