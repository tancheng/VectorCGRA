"""
==========================================================================
ExtractPredicateRTL_test.py
==========================================================================
Test cases for ExtractPredicateRTL functional unit.

Author : Shangkun LI
  Date : January 27, 2026
"""

import pytest

from pymtl3 import *
from pymtl3.stdlib.test_utils import (run_sim, config_model_with_cmdline_opts)

from ....lib.messages import *
from ....lib.opt_type import *
from ..ExtractPredicateRTL import ExtractPredicateRTL
from ....lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ....lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, FunctionUnit, IntraCgraPktType, DataType, CtrlType,
                num_inports, num_outports,
                data_mem_size, src_in0, src_opt, sink_out):

    s.src_in0 = TestSrcRTL(DataType, src_in0)
    s.src_opt = TestSrcRTL(CtrlType, src_opt)
    s.sink_out = TestSinkRTL(DataType, sink_out)

    s.dut = FunctionUnit(IntraCgraPktType, num_inports, num_outports)

    FuInType = mk_bits(clog2(num_inports + 1))

    # Connections
    s.src_in0.send //= s.dut.recv_in[0]
    s.src_opt.send //= s.dut.recv_opt
    s.dut.send_out[0] //= s.sink_out.recv

    # Tie off unused ports
    s.dut.recv_const.val //= 0
    s.dut.recv_const.msg //= DataType()
    for i in range(1, num_inports):
      s.dut.recv_in[i].val //= 0
      s.dut.recv_in[i].msg //= DataType()
    for i in range(1, num_outports):
      s.dut.send_out[i].rdy //= 0
    
    s.dut.recv_from_ctrl_mem.val //= 0
    s.dut.recv_from_ctrl_mem.msg //= s.dut.CgraPayloadType()
    s.dut.send_to_ctrl_mem.rdy //= 0

  def done(s):
    return s.src_in0.done() and s.src_opt.done() and s.sink_out.done()

  def line_trace(s):
    return s.dut.line_trace()

def run_sim(th, max_cycles=100):
  th.elaborate()
  th.apply(DefaultPassGroup())
  th.sim_reset()

  ncycles = 0
  print()
  print("{:3}: {}".format(ncycles, th.line_trace()))
  while not th.done() and ncycles < max_cycles:
    th.sim_tick()
    ncycles += 1
    print("{:3}: {}".format(ncycles, th.line_trace()))

  assert ncycles < max_cycles
  th.sim_tick()
  th.sim_tick()
  th.sim_tick()

#-------------------------------------------------------------------------
# Test cases
#-------------------------------------------------------------------------

def test_extract_predicate_basic():
  """Test basic predicate extraction"""
  
  num_inports = 4
  num_outports = 2
  
  data_bitwidth = 32
  DataType = mk_data(data_bitwidth, 1)
  num_ctrl_operations = 64
  num_fu_inports = num_inports
  num_fu_outports = num_outports
  num_tile_inports = 8
  num_tile_outports = 8
  num_registers_per_reg_bank = 16
  CtrlType = mk_ctrl(num_fu_inports, num_fu_outports,
                     num_tile_inports, num_tile_outports,
                     num_registers_per_reg_bank)
  FuInType = mk_bits(clog2(num_inports + 1))
  
  data_mem_size = 8
  ctrl_mem_size = 8
  DataAddrType  = mk_bits(clog2(data_mem_size))
  CtrlAddrType  = mk_bits(clog2(ctrl_mem_size))
  CgraPayloadType = mk_cgra_payload(DataType, DataAddrType, CtrlType, CtrlAddrType)
  IntraCgraPktType = mk_intra_cgra_pkt(1, 1, 1, CgraPayloadType)

  # Input data with different predicates
  # payload doesn't matter, only predicate is extracted
  src_in0 = [
    DataType(100, 1),  # predicate = 1
    DataType(200, 0),  # predicate = 0
    DataType(300, 1),  # predicate = 1
    DataType(400, 0),  # predicate = 0
  ]
  
  # Operations: all OPT_EXTRACT_PREDICATE
  src_opt = [
    CtrlType(OPT_EXTRACT_PREDICATE, fu_in = [FuInType(1), FuInType(0), FuInType(0), FuInType(0)]),
    CtrlType(OPT_EXTRACT_PREDICATE, fu_in = [FuInType(1), FuInType(0), FuInType(0), FuInType(0)]),
    CtrlType(OPT_EXTRACT_PREDICATE, fu_in = [FuInType(1), FuInType(0), FuInType(0), FuInType(0)]),
    CtrlType(OPT_EXTRACT_PREDICATE, fu_in = [FuInType(1), FuInType(0), FuInType(0), FuInType(0)]),
  ]
  
  # Expected outputs: payload = extracted predicate, predicate = 1 (always valid)
  sink_out = [
    DataType(1, 1),  # extracted pred=1, output pred=1
    DataType(0, 1),  # extracted pred=0, output pred=1
    DataType(1, 1),  # extracted pred=1, output pred=1
    DataType(0, 1),  # extracted pred=0, output pred=1
  ]
  
  th = TestHarness(ExtractPredicateRTL, IntraCgraPktType, DataType, CtrlType,
                   num_inports, num_outports, data_mem_size,
                   src_in0, src_opt, sink_out)
  run_sim(th)

def test_extract_predicate_for_loop_termination():
  """Test predicate extraction for loop termination detection"""
  
  num_inports = 4
  num_outports = 2
  data_bitwidth = 32
  DataType = mk_data(data_bitwidth, 1)
  num_ctrl_operations = 64
  num_fu_inports = num_inports
  num_fu_outports = num_outports
  num_tile_inports = 8
  num_tile_outports = 8
  num_registers_per_reg_bank = 16
  CtrlType = mk_ctrl(num_fu_inports, num_fu_outports,
                     num_tile_inports, num_tile_outports,
                     num_registers_per_reg_bank)
  FuInType = mk_bits(clog2(num_inports + 1))

  data_mem_size = 8
  ctrl_mem_size = 8
  DataAddrType  = mk_bits(clog2(data_mem_size))
  CtrlAddrType  = mk_bits(clog2(ctrl_mem_size))
  CgraPayloadType = mk_cgra_payload(DataType, DataAddrType, CtrlType, CtrlAddrType)
  IntraCgraPktType = mk_intra_cgra_pkt(1, 1, 1, CgraPayloadType)

  # Simulating counter output pattern:
  # - pred=1 for valid iterations
  # - pred=0 when loop terminates
  src_in0 = [
    DataType(0, 1),  # counter=0, pred=1 (valid)
    DataType(1, 1),  # counter=1, pred=1 (valid)
    DataType(2, 1),  # counter=2, pred=1 (valid)
    DataType(3, 0),  # counter=3, pred=0 (terminated!)
  ]
  
  src_opt = [
    CtrlType(OPT_EXTRACT_PREDICATE, fu_in = [FuInType(1), FuInType(0), FuInType(0), FuInType(0)]),
    CtrlType(OPT_EXTRACT_PREDICATE, fu_in = [FuInType(1), FuInType(0), FuInType(0), FuInType(0)]),
    CtrlType(OPT_EXTRACT_PREDICATE, fu_in = [FuInType(1), FuInType(0), FuInType(0), FuInType(0)]),
    CtrlType(OPT_EXTRACT_PREDICATE, fu_in = [FuInType(1), FuInType(0), FuInType(0), FuInType(0)]),
  ]
  
  # Expected: extract predicate as boolean for use with NOT and grant_predicate
  sink_out = [
    DataType(1, 1),  # pred=1 -> payload=1 (continue)
    DataType(1, 1),  # pred=1 -> payload=1 (continue)
    DataType(1, 1),  # pred=1 -> payload=1 (continue)
    DataType(0, 1),  # pred=0 -> payload=0 (terminate!)
  ]
  
  th = TestHarness(ExtractPredicateRTL, IntraCgraPktType, DataType, CtrlType,
                   num_inports, num_outports, data_mem_size,
                   src_in0, src_opt, sink_out)
  run_sim(th)
