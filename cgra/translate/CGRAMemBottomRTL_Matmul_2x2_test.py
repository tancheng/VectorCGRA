"""
==========================================================================
CGRARTL_Matmul_2x2_test.py
==========================================================================
Translation for 2x2 CGRA. The provided test is only used for a 2x2 matmul.

Author : Cheng Tan
  Date : Oct 14, 2024
"""

from pymtl3 import *
from pymtl3.passes.backends.verilog import VerilogTranslationPass
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)

from ...lib.test_srcs import TestSrcRTL
from ...lib.test_sinks import TestSinkRTL
from ...lib.opt_type import *
from ...lib.messages import *
from ...fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from ...fu.single.AdderRTL import AdderRTL
from ...fu.single.MemUnitRTL import MemUnitRTL
from ...fu.single.MulRTL import MulRTL
from ...fu.single.SelRTL import SelRTL
from ...fu.single.ShifterRTL import ShifterRTL
from ...fu.single.LogicRTL import LogicRTL
from ...fu.single.PhiRTL import PhiRTL
from ...fu.single.CompRTL import CompRTL
from ...fu.double.SeqMulAdderRTL import SeqMulAdderRTL
from ...fu.single.BranchRTL import BranchRTL
from ..CGRAMemBottomRTL import CGRAMemBottomRTL

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

kMaxCycles = 12

class TestHarness(Component):

  def construct(s, DUT, FunctionUnit, fu_list, DataType, PredicateType,
                CtrlType, width, height, ctrl_mem_size, data_mem_size,
                src_opt, ctrl_waddr, preload_data, preload_const,
                sink_out):

    s.num_tiles = width * height
    AddrType = mk_bits(clog2(ctrl_mem_size))

    s.src_opt = [TestSrcRTL(CtrlType, src_opt[i])
                for i in range(s.num_tiles)]
    s.ctrl_waddr = [TestSrcRTL(AddrType, ctrl_waddr[i])
                   for i in range(s.num_tiles)]

    s.dut = DUT(DataType, PredicateType, CtrlType, width, height,
                ctrl_mem_size, data_mem_size, kMaxCycles,
                kMaxCycles, FunctionUnit, fu_list, preload_data,
                preload_const)

    s.sink_out = [TestSinkRTL(DataType, sink_out[i])
                  for i in range(height - 1)]

    print("[cheng] height: ", height)
    for i in range(height - 1):
      connect(s.dut.send_data[i], s.sink_out[i].recv)

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

def run_sim( test_harness, max_cycles = kMaxCycles ):
  # test_harness.elaborate()
  test_harness.apply( DefaultPassGroup() )

  # Run simulation
  ncycles = 0
  print()
  print("{}:{}".format( ncycles, test_harness.line_trace()))
  while ncycles < max_cycles:
    test_harness.sim_tick()
    ncycles += 1
    print("----------------------------------------------------")
    print("{}:{}".format( ncycles, test_harness.line_trace()))
    print("[cheng] test_harness.dut.sink_out.recv -- rdy: ", test_harness.sink_out[0].recv.rdy, ", en: ", test_harness.sink_out[0].recv.en)

  # Check timeout
#  assert ncycles < max_cycles

  test_harness.sim_tick()
  test_harness.sim_tick()
  test_harness.sim_tick()

def test_CGRA_systolic(cmdline_opts):
  num_tile_inports = 4
  num_tile_outports = 4
  num_xbar_inports = 6
  num_xbar_outports = 8
  ctrl_mem_size = 8
  width = 2
  height = 3
  RouteType = mk_bits(clog2(num_xbar_inports + 1))
  AddrType = mk_bits(clog2(ctrl_mem_size))
  num_tiles = width * height
  num_fu_in = 4
  DUT = CGRAMemBottomRTL
  FunctionUnit = FlexibleFuRTL
  FuList = [SeqMulAdderRTL, AdderRTL, MulRTL, LogicRTL, ShifterRTL, PhiRTL, CompRTL, BranchRTL, MemUnitRTL]
  DataType = mk_data(32, 1)
  PredicateType = mk_predicate(1, 1)
  #  FuList = [ SeqMulAdderRTL, AdderRTL, MulRTL, LogicRTL, ShifterRTL, PhiRTL, CompRTL, BranchRTL, MemUnitRTL ]
  #  DataType = mk_data(16, 1)
  CtrlType = mk_ctrl(num_fu_in, num_xbar_inports, num_xbar_outports)
  FuInType = mk_bits(clog2( num_fu_in + 1))
  pickRegister = [FuInType(x + 1) for x in range(num_fu_in)]
  
  src_opt = [
             # On tile 0 ([0, 0]).
             [CtrlType(OPT_LD_CONST, b1(0), pickRegister, [
              RouteType(5), RouteType(0), RouteType(0), RouteType(0),
              RouteType(0), RouteType(0), RouteType(0), RouteType(0)]),
              CtrlType( OPT_LD_CONST, b1(0), pickRegister, [
              RouteType(5), RouteType(0), RouteType(0), RouteType(0),
              RouteType(0), RouteType(0), RouteType(0), RouteType(0)]),
              CtrlType( OPT_LD_CONST, b1(0), pickRegister, [
              RouteType(5), RouteType(0), RouteType(0), RouteType(0),
              RouteType(0), RouteType(0), RouteType(0), RouteType(0)]),
              CtrlType( OPT_LD_CONST, b1(0), pickRegister, [
              RouteType(5), RouteType(0), RouteType(0), RouteType(0),
              RouteType(0), RouteType(0), RouteType(0), RouteType(0)]),
             ],
             # On tile 1 ([0, 1]).
             [CtrlType( OPT_NAH, b1(0), pickRegister, [
              RouteType(5), RouteType(0), RouteType(0), RouteType(0),
              RouteType(0), RouteType(0), RouteType(0), RouteType(0)]),
              CtrlType( OPT_LD_CONST, b1(0), pickRegister, [
              RouteType(5), RouteType(0), RouteType(0), RouteType(0),
              RouteType(0), RouteType(0), RouteType(0), RouteType(0)]),
              CtrlType( OPT_LD_CONST, b1(0), pickRegister, [
              RouteType(5), RouteType(0), RouteType(0), RouteType(0),
              RouteType(0), RouteType(0), RouteType(0), RouteType(0)]),
              CtrlType( OPT_LD_CONST, b1(0), pickRegister, [
              RouteType(5), RouteType(0), RouteType(0), RouteType(0),
              RouteType(0), RouteType(0), RouteType(0), RouteType(0)]),
              CtrlType( OPT_LD_CONST, b1(0), pickRegister, [
              RouteType(5), RouteType(0), RouteType(0), RouteType(0),
              RouteType(0), RouteType(0), RouteType(0), RouteType(0)]),
             ],
             # On tile 2 ([1, 0]).
             [CtrlType( OPT_NAH, b1(0), pickRegister, [
              RouteType(2), RouteType(0), RouteType(0), RouteType(0),
              RouteType(2), RouteType(0), RouteType(0), RouteType(0)]),
              CtrlType( OPT_MUL_CONST, b1(0), pickRegister, [
              RouteType(2), RouteType(0), RouteType(0), RouteType(5),
              RouteType(2), RouteType(0), RouteType(0), RouteType(0)]),
              CtrlType( OPT_MUL_CONST, b1(0), pickRegister, [
              RouteType(2), RouteType(0), RouteType(0), RouteType(5),
              RouteType(2), RouteType(0), RouteType(0), RouteType(0)]),
              CtrlType( OPT_MUL_CONST, b1(0), pickRegister, [
              RouteType(2), RouteType(0), RouteType(0), RouteType(5),
              RouteType(2), RouteType(0), RouteType(0), RouteType(0)]),

              CtrlType( OPT_NAH, b1(0), pickRegister, [
              RouteType(2), RouteType(0), RouteType(0), RouteType(0),
              RouteType(2), RouteType(0), RouteType(0), RouteType(0)]),
              CtrlType( OPT_NAH, b1(0), pickRegister, [
              RouteType(2), RouteType(0), RouteType(0), RouteType(0),
              RouteType(2), RouteType(0), RouteType(0), RouteType(0)]),
             ],
             # On tile 3 ([1, 1]).
             [CtrlType( OPT_NAH, b1(0), pickRegister, [
              RouteType(2), RouteType(0), RouteType(0), RouteType(0),
              RouteType(2), RouteType(0), RouteType(0), RouteType(0)]),
              CtrlType( OPT_NAH, b1(0), pickRegister, [
              RouteType(2), RouteType(0), RouteType(0), RouteType(0),
              RouteType(2), RouteType(0), RouteType(3), RouteType(0)]),
              CtrlType( OPT_MUL_CONST_ADD, b1(0), pickRegister, [
              RouteType(2), RouteType(0), RouteType(0), RouteType(5),
              RouteType(2), RouteType(0), RouteType(3), RouteType(0)]),
              CtrlType( OPT_MUL_CONST_ADD, b1(0), pickRegister, [
              RouteType(2), RouteType(0), RouteType(0), RouteType(5),
              RouteType(2), RouteType(0), RouteType(3), RouteType(0)]),

              CtrlType( OPT_NAH, b1(0), pickRegister, [
              RouteType(2), RouteType(0), RouteType(0), RouteType(0),
              RouteType(2), RouteType(0), RouteType(0), RouteType(0)]),
              CtrlType( OPT_NAH, b1(0), pickRegister, [
              RouteType(2), RouteType(0), RouteType(0), RouteType(0),
              RouteType(2), RouteType(0), RouteType(0), RouteType(0)]),

             ],
             # On tile 4 ([2, 0]).
             [CtrlType( OPT_NAH, b1(0), pickRegister, [
              RouteType(0), RouteType(0), RouteType(0), RouteType(0),
              RouteType(2), RouteType(0), RouteType(0), RouteType(0)]),
              CtrlType( OPT_NAH, b1(0), pickRegister, [
              RouteType(0), RouteType(0), RouteType(0), RouteType(0),
              RouteType(2), RouteType(0), RouteType(0), RouteType(0)]),
              CtrlType( OPT_MUL_CONST, b1(0), pickRegister, [
              RouteType(0), RouteType(0), RouteType(0), RouteType(5),
              RouteType(2), RouteType(0), RouteType(0), RouteType(0)]),
              CtrlType( OPT_MUL_CONST, b1(0), pickRegister, [
              RouteType(0), RouteType(0), RouteType(0), RouteType(5),
              RouteType(2), RouteType(0), RouteType(0), RouteType(0)]),

              CtrlType( OPT_NAH, b1(0), pickRegister, [
              RouteType(2), RouteType(0), RouteType(0), RouteType(0),
              RouteType(2), RouteType(0), RouteType(0), RouteType(0)]),
              CtrlType( OPT_NAH, b1(0), pickRegister, [
              RouteType(2), RouteType(0), RouteType(0), RouteType(0),
              RouteType(2), RouteType(0), RouteType(0), RouteType(0)]),

             ],
             # On tile 5 ([2, 1]).
             [CtrlType( OPT_NAH, b1(0), pickRegister, [
              RouteType(0), RouteType(0), RouteType(0), RouteType(0),
              RouteType(2), RouteType(0), RouteType(3), RouteType(0)]),
              CtrlType( OPT_NAH, b1(0), pickRegister, [
              RouteType(0), RouteType(0), RouteType(0), RouteType(0),
              RouteType(2), RouteType(0), RouteType(3), RouteType(0)]),
              CtrlType( OPT_NAH, b1(0), pickRegister, [
              RouteType(0), RouteType(0), RouteType(0), RouteType(0),
              RouteType(2), RouteType(0), RouteType(3), RouteType(0)]),
              CtrlType( OPT_MUL_CONST_ADD, b1(0), pickRegister, [
              RouteType(0), RouteType(0), RouteType(0), RouteType(5),
              RouteType(2), RouteType(0), RouteType(3), RouteType(0)]),
              CtrlType( OPT_MUL_CONST_ADD, b1(0), pickRegister, [
              RouteType(0), RouteType(0), RouteType(0), RouteType(5),
              RouteType(2), RouteType(0), RouteType(3), RouteType(0)]),

              CtrlType( OPT_NAH, b1(0), pickRegister, [
              RouteType(2), RouteType(0), RouteType(0), RouteType(0),
              RouteType(2), RouteType(0), RouteType(0), RouteType(0)]),
              CtrlType( OPT_NAH, b1(0), pickRegister, [
              RouteType(2), RouteType(0), RouteType(0), RouteType(0),
              RouteType(2), RouteType(0), RouteType(0), RouteType(0)]),

             ]
            ]
  
  preload_mem = [DataType(1, 1), DataType(2, 1), DataType(3, 1),
                 DataType(4, 1)]
  preload_const = [[DataType(0, 1), DataType(1, 1)],
                   [DataType(0, 0), DataType(2, 1), DataType(3, 1)], # offset address used for loading
                   [DataType(2, 1)], [DataType(4, 1)], # preloaded data
                   [DataType(6, 1)], [DataType(8, 1)]] # preloaded data
  
  data_mem_size = len(preload_mem)

  """
  1 3      2 6     14 20
       x        =
  2 4      4 8     30 44
  """
  sink_out = [[DataType(14, 1), DataType(20, 1)], [DataType(30, 1),
               DataType(44, 1)]]

  ctrl_waddr = [[AddrType(0), AddrType(1), AddrType(2), AddrType(3)]
               for _ in range(num_tiles)]

  th = TestHarness(DUT, FunctionUnit, FuList, DataType, PredicateType,
                   CtrlType, width, height, ctrl_mem_size, data_mem_size,
                   src_opt, ctrl_waddr, preload_mem, preload_const,
                   sink_out)

  th.elaborate()
  th.dut.set_metadata(VerilogTranslationPass.explicit_module_name,
                      f'CGRARTL')
  # th.dut.set_metadata( VerilogVerilatorImportPass.vl_Wno_list,
  #                   ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
  #                    'ALWCOMBORDER'] )
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts=['dut'])

  run_sim(th)

