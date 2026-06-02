"""
==========================================================================
DataMemControllerRTL_dma_test.py
==========================================================================
"""

from pymtl3 import *

from ..DataMemControllerRTL import DataMemControllerRTL
from ....lib.messages import *
from ....lib.opt_type import *


def make_types(data_mem_size_global, ctrl_mem_size, num_tiles, num_rd_tiles):
  DataType = mk_data(32, 1)
  DataAddrType = mk_bits(clog2(data_mem_size_global))
  CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
  CtrlType = mk_ctrl(4, 2, 4, 4, 16)
  CgraPayloadType = mk_cgra_payload(DataType, DataAddrType, CtrlType, CtrlAddrType)
  NocPktType = mk_inter_cgra_pkt(1, 1, num_tiles, num_rd_tiles, CgraPayloadType)
  return DataType, DataAddrType, NocPktType


def drive_defaults(dut, DataAddrType, DataType, NocPktType, num_rd_tiles, num_wr_tiles):
  for i in range(num_rd_tiles):
    dut.recv_raddr[i].val @= 0
    dut.recv_raddr[i].msg @= DataAddrType(0)
    dut.send_rdata[i].rdy @= 1

  for i in range(num_wr_tiles):
    dut.recv_waddr[i].val @= 0
    dut.recv_waddr[i].msg @= DataAddrType(0)
    dut.recv_wdata[i].val @= 0
    dut.recv_wdata[i].msg @= DataType(0, 0, 0, 0)

  dut.recv_from_noc_load_request.val @= 0
  dut.recv_from_noc_load_request.msg @= NocPktType()
  dut.recv_from_noc_store_request.val @= 0
  dut.recv_from_noc_store_request.msg @= NocPktType()
  dut.recv_from_noc_load_response_pkt.val @= 0
  dut.recv_from_noc_load_response_pkt.msg @= NocPktType()
  dut.send_to_noc_load_request_pkt.rdy @= 1
  dut.send_to_noc_load_response_pkt.rdy @= 1
  dut.send_to_noc_store_pkt.rdy @= 1

  dut.spm_dma_wval @= 0
  dut.spm_dma_waddr @= DataAddrType(0)
  dut.spm_dma_wdata @= 0
  dut.spm_dma_wmask @= 0
  dut.spm_dma_rval @= 0
  dut.spm_dma_raddr @= DataAddrType(0)
  dut.spm_dma_rresp_rdy @= 1

  dut.cgra_id @= 0
  dut.address_lower @= DataAddrType(0)
  dut.address_upper @= DataAddrType(15)


def test_dma_ports_write_then_read():
  """
  Verifies that the DataMemController correctly handles requests from the
  DMA ports. It performs a DMA write to a specific address and then a
  DMA read from the same address to verify the data.
  """
  data_mem_size_global = 64
  data_mem_size_per_bank = 16
  num_banks = 4
  num_rd_tiles = 2
  num_wr_tiles = 2
  num_tiles = 4
  ctrl_mem_size = 16

  DataType, DataAddrType, NocPktType = make_types(
      data_mem_size_global, ctrl_mem_size, num_tiles, num_rd_tiles)

  dut = DataMemControllerRTL(NocPktType,
                             data_mem_size_global,
                             data_mem_size_per_bank,
                             num_banks,
                             num_rd_tiles,
                             num_wr_tiles,
                             1,
                             1,
                             num_tiles,
                             True,
                             {0: [0, 0]},
                             has_dma_ports = True)
  dut.apply(DefaultPassGroup())
  dut.sim_reset()
  drive_defaults(dut, DataAddrType, DataType, NocPktType, num_rd_tiles, num_wr_tiles)

  dut.spm_dma_wval @= 1
  dut.spm_dma_waddr @= DataAddrType(3)
  dut.spm_dma_wdata @= 0xaaaabbbb
  dut.spm_dma_wmask @= 0xf
  dut.sim_eval_combinational()
  assert dut.spm_dma_wrdy
  dut.sim_tick()
  dut.spm_dma_wval @= 0

  dut.spm_dma_rval @= 1
  dut.spm_dma_raddr @= DataAddrType(3)

  seen_response = False
  for _ in range(10):
    dut.sim_eval_combinational()
    if dut.spm_dma_rval & dut.spm_dma_rrdy:
      dut.spm_dma_rval @= 0
    if dut.spm_dma_rresp_val:
      assert int(dut.spm_dma_rresp_data) == 0xaaaabbbb
      seen_response = True
      break
    dut.sim_tick()

  assert seen_response
