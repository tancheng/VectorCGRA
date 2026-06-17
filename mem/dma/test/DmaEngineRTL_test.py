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

  dut.dma_cmd.val @= 0
  dut.dma_cmd.msg.opcode @= 0
  dut.dma_cmd.msg.dram_addr @= 0
  dut.dma_cmd.msg.spm_addr @= 0
  dut.dma_cmd.msg.nbytes @= 0
  dut.dma_cmd.msg.tag @= 0
  dut.dma_done.rdy @= 1

  dut.send_dram_rd_req.rdy @= 1
  dut.recv_dram_rd_resp.val @= 0
  dut.recv_dram_rd_resp.msg @= 0
  dut.dram_wr_req.rdy @= 1
  dut.dram_wr_resp_val @= 1

  dut.spm.write.rdy @= 1
  dut.spm.read.rdy @= 1
  dut.spm.read_resp.val @= 0
  dut.spm.read_resp.msg.data @= 0
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
  dut.dma_cmd.val @= 1
  dut.dma_cmd.msg.opcode @= opcode
  dut.dma_cmd.msg.dram_addr @= dram_addr
  dut.dma_cmd.msg.spm_addr @= spm_addr
  dut.dma_cmd.msg.nbytes @= nbytes
  dut.dma_cmd.msg.tag @= tag
  dut.sim_eval_combinational()
  assert dut.dma_cmd.rdy
  dut.sim_tick()
  dut.dma_cmd.val @= 0


def test_dma_mvin_one_beat():
  """
  Tests DMA_MVIN operation.
  The DRAM contains 2 beats of data, which should be unpacked into 8
  sequential SPM writes.
  """
  dut = make_dut()
  issue_cmd(dut, DMA_MVIN, 
           0x1000, # dram_addr
           4, # spm_addr
           32, # nbytes(number of bytes to transfer)
           0x5a) # tag

  dram = {
    0x1000: concat(Bits32(0x44444444), Bits32(0x33333333),
                   Bits32(0x22222222), Bits32(0x11111111)), # 4 x 4 bytes = 16 bytes in total.
    
    # Address bias: +16, since DRAM is byte-addressed(each address points to a byte).
    0x1010: concat(Bits32(0x88888888), Bits32(0x77777777),
                   Bits32(0x66666666), Bits32(0x55555555)),
  }
  pending_resp = None
  spm_writes = []

  for _ in range(20):
    dut.recv_dram_rd_resp.val @= 0
    if pending_resp is not None:
      dut.recv_dram_rd_resp.val @= 1
      dut.recv_dram_rd_resp.msg @= pending_resp

    dut.sim_eval_combinational()

    if dut.send_dram_rd_req.val & dut.send_dram_rd_req.rdy:
      pending_resp = dram[int(dut.send_dram_rd_req.msg)]
    else:
      pending_resp = None

    if dut.spm.write.val & dut.spm.write.rdy:
      spm_writes.append((int(dut.spm.write.msg.addr), int(dut.spm.write.msg.data)))

    if dut.dma_done.val:
      assert int(dut.dma_done.msg.tag) == 0x5a
      break

    dut.sim_tick()

  for elem in spm_writes:
    print(f'{elem[0]}: 0x{elem[1]:08x}')

  assert spm_writes == [
    (4, 0x11111111),
    (5, 0x22222222),
    (6, 0x33333333),
    (7, 0x44444444),

    (8, 0x55555555),
    (9, 0x66666666),
    (10, 0x77777777),
    (11, 0x88888888),
  ]


def test_dma_mvout_partial_beat():
  """
  Tests a partial beat MVOUT operation (12 bytes / 3 words).
  The DMA should read three words from SPM, pack them into a 128-bit beat
  with a proper byte mask, and write it to DRAM.
  """
  dut = make_dut()
  issue_cmd(dut, DMA_MVOUT, 
            0x2000, # dram_addr
            8, # spm_addr
            12, # nbytes(number of bytes to transfer)
            0xa5) # tag

  spm = {
    8: 0xaaaabbbb,
    9: 0xccccdddd,
    10: 0xeeeeffff,
  }
  pending_rresp = None
  mem_writes = []

  for _ in range(30):
    dut.spm.read_resp.val @= 0
    if pending_rresp is not None:
      dut.spm.read_resp.val @= 1
      dut.spm.read_resp.msg.data @= pending_rresp

    dut.sim_eval_combinational()

    if dut.spm.read.val & dut.spm.read.rdy:
      pending_rresp = spm[int(dut.spm.read.msg.addr)]
    else:
      pending_rresp = None

    if dut.dram_wr_req.val & dut.dram_wr_req.rdy:
      mem_writes.append((int(dut.dram_wr_req.addr),
                         int(dut.dram_wr_req.data),
                         int(dut.dram_wr_req.mask)))

    if dut.dma_done.val:
      assert int(dut.dma_done.msg.tag) == 0xa5
      break

    dut.sim_tick()

  assert mem_writes == [
    (0x2000,
     int(concat(Bits32(0), Bits32(0xeeeeffff),
                Bits32(0xccccdddd), Bits32(0xaaaabbbb))),
     0x0fff), # mask
  ]

def test_dma_mvout_full_beat():
  """
  Tests a full beat MVOUT operation (16 bytes / 4 words).
  The DMA should read four words from SPM, pack them into a 128-bit beat
  with a proper byte mask, and write it to DRAM.
  """
  dut = make_dut()
  issue_cmd(dut, DMA_MVOUT, 
            0x2000, # dram_addr
            8, # spm_addr
            32, # nbytes(number of bytes to transfer)
            0xa5) # tag

  spm = {
    8 : 0x11112222,
    9 : 0x33334444,
    10: 0x55556666,
    11: 0x77778888,
    12: 0x9999aaaa,
    13: 0xbbbbcccc,
    14: 0xddddeeee,
    15: 0xffff0000,
  }
  pending_rresp = None
  mem_writes = []

  for _ in range(30):
    dut.spm.read_resp.val @= 0
    if pending_rresp is not None:
      dut.spm.read_resp.val @= 1
      dut.spm.read_resp.msg.data @= pending_rresp

    dut.sim_eval_combinational()

    if dut.spm.read.val & dut.spm.read.rdy:
      pending_rresp = spm[int(dut.spm.read.msg.addr)]
    else:
      pending_rresp = None

    if dut.dram_wr_req.val & dut.dram_wr_req.rdy:
      mem_writes.append((int(dut.dram_wr_req.addr),
                         int(dut.dram_wr_req.data),
                         int(dut.dram_wr_req.mask)))

    if dut.dma_done.val:
      assert int(dut.dma_done.msg.tag) == 0xa5
      break

    dut.sim_tick()

  for elem in mem_writes:
    print(f'{elem[0]}: 0x{elem[1]:08x}')
    print(f'mask: 0x{elem[2]:08x}')

  assert mem_writes == [
    (0x2000,
     int(concat(Bits32(0x77778888), Bits32(0x55556666),
                Bits32(0x33334444), Bits32(0x11112222))),
     0xffff), # mask

     (0x2010,
      int(concat(Bits32(0xffff0000), Bits32(0xddddeeee),
                Bits32(0xbbbbcccc), Bits32(0x9999aaaa))),
     0xffff),
  ]