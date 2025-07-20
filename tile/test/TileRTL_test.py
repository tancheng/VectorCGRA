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

from pymtl3.passes.backends.verilog import (VerilogVerilatorImportPass)
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)

from ..TileRTL import TileRTL
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
                CtrlType, ctrl_mem_size, data_mem_size, 3, 2, # 2 opts
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
  ctrl_mem_size = 3
  data_mem_size = 8
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
            GrantRTL,
            MemUnitRTL,
            SelRTL,
            ThreeMulAdderShifterRTL,
            VectorMulComboRTL,
            VectorAdderComboRTL]
  # 64-bit to satisfy the default bitwidth of vector FUs.
  DataType = mk_data(64, 1)
  PredicateType = mk_predicate(1, 1)
  cgra_id_nbits = 1
  data_nbits = 64
  data_mem_size_global = 16
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

  InterCgraPktType = mk_inter_cgra_pkt(num_cgra_columns,
                                       num_cgra_rows,
                                       num_tiles,
                                       CgraPayloadType)

  IntraCgraPktType = mk_intra_cgra_pkt(num_cgra_columns,
                                       num_cgra_rows,
                                       num_tiles,
                                       CgraPayloadType)

  src_ctrl_pkt = [
                # cgraid src dst vc_id opq cmd_type addr operation predicate
      IntraCgraPktType(0,  0,  0,       0,       0, 0, 0, 0,
                       payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                 ctrl = CtrlType(OPT_ADD, 0,
                                                                 [FuInType(1), FuInType(2), FuInType(0), FuInType(0)],
                                                                 [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                  TileInType(4), TileInType(3), TileInType(0), TileInType(0)],
                                                                 [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(1),
                                                                  FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),
      IntraCgraPktType(0,  0,  0,       0,       0, 0, 0, 0,
                       payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                 ctrl = CtrlType(OPT_SUB, 0,
                                                                 [FuInType(1), FuInType(2), FuInType(0), FuInType(0)],
                                                                 [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                  TileInType(4), TileInType(1), TileInType(0), TileInType(0)],
                                                                 [FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(1),
                                                                  FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

      # For constant 5, 7.
      IntraCgraPktType(0, 0, 0, 0, 0, 0, 0, 0, payload = CgraPayloadType(CMD_CONST, data = DataType(5, 1))),
      IntraCgraPktType(0, 0, 0, 0, 0, 0, 0, 0, payload = CgraPayloadType(CMD_CONST, data = DataType(7, 1))),

      IntraCgraPktType(0, 0, 0, 0, 0, 0, 0, 0, payload = CgraPayloadType(CMD_LAUNCH))]

  src_data = [[DataType(3, 1)],
              [],
              [DataType(4, 1)],
              [DataType(5, 1), DataType(7, 1)]]

  sink_out = [
              # 7 - 3 = 4.
              [DataType(4, 1)],
              [],
              [],
              # 5 + 4 = 9; 7 - 3 = 4.
              [DataType(9, 1), DataType(4, 1)]]
                                             # src  dst        src/dst cgra x/y
  complete_signal_sink_out = [IntraCgraPktType(0,   num_tiles, 0, 0, 0, 0, 0, 0, payload = CgraPayloadType(CMD_COMPLETE))]
#          IntraCgraPktType(0,           0,   num_tiles, 0,   0,  ctrl_action = CMD_COMPLETE)]

  th = TestHarness(DUT, FunctionUnit, FuList, DataType, PredicateType,
                   IntraCgraPktType, CgraPayloadType, CtrlType, ctrl_mem_size,
                   data_mem_size, num_fu_inports, num_fu_outports,
                   num_tile_inports, num_tile_outports,
                   num_registers_per_reg_bank, src_data,
                   src_ctrl_pkt, sink_out, num_tiles, complete_signal_sink_out)
  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                      ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                       'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)

def test_tile_multicycle_exclusive(cmdline_opts):
  num_tile_inports = 4
  num_tile_outports = 4
  num_fu_inports = 4
  num_fu_outports = 2
  num_routing_outports = num_fu_inports + num_tile_outports
  ctrl_mem_size = 3
  data_mem_size = 8
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
            GrantRTL,
            MemUnitRTL,
            SelRTL,
            ExclusiveDivRTL]
  # 64-bit to satisfy the default bitwidth of vector FUs.
  DataType = mk_data(32, 1)
  PredicateType = mk_predicate(1, 1)
  cgra_id_nbits = 1
  data_nbits = 32
  data_mem_size_global = 16
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

  InterCgraPktType = mk_inter_cgra_pkt(num_cgra_columns,
                                       num_cgra_rows,
                                       num_tiles,
                                       CgraPayloadType)

  IntraCgraPktType = mk_intra_cgra_pkt(num_cgra_columns,
                                       num_cgra_rows,
                                       num_tiles,
                                       CgraPayloadType)

  src_ctrl_pkt = [
                # cgraid src dst vc_id opq cmd_type addr operation predicate
      IntraCgraPktType(0,  0,  0,       0,       0, 0, 0, 0,
                       payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                 ctrl = CtrlType(OPT_DIV, 0,
                                                                 [FuInType(1), FuInType(2), FuInType(0), FuInType(0)],
                                                                 [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                  TileInType(4), TileInType(3), TileInType(0), TileInType(0)],
                                                                 [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(1),
                                                                  FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),
      IntraCgraPktType(0,  0,  0,       0,       0, 0, 0, 0,
                       payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                 ctrl = CtrlType(OPT_ADD, 0,
                                                                 [FuInType(1), FuInType(2), FuInType(0), FuInType(0)],
                                                                 [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                  TileInType(4), TileInType(1), TileInType(0), TileInType(0)],
                                                                 [FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(1),
                                                                  FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

      # For constant 5, 7.
      IntraCgraPktType(0, 0, 0, 0, 0, 0, 0, 0, payload = CgraPayloadType(CMD_CONST, data = DataType(5, 1))),
      IntraCgraPktType(0, 0, 0, 0, 0, 0, 0, 0, payload = CgraPayloadType(CMD_CONST, data = DataType(7, 1))),

      IntraCgraPktType(0, 0, 0, 0, 0, 0, 0, 0, payload = CgraPayloadType(CMD_LAUNCH))]

  src_data = [[DataType(3, 1)],
              [],
              [DataType(4, 1)],
              [DataType(12, 1), DataType(8, 1)]]

  sink_out = [
              # 8 + 3 = 11.
              [DataType(11, 1)],
              [],
              [],
              # 12 ÷ 4 = 3; 8 + 3 = 11.
              [DataType(3, 1), DataType(11, 1)]]
                                             # src  dst        src/dst cgra x/y
  complete_signal_sink_out = [IntraCgraPktType(0,   num_tiles, 0, 0, 0, 0, 0, 0, payload = CgraPayloadType(CMD_COMPLETE))]
#          IntraCgraPktType(0,           0,   num_tiles, 0,   0,  ctrl_action = CMD_COMPLETE)]

  th = TestHarness(DUT, FunctionUnit, FuList, DataType, PredicateType,
                   IntraCgraPktType, CgraPayloadType, CtrlType, ctrl_mem_size,
                   data_mem_size, num_fu_inports, num_fu_outports,
                   num_tile_inports, num_tile_outports,
                   num_registers_per_reg_bank, src_data,
                   src_ctrl_pkt, sink_out, num_tiles, complete_signal_sink_out)
  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                      ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                       'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)

def test_tile_multicycle_inclusive(cmdline_opts):
  num_tile_inports = 4
  num_tile_outports = 4
  num_fu_inports = 4
  num_fu_outports = 2
  num_routing_outports = num_fu_inports + num_tile_outports
  ctrl_mem_size = 3
  data_mem_size = 8
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
            GrantRTL,
            MemUnitRTL,
            SelRTL,
            InclusiveDivRTL]
  # 64-bit to satisfy the default bitwidth of vector FUs.
  DataType = mk_data(32, 1)
  PredicateType = mk_predicate(1, 1)
  cgra_id_nbits = 1
  data_nbits = 32
  data_mem_size_global = 16
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

  InterCgraPktType = mk_inter_cgra_pkt(num_cgra_columns,
                                       num_cgra_rows,
                                       num_tiles,
                                       CgraPayloadType)

  IntraCgraPktType = mk_intra_cgra_pkt(num_cgra_columns,
                                       num_cgra_rows,
                                       num_tiles,
                                       CgraPayloadType)

  src_ctrl_pkt = [
                # cgraid src dst vc_id opq cmd_type addr operation predicate
      IntraCgraPktType(0,  0,  0,       0,       0, 0, 0, 0,
                       payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                 ctrl = CtrlType(OPT_DIV_INCLUSIVE_START, 0,
                                                                 [FuInType(1), FuInType(2), FuInType(0), FuInType(0)],
                                                                 [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                  TileInType(4), TileInType(3), TileInType(0), TileInType(0)],
                                                                 [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(1),
                                                                  FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),
      
      IntraCgraPktType(0,  0,  0,       0,       0, 0, 0, 0,
                  payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                            ctrl = CtrlType(OPT_DIV_INCLUSIVE_END, 0,
                                                            [FuInType(1), FuInType(2), FuInType(0), FuInType(0)],
                                                            [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                            TileInType(4), TileInType(1), TileInType(0), TileInType(0)],
                                                            [FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(1),
                                                            FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),         
      # For constant 5, 7.
      IntraCgraPktType(0, 0, 0, 0, 0, 0, 0, 0, payload = CgraPayloadType(CMD_CONST, data = DataType(5, 1))),
      IntraCgraPktType(0, 0, 0, 0, 0, 0, 0, 0, payload = CgraPayloadType(CMD_CONST, data = DataType(7, 1))),

      IntraCgraPktType(0, 0, 0, 0, 0, 0, 0, 0, payload = CgraPayloadType(CMD_LAUNCH))]

  src_data = [[DataType(3, 1)],
              [],
              [DataType(4, 1)],
              [DataType(12, 1), DataType(8, 1)]]

  sink_out = [
              [DataType(3, 1)],
              [],
              [],
              # div start; div ends;
              [DataType(0, 1), DataType(3, 1)]]
                                             # src  dst        src/dst cgra x/y
  complete_signal_sink_out = [IntraCgraPktType(0,   num_tiles, 0, 0, 0, 0, 0, 0, payload = CgraPayloadType(CMD_COMPLETE))]
#          IntraCgraPktType(0,           0,   num_tiles, 0,   0,  ctrl_action = CMD_COMPLETE)]

  th = TestHarness(DUT, FunctionUnit, FuList, DataType, PredicateType,
                   IntraCgraPktType, CgraPayloadType, CtrlType, ctrl_mem_size,
                   data_mem_size, num_fu_inports, num_fu_outports,
                   num_tile_inports, num_tile_outports,
                   num_registers_per_reg_bank, src_data,
                   src_ctrl_pkt, sink_out, num_tiles, complete_signal_sink_out)
  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                      ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                       'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)
