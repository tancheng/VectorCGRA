"""
==========================================================================
MeshMultiCgraTemplateRTL_test.py
==========================================================================
Translation for parameterizable multi CGRA based on the template.

Author : Yuqi Sun
  Date : Oct 4, 2025
"""

from pymtl3.passes.backends.verilog import (
    VerilogVerilatorImportPass,
    VerilogPlaceholderPass,
)
from pymtl3.passes.backends.verilog.translation.VerilogTranslationPass import VerilogTranslationPass
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)

from ..MeshMultiCgraTemplateRTL import MeshMultiCgraTemplateRTL
from ...fu.double.SeqMulAdderRTL import SeqMulAdderRTL
from ...fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from ...fu.float.FpAddRTL import FpAddRTL
from ...fu.float.FpMulRTL import FpMulRTL
from ...fu.single.AdderRTL import AdderRTL
from ...fu.single.GrantRTL import GrantRTL
from ...fu.single.CompRTL import CompRTL
from ...fu.single.LogicRTL import LogicRTL
from ...fu.single.MemUnitRTL import MemUnitRTL
from ...fu.single.MulRTL import MulRTL
from ...fu.single.PhiRTL import PhiRTL
from ...fu.single.RetRTL import RetRTL
from ...fu.single.SelRTL import SelRTL
from ...fu.single.ShifterRTL import ShifterRTL
from ...fu.vector.VectorAllReduceRTL import VectorAllReduceRTL
from ...fu.vector.VectorAdderComboRTL import VectorAdderComboRTL
from ...fu.vector.VectorMulComboRTL import VectorMulComboRTL
from ...lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ...lib.messages import *
from ...lib.opt_type import *
from ...lib.util.common import *


#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):
  def construct(s, DUT, FunctionUnit, FuList, DataType, PredicateType,
                IntraCgraPktType, CgraPayloadType, CtrlSignalType, NocPktType,
                data_nbits, cgra_rows, cgra_columns, width, height, ctrl_mem_size,
                data_mem_size_global, data_mem_size_per_bank,
                num_banks_per_cgra, num_registers_per_reg_bank,
                src_ctrl_pkt, src_query_pkt,
                ctrl_steps_per_iter,
                ctrl_steps_total,
                mem_access_is_combinational,
                controller2addr_map, expected_sink_out_pkt,
                cmp_func):

    s.num_terminals = cgra_rows * cgra_columns
    s.num_tiles = width * height

    s.src_ctrl_pkt = TestSrcRTL(IntraCgraPktType, src_ctrl_pkt)
    s.src_query_pkt = TestSrcRTL(IntraCgraPktType, src_query_pkt)

    s.expected_sink_out = TestSinkRTL(IntraCgraPktType, expected_sink_out_pkt, cmp_fn = cmp_func)

    id2ctrlMemSize_map = {
      0: 16,
      1: 16,
      2: 16,
      3: 16
    }
    id2cgraSize_map = {
      0: [4, 4],
      1: [4, 4],
      2: [4, 4],
      3: [4, 4]
    }
    # id2validTiles = {}
    # id2validLinks = {}
    # id2dataSPM = {}


    dataSPM = None
    tiles = []
    links = None

    for r in range(height):
      tiles.append([])
      for c in range(width):
        tiles[r].append(Tile(c, r))
    # Assumes first column tiles are connected to memory.
    dataSPM = DataSPM(width, width)

    links = [Link(None, None, 0, 0) for _ in range(16)]

    links[0].srcTile = None
    links[0].dstTile = tiles[0][0]
    links[0].srcPort = 0
    links[0].dstPort = PORT_WEST
    links[0].fromMem = True
    links[0].memPort = 0
    links[0].validatePorts()

    links[1].srcTile = tiles[0][0]
    links[1].dstTile = None
    links[1].srcPort = PORT_WEST
    links[1].dstPort = 0
    links[1].toMem = True
    links[1].memPort = 0
    links[1].validatePorts()

    links[2].srcTile = None
    links[2].dstTile = tiles[1][0]
    links[2].srcPort = 1
    links[2].dstPort = PORT_WEST
    links[2].fromMem = True
    links[2].memPort = 1
    links[2].validatePorts()

    links[3].srcTile = tiles[1][0]
    links[3].dstTile = None
    links[3].srcPort = PORT_WEST
    links[3].dstPort = 1
    links[3].toMem = True
    links[3].memPort = 1
    links[3].validatePorts()

    links[4].srcTile = tiles[0][0]
    links[4].dstTile = tiles[0][1]
    links[4].srcPort = PORT_EAST
    links[4].dstPort = PORT_WEST
    links[4].validatePorts()

    links[5].srcTile = tiles[0][1]
    links[5].dstTile = tiles[0][0]
    links[5].srcPort = PORT_WEST
    links[5].dstPort = PORT_EAST
    links[5].validatePorts()

    links[6].srcTile = tiles[1][0]
    links[6].dstTile = tiles[1][1]
    links[6].srcPort = PORT_EAST
    links[6].dstPort = PORT_WEST
    links[6].validatePorts()

    links[7].srcTile = tiles[1][1]
    links[7].dstTile = tiles[1][0]
    links[7].srcPort = PORT_WEST
    links[7].dstPort = PORT_EAST
    links[7].validatePorts()

    links[8].srcTile = tiles[0][0]
    links[8].dstTile = tiles[1][0]
    links[8].srcPort = PORT_NORTH
    links[8].dstPort = PORT_SOUTH
    links[8].validatePorts()

    links[9].srcTile = tiles[1][0]
    links[9].dstTile = tiles[0][0]
    links[9].srcPort = PORT_SOUTH
    links[9].dstPort = PORT_NORTH
    links[9].validatePorts()

    links[10].srcTile = tiles[0][1]
    links[10].dstTile = tiles[1][1]
    links[10].srcPort = PORT_NORTH
    links[10].dstPort = PORT_SOUTH
    links[10].validatePorts()

    links[11].srcTile = tiles[1][1]
    links[11].dstTile = tiles[0][1]
    links[11].srcPort = PORT_SOUTH
    links[11].dstPort = PORT_NORTH
    links[11].validatePorts()

    links[12].srcTile = tiles[0][0]
    links[12].dstTile = tiles[1][1]
    links[12].srcPort = PORT_NORTHEAST
    links[12].dstPort = PORT_SOUTHWEST
    links[12].validatePorts()

    links[13].srcTile = tiles[1][1]
    links[13].dstTile = tiles[0][0]
    links[13].srcPort = PORT_SOUTHWEST
    links[13].dstPort = PORT_NORTHEAST
    links[13].validatePorts()

    links[14].srcTile = tiles[0][1]
    links[14].dstTile = tiles[1][0]
    links[14].srcPort = PORT_NORTHWEST
    links[14].dstPort = PORT_SOUTHEAST
    links[14].validatePorts()

    links[15].srcTile = tiles[1][0]
    links[15].dstTile = tiles[0][1]
    links[15].srcPort = PORT_SOUTHEAST
    links[15].dstPort = PORT_NORTHWEST
    links[15].validatePorts()

    def handleReshape( t_tiles ):
      tiles = []
      for row in t_tiles:
        for t in row:
          tiles.append(t)
      return tiles

    tiles = handleReshape(tiles)

    id2validTiles = {
      0: tiles,
      1: tiles,
      2: tiles,
      3: tiles
    }
    id2validLinks = {
      0: links,
      1: links,
      2: links,
      3: links
    }
    id2dataSPM = {
      0: dataSPM,
      1: dataSPM,
      2: dataSPM,
      3: dataSPM
    }

    idTo2d_map = {
      0: [0, 0],
      1: [1, 0],
      2: [2, 0],
      3: [3, 0]
    }

    s.dut = DUT(DataType, PredicateType, IntraCgraPktType, 
                CgraPayloadType, CtrlSignalType, NocPktType, data_nbits, 
                cgra_rows, cgra_columns, height, width, 
                ctrl_mem_size, data_mem_size_global,
                data_mem_size_per_bank, num_banks_per_cgra,
                num_registers_per_reg_bank,
                ctrl_steps_per_iter, ctrl_steps_total, FunctionUnit, FuList,
                controller2addr_map, id2ctrlMemSize_map, id2cgraSize_map, 
                id2validTiles, id2validLinks, id2dataSPM, idTo2d_map,
                mem_access_is_combinational
                )

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

  # Runs simulation.
  ncycles = 0
  print("cycle {}:{}".format(ncycles, test_harness.line_trace()))
  while not test_harness.done() and ncycles < max_cycles:
    test_harness.sim_tick()
    ncycles += 1
    print("cycle {}:{}".format(ncycles, test_harness.line_trace()))

  # Checks timeout.
  assert ncycles < max_cycles

  test_harness.sim_tick()
  test_harness.sim_tick()
  test_harness.sim_tick()


def test_mesh_multi_cgra_universal(cmdline_opts, multiCgraParam = None):
  # num_tile_inports = 8
  # num_tile_outports = 8
  # num_fu_inports = 4
  # num_fu_outports = 2
  # num_routing_outports = num_tile_outports + num_fu_inports
  # ctrl_mem_size = 16
  num_cgra_rows = 2
  num_cgra_columns = 2
  num_x_tiles_per_cgra = 2
  num_y_tiles_per_cgra = 2
  num_banks_per_cgra = 2
  data_mem_size_per_bank = 32
  mem_access_is_combinational = True

  num_tile_inports = 8
  num_tile_outports = 8
  num_fu_inports = 4
  num_fu_outports = 2
  num_routing_outports = num_tile_outports + num_fu_inports
  ctrl_mem_size = 16
  num_cgras = num_cgra_rows * num_cgra_columns
  data_mem_size_global = data_mem_size_per_bank * num_banks_per_cgra * num_cgras
  num_tiles = num_x_tiles_per_cgra * num_y_tiles_per_cgra
  num_rd_tiles = num_x_tiles_per_cgra + num_y_tiles_per_cgra - 1
  TileInType = mk_bits(clog2(num_tile_inports + 1))
  FuInType = mk_bits(clog2(num_fu_inports + 1))
  FuOutType = mk_bits(clog2(num_fu_outports + 1))
  ctrl_addr_nbits = clog2(ctrl_mem_size)
  data_addr_nbits = clog2(data_mem_size_global)
  data_nbits = 32
  DataType = mk_data(data_nbits, 1)
  DataAddrType = mk_bits(clog2(data_mem_size_global))
  DUT = MeshMultiCgraTemplateRTL
  
  FunctionUnit = FlexibleFuRTL
  FuList = [AdderRTL,
            MulRTL,
            LogicRTL,
            ShifterRTL,
            PhiRTL,
            CompRTL,
            GrantRTL,
            MemUnitRTL,
            SelRTL,
            RetRTL,
            # FpAddRTL,
            # FpMulRTL,
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
                                       num_rd_tiles,
                                       CgraPayloadType)

  IntraCgraPktType = mk_intra_cgra_pkt(num_cgra_columns,
                                       num_cgra_rows,
                                       num_tiles,
                                       CgraPayloadType)

  src_ctrl_pkt = []
  expected_sink_out_pkt = []
  src_query_pkt = []
  ctrl_steps_per_iter = 0
  ctrl_steps_global = 0

  cmp_func = lambda a, b : a.payload.data == b.payload.data and a.payload.cmd == b.payload.cmd

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
        IntraCgraPktType(0, 0, 0, 1, 0, 0, 0, 1, payload = CgraPayloadType(CMD_CONST, data = DataType(34, 1))),
                      # src dst src_cgra dst_cgra
        IntraCgraPktType(0, 0,  0,       1,       0, 0, 0, 1,
                        payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                  ctrl = CtrlType(OPT_LD_CONST,
                                                                  [FuInType(0), FuInType(0), FuInType(0), FuInType(0)],
                                                                  [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                   TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                   TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                  [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                   FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                   # Note that we still need to set FU xbar.
                                                                   FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                  # 2 indicates the FU xbar port (instead of const queue or routing xbar port).
                                                                  write_reg_from = [b2(2), b2(0), b2(0), b2(0)],
                                                                  write_reg_idx = [RegIdxType(7), RegIdxType(0), RegIdxType(0), RegIdxType(0)]))),
        IntraCgraPktType(0,  0,  0,       1,       0, 0, 0, 1,
                        payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                  ctrl = CtrlType(OPT_INC,
                                                                  [FuInType(1), FuInType(0), FuInType(0), FuInType(0)],
                                                                  [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                   TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                   TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                  [FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                   FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                   FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                  read_reg_from = [b1(1), b1(0), b1(0), b1(0)],
                                                                  read_reg_idx = [RegIdxType(7), RegIdxType(0), RegIdxType(0), RegIdxType(0)]))),

        # Tile 2. Note that tile 0 and tile 2 can access the memory, as they are on
        # the first column.
        # Indicates the store address of 3.
        IntraCgraPktType(0, 1, 0, 1, 0, 0, 0, 1, payload = CgraPayloadType(CMD_CONST, data = DataType(3, 1))),
                      # src dst src_cgra dst_cgra
        IntraCgraPktType(0,  1,  0,       1,       0, 0, 0, 1,
                        payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                  ctrl = CtrlType(OPT_STR_CONST,
                                                                  [FuInType(1), FuInType(0), FuInType(0), FuInType(0)],
                                                                  [TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                   TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                   TileInType(2), TileInType(0), TileInType(0), TileInType(0)],
                                                                  [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                   FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                   FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),
        # Pre-configure per-tile total config count.
        # Only execute one operation (i.e., store) is enough for this tile.
        # If this is set more than 1, no `COMPLETE` signal would be set back
        # to CPU/test_harness.
        IntraCgraPktType(0, 1, 0, 1, 0, 0, 0, 1, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(1))),

        # For launching the two tiles.
        IntraCgraPktType(0, 0, 0, 1, 0, 0, 0, 1, payload = CgraPayloadType(CMD_LAUNCH)),
        IntraCgraPktType(0, 1, 0, 1, 0, 0, 0, 1, payload = CgraPayloadType(CMD_LAUNCH)),
      ]

  src_query_pkt = \
      [
        IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = 34)),
        IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = 3)),
      ]

  expected_sink_out_pkt = \
      [
                      # src  dst        src/dst cgra x/y
        IntraCgraPktType(0,   num_tiles, 1, 0, 0, 1, 0, 0, payload = CgraPayloadType(CMD_COMPLETE)),
        IntraCgraPktType(2,   num_tiles, 1, 0, 0, 1, 0, 0, payload = CgraPayloadType(CMD_COMPLETE)),
                                                                                                                      # Expected updated value.
        IntraCgraPktType(0,   num_tiles, 0, 0, 0, 0, 0, 0, payload = CgraPayloadType(CMD_LOAD_RESPONSE, data = DataType(0xff, 1), data_addr = 3)),
        IntraCgraPktType(0,   num_tiles, 1, 0, 1, 0, 0, 0, payload = CgraPayloadType(CMD_LOAD_RESPONSE, data = DataType(0xfe, 1), data_addr = 34)),
      ]

  # We only needs 2 steps to finish this test.
  ctrl_steps_per_iter = 2
  ctrl_steps_total = 2

  th = TestHarness(DUT, FunctionUnit, FuList, DataType, PredicateType, IntraCgraPktType,
                   CgraPayloadType, CtrlType, InterCgraPktType, data_nbits,
                   num_cgra_rows, num_cgra_columns,
                   num_x_tiles_per_cgra, num_y_tiles_per_cgra, ctrl_mem_size, data_mem_size_global,
                   data_mem_size_per_bank, num_banks_per_cgra,
                   num_registers_per_reg_bank, src_ctrl_pkt, src_query_pkt,
                   ctrl_steps_per_iter, ctrl_steps_total, mem_access_is_combinational,
                   controller2addr_map, expected_sink_out_pkt, cmp_func)
  # return th

  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                      ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                       'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)

class Tile:
  def __init__(s, dimX, dimY):
    s.disabled = False
    s.dimX = dimX
    s.dimY = dimY
    s.toMem = False
    s.fromMem = False
    s.invalidOutPorts = set()
    s.invalidInPorts = set()
    for i in range(PORT_DIRECTION_COUNTS):
      s.invalidOutPorts.add(i)
      s.invalidInPorts.add(i)

  def getInvalidInPorts(s):
    return s.invalidInPorts

  def getInvalidOutPorts(s):
    return s.invalidOutPorts

  def hasToMem(s):
    return s.toMem

  def hasFromMem(s):
    return s.fromMem

  def getIndex(s, TileList):
    if s.disabled:
      return -1
    index = 0
    for tile in TileList:
      if tile.dimY < s.dimY and not tile.disabled:
        index += 1
      elif tile.dimY == s.dimY and tile.dimX < s.dimX and not tile.disabled:
        index += 1
    return index

class DataSPM:
  def __init__(s, numOfReadPorts, numOfWritePorts):
    s.numOfReadPorts = numOfReadPorts
    s.numOfWritePorts = numOfWritePorts

  def getNumOfValidReadPorts(s):
    return s.numOfReadPorts

  def getNumOfValidWritePorts(s):
    return s.numOfWritePorts

class Link:
  def __init__(s, srcTile, dstTile, srcPort, dstPort):
    s.srcTile = srcTile
    s.dstTile = dstTile
    s.srcPort = srcPort
    s.dstPort = dstPort
    s.disabled = False
    s.toMem = False
    s.fromMem = False
    s.memPort = -1

  def getMemReadPort(s):
      return s.memPort

  def getMemWritePort(s):
      return s.memPort

  def isToMem(s):
    return s.toMem

  def isFromMem(s):
    return s.fromMem

  def validatePorts(s):
    if not s.toMem and not s.fromMem:
      s.srcTile.invalidOutPorts.remove(s.srcPort)
      s.dstTile.invalidInPorts.remove(s.dstPort)
    if s.toMem:
      s.srcTile.toMem = True
    if s.fromMem:
      s.dstTile.fromMem = True