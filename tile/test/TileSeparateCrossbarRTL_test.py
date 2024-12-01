"""
==========================================================================
TileSeparateCrossbarRTL_test.py
==========================================================================
Test cases for TileSeparateCrossbarRTL.
Command:
pytest TileSeparateCrossbarRTL_test.py -xvs --tb=short --test-verilog --dump-vtb --dump-vcd

Author : Cheng Tan
  Date : Nov 26, 2024

"""

from pymtl3 import *
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)
from pymtl3.passes.backends.verilog import (VerilogTranslationPass,
                                            VerilogVerilatorImportPass)
from ...lib.test_sinks import TestSinkRTL
from ...lib.test_srcs import TestSrcRTL
from ...lib.opt_type import *
from ...lib.messages import *
from ...fu.single.AdderRTL import AdderRTL
from ...fu.single.MulRTL import MulRTL
from ...fu.single.MemUnitRTL import MemUnitRTL
from ...fu.triple.ThreeMulAdderShifterRTL import ThreeMulAdderShifterRTL
from ...fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from ...mem.ctrl.CtrlMemRTL import CtrlMemRTL
from ..TileSeparateCrossbarRTL import TileSeparateCrossbarRTL

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, DUT, FunctionUnit, FuList, DataType, PredicateType,
                CtrlType, ctrl_mem_size, data_mem_size,
                num_fu_inports, num_fu_outports,
                src_data, src_opt, opt_waddr, sink_out):

    AddrType = mk_bits(clog2(ctrl_mem_size))

    # s.src_predicate = TestSrcRTL( b1, src_predicate )
    s.src_opt = TestSrcRTL(CtrlType, src_opt)
    s.opt_waddr = TestSrcRTL(AddrType, opt_waddr)
    s.src_data = [TestSrcRTL(DataType, src_data[i])
                  for i in range(4)]#num_tile_inports)]
    s.sink_out = [TestSinkRTL(DataType, sink_out[i])
                  for i in range(4)]#num_tile_outports)]

    s.dut = DUT(DataType, PredicateType, CtrlType,
                ctrl_mem_size, data_mem_size, len(src_opt),
                len(src_opt), num_fu_inports, num_fu_outports,
                4, 4, FunctionUnit, FuList)

    # connect(s.src_predicate.send, s.dut.reg_predicate)
    connect(s.src_opt.send, s.dut.recv_wopt)
    connect(s.opt_waddr.send, s.dut.recv_waddr)

    for i in range(4):# num_tile_inports):
      connect(s.src_data[i].send, s.dut.recv_data[i])
    for i in range(4):#num_tile_outports ):
      connect(s.dut.send_data[i], s.sink_out[i].recv)

    if MemUnitRTL in FuList:
      s.dut.to_mem_raddr.rdy //= 0
      s.dut.from_mem_rdata.en //= 0
      s.dut.from_mem_rdata.msg //= DataType(0, 0)
      s.dut.to_mem_waddr.rdy //= 0
      s.dut.to_mem_wdata.rdy //= 0

  def done(s):
    done = True
    for i in range(4): # s.num_tile_outports ):
      if not s.sink_out[i].done(): # and not s.src_data[i].done():
        done = False
        break
    return done

  def line_trace(s):
    return s.dut.line_trace()

def test_tile_alu(cmdline_opts):
  num_tile_inports = 4
  num_tile_outports = 4
  num_fu_inports = 4
  num_fu_outports = 1
  num_routing_outports = num_fu_inports + num_tile_outports
  ctrl_mem_size = 3
  data_mem_size = 8
  # number of inputs of FU is fixed inside the tile
  # num_fu_in = 4
  # num_fu_out = 2
  TileInType = mk_bits(clog2(num_tile_inports + 1))
  AddrType = mk_bits(clog2(ctrl_mem_size))
  FuInType = mk_bits(clog2(num_fu_inports + 1))
  FuOutType = mk_bits(clog2(num_fu_outports + 1))
  pickRegister0 = [FuInType(0) for x in range(num_fu_inports)]
  pickRegister1 = [FuInType(1), FuInType(2), FuInType(0), FuInType(0)]
  DUT = TileSeparateCrossbarRTL
  FunctionUnit = FlexibleFuRTL
  FuList = [AdderRTL, MulRTL, MemUnitRTL]
  DataType = mk_data(16, 1)
  PredicateType = mk_predicate(1, 1)
  CtrlType = mk_separate_ctrl(num_fu_inports, num_fu_outports,
                              num_tile_inports, num_tile_outports)
  opt_waddr = [AddrType(0), AddrType(1), AddrType(2)]
  src_opt = [CtrlType(OPT_NAH, b1(0), pickRegister0,
                      # routing_xbar_output
                      [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                       TileInType(4), TileInType(3), TileInType(0), TileInType(0)],
                      # fu_xbar_output
                      [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]),
             CtrlType(OPT_ADD, b1(0), pickRegister1,
                      # routing_xbar_output
                      [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                       TileInType(4), TileInType(1), TileInType(0), TileInType(0)],
                      # fu_xbar_output
                      [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(1),
                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]),
             CtrlType(OPT_SUB, b1(0), pickRegister1,
                      # routing_xbar_output
                      [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                       TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                      # fu_xbar_output
                      [FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(1),
                       FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)])]
  src_data = [[DataType(3, 1)], # DataType( 3, 1)],
              [], # DataType(3, 1), DataType( 4, 1)],
              [DataType(4, 1)], # DataType( 5, 1)],
              [DataType(5, 1), DataType(7, 1)]]
  # src_predicate = [b1(0), b1(0), b1(0) ]
  src_const = [DataType(5, 1), DataType(0, 0), DataType(7, 1)]
  sink_out = [
              # 7 - 3 = 4.
              [DataType(4, 1)],
              [],
              [],
              # 5 + 4 = 9; 7 - 3 = 4.
              [DataType(9, 1), DataType( 4, 1)]]

  th = TestHarness(DUT, FunctionUnit, FuList, DataType, PredicateType,
                   CtrlType, ctrl_mem_size, data_mem_size,
                   num_fu_inports, num_fu_outports,
                   src_data, src_opt, opt_waddr, sink_out)
  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                      ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                       'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts=['dut'])
  run_sim(th)

