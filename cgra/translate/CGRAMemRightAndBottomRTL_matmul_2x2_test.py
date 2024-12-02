"""
==========================================================================
CGRARightAndBottomRTL_matmul_2x2_test.py
==========================================================================
Translation for 3x3 CGRA. The provided test is only used for a 2x2 matmul.

Author : Cheng Tan
  Date : Nov 19, 2024
"""


from pymtl3 import *
from pymtl3.passes.backends.verilog import VerilogTranslationPass
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)
from ..CGRAMemRightAndBottomRTL import CGRAMemRightAndBottomRTL
from ...fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from ...fu.single.AdderRTL import AdderRTL
from ...fu.single.BranchRTL import BranchRTL
from ...fu.single.CompRTL import CompRTL
from ...fu.single.LogicRTL import LogicRTL
from ...fu.single.MemUnitRTL import MemUnitRTL
from ...fu.single.MulRTL import MulRTL
from ...fu.single.PhiRTL import PhiRTL
from ...fu.single.SelRTL import SelRTL
from ...fu.double.SeqMulAdderRTL import SeqMulAdderRTL
from ...fu.single.ShifterRTL import ShifterRTL
from ...lib.basic.en_rdy.test_sinks import TestSinkRTL
from ...lib.basic.en_rdy.test_srcs import TestSrcRTL
from ...lib.messages import *
from ...lib.opt_type import *


#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

kMaxCycles = 12

class TestHarness(Component):

  def construct(s, DUT, FunctionUnit, fu_list, DataType, PredicateType,
                CtrlType, width, height, ctrl_mem_size, data_mem_size,
                src_opt, ctrl_waddr, preload_data, preload_const,
                expected_out):

    s.DataType = DataType
    s.expected_out = expected_out
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

    # s.sink_out = [TestSinkRTL(DataType, sink_out[i])
    #               for i in range(height - 1)]

    # for i in range(height - 1):
    #   connect(s.dut.send_data[i], s.sink_out[i].recv)

    for i in range(s.num_tiles):
      connect(s.src_opt[i].send, s.dut.recv_wopt[i])
      connect(s.ctrl_waddr[i].send, s.dut.recv_waddr[i])

  # Simulation terminates if the output memory contains
  # not less than the expected number of outputs.
  def done(s):
    num_valid_out = 0
    for data in s.dut.data_mem_east.reg_file.regs:
      if data != s.DataType(0, 0):
        num_valid_out += 1
    if num_valid_out >= len(s.expected_out):
      return True
    return False

  # Checks the output parity.
  def check_parity(s):
    for i in range(len(s.expected_out)):
      if s.expected_out[i] != s.dut.data_mem_east.reg_file.regs[i]:
        return False
    return True

  def line_trace(s):
    return s.dut.line_trace()

def run_sim(test_harness, enable_verification_pymtl,
            max_cycles = kMaxCycles):
  # test_harness.elaborate()
  test_harness.apply( DefaultPassGroup() )

  # Run simulation
  ncycles = 0
  print()
  print("{}:{}".format( ncycles, test_harness.line_trace()))
  if enable_verification_pymtl:
    while not test_harness.done():
      test_harness.sim_tick()
      ncycles += 1
      print("----------------------------------------------------")
      print("{}:{}".format( ncycles, test_harness.line_trace()))

    # Checks the output parity.
    assert test_harness.check_parity()

    # Checks timeout.
    assert ncycles < max_cycles
  else:
    while ncycles < max_cycles:
      test_harness.sim_tick()
      ncycles += 1
      print("----------------------------------------------------")
      print("{}:{}".format( ncycles, test_harness.line_trace()))

  test_harness.sim_tick()
  test_harness.sim_tick()
  test_harness.sim_tick()

def test_CGRA_systolic(cmdline_opts):
  num_tile_inports = 4
  num_tile_outports = 4
  num_xbar_inports = 6
  num_xbar_outports = 8
  ctrl_mem_size = 8
  width = 3
  height = 3
  RouteType = mk_bits(clog2(num_xbar_inports + 1))
  AddrType = mk_bits(clog2(ctrl_mem_size))
  num_tiles = width * height
  num_fu_in = 4
  DUT = CGRAMemRightAndBottomRTL
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

              CtrlType( OPT_NAH, b1(0), pickRegister, [
              RouteType(2), RouteType(0), RouteType(0), RouteType(0),
              RouteType(2), RouteType(0), RouteType(0), RouteType(0)]),
              CtrlType( OPT_NAH, b1(0), pickRegister, [
              RouteType(2), RouteType(0), RouteType(0), RouteType(0),
              RouteType(2), RouteType(0), RouteType(0), RouteType(0)]),
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

              CtrlType( OPT_NAH, b1(0), pickRegister, [
              RouteType(2), RouteType(0), RouteType(0), RouteType(0),
              RouteType(2), RouteType(0), RouteType(0), RouteType(0)]),
             ],

             # On tile 2 ([0, 2]).
             [CtrlType( OPT_NAH, b1(0), pickRegister, [
              RouteType(2), RouteType(0), RouteType(0), RouteType(0),
              RouteType(2), RouteType(0), RouteType(0), RouteType(0)]),
              CtrlType( OPT_NAH, b1(0), pickRegister, [
              RouteType(2), RouteType(0), RouteType(0), RouteType(0),
              RouteType(2), RouteType(0), RouteType(0), RouteType(0)]),
              CtrlType( OPT_NAH, b1(0), pickRegister, [
              RouteType(2), RouteType(0), RouteType(0), RouteType(0),
              RouteType(2), RouteType(0), RouteType(0), RouteType(0)]),
              CtrlType( OPT_NAH, b1(0), pickRegister, [
              RouteType(2), RouteType(0), RouteType(0), RouteType(0),
              RouteType(2), RouteType(0), RouteType(0), RouteType(0)]),

              CtrlType( OPT_NAH, b1(0), pickRegister, [
              RouteType(2), RouteType(0), RouteType(0), RouteType(0),
              RouteType(2), RouteType(0), RouteType(0), RouteType(0)]),
              CtrlType( OPT_NAH, b1(0), pickRegister, [
              RouteType(2), RouteType(0), RouteType(0), RouteType(0),
              RouteType(2), RouteType(0), RouteType(0), RouteType(0)]),
             ],

             # On tile 3 ([1, 0]).
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
             # On tile 4 ([1, 1]).
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

             # On tile 5 ([1, 2]).
             [CtrlType( OPT_NAH, b1(0), pickRegister, [
              RouteType(2), RouteType(0), RouteType(0), RouteType(0),
              RouteType(2), RouteType(0), RouteType(0), RouteType(0)]),
              CtrlType( OPT_NAH, b1(0), pickRegister, [
              RouteType(2), RouteType(0), RouteType(0), RouteType(0),
              RouteType(2), RouteType(0), RouteType(0), RouteType(0)]),
              CtrlType( OPT_NAH, b1(0), pickRegister, [
              RouteType(2), RouteType(0), RouteType(0), RouteType(0),
              RouteType(3), RouteType(0), RouteType(0), RouteType(0)]),
              CtrlType( OPT_STR_CONST, b1(0), pickRegister, [
              RouteType(2), RouteType(0), RouteType(0), RouteType(0),
              RouteType(3), RouteType(0), RouteType(0), RouteType(0)]),

              CtrlType( OPT_STR_CONST, b1(0), pickRegister, [
              RouteType(2), RouteType(0), RouteType(0), RouteType(0),
              RouteType(2), RouteType(0), RouteType(0), RouteType(0)]),
              CtrlType( OPT_NAH, b1(0), pickRegister, [
              RouteType(2), RouteType(0), RouteType(0), RouteType(0),
              RouteType(2), RouteType(0), RouteType(0), RouteType(0)]),
             ],

             # On tile 6 ([2, 0]).
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

             # On tile 7 ([2, 1]).
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
             ],

             # On tile 8 ([2, 2]).
             [CtrlType( OPT_NAH, b1(0), pickRegister, [
              RouteType(2), RouteType(0), RouteType(0), RouteType(0),
              RouteType(2), RouteType(0), RouteType(0), RouteType(0)]),
              CtrlType( OPT_NAH, b1(0), pickRegister, [
              RouteType(2), RouteType(0), RouteType(0), RouteType(0),
              RouteType(2), RouteType(0), RouteType(0), RouteType(0)]),
              CtrlType( OPT_NAH, b1(0), pickRegister, [
              RouteType(2), RouteType(0), RouteType(0), RouteType(0),
              RouteType(2), RouteType(0), RouteType(0), RouteType(0)]),
              CtrlType( OPT_NAH, b1(0), pickRegister, [
              RouteType(2), RouteType(0), RouteType(0), RouteType(0),
              RouteType(3), RouteType(0), RouteType(0), RouteType(0)]),

              CtrlType( OPT_STR_CONST, b1(0), pickRegister, [
              RouteType(2), RouteType(0), RouteType(0), RouteType(0),
              RouteType(3), RouteType(0), RouteType(0), RouteType(0)]),
              CtrlType( OPT_STR_CONST, b1(0), pickRegister, [
              RouteType(2), RouteType(0), RouteType(0), RouteType(0),
              RouteType(2), RouteType(0), RouteType(0), RouteType(0)]),
             ],
            ]
  
  preload_mem = [DataType(1, 1), DataType(2, 1), DataType(3, 1),
                 DataType(4, 1)]
  preload_const = [
                   # The offset address used for loading input activation.
                   # We use a shared data memory here, indicating global address
                   # space. Users can make each tile has its own address space.

                   # The last one is not useful for the first colum, which is just
                   # to make the length aligned.
                   [DataType(0, 1), DataType(1, 1), DataType(0, 0)],
                   # The first one is not useful for the second colum, which is just
                   # to make the length aligned.
                   [DataType(0, 0), DataType(2, 1), DataType(3, 1)],
                   # The third column is not actually necessary to perform activation
                   # loading nor storing parameters.
                   [DataType(0, 0), DataType(0, 0), DataType(0, 0)],

                   # Preloads weights. 3 items to align with the above const length.
                   # Duplication exists as the iter of the const queue automatically
                   # increment.
                   [DataType(2, 1), DataType(2, 1), DataType(2, 1)],
                   [DataType(4, 1), DataType(4, 1), DataType(4, 1)],
                   # The third column (except the bottom one) is used to store the
                   # accumulated results.
                   [DataType(0, 1), DataType(2, 1), DataType(0, 0)],

                   [DataType(6, 1), DataType(6, 1), DataType(6, 1)],
                   [DataType(8, 1), DataType(8, 1), DataType(8, 1)],
                   # The third column (except the bottom one) is used to store the
                   # accumulated results.
                   [DataType(1, 1), DataType(3, 1), DataType(0, 0)]]
  
  data_mem_size = len(preload_mem)

  """
  1 3      2 6     14 20
       x        =
  2 4      4 8     30 44
  """
  expected_out = [DataType(14, 1), DataType(30, 1), DataType(20, 1),
                  DataType(44, 1)]

  # When the max iterations are larger than the number of control signals,
  # enough ctrl_waddr needs to be provided to make execution (i.e., ctrl
  # read) continue.
  ctrl_waddr = [[AddrType(0), AddrType(1), AddrType(2), AddrType(3),
                 AddrType(4), AddrType(5)] for _ in range(num_tiles)]

  th = TestHarness(DUT, FunctionUnit, FuList, DataType, PredicateType,
                   CtrlType, width, height, ctrl_mem_size, data_mem_size,
                   src_opt, ctrl_waddr, preload_mem, preload_const,
                   expected_out)

  th.elaborate()
  th.dut.set_metadata(VerilogTranslationPass.explicit_module_name,
                      f'CGRAMemRightAndBottomRTL')
  # th.dut.set_metadata( VerilogVerilatorImportPass.vl_Wno_list,
  #                   ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
  #                    'ALWCOMBORDER'] )
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts=['dut'])

  enable_verification_pymtl = not (cmdline_opts['test_verilog'] or \
                                   cmdline_opts['dump_vcd'] or \
                                   cmdline_opts['dump_vtb'])
  run_sim(th, enable_verification_pymtl)

