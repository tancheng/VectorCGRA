"""
==========================================================================
MeshMultiCgraTemplateRTL_test.py
==========================================================================
Translation for parameterizable multi-CGRA based on the template.
"""

from pymtl3.passes.backends.verilog import (
    VerilogVerilatorImportPass,
    VerilogPlaceholderPass,
)
from pymtl3.passes.backends.verilog.translation.VerilogTranslationPass import VerilogTranslationPass
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)

from ..MeshMultiCgraRTL import MeshMultiCgraRTL
from ...fu.double.SeqMulAdderRTL import SeqMulAdderRTL
from ...fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from ...fu.float.FpAddRTL import FpAddRTL
from ...fu.float.FpMulRTL import FpMulRTL
from ...fu.single.AdderRTL import AdderRTL
from ...fu.single.BranchRTL import BranchRTL
from ...fu.single.CompRTL import CompRTL
from ...fu.single.LogicRTL import LogicRTL
from ...fu.single.MemUnitRTL import MemUnitRTL
from ...fu.single.MulRTL import MulRTL
from ...fu.single.PhiRTL import PhiRTL
from ...fu.single.SelRTL import SelRTL
from ...fu.single.ShifterRTL import ShifterRTL
from ...fu.vector.VectorAdderComboRTL import VectorAdderComboRTL
from ...fu.vector.VectorMulComboRTL import VectorMulComboRTL
from ...lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ...lib.messages import *
from ...lib.opt_type import *


#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):
  def construct(s, DUT, FunctionUnit, FuList, DataType, PredicateType,
                IntraCgraPktType, CgraPayloadType, CtrlSignalType, NocPktType,
                cgra_rows, cgra_columns, width, height, ctrl_mem_size,
                data_mem_size_global, data_mem_size_per_bank,
                num_banks_per_cgra, num_registers_per_reg_bank,
                src_ctrl_pkt, src_query_pkt, ctrl_steps,
                controller2addr_map, expected_sink_out_pkt):

    s.num_terminals = cgra_rows * cgra_columns
    s.num_tiles = width * height

    s.src_ctrl_pkt = TestSrcRTL(IntraCgraPktType, src_ctrl_pkt)
    s.src_query_pkt = TestSrcRTL(IntraCgraPktType, src_query_pkt)

    cmp_fn = lambda a, b : a.payload.data == b.payload.data and a.payload.cmd == b.payload.cmd
    s.expected_sink_out = TestSinkRTL(IntraCgraPktType, expected_sink_out_pkt, cmp_fn = cmp_fn)

    s.dut = DUT(DataType, PredicateType, IntraCgraPktType, CgraPayloadType,
                CtrlSignalType, NocPktType, cgra_rows, cgra_columns,
                height, width, ctrl_mem_size, data_mem_size_global,
                data_mem_size_per_bank, num_banks_per_cgra,
                num_registers_per_reg_bank, ctrl_steps, ctrl_steps,
                FunctionUnit, FuList, controller2addr_map)

    # Connections
    s.expected_sink_out.recv //= s.dut.send_to_cpu_pkt

    complete_count_value = \
            sum(1 for pkt in expected_sink_out_pkt \
                if pkt.payload.cmd == CMD_COMPLETE)

    CompleteCountType = mk_bits(clog2(complete_count_value + 1))
    s.complete_count = Wire(CompleteCountType)

    @update
    def conditional_issue_ctrl_or_query():
      s.dut.recv_from_cpu_pkt.val @= s.src_ctrl_pkt.send.val
      s.dut.recv_from_cpu_pkt.msg @= s.src_ctrl_pkt.send.msg
      s.src_ctrl_pkt.send.rdy @= 0
      s.src_query_pkt.send.rdy @= 0
      if (s.complete_count >= complete_count_value) & \
         ~s.src_ctrl_pkt.send.val:
        s.dut.recv_from_cpu_pkt.val @= s.src_query_pkt.send.val
        s.dut.recv_from_cpu_pkt.msg @= s.src_query_pkt.send.msg
        s.src_query_pkt.send.rdy @= s.dut.recv_from_cpu_pkt.rdy
      else:
        s.src_ctrl_pkt.send.rdy @= s.dut.recv_from_cpu_pkt.rdy
  
    @update_ff
    def update_complete_count():
      if s.reset:
        s.complete_count <<= 0
      else:
        if s.expected_sink_out.recv.val & s.expected_sink_out.recv.rdy & \
           (s.complete_count < complete_count_value):
          s.complete_count <<= s.complete_count + CompleteCountType(1)

  def done(s):
    return s.src_ctrl_pkt.done() and s.src_query_pkt.done() and \
           s.expected_sink_out.done()

  def line_trace(s):
    return s.dut.line_trace()

def run_sim(test_harness, max_cycles = 200):
  test_harness.apply(DefaultPassGroup())
  test_harness.sim_reset()

  # Run simulation

  ncycles = 0
  print("cycle {}:{}".format(ncycles, test_harness.line_trace()))
  while not test_harness.done() and ncycles < max_cycles:
    test_harness.sim_tick()
    ncycles += 1
    print("cycle {}:{}".format(ncycles, test_harness.line_trace()))

  # Check timeout
  assert ncycles < max_cycles

  test_harness.sim_tick()
  test_harness.sim_tick()
  test_harness.sim_tick()

def initialize_test_harness(cmdline_opts,
                            num_cgra_rows = 2,
                            num_cgra_columns = 2,
                            num_x_tiles_per_cgra = 2,
                            num_y_tiles_per_cgra = 2,
                            num_banks_per_cgra = 2,
                            data_mem_size_per_bank = 16,
                            multiCgraParam = None):
  # TODO
  # Read properties from multiCgraParam
  num_cgra_rows = multiCgraParam.rows if multiCgraParam != None else num_cgra_rows
  num_cgra_columns = multiCgraParam.cols if multiCgraParam != None else num_cgra_columns
  num_x_tiles_per_cgra = multiCgraParam.cgras[0][0].columns if multiCgraParam != None else num_x_tiles_per_cgra
  num_y_tiles_per_cgra = multiCgraParam.cgras[0][0].rows if multiCgraParam != None else num_x_tiles_per_cgra
  ctrl_mem_size = multiCgraParam.cgras[0][0].configMemSize if multiCgraParam != None else 16
  print(f"""[LOG] num_cgra_rows: {num_cgra_rows}, num_cgra_columns: {num_cgra_columns}, 
                  num_x_tiles_per_cgra: {num_x_tiles_per_cgra}, num_y_tiles_per_cgra: {num_y_tiles_per_cgra},
                  ctrl_mem_size: {ctrl_mem_size}""")

  num_tile_inports = 4
  num_tile_outports = 4
  num_fu_inports = 4
  num_fu_outports = 2
  num_routing_outports = num_tile_outports + num_fu_inports
  
  num_cgras = num_cgra_rows * num_cgra_columns
  data_mem_size_global = data_mem_size_per_bank * num_banks_per_cgra * num_cgras
  num_tiles = num_x_tiles_per_cgra * num_y_tiles_per_cgra
  TileInType = mk_bits(clog2(num_tile_inports + 1))
  FuInType = mk_bits(clog2(num_fu_inports + 1))
  FuOutType = mk_bits(clog2(num_fu_outports + 1))
  ctrl_addr_nbits = clog2(ctrl_mem_size)
  data_addr_nbits = clog2(data_mem_size_global)
  data_nbits = 32
  DataType = mk_data(data_nbits, 1)
  DataAddrType = mk_bits(clog2(data_mem_size_global))
  DUT = MeshMultiCgraRTL
  FunctionUnit = FlexibleFuRTL
  FuList = [AdderRTL,
            MulRTL,
            LogicRTL,
            ShifterRTL,
            PhiRTL,
            CompRTL,
            BranchRTL,
            MemUnitRTL,
            SelRTL,
            FpAddRTL,
            FpMulRTL,
            SeqMulAdderRTL,
            # PrlMulAdderRTL, FIXME: https://github.com/tancheng/VectorCGRA/issues/123
            VectorMulComboRTL,
            VectorAdderComboRTL]
  predicate_nbits = 1
  PredicateType = mk_predicate(1, 1)
  num_registers_per_reg_bank = 16
  per_cgra_data_size = int(data_mem_size_global / num_cgras)
  controller2addr_map = {}
  for i in range(num_cgras):
    controller2addr_map[i] = [i * per_cgra_data_size,
                              (i + 1) * per_cgra_data_size - 1]
  print("[LOG] controller2addr_map: ", controller2addr_map)

  RegIdxType = mk_bits(clog2(num_registers_per_reg_bank))

  cgra_id_nbits = clog2(num_cgras)

  CtrlType = mk_ctrl(num_fu_inports,
                     num_fu_outports,
                     num_tile_inports,
                     num_tile_outports,
                     num_registers_per_reg_bank)

  CtrlAddrType = mk_bits(clog2(ctrl_mem_size))

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

  src_ctrl_pkt = []
  expected_sink_out_pkt = []
  src_query_pkt = []
  ctrl_steps = 0

  '''
  Creates test performing load -> inc -> store on cgra 2. Specifically,
  cgra 2 tile 0 performs `load` on memory address 34, and stores the result (0xfe) in register 7.
  cgra 2 tile 0 read data from register 7 and performs `inc` (0xfe -> 0xff), and sends result to tile 2.
  cgra 2 tile 2 waits for the data from tile 0, and performs stores (0xff) to memory address 3.
  Note that address 34 is in cgra 1's sram bank 0, while address 3 is in cgra 0's sram bank 0,
  therefore, all the memory addresses from cgra 2 are remote.
  '''
  src_ctrl_pkt = \
      [
        # Preloads data.                                            address 34 belongs to cgra 1 (not cgra 0)
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(254, 1), data_addr = 34)),
        # Tile 0.
        # Indicates the load address of 2.    dst_cgra_y
        IntraCgraPktType(0, 0, 0, 2, 0, 0, 0, 1, payload = CgraPayloadType(CMD_CONST, data = DataType(34, 1))),
                      # src dst src_cgra dst_cgra
        IntraCgraPktType(0,  0,  0,       2,       0, 0, 0, 1,
                        payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                  ctrl = CtrlType(OPT_LD_CONST, 0,
                                                                  [FuInType(0), FuInType(0), FuInType(0), FuInType(0)],
                                                                  [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                    TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                  [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                    # Note that we still need to set FU xbar.
                                                                    FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                  # 2 indicates the FU xbar port (instead of const queue or routing xbar port).
                                                                  write_reg_from = [b2(2), b2(0), b2(0), b2(0)],
                                                                  write_reg_idx = [RegIdxType(7), RegIdxType(0), RegIdxType(0), RegIdxType(0)]))),
        IntraCgraPktType(0,  0,  0,       2,       0, 0, 0, 1,
                        payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                  ctrl = CtrlType(OPT_INC, 0,
                                                                  [FuInType(1), FuInType(0), FuInType(0), FuInType(0)],
                                                                  [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                    TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                  [FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                    FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                  read_reg_from = [b1(1), b1(0), b1(0), b1(0)],
                                                                  read_reg_idx = [RegIdxType(7), RegIdxType(0), RegIdxType(0), RegIdxType(0)]))),

        # Tile 2. Note that tile 0 and tile 2 can access the memory, as they are on
        # the first column.
        # Indicates the store address of 3.
        IntraCgraPktType(0, 2, 0, 2, 0, 0, 0, 1, payload = CgraPayloadType(CMD_CONST, data = DataType(3, 1))),
                      # src dst src_cgra dst_cgra
        IntraCgraPktType(0,  2,  0,       2,       0, 0, 0, 1,
                        payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                  ctrl = CtrlType(OPT_STR_CONST, 0,
                                                                  [FuInType(1), FuInType(0), FuInType(0), FuInType(0)],
                                                                  [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                    TileInType(2), TileInType(0), TileInType(0), TileInType(0)],
                                                                  [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                    FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),
        # Pre-configure per-tile total config count.
        # Only execute one operation (i.e., store) is enough for this tile.
        # If this is set more than 1, no `COMPLETE` signal would be set back
        # to CPU/test_harness.
        IntraCgraPktType(0, 2, 0, 2, 0, 0, 0, 1, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(1))),

        # For launching the two tiles.
        IntraCgraPktType(0, 0, 0, 2, 0, 0, 0, 1, payload = CgraPayloadType(CMD_LAUNCH)),
        IntraCgraPktType(0, 2, 0, 2, 0, 0, 0, 1, payload = CgraPayloadType(CMD_LAUNCH)),
      ]

  src_query_pkt = \
      [
        IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = 34)),
        IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = 3)),
      ]

  expected_sink_out_pkt = \
      [
                      # src  dst        src/dst cgra x/y
        IntraCgraPktType(0,   num_tiles, 2, 0, 0, 1, 0, 0, payload = CgraPayloadType(CMD_COMPLETE)),
        IntraCgraPktType(2,   num_tiles, 2, 0, 0, 1, 0, 0, payload = CgraPayloadType(CMD_COMPLETE)),
                                                                                                                      # Expected updated value.
        IntraCgraPktType(0,   num_tiles, 0, 0, 0, 0, 0, 0, payload = CgraPayloadType(CMD_LOAD_RESPONSE, data = DataType(0xff, 1), data_addr = 3)),
        IntraCgraPktType(0,   num_tiles, 1, 0, 1, 0, 0, 0, payload = CgraPayloadType(CMD_LOAD_RESPONSE, data = DataType(0xfe, 1), data_addr = 34)),
      ]

  # We only needs 2 steps to finish this test.
  ctrl_steps = 2

  th = TestHarness(DUT, FunctionUnit, FuList, DataType, PredicateType, IntraCgraPktType,
                   CgraPayloadType, CtrlType, InterCgraPktType, num_cgra_rows, num_cgra_columns,
                   num_x_tiles_per_cgra, num_y_tiles_per_cgra, ctrl_mem_size, data_mem_size_global,
                   data_mem_size_per_bank, num_banks_per_cgra,
                   num_registers_per_reg_bank, src_ctrl_pkt, src_query_pkt,
                   ctrl_steps, controller2addr_map, expected_sink_out_pkt)
  return th


def test_multi_CGRA_universal(cmdline_opts, multiCgraParam = None):
  th = initialize_test_harness(cmdline_opts,
                               num_cgra_rows = 2,
                               num_cgra_columns = 2,
                               num_x_tiles_per_cgra = 2,
                               num_y_tiles_per_cgra = 2,
                               num_banks_per_cgra = 2,
                               data_mem_size_per_bank = 16,
                               multiCgraParam = multiCgraParam)

  th.elaborate()
  # TODO
  # Use CgraTemplateRTL for now, to change(CGRA-Flow, mflowgen accordingly) once multi-cgra works good.
  th.dut.set_metadata(VerilogTranslationPass.explicit_module_name,
                      f'CgraTemplateRTL')
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                      ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                       'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)
