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
from ...lib.cmd_type import *
from ...lib.messages import *
from ...lib.opt_type import *
from ...lib.util.cgra.DataSPM import DataSPM
from ...lib.util.cgra.Tile import Tile
from ...lib.util.cgra.cgra_helper import get_links


def issue_cpu_pkt(dut, pkt, max_cycles = 20):
  """
     CPU issues a packet to the CGRA.
  """
  dut.recv_from_cpu_pkt.val @= 1
  dut.recv_from_cpu_pkt.msg @= pkt

  for _ in range(max_cycles):
    dut.sim_eval_combinational()
    if dut.recv_from_cpu_pkt.rdy:
      dut.sim_tick()
      dut.recv_from_cpu_pkt.val @= 0
      dut.sim_eval_combinational()
      return
    dut.sim_tick()

  assert False, "CPU packet was not accepted by the CGRA"


def issue_dma_cmd(dut, CtrlPktType, CgraPayloadType, DataType, DataAddrType,
                  dma_cmd, dram_addr, spm_addr, nbytes, tag):

  """
  Issues a DMA command to the CGRA.
  Args:
    dut: The CGRA instance.
    CtrlPktType: The type of the control packet.
    CgraPayloadType: The type of the CGRA payload.
    DataType: The type of the data.
    DataAddrType: The type of the data address.

    dma_cmd: The DMA command to issue.(CMD_DMA_MVIN or CMD_DMA_MVOUT)
    dram_addr: The DRAM address to transfer data from or to.(64 bits)
    spm_addr: The SPM address to transfer data from or to.(32 bits)
    nbytes: The number of bytes to transfer.
    tag: The tag of the DMA command.
  """
  config_pkts = [
    # The bindwidth of dram address is 64 bits, so we need to split it into two 32 bits parts.
    # Lower 32 bits are sent first.
    CtrlPktType(0, 0, payload = CgraPayloadType(
      CMD_DMA_CONFIG_DRAM_ADDR_LO,
      data = DataType(dram_addr & 0xffffffff, 1))),
    
    # Higher 32 bits are sent second.
    CtrlPktType(0, 0, payload = CgraPayloadType(
      CMD_DMA_CONFIG_DRAM_ADDR_HI,
      data = DataType((dram_addr >> 32) & 0xffffffff, 1))),
    
    # The SPM address to read from or write to.
    CtrlPktType(0, 0, payload = CgraPayloadType(
      CMD_DMA_CONFIG_SPM_ADDR,
      data_addr = DataAddrType(spm_addr))),

    # The number of bytes to transfer.
    CtrlPktType(0, 0, payload = CgraPayloadType(
      CMD_DMA_CONFIG_BYTES,
      data = DataType(nbytes, 1))),
    
    # The tag of the DMA command.
    CtrlPktType(0, 0, payload = CgraPayloadType(
      CMD_DMA_CONFIG_TAG,
      data = DataType(tag, 1))),
    CtrlPktType(0, 0, payload = CgraPayloadType(dma_cmd)),
  ]

  for pkt in config_pkts:
    issue_cpu_pkt(dut, pkt)


def observed_dma_done(dut, expected_tag):
  dut.sim_eval_combinational()
  if dut.send_to_cpu_pkt.val and dut.send_to_cpu_pkt.msg.payload.cmd == CMD_DMA_DONE:
    assert int(dut.send_to_cpu_pkt.msg.opaque) == expected_tag
    assert int(dut.send_to_cpu_pkt.msg.payload.data.payload) == expected_tag
    return True
  return False


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
  dut.dram_rd_req.rdy @= 1
  dut.dram_rd_resp.val @= 0
  dut.dram_rd_resp.msg @= 0
  dut.dram_wr_req_rdy @= 1
  dut.dram_wr_resp_val @= 0

  # Read 16 bytes from DRAM address 0x1000 and write them to SPM words 0..3.
  issue_dma_cmd(dut, CtrlPktType, CgraPayloadType, DataType, DataAddrType,
                CMD_DMA_MVIN, 0x1000, 0, 16, 0x33)

  beat = concat(WordType(0x44444444), WordType(0x33333333),
                WordType(0x22222222), WordType(0x11111111))
  pending_resp = False

  for _ in range(40):
    dut.dram_rd_resp.val @= 0
    if pending_resp:
      dut.dram_rd_resp.val @= 1
      # Simulate the read response from DRAM.
      dut.dram_rd_resp.msg @= beat

    dut.sim_eval_combinational()

    pending_resp = bool(dut.dram_rd_req.val & dut.dram_rd_req.rdy)

    if observed_dma_done(dut, 0x33):
      break

    dut.sim_tick()

  assert observed_dma_done(dut, 0x33)
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
  dut.dram_rd_req.rdy @= 1
  dut.dram_rd_resp.val @= 0
  dut.dram_rd_resp.msg @= 0
  dut.dram_wr_req_rdy @= 1
  dut.dram_wr_resp_val @= 0

  # Read SPM words 0..3 and write 16 bytes to DRAM address 0x2000.
  issue_dma_cmd(dut, CtrlPktType, CgraPayloadType, DataType, DataAddrType,
                CMD_DMA_MVOUT, 0x2000, 0, 16, 0x44)

  # Expected 128-bit beat
  expected_beat = concat(WordType(0x44444444), WordType(0x33333333),
                         WordType(0x22222222), WordType(0x11111111))

  done = False
  pending_wr_resp = False
  for _ in range(40):
    dut.dram_wr_resp_val @= 0
    if pending_wr_resp:
      dut.dram_wr_resp_val @= 1
      pending_wr_resp = False

    dut.sim_eval_combinational()

    if dut.dram_wr_req_val & dut.dram_wr_req_rdy:
      assert dut.dram_wr_req_addr == 0x2000
      assert dut.dram_wr_req_data == expected_beat
      pending_wr_resp = True

    if observed_dma_done(dut, 0x44):
      done = True
      break

    dut.sim_tick()

  assert done
