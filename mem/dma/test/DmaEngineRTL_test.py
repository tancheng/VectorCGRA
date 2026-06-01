"""
==========================================================================
DmaEngineRTL_test.py
==========================================================================
"""

from pymtl3 import *

from ..DmaEngineRTL import DmaEngineRTL, DMA_MVIN, DMA_MVOUT


def make_dut():
  dut = DmaEngineRTL()
  dut.apply(DefaultPassGroup())
  dut.sim_reset()

  dut.dma_cmd_val @= 0
  dut.dma_cmd_opcode @= 0
  dut.dma_cmd_dram_addr @= 0
  dut.dma_cmd_spm_addr @= 0
  dut.dma_cmd_bytes @= 0
  dut.dma_cmd_tag @= 0
  dut.dma_done_rdy @= 1

  dut.mem_rd_req_rdy @= 1
  dut.mem_rd_resp_val @= 0
  dut.mem_rd_resp_data @= 0
  dut.mem_wr_req_rdy @= 1
  dut.mem_wr_resp_val @= 1

  dut.spm_dma_wrdy @= 1
  dut.spm_dma_rrdy @= 1
  dut.spm_dma_rresp_val @= 0
  dut.spm_dma_rresp_data @= 0
  dut.sim_eval_combinational()
  return dut


def issue_cmd(dut, opcode, dram_addr, spm_addr, nbytes, tag):
  """
  Issues a DMA command to the DUT.
  Args:
    dut: The DUT instance.
    opcode: The opcode of the DMA command. DMA_MVIN or DMA_MVOUT.
    dram_addr: The DRAM address of the DMA command.
    spm_addr: The SPM address of the DMA command.
    nbytes: The number of bytes to transfer.
    tag: The tag of the DMA command.
  """
  dut.dma_cmd_val @= 1
  dut.dma_cmd_opcode @= opcode
  dut.dma_cmd_dram_addr @= dram_addr
  dut.dma_cmd_spm_addr @= spm_addr
  dut.dma_cmd_bytes @= nbytes
  dut.dma_cmd_tag @= tag
  dut.sim_eval_combinational()
  assert dut.dma_cmd_rdy
  dut.sim_tick()
  dut.dma_cmd_val @= 0


def test_dma_mvin_one_beat():
  """
  Tests a single 128-bit beat MVIN operation.
  The DRAM contains one beat of data, which should be unpacked into four
  sequential SPM writes.
  """
  dut = make_dut()
  issue_cmd(dut, DMA_MVIN, 0x1000, 4, 16, 0x5a)

  dram = {
    0x1000: concat(Bits32(0x44444444), Bits32(0x33333333),
                   Bits32(0x22222222), Bits32(0x11111111)),
  }
  pending_resp = None
  spm_writes = []

  for _ in range(20):
    dut.mem_rd_resp_val @= 0
    if pending_resp is not None:
      dut.mem_rd_resp_val @= 1
      dut.mem_rd_resp_data @= pending_resp

    dut.sim_eval_combinational()

    if dut.mem_rd_req_val & dut.mem_rd_req_rdy:
      pending_resp = dram[int(dut.mem_rd_req_addr)]
    else:
      pending_resp = None

    if dut.spm_dma_wval & dut.spm_dma_wrdy:
      spm_writes.append((int(dut.spm_dma_waddr), int(dut.spm_dma_wdata)))

    if dut.dma_done_val:
      assert int(dut.dma_done_tag) == 0x5a
      break

    dut.sim_tick()

  for elem in spm_writes:
    print(f'{elem[0]}: 0x{elem[1]:08x}')

  assert spm_writes == [
    (4, 0x11111111),
    (5, 0x22222222),
    (6, 0x33333333),
    (7, 0x44444444),
  ]


def test_dma_mvout_partial_beat():
  """
  Tests a partial beat MVOUT operation (12 bytes / 3 words).
  The DMA should read three words from SPM, pack them into a 128-bit beat
  with a proper byte mask, and write it to DRAM.
  """
  dut = make_dut()
  issue_cmd(dut, DMA_MVOUT, 0x2000, 8, 12, 0xa5)

  spm = {
    8: 0xaaaabbbb,
    9: 0xccccdddd,
    10: 0xeeeeffff,
  }
  pending_rresp = None
  mem_writes = []

  for _ in range(30):
    dut.spm_dma_rresp_val @= 0
    if pending_rresp is not None:
      dut.spm_dma_rresp_val @= 1
      dut.spm_dma_rresp_data @= pending_rresp

    dut.sim_eval_combinational()

    if dut.spm_dma_rval & dut.spm_dma_rrdy:
      pending_rresp = spm[int(dut.spm_dma_raddr)]
    else:
      pending_rresp = None

    if dut.mem_wr_req_val & dut.mem_wr_req_rdy:
      mem_writes.append((int(dut.mem_wr_req_addr),
                         int(dut.mem_wr_req_data),
                         int(dut.mem_wr_req_mask)))

    if dut.dma_done_val:
      assert int(dut.dma_done_tag) == 0xa5
      break

    dut.sim_tick()

  assert mem_writes == [
    (0x2000,
     int(concat(Bits32(0), Bits32(0xeeeeffff),
                Bits32(0xccccdddd), Bits32(0xaaaabbbb))),
     0x0fff),
  ]
