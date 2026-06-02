"""
==========================================================================
CgraDmaRTL_test.py
==========================================================================
"""

from pymtl3 import *

from ..CgraDmaRTL import CgraDmaRTL
from ...fu.single.AdderRTL import AdderRTL
from ...fu.single.MemUnitRTL import MemUnitRTL
from ...fu.single.RetRTL import RetRTL
from ...lib.messages import *
from ...lib.opt_type import *
from ...lib.util.cgra.DataSPM import DataSPM
from ...lib.util.cgra.Tile import Tile
from ...lib.util.cgra.cgra_helper import get_links
from ...mem.dma.DmaEngineRTL import DMA_MVIN, DMA_MVOUT


def test_cgra_dma_mvin_to_local_spm():
  """
  Integration test for the CgraDmaRTL wrapper.
  It simulates a DMA MVIN command that moves data from external DRAM into
  the CGRA's dataSPM. It then checks the SPM contents to ensure the
  transfer was successful.
  """
  ctrl_mem_size = 8
  data_mem_size_global = 64
  data_mem_size_per_bank = 16
  num_banks_per_cgra = 4
  num_registers_per_reg_bank = 16
  num_ctrl = 1
  total_steps = 1

  DataType = mk_data(32, 1)
  WordType = mk_bits(32)
  DataAddrType = mk_bits(clog2(data_mem_size_global))
  CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
  CtrlType = mk_ctrl(4, 2, 8, 8, num_registers_per_reg_bank)
  CgraPayloadType = mk_cgra_payload(DataType, DataAddrType, CtrlType, CtrlAddrType)
  CtrlPktType = mk_intra_cgra_pkt(1, 1, 4, CgraPayloadType)

  # 2x2 tiles
  tiles_2d = [[Tile(x, y, num_registers_per_reg_bank, ["add", "mem", "return"])
               for x in range(2)] for y in range(2)]
  TileList = [t for row in tiles_2d for t in row]
  LinkList = get_links(tiles_2d)
  # The first row and the first column of the 2x2 tiles are connected to the data SPM.
  dataSPM = DataSPM(3, 3)

  dut = CgraDmaRTL(CgraPayloadType,
                   1, 1, # multi_cgra_rows, multi_cgra_columns
                   2, 2, # per_cgra_rows, per_cgra_columns
                   ctrl_mem_size, data_mem_size_global,
                   data_mem_size_per_bank, num_banks_per_cgra,
                   num_registers_per_reg_bank, num_ctrl,
                   total_steps, True,
                   None, [AdderRTL, MemUnitRTL, RetRTL],
                   TileList, LinkList, dataSPM,
                   {0: [0, 15]}, # controller to address map
                   {0: [0, 0]}, # cgra id to 2D coordinate
                   is_multi_cgra = False)

  dut.apply(DefaultPassGroup())
  dut.sim_reset()

  dut.cgra_id @= 0
  # Address range: [0:15]
  dut.address_lower @= DataAddrType(0)
  dut.address_upper @= DataAddrType(15)

  dut.recv_from_cpu_pkt.val @= 0
  dut.recv_from_cpu_pkt.msg @= CtrlPktType()
  dut.send_to_cpu_pkt.rdy @= 1
  dut.mem_rd_req_rdy @= 1
  dut.mem_rd_resp_val @= 0
  dut.mem_rd_resp_data @= 0
  dut.mem_wr_req_rdy @= 1
  dut.mem_wr_resp_val @= 0
  dut.dma_done_rdy @= 1

  dut.dma_cmd_val @= 1
  dut.dma_cmd_opcode @= DMA_MVIN
  # Read the data of DRAM from address 0x1000(16 bytes in total),
  # then write the data to SPM from address 0x0 to 0x3.
  dut.dma_cmd_dram_addr @= 0x1000
  dut.dma_cmd_spm_addr @= DataAddrType(0)
  dut.dma_cmd_bytes @= 16
  dut.dma_cmd_tag @= 0x33
  dut.sim_eval_combinational()
  assert dut.dma_cmd_rdy
  dut.sim_tick()
  dut.dma_cmd_val @= 0

  beat = concat(WordType(0x44444444), WordType(0x33333333),
                WordType(0x22222222), WordType(0x11111111))
  pending_resp = False

  for _ in range(40):
    dut.mem_rd_resp_val @= 0
    if pending_resp:
      dut.mem_rd_resp_val @= 1
      # Simulate the read response from DRAM.
      dut.mem_rd_resp_data @= beat

    dut.sim_eval_combinational()

    pending_resp = bool(dut.mem_rd_req_val & dut.mem_rd_req_rdy)

    if dut.dma_done_val:
      # Transfer finished, check the tag.
      assert int(dut.dma_done_tag) == 0x33
      break

    dut.sim_tick()

  assert dut.dma_done_val
  # Check the data in the dataSPM.
  assert dut.cgra.data_mem.memory_wrapper[0].memory.regs[0] == DataType(0x11111111, 1, 0, 0)
  assert dut.cgra.data_mem.memory_wrapper[0].memory.regs[1] == DataType(0x22222222, 1, 0, 0)
  assert dut.cgra.data_mem.memory_wrapper[0].memory.regs[2] == DataType(0x33333333, 1, 0, 0)
  assert dut.cgra.data_mem.memory_wrapper[0].memory.regs[3] == DataType(0x44444444, 1, 0, 0)


def test_cgra_dma_mvout_from_local_spm():
  """
  Integration test for the CgraDmaRTL wrapper.
  It simulates a DMA MVOUT command that moves data from the local SPM
  into external DRAM.
  """
  ctrl_mem_size = 8
  data_mem_size_global = 64
  data_mem_size_per_bank = 16
  num_banks_per_cgra = 4
  num_registers_per_reg_bank = 16
  num_ctrl = 1
  total_steps = 1

  DataType = mk_data(32, 1)
  WordType = mk_bits(32)
  DataAddrType = mk_bits(clog2(data_mem_size_global))
  CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
  CtrlType = mk_ctrl(4, 2, 8, 8, num_registers_per_reg_bank)
  CgraPayloadType = mk_cgra_payload(DataType, DataAddrType, CtrlType, CtrlAddrType)
  CtrlPktType = mk_intra_cgra_pkt(1, 1, 4, CgraPayloadType)

  tiles_2d = [[Tile(x, y, num_registers_per_reg_bank, ["add", "mem", "return"])
               for x in range(2)] for y in range(2)]
  TileList = [t for row in tiles_2d for t in row]
  LinkList = get_links(tiles_2d)
  dataSPM = DataSPM(3, 3)

  dut = CgraDmaRTL(CgraPayloadType,
                   1, 1, # multi_cgra_rows, multi_cgra_columns
                   2, 2, # per_cgra_rows, per_cgra_columns
                   ctrl_mem_size, data_mem_size_global,
                   data_mem_size_per_bank, num_banks_per_cgra,
                   num_registers_per_reg_bank, num_ctrl,
                   total_steps, True,
                   None, [AdderRTL, MemUnitRTL, RetRTL],
                   TileList, LinkList, dataSPM,
                   {0: [0, 15]}, # controller to address map
                   {0: [0, 0]}, # cgra id to 2D coordinate
                   is_multi_cgra = False)

  dut.apply(DefaultPassGroup())
  dut.sim_reset()

  # Pre-load SPM with data
  dut.cgra.data_mem.memory_wrapper[0].memory.regs[0] <<= DataType(0x11111111, 1, 0, 0)
  dut.cgra.data_mem.memory_wrapper[0].memory.regs[1] <<= DataType(0x22222222, 1, 0, 0)
  dut.cgra.data_mem.memory_wrapper[0].memory.regs[2] <<= DataType(0x33333333, 1, 0, 0)
  dut.cgra.data_mem.memory_wrapper[0].memory.regs[3] <<= DataType(0x44444444, 1, 0, 0)
  dut.sim_tick()

  dut.cgra_id @= 0
  # Address range: [0:15]
  dut.address_lower @= DataAddrType(0)
  dut.address_upper @= DataAddrType(15)

  dut.recv_from_cpu_pkt.val @= 0
  dut.recv_from_cpu_pkt.msg @= CtrlPktType()
  dut.send_to_cpu_pkt.rdy @= 1
  dut.mem_rd_req_rdy @= 1
  dut.mem_rd_resp_val @= 0
  dut.mem_rd_resp_data @= 0
  dut.mem_wr_req_rdy @= 1
  dut.mem_wr_resp_val @= 0
  dut.dma_done_rdy @= 1

  # Issue DMA MVOUT command
  dut.dma_cmd_val @= 1
  dut.dma_cmd_opcode @= DMA_MVOUT
  # Read the data of SPM from address 0x0 to 0x3(16 bytes in total),
  # then write the data to DRAM address 0x2000.
  dut.dma_cmd_dram_addr @= 0x2000
  dut.dma_cmd_spm_addr @= DataAddrType(0)
  dut.dma_cmd_bytes @= 16
  dut.dma_cmd_tag @= 0x44
  dut.sim_eval_combinational()
  assert dut.dma_cmd_rdy
  dut.sim_tick()
  dut.dma_cmd_val @= 0

  # Expected 128-bit beat
  expected_beat = concat(WordType(0x44444444), WordType(0x33333333),
                         WordType(0x22222222), WordType(0x11111111))

  done = False
  pending_wr_resp = False
  for _ in range(40):
    dut.mem_wr_resp_val @= 0
    if pending_wr_resp:
      dut.mem_wr_resp_val @= 1
      pending_wr_resp = False

    if dut.mem_wr_req_val:
      assert dut.mem_wr_req_addr == 0x2000
      assert dut.mem_wr_req_data == expected_beat
      pending_wr_resp = True

    dut.sim_eval_combinational()

    if dut.dma_done_val:
      assert int(dut.dma_done_tag) == 0x44
      done = True
      break

    dut.sim_tick()

  assert done
