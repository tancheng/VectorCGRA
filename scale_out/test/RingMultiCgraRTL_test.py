"""
==========================================================================
RingMultiCgraRTL_test.py
==========================================================================
Test cases for multi-CGRA with ring NoC.

Author : Cheng Tan
  Date : Dec 23, 2024
"""

from pymtl3.passes.backends.verilog import (VerilogVerilatorImportPass)
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)

from ..RingMultiCgraRTL import RingMultiCgraRTL
from ...fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from ...fu.single.AdderRTL import AdderRTL
from ...fu.single.MemUnitRTL import MemUnitRTL
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
                IntraCgraPktType, CgraPayloadType, CtrlType, InterCgraPktType,
                cgra_rows, cgra_columns, width, height, ctrl_mem_size,
                data_mem_size_global, data_mem_size_per_bank,
                num_banks_per_cgra, num_registers_per_reg_bank,
                src_ctrl_pkt, ctrl_steps, controller2addr_map,
                complete_signal_sink_out):

    s.num_cgras = cgra_rows * cgra_columns
    s.num_tiles = width * height

    s.src_ctrl_pkt = TestSrcRTL(IntraCgraPktType, src_ctrl_pkt)
    s.complete_signal_sink_out = TestSinkRTL(IntraCgraPktType, complete_signal_sink_out)

    s.dut = DUT(DataType, PredicateType, IntraCgraPktType, CgraPayloadType,
                CtrlType, InterCgraPktType, cgra_rows, cgra_columns,
                height, width, ctrl_mem_size, data_mem_size_global,
                data_mem_size_per_bank, num_banks_per_cgra,
                num_registers_per_reg_bank, ctrl_steps, ctrl_steps,
                FunctionUnit, FuList, controller2addr_map)

    # Connections
    s.src_ctrl_pkt.send //= s.dut.recv_from_cpu_pkt
    s.complete_signal_sink_out.recv //= s.dut.send_to_cpu_pkt

  def done(s):
    # FIXME: Enable ring simulation, i.e., return COMPLETE.
    # and s.complete_signal_sink_out.done()
    return s.src_ctrl_pkt.done()

  def line_trace(s):
    return s.dut.line_trace()

def test_homo_1x4(cmdline_opts):
  num_tile_inports  = 4
  num_tile_outports = 4
  num_fu_inports = 4
  num_fu_outports = 2
  num_routing_outports = num_tile_outports + num_fu_inports
  ctrl_mem_size = 6
  data_mem_size_global = 32
  data_mem_size_per_bank = 4
  num_banks_per_cgra = 2
  num_cgra_rows = 1
  num_cgra_columns = 4
  num_cgras = num_cgra_rows * num_cgra_columns
  width = 2
  height = 2
  TileInType = mk_bits(clog2(num_tile_inports + 1))
  FuInType = mk_bits(clog2(num_fu_inports + 1))
  FuOutType = mk_bits(clog2(num_fu_outports + 1))
  ctrl_addr_nbits = clog2(ctrl_mem_size)
  data_addr_nbits = clog2(data_mem_size_global)
  num_tiles = width * height
  DUT = RingMultiCgraRTL
  FunctionUnit = FlexibleFuRTL
  FuList = [MemUnitRTL, AdderRTL]
  data_nbits = 32
  DataType = mk_data(data_nbits, 1)
  PredicateType = mk_predicate(1, 1)
  num_registers_per_reg_bank = 16
  controller2addr_map = {
          0: [0, 7],
          1: [8, 15],
          2: [16, 23],
          3: [24, 31],
  }

  cgra_id_nbits = 2
  data_nbits = 32
  addr_nbits = clog2(data_mem_size_global)
  predicate_nbits = 1

  # IntraCgraPktType = \
  #       mk_intra_cgra_pkt(num_tiles,
  #                       cgra_id_nbits,
  #                       num_commands,
  #                       ctrl_mem_size,
  #                       num_ctrl_operations,
  #                       num_fu_inports,
  #                       num_fu_outports,
  #                       num_tile_inports,
  #                       num_tile_outports,
  #                       num_registers_per_reg_bank,
  #                       addr_nbits,
  #                       data_nbits,
  #                       predicate_nbits)

  # CtrlType = \
  #     mk_separate_reg_ctrl(num_ctrl_operations,
  #                          num_fu_inports,
  #                          num_fu_outports,
  #                          num_tile_inports,
  #                          num_tile_outports,
  #                          num_registers_per_reg_bank)

  # InterCgraPktType = mk_multi_cgra_noc_pkt(ncols = num_cgras,
  #                                    nrows = 1,
  #                                    ntiles = num_tiles,
  #                                    addr_nbits = data_addr_nbits,
  #                                    data_nbits = 32,
  #                                    predicate_nbits = 1,
  #                                    ctrl_actions = num_commands,
  #                                    ctrl_mem_size = ctrl_mem_size,
  #                                    ctrl_operations = num_ctrl_operations,
  #                                    ctrl_fu_inports = num_fu_inports,
  #                                    ctrl_fu_outports = num_fu_outports,
  #                                    ctrl_tile_inports = num_tile_inports,
  #                                    ctrl_tile_outports = num_tile_outports)

  CtrlType = \
      mk_separate_reg_ctrl(NUM_OPTS,
                           num_fu_inports,
                           num_fu_outports,
                           num_tile_inports,
                           num_tile_outports,
                           num_registers_per_reg_bank)

  CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
  DataAddrType = mk_bits(clog2(data_mem_size_global))

  CgraPayloadType = mk_cgra_payload(DataType,
                                    DataAddrType,
                                    CtrlType,
                                    CtrlAddrType)

  InterCgraPktType = mk_inter_cgra_pkt(num_cgra_columns,
                                       num_cgra_rows,
                                       num_tiles,
                                       CgraPayloadType)

  IntraCgraPktType = mk_new_intra_cgra_pkt(num_cgra_columns,
                                           num_cgra_rows,
                                           num_tiles,
                                           CgraPayloadType)

  pickRegister = [FuInType(x + 1) for x in range(num_fu_inports)]

  src_opt_per_tile = [[
      #           # dst_cgra_id src dst vc_id opq cmd_type    addr operation predicate
      # IntraCgraPktType(0,          0,  0,  0,    0,  CMD_CONFIG, 0,   OPT_INC,  b1(0),
      #                  pickRegister,
      #                  [TileInType(4), TileInType(3), TileInType(2), TileInType(1),
      #                   # TODO: make below as TileInType(5) to double check.
      #                   TileInType(0), TileInType(0), TileInType(0), TileInType(0)],

      #                  [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
      #                   FuOutType(1), FuOutType(1), FuOutType(1), FuOutType(1)]),
                     # src dst src_cgra dst_cgra
      IntraCgraPktType(0,  0,  0,       0,       0, 0, 0, 0,
                       payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                 ctrl = CtrlType(OPT_INC, 0,
                                                                 [FuInType(1), FuInType(0), FuInType(0), FuInType(0)],
                                                                 [TileInType(4), TileInType(3), TileInType(2), TileInType(1),
                                                                  TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                 [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                  FuOutType(1), FuOutType(1), FuOutType(1), FuOutType(1)]))),

      # IntraCgraPktType(0,      0,  0,  0,    0,  CMD_CONFIG, 1,   OPT_INC, b1(0),
      #                  pickRegister,
      #                  [TileInType(4), TileInType(3), TileInType(2), TileInType(1),
      #                   TileInType(0), TileInType(0), TileInType(0), TileInType(0)],

      #                  [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
      #                   FuOutType(1), FuOutType(1), FuOutType(1), FuOutType(1)]),

                     # src dst src_cgra dst_cgra
      IntraCgraPktType(0,  0,  0,       0,       0, 0, 0, 0,
                       payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                 ctrl = CtrlType(OPT_INC, 0,
                                                                 [FuInType(1), FuInType(0), FuInType(0), FuInType(0)],
                                                                 [TileInType(4), TileInType(3), TileInType(2), TileInType(1),
                                                                  TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                 [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                  FuOutType(1), FuOutType(1), FuOutType(1), FuOutType(1)]))),


      # IntraCgraPktType(0,      0,  0,  0,    0,  CMD_CONFIG, 2,   OPT_ADD, b1(0),
      #                  pickRegister,
      #                  [TileInType(4), TileInType(3), TileInType(2), TileInType(1),
      #                   TileInType(0), TileInType(0), TileInType(0), TileInType(0)],

      #                  [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
      #                   FuOutType(1), FuOutType(1), FuOutType(1), FuOutType(1)]),

                     # src dst src_cgra dst_cgra
      IntraCgraPktType(0,  0,  0,       0,       0, 0, 0, 0,
                       payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                 ctrl = CtrlType(OPT_ADD, 0,
                                                                 [FuInType(1), FuInType(2), FuInType(0), FuInType(0)],
                                                                 [TileInType(4), TileInType(3), TileInType(2), TileInType(1),
                                                                  TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                 [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                  FuOutType(1), FuOutType(1), FuOutType(1), FuOutType(1)]))),

      # IntraCgraPktType(0,      0,  0,  0,    0,  CMD_CONFIG, 3,   OPT_STR, b1(0),
      #                  pickRegister,
      #                  [TileInType(4), TileInType(3), TileInType(2), TileInType(1),
      #                   TileInType(0), TileInType(0), TileInType(0), TileInType(0)],

      #                  [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
      #                   FuOutType(1), FuOutType(1), FuOutType(1), FuOutType(1)]),

                     # src dst src_cgra dst_cgra
      IntraCgraPktType(0,  0,  0,       0,       0, 0, 0, 0,
                       payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 3,
                                                 ctrl = CtrlType(OPT_STR, 0,
                                                                 [FuInType(1), FuInType(2), FuInType(0), FuInType(0)],
                                                                 [TileInType(4), TileInType(3), TileInType(2), TileInType(1),
                                                                  TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                 [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                  FuOutType(1), FuOutType(1), FuOutType(1), FuOutType(1)]))),

      # IntraCgraPktType(0,      0,  0,  0,    0,  CMD_CONFIG, 4,   OPT_ADD, b1(0),
      #                  pickRegister,
      #                  [TileInType(4), TileInType(3), TileInType(2), TileInType(1),
      #                   TileInType(0), TileInType(0), TileInType(0), TileInType(0)],

      #                  [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
      #                   FuOutType(1), FuOutType(1), FuOutType(1), FuOutType(1)]),

                     # src dst src_cgra dst_cgra
      IntraCgraPktType(0,  0,  0,       0,       0, 0, 0, 0,
                       payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 4,
                                                 ctrl = CtrlType(OPT_ADD, 0,
                                                                 [FuInType(1), FuInType(2), FuInType(0), FuInType(0)],
                                                                 [TileInType(4), TileInType(3), TileInType(2), TileInType(1),
                                                                  TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                 [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                  FuOutType(1), FuOutType(1), FuOutType(1), FuOutType(1)]))),

      # IntraCgraPktType(0,      0,  0,  0,    0,  CMD_CONFIG, 5,   OPT_ADD, b1(0),
      #                  pickRegister,
      #                  [TileInType(4), TileInType(3), TileInType(2), TileInType(1),
      #                   TileInType(0), TileInType(0), TileInType(0), TileInType(0)],

      #                  [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
      #                   FuOutType(1), FuOutType(1), FuOutType(1), FuOutType(1)]),

                     # src dst src_cgra dst_cgra
      IntraCgraPktType(0,  0,  0,       0,       0, 0, 0, 0,
                       payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 5,
                                                 ctrl = CtrlType(OPT_ADD, 0,
                                                                 [FuInType(1), FuInType(2), FuInType(0), FuInType(0)],
                                                                 [TileInType(4), TileInType(3), TileInType(2), TileInType(1),
                                                                  TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                 [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                  FuOutType(1), FuOutType(1), FuOutType(1), FuOutType(1)]))),


      # This last one is for launching kernel.
      IntraCgraPktType(0, 0, 0, 0, 0, 0, 0, 0, payload = CgraPayloadType(CMD_LAUNCH))] for i in range(num_tiles)]

  # vc_id needs to be 1 due to the message might traverse across the date line via ring.
  expected_sink_out_pkt = [
                      # src  dst        src/dst cgra x/y
       IntraCgraPktType(0,   num_tiles, 0, 0, 0, 0, 0, 0, payload = CgraPayloadType(CMD_COMPLETE))]

  src_ctrl_pkt = []
  for opt_per_tile in src_opt_per_tile:
    src_ctrl_pkt.extend(opt_per_tile)

  th = TestHarness(DUT, FunctionUnit, FuList, DataType, PredicateType, IntraCgraPktType,
                   CgraPayloadType, CtrlType, InterCgraPktType, num_cgra_rows, num_cgra_columns,
                   width, height, ctrl_mem_size, data_mem_size_global,
                   data_mem_size_per_bank, num_banks_per_cgra,
                   num_registers_per_reg_bank, src_ctrl_pkt,
                   ctrl_mem_size, controller2addr_map, expected_sink_out_pkt)
  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                      ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                       'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)

