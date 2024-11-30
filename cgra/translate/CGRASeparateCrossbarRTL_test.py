"""
==========================================================================
CGRASeparateCrossbarRTL_test.py
==========================================================================
Test cases for CGRAs with different configurations.

Author : Cheng Tan
  Date : Nov 29, 2024

"""

from pymtl3 import *
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)
from pymtl3.passes.backends.verilog import (VerilogTranslationPass,
                                            VerilogVerilatorImportPass)
from ..CGRASeparateCrossbarRTL import CGRASeparateCrossbarRTL
from ...fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from ...fu.single.AdderRTL import AdderRTL
from ...fu.single.MemUnitRTL import MemUnitRTL
from ...fu.single.ShifterRTL import ShifterRTL
from ...lib.messages import *
from ...lib.opt_type import *
from ...lib.test_srcs import TestSrcRTL

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, DUT, FunctionUnit, FuList, DataType, PredicateType,
                CtrlType, width, height, ctrl_mem_size, data_mem_size,
                src_opt, ctrl_waddr):

    s.num_tiles = width * height
    AddrType = mk_bits(clog2(ctrl_mem_size))

    s.src_opt = [TestSrcRTL(CtrlType, src_opt[i])
                 for i in range(s.num_tiles)]
    s.ctrl_waddr = [TestSrcRTL(AddrType, ctrl_waddr[i])
                    for i in range(s.num_tiles)]

    s.dut = DUT(DataType, PredicateType, CtrlType, width, height,
                ctrl_mem_size, data_mem_size, len(src_opt[0]),
                len(src_opt[0]), FunctionUnit, FuList)

    for i in range(s.num_tiles):
      connect(s.src_opt[i].send, s.dut.recv_wopt[i])
      connect(s.ctrl_waddr[i].send, s.dut.recv_waddr[i])

  def done(s):
    done = True
    for i in range(s.num_tiles):
      if not s.src_opt[i].done():
        done = False
        break
    return done

  def line_trace(s):
    return s.dut.line_trace()

def test_homo_2x2(cmdline_opts):
  num_tile_inports  = 4
  num_tile_outports = 4
  num_fu_inports = 4
  num_fu_outports = 2
  num_routing_outports = num_tile_outports + num_fu_inports
  ctrl_mem_size = 6
  data_mem_size = 8
  width = 2
  height = 2
  TileInType = mk_bits(clog2(num_tile_inports + 1))
  FuInType = mk_bits(clog2(num_fu_inports + 1))
  FuOutType = mk_bits(clog2(num_fu_outports + 1))
  AddrType = mk_bits(clog2(ctrl_mem_size))
  num_tiles = width * height
  DUT = CGRASeparateCrossbarRTL
  FunctionUnit = FlexibleFuRTL
  FuList = [MemUnitRTL, AdderRTL]
  DataType = mk_data(16, 1)
  PredicateType = mk_predicate(1, 1)
  CtrlType = mk_separate_ctrl(num_fu_inports, num_fu_outports,
                              num_tile_inports, num_tile_outports)
  pickRegister = [FuInType(x + 1) for x in range(num_fu_inports)]
  src_opt = [[
              CtrlType(OPT_INC, b1(0),
                       pickRegister,
                       [TileInType(4), TileInType(3), TileInType(2), TileInType(1),
                        # TODO: make below as TileInType(5) to double check.
                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],

                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                        FuOutType(1), FuOutType(1), FuOutType(1), FuOutType(1)]),
              CtrlType(OPT_INC, b1(0),
                       pickRegister,
                       [TileInType(4), TileInType(3), TileInType(2), TileInType(1),
                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],

                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                        FuOutType(1), FuOutType(1), FuOutType(1), FuOutType(1)]),

              CtrlType(OPT_ADD, b1(0),
                       pickRegister,
                       [TileInType(4), TileInType(3), TileInType(2), TileInType(1),
                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],

                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                        FuOutType(1), FuOutType(1), FuOutType(1), FuOutType(1)]),

              CtrlType(OPT_STR, b1(0),
                       pickRegister,
                       [TileInType(4), TileInType(3), TileInType(2), TileInType(1),
                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],

                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                        FuOutType(1), FuOutType(1), FuOutType(1), FuOutType(1)]),

              CtrlType(OPT_ADD, b1(0),
                       pickRegister,
                       [TileInType(4), TileInType(3), TileInType(2), TileInType(1),
                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],

                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                        FuOutType(1), FuOutType(1), FuOutType(1), FuOutType(1)]),

              CtrlType(OPT_ADD, b1(0),
                       pickRegister,
                       [TileInType(4), TileInType(3), TileInType(2), TileInType(1),
                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)],

                       [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                        FuOutType(1), FuOutType(1), FuOutType(1), FuOutType(1)])

             ] for _ in range(num_tiles)]
  ctrl_waddr = [[AddrType(0), AddrType(1), AddrType(2), AddrType(3),
                 AddrType(4), AddrType(5)] for _ in range(num_tiles)]
  th = TestHarness(DUT, FunctionUnit, FuList, DataType, PredicateType,
                   CtrlType, width, height, ctrl_mem_size, data_mem_size,
                   src_opt, ctrl_waddr)
  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                      ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                       'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts=['dut'])
  run_sim(th)

