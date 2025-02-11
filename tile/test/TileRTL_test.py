"""
==========================================================================
TileRTL_test.py
==========================================================================
Test cases for TileRTL.
Command:
pytest TileRTL_test.py -xvs --tb=short --test-verilog --dump-vtb --dump-vcd

Author : Cheng Tan
  Date : Nov 26, 2024
"""

from pymtl3 import *
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)
from pymtl3.passes.backends.verilog import (VerilogTranslationPass,
                                            VerilogVerilatorImportPass)
from ..TileRTL import TileRTL
from ...fu.triple.ThreeMulAdderShifterRTL import ThreeMulAdderShifterRTL
from ...fu.triple.ThreeMulAdderShifterRTL import ThreeMulAdderShifterRTL
from ...fu.flexible.FlexibleFuRTL         import FlexibleFuRTL
from ...fu.vector.VectorMulComboRTL       import VectorMulComboRTL
from ...fu.vector.VectorAdderComboRTL     import VectorAdderComboRTL
from ...fu.vector.VectorAllReduceRTL      import VectorAllReduceRTL
from ...fu.single.AdderRTL                import AdderRTL
from ...fu.single.MemUnitRTL              import MemUnitRTL
from ...fu.single.MulRTL                  import MulRTL
from ...fu.single.SelRTL                  import SelRTL
from ...fu.single.ShifterRTL              import ShifterRTL
from ...fu.single.LogicRTL                import LogicRTL
from ...fu.single.PhiRTL                  import PhiRTL
from ...fu.single.CompRTL                 import CompRTL
from ...fu.single.BranchRTL               import BranchRTL
from ...fu.single.NahRTL                  import NahRTL
from ...fu.triple.ThreeMulAdderShifterRTL import ThreeMulAdderShifterRTL
from ...fu.flexible.FlexibleFuRTL         import FlexibleFuRTL
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as ValRdyTestSrcRTL
from ...lib.basic.val_rdy.SinkRTL import SinkRTL as ValRdyTestSinkRTL
from ...lib.messages import *
from ...lib.cmd_type import *
from ...lib.opt_type import *
from ...mem.ctrl.CtrlMemRTL import CtrlMemRTL

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, DUT, FunctionUnit, FuList, DataType, PredicateType,
                CpuPktType, CtrlSignalType, ctrl_mem_size, data_mem_size,
                num_fu_inports, num_fu_outports, num_tile_inports,
                num_tile_outports, src_data, src_cpu_pkt, sink_out):

    s.num_tile_inports = num_tile_inports
    s.num_tile_outports = num_tile_outports

    s.src_cpu_pkt = ValRdyTestSrcRTL(CpuPktType, src_cpu_pkt)
    s.src_data = [ValRdyTestSrcRTL(DataType, src_data[i])
                  for i in range(num_tile_inports)]
    s.sink_out = [ValRdyTestSinkRTL(DataType, sink_out[i])
                  for i in range(num_tile_outports)]

    s.dut = DUT(DataType, PredicateType, CpuPktType, CtrlSignalType,
                ctrl_mem_size, data_mem_size, 3, 3, # 3 opts
                num_fu_inports, num_fu_outports, num_tile_inports,
                num_tile_outports, FunctionUnit, FuList)

    connect(s.src_cpu_pkt.send, s.dut.recv_ctrl_pkt)

    for i in range(num_tile_inports):
      connect(s.src_data[i].send, s.dut.recv_data[i])
    for i in range(num_tile_outports):
      connect(s.dut.send_data[i], s.sink_out[i].recv)

    if MemUnitRTL in FuList:
      s.dut.to_mem_raddr.rdy //= 0
      s.dut.from_mem_rdata.val //= 0
      s.dut.from_mem_rdata.msg //= DataType(0, 0)
      s.dut.to_mem_waddr.rdy //= 0
      s.dut.to_mem_wdata.rdy //= 0

  def done(s):
    for i in range(s.num_tile_inports):
      if not s.src_data[i].done():
        return False

    for i in range(s.num_tile_outports):
      if not s.sink_out[i].done():
        return False

    return True

  def line_trace(s):
    return s.dut.line_trace()

def test_tile_alu(cmdline_opts):
  cmdline_opts['max_cycles'] = 20
  num_tile_inports = 4
  num_tile_outports = 4
  num_fu_inports = 4
  num_fu_outports = 2
  num_routing_outports = num_fu_inports + num_tile_outports
  ctrl_mem_size = 3
  data_mem_size = 8
  num_terminals = 4
  num_ctrl_actions = 6
  num_ctrl_operations = 64
  TileInType = mk_bits(clog2(num_tile_inports + 1))
  FuInType = mk_bits(clog2(num_fu_inports + 1))
  FuOutType = mk_bits(clog2(num_fu_outports + 1))
  pick_register0 = [FuInType(0) for x in range(num_fu_inports)]
  pick_register1 = [FuInType(1), FuInType(2), FuInType(0), FuInType(0)]
  DUT = TileRTL
  FunctionUnit = FlexibleFuRTL
  # FuList = [AdderRTL, MulRTL, MemUnitRTL]
  FuList = [AdderRTL,
            MulRTL,
            LogicRTL,
            ShifterRTL,
            PhiRTL,
            CompRTL,
            BranchRTL,
            MemUnitRTL,
            SelRTL,
            ThreeMulAdderShifterRTL,
            VectorMulComboRTL,
            VectorAdderComboRTL]
  # 64-bit to satisfy the default bitwidth of vector FUs.
  data_nbits = 64
  DataType = mk_data(data_nbits, 1)
  PredicateType = mk_predicate(1, 1)
  # mk_intra_cgra_pkt(nrouters = 4,
  #                   cmd_nbits = 4,
  #                   cgraId_nbits = 4,
  #                   ctrl_actions = 8,
  #                   ctrl_mem_size = 16,
  #                   ctrl_operations = 64,
  #                   ctrl_fu_inports = 2,
  #                   ctrl_fu_outports = 2,
  #                   ctrl_tile_inports = 4,
  #                   ctrl_tile_outports = 4,
  #                   addr_nbits = 16,
  #                   data_nbits = 16,
  #                   predicate_nbits = 1,
  #                   prefix = "IntraCgraPacket"):
  CpuPktType = mk_intra_cgra_pkt(nrouters=num_terminals,
                                 ctrl_mem_size=ctrl_mem_size,
                                 ctrl_fu_inports=num_fu_inports,
                                 ctrl_fu_outports=num_fu_outports,
                                 ctrl_tile_inports=num_tile_inports,
                                 ctrl_tile_outports=num_tile_outports,
                                 data_nbits = data_nbits,
                                 )
  CtrlSignalType = \
      mk_separate_ctrl(num_ctrl_operations, num_fu_inports,
                       num_fu_outports, num_tile_inports,
                       num_tile_outports)
  src_cpu_pkt = [
               # cgraId, srcTile, dstTile, opaque, vc_id, ctrl_action, ctrl_addr,  ctrl_operation, ctrl_predicate,     ctrl_fu_in,
      CpuPktType(     0,       0,       0,      0,     0,  CMD_CONFIG,         0,         OPT_NAH,          b1(0), pick_register0,
                  # ctrl_routing_xbar_outport
                  [# to fu
                   TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                   # to tile
                   # why this maps with tile_inports: (0000000000000003.1.0.0, val: 1, rdy: 0)|(0000000000000000.0.0.0, val: 0, rdy: 0)|(0000000000000004?
                   TileInType(4), TileInType(3), TileInType(0), TileInType(0)],
                  # fu_xbar_output
                  [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                   FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                  # ctrl_routing_predicate_in
                  [b1(1), b1(1), b1(1), b1(1)],
                  #     cmd, addr,           data,   data_predicate
                  # todo
                  # Shouldn't data use DataType?
                        0,      0, 1,            b1(1)
                ),
      CpuPktType(0, 0, 0, 0, 0, CMD_CONFIG, 0, OPT_NAH, b1(0), pick_register0,
                 # ctrl_routing_xbar_outport
                 [  # to fu
                     TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                     # to tile
                     TileInType(4), TileInType(3), TileInType(0), TileInType(0)],
                 # fu_xbar_output
                 [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                  FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                 # ctrl_routing_predicate_in
                 [b1(1), b1(1), b1(1), b1(1)],
                 #     cmd, addr,           data,   data_predicate
                 0, 0, 2, b1(1)
                 ),
      CpuPktType(0, 0, 0, 0, 0, CMD_CONFIG, 1, OPT_ADD, b1(0), pick_register0,
                 # ctrl_routing_xbar_outport
                 [  # to fu
                     TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                     # to tile
                     TileInType(4), TileInType(7), TileInType(0), TileInType(0)],
                 # fu_xbar_output
                 [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(1),
                  FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                 # ctrl_routing_predicate_in
                 [b1(1), b1(1), b1(1), b1(1)],
                 #     cmd, addr,           data,   data_predicate
                 0,    1, 0,   b1(1)
                 ),
      # CpuPktType(0, 0, 0, 0, 0, CMD_CONFIG, 2, OPT_SUB, b1(0), pick_register0,
      #            # ctrl_routing_xbar_outport
      #            [  # to fu
      #                TileInType(0), TileInType(0), TileInType(0), TileInType(0),
      #                # to tile
      #                TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
      #            # fu_xbar_output
      #            [FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(1),
      #             FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
      #            # ctrl_routing_predicate_in
      #            [b1(1), b1(1), b1(1), b1(1)],
      #            #     cmd, addr,           data,   data_predicate
      #            CMD_CONST,    1, DataType(3, 1),   b1(1)
      #            ),
      # CpuPktType(0, 0, 0, 0, 0, CMD_LAUNCH, 0, OPT_ADD, b1(0), pick_register0,
      #            # ctrl_routing_xbar_outport
      #            [  # to fu
      #                TileInType(0), TileInType(0), TileInType(0), TileInType(0),
      #                # to tile
      #                TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
      #            # fu_xbar_output
      #            [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
      #             FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
      #            # ctrl_routing_predicate_in
      #            [b1(1), b1(1), b1(1), b1(1)],
      #            #     cmd, addr,           data,   data_predicate
      #            CMD_CONST,    2, DataType(4, 1),   b1(1)
      #            ),
      # CpuPktType(0,  0,  0,    0,  CMD_CONFIG, 1,   OPT_ADD, b1(0), pick_register1,
      #             # routing_xbar_output
      #             [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
      #              TileInType(4), TileInType(1), TileInType(0), TileInType(0)],
      #             # fu_xbar_output
      #             [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(1),
      #              FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]),
      # CpuPktType(0,  0,  0,    0,  CMD_CONFIG, 2,   OPT_SUB, b1(0), pick_register1,
      #             # routing_xbar_output
      #             [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
      #              TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
      #             # fu_xbar_output
      #             [FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(1),
      #              FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]),
      # CpuPktType(0,  0,  0,    0,  CMD_LAUNCH, 0,   OPT_ADD, b1(0), pick_register1,
      #             # routing_xbar_output
      #             [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
      #              TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
      #             # fu_xbar_output
      #             [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
      #              FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)])
      ]
  src_data = [[DataType(3, 1)],
              [],
              [DataType(4, 1)],
              [DataType(5, 1), DataType(7, 1)]]
  src_const = [DataType(5, 1), DataType(0, 0), DataType(7, 1)]
  sink_out = [
              # 7 - 3 = 4.
              [DataType(4, 1)],
              [],
              [],
              # 5 + 4 = 9; 7 - 3 = 4.
              [DataType(9, 1), DataType(4, 1)]]

  th = TestHarness(DUT, FunctionUnit, FuList, DataType, PredicateType,
                   CpuPktType, CtrlSignalType, ctrl_mem_size,
                   data_mem_size, num_fu_inports, num_fu_outports,
                   num_tile_inports, num_tile_outports, src_data,
                   src_cpu_pkt, sink_out)
  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                      ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                       'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  # todo
  # cmdline_ops 不放在这里不起作用
  run_sim(th, cmdline_opts)

