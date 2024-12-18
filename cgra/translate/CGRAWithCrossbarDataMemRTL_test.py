"""
==========================================================================
CGRAWithCrossbarDataMemRTL_test.py
==========================================================================
Test cases for CGRA with crossbar-based data memory.

Author : Cheng Tan
  Date : Dec 14, 2024
"""


from pymtl3 import *
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)
from pymtl3.passes.backends.verilog import (VerilogTranslationPass,
                                            VerilogVerilatorImportPass)
from ..CGRAWithCrossbarDataMemRTL import CGRAWithCrossbarDataMemRTL
from ...fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from ...fu.single.AdderRTL import AdderRTL
from ...fu.single.MemUnitRTL import MemUnitRTL
from ...fu.single.ShifterRTL import ShifterRTL
from ...lib.messages import *
from ...lib.opt_type import *
from ...lib.basic.en_rdy.test_srcs import TestSrcRTL


#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, DUT, FunctionUnit, FuList, DataType,
                PredicateType, CtrlType, NocPktType, CmdType,
                ControllerIdType, controller_id, width, height,
                ctrl_mem_size, data_mem_size_global,
                data_mem_size_per_bank, num_banks_per_cgra,
                src_opt, ctrl_waddr, controller2addr_map):

    s.num_tiles = width * height
    CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
    DataAddrType = mk_bits(clog2(data_mem_size_global))

    s.src_opt = [TestSrcRTL(CtrlType, src_opt[i])
                 for i in range(s.num_tiles)]
    s.ctrl_waddr = [TestSrcRTL(CtrlAddrType, ctrl_waddr[i])
                    for i in range(s.num_tiles)]

    s.dut = DUT(DataType, PredicateType, CtrlType, NocPktType,
                CmdType, ControllerIdType, controller_id,
                width, height, ctrl_mem_size, data_mem_size_global,
                data_mem_size_per_bank, num_banks_per_cgra,
                len(src_opt[0]), len(src_opt[0]), FunctionUnit, FuList,
                controller2addr_map)

    # Connections
    s.dut.send_to_noc.rdy //= 0
    s.dut.recv_from_noc.val //= 0
    s.dut.recv_from_noc.msg //= NocPktType(0, 0, 0, 0, 0, 0)

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
  data_mem_size_global = 512
  data_mem_size_per_bank = 32
  num_banks_per_cgra = 2
  width = 2
  height = 2
  TileInType = mk_bits(clog2(num_tile_inports + 1))
  FuInType = mk_bits(clog2(num_fu_inports + 1))
  FuOutType = mk_bits(clog2(num_fu_outports + 1))
  addr_nbits = clog2(data_mem_size_global)
  AddrType = mk_bits(addr_nbits)
  CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
  num_tiles = width * height
  DUT = CGRAWithCrossbarDataMemRTL
  FunctionUnit = FlexibleFuRTL
  FuList = [MemUnitRTL, AdderRTL]
  DataType = mk_data(32, 1)
  PredicateType = mk_predicate(1, 1)

  nterminals = 4
  CmdType = mk_bits(4)
  ControllerIdType = mk_bits(clog2(nterminals))
  controller_id = 1
  controller2addr_map = {
          0: [0, 3],
          1: [4, 7],
          2: [8, 11],
          3: [12, 15],
  }

  CtrlType = mk_separate_ctrl(num_fu_inports, num_fu_outports,
                              num_tile_inports, num_tile_outports)
  NocPktType = mk_ring_multi_cgra_pkt(nrouters = nterminals,
                                      addr_nbits = addr_nbits,
                                      data_nbits = 32,
                                      predicate_nbits = 1)
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
  ctrl_waddr = [[CtrlAddrType(0), CtrlAddrType(1), CtrlAddrType(2), CtrlAddrType(3),
                 CtrlAddrType(4), CtrlAddrType(5)] for _ in range(num_tiles)]
  th = TestHarness(DUT, FunctionUnit, FuList, DataType, PredicateType,
                   CtrlType, NocPktType, CmdType, ControllerIdType,
                   controller_id, width, height, ctrl_mem_size,
                   data_mem_size_global, data_mem_size_per_bank,
                   num_banks_per_cgra, src_opt, ctrl_waddr,
                   controller2addr_map)
  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                      ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                       'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts=['dut'])
  run_sim(th)

