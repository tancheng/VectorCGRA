"""
==========================================================================
TileWithContextSwitchRTL_test.py
==========================================================================
Test cases for TileWithContextSwitchRTL.
Command:

Author : Yufei Yang
  Date : Sep 24, 2025
"""

from pymtl3.passes.backends.verilog import (VerilogVerilatorImportPass)
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)

from ..TileWithContextSwitchRTL import TileWithContextSwitchRTL
from ...fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from ...fu.single.AdderRTL import AdderRTL
from ...fu.single.GrantRTL import GrantRTL
from ...fu.single.CompRTL import CompRTL
from ...fu.single.LogicRTL import LogicRTL
from ...fu.single.MemUnitRTL import MemUnitRTL
from ...fu.single.MulRTL import MulRTL
from ...fu.single.PhiRTL import PhiRTL
from ...fu.single.SelRTL import SelRTL
from ...fu.single.ShifterRTL import ShifterRTL
from ...fu.single.ExclusiveDivRTL import ExclusiveDivRTL
from ...fu.single.InclusiveDivRTL import InclusiveDivRTL
from ...fu.triple.ThreeMulAdderShifterRTL import ThreeMulAdderShifterRTL
from ...fu.vector.VectorAdderComboRTL import VectorAdderComboRTL
from ...fu.vector.VectorMulComboRTL import VectorMulComboRTL
from ...lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ...lib.cmd_type import *
from ...lib.messages import *
from ...lib.opt_type import *

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, DUT, FunctionUnit, FuList, DataType, PredicateType,
                IntraCgraPktType, CgraPayloadType, CtrlType,
                data_nbits,
                ctrl_mem_size, data_mem_size, num_fu_inports,
                num_fu_outports, num_tile_inports,
                num_tile_outports, num_registers_per_reg_bank, src_data,
                src_ctrl_pkt, sink_out, num_tiles, complete_signal_sink_out):

    s.num_tile_inports = num_tile_inports
    s.num_tile_outports = num_tile_outports

    s.src_ctrl_pkt = TestSrcRTL(IntraCgraPktType, src_ctrl_pkt)
    s.src_data = [TestSrcRTL(DataType, src_data[i])
                  for i in range(num_tile_inports)]
    s.sink_out = [TestSinkRTL(DataType, sink_out[i])
                  for i in range(num_tile_outports)]
    s.complete_signal_sink_out = TestSinkRTL(IntraCgraPktType, complete_signal_sink_out)

    s.dut = DUT(DataType, PredicateType, IntraCgraPktType, CgraPayloadType,
                CtrlType, data_nbits, ctrl_mem_size, data_mem_size, 1, 6, 
                num_fu_inports, num_fu_outports, num_tile_inports,
                num_tile_outports, 1, num_tiles,
                num_registers_per_reg_bank,
                FunctionUnit, FuList)

    # Connects tile id.
    s.dut.cgra_id //= 0
    s.dut.tile_id //= 0

    connect(s.src_ctrl_pkt.send, s.dut.recv_from_controller_pkt)
    s.complete_signal_sink_out.recv //= s.dut.send_to_controller_pkt

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

    if not s.complete_signal_sink_out.done():
        return False

    return True

  def line_trace(s):
    return s.dut.line_trace()

def test_tile_alu(cmdline_opts):
  num_tile_inports = 4
  num_tile_outports = 4
  num_fu_inports = 4
  num_fu_outports = 2
  num_routing_outports = num_fu_inports + num_tile_outports
  ctrl_mem_size = 2
  data_mem_size_global = 16
  num_cgra_rows = 1
  num_cgra_columns = 1
  num_cgras = num_cgra_rows * num_cgra_columns
  num_tiles = 4
  num_commands = NUM_CMDS
  num_ctrl_operations = NUM_OPTS
  num_registers_per_reg_bank = 16
  TileInType = mk_bits(clog2(num_tile_inports + 1))
  FuInType = mk_bits(clog2(num_fu_inports + 1))
  FuOutType = mk_bits(clog2(num_fu_outports + 1))
  DUT = TileWithContextSwitchRTL
  FunctionUnit = FlexibleFuRTL
  # FuList = [AdderRTL, MulRTL, MemUnitRTL]
  FuList = [AdderRTL,
            MulRTL,
            LogicRTL,
            ShifterRTL,
            PhiRTL,
            CompRTL,
            GrantRTL,
            MemUnitRTL,
            SelRTL,
            ThreeMulAdderShifterRTL,
            VectorMulComboRTL,
            VectorAdderComboRTL]
  # 64-bit to satisfy the default bitwidth of vector FUs.
  data_nbits = 64
  DataType = mk_data(data_nbits, 1)
  PredicateType = mk_predicate(1, 1)
  cgra_id_nbits = 1
  addr_nbits = clog2(data_mem_size_global)
  predicate_nbits = 1

  CtrlType = mk_ctrl(num_fu_inports,
                     num_fu_outports,
                     num_tile_inports,
                     num_tile_outports,
                     num_registers_per_reg_bank)

  CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
  DataAddrType = mk_bits(addr_nbits)

  CgraPayloadType = mk_cgra_payload(DataType,
                                    DataAddrType,
                                    CtrlType,
                                    CtrlAddrType)

  IntraCgraPktType = mk_intra_cgra_pkt(num_cgra_columns,
                                       num_cgra_rows,
                                       num_tiles,
                                       CgraPayloadType)

  src_ctrl_pkt = [
      # Loads the config to tile's ctrl mem, we use 6 same configs that only contain PHI_CONST for simplcity.
                     # src dst src_cgra_id dst_cgra_id cgra_src/dst_x/y
      IntraCgraPktType(0,  0,  0,          0,          0, 0, 0, 0,
                       payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                 ctrl = CtrlType(OPT_PHI_CONST,
                                                                 [FuInType(1), FuInType(0), FuInType(0), FuInType(0)],
                                                                 [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                  TileInType(1), TileInType(0), TileInType(0), TileInType(0)],
                                                                 [FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                  FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),
      # PHI_CONST should firstly output the constant 0 to indicate the iteration 0.
      IntraCgraPktType(0, 0, 0, 0, 0, 0, 0, 0, payload = CgraPayloadType(CMD_CONST, data = DataType(0, 1))),
      # Sets the ctrl signal address of the initail PHI node to 0, as we only have one ctrl signal.
      IntraCgraPktType(0, 0, 0, 0, 0, 0, 0, 0, payload = CgraPayloadType(CMD_RECORD_PHI_ADDR, ctrl_addr = CtrlAddrType(0))),
      # Launches the execution.
      IntraCgraPktType(0, 0, 0, 0, 0, 0, 0, 0, payload = CgraPayloadType(CMD_LAUNCH)),
      # Clock cycle 1, executes normally, we use CMD_CONST to simulate this normal execution.
      IntraCgraPktType(0, 0, 0, 0, 0, 0, 0, 0, payload = CgraPayloadType(CMD_CONST)),
      # Clock cycle 2, sends the pausing command.
      IntraCgraPktType(0, 0, 0, 0, 0, 0, 0, 0, payload = CgraPayloadType(CMD_PAUSE)),
      # Clock cycle 3, executes normally but under the pauing status, we use CMD_CONST to simulate this normal execution.
      IntraCgraPktType(0, 0, 0, 0, 0, 0, 0, 0, payload = CgraPayloadType(CMD_CONST)),
      # Clock cycle 4, sends the resuming command.
      IntraCgraPktType(0, 0, 0, 0, 0, 0, 0, 0, payload = CgraPayloadType(CMD_RESUME)),
      # Clock cycle 5, executes normally but under the resuming status, we use CMD_CONST to simulate this normal execution.
      IntraCgraPktType(0, 0, 0, 0, 0, 0, 0, 0, payload = CgraPayloadType(CMD_CONST)),
      # Clock cycle 6, executes normally, we use CMD_CONST to simulate this normal execution.
      IntraCgraPktType(0, 0, 0, 0, 0, 0, 0, 0, payload = CgraPayloadType(CMD_CONST))
      ]

  src_data = [# Data of the 1st port.
              [
                  # Clock cycle 1: Any value as PHI_CONST will firstly output a const 0 to represent iteration 0.
                  DataType(999, 1),
                  # Clock cycle 2: DataType(1, 1) to simulate i+=1.
                  DataType(1, 1),
                  # Clock cycle 3: DataType(2, 1) to simulate i+=1 even under the pausing status.
                  DataType(2, 1),
                  # Clock cycle 4: DataType(3, 1) to simulate i+=1 even under the pausing status.
                  DataType(3, 1),
                  # Clock cycle 5: DataType(4, 1) to simulate i+=1 even under the resuming status.
                  DataType(4, 1),
                  # Clock cycle 6: DataType(3, 1) to simulate i+=1 after resuming the progress.
                  DataType(3, 1),
              ],
              # Nothing for the 2nd, 3rd, and 4th ports.
              [],
              [],
              []]

  sink_out = [# output of the 1st port.
              [
                  # Clock cycle 1: PHI_CONST will firstly output the const to represent iteration 0.
                  DataType(0, 1),
                  # Clock cycle 2: DataType(1, 1) for iteration 1.
                  DataType(1, 1),
                  # Clock cycle 3: DataType(2, 0), as iteration 2 cannot be initiated during the pausing status.
                  DataType(0, 0),
                  # Clock cycle 4: DataType(3, 0), as iteration 3 cannot be initiated during the pausing status.
                  DataType(0, 0),
                  # Clock cycle 5: Resumes the recorded progress DataType(2, 1) to continune iteration 2.
                  DataType(2, 1),
                  # Clock cycle 6: DataType(3, 1) to continue iteration 3.
                  DataType(3, 1)
                  ],
              # Nothing for the 2nd, 3rd, and 4th ports.
              [],
              [],
              []]

                                             # src  dst        src/dst cgra x/y
  complete_signal_sink_out = [IntraCgraPktType(0,   num_tiles, 0, 0,   0, 0, 0, 0, payload = CgraPayloadType(CMD_COMPLETE))]
#          IntraCgraPktType(0,           0,   num_tiles, 0,   0,  ctrl_action = CMD_COMPLETE)]

  th = TestHarness(DUT, FunctionUnit, FuList, DataType, PredicateType,
                   IntraCgraPktType, CgraPayloadType, CtrlType,
                   data_nbits, ctrl_mem_size,
                   data_mem_size_global, num_fu_inports, num_fu_outports,
                   num_tile_inports, num_tile_outports,
                   num_registers_per_reg_bank, src_data,
                   src_ctrl_pkt, sink_out, num_tiles, complete_signal_sink_out)
  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                      ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                       'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)

