"""
==========================================================================
DataMemControllerRTL_test.py
==========================================================================
Test cases for DataMemControllerRTL.

Author : Cheng Tan
  Date : Aug 28, 2025
"""

from pymtl3.passes.backends.verilog import (VerilogTranslationPass)
from pymtl3.stdlib.test_utils import config_model_with_cmdline_opts

from ..DataMemControllerRTL import DataMemControllerRTL
from ....lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ....lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ....lib.messages import *
from ....lib.opt_type import *

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, NocPktType, CgraPayloadType, DataType, DataAddrType,
                data_mem_size_global, data_mem_size_per_bank, num_banks,
                rd_tiles, wr_tiles, num_cgra_rows, num_cgra_columns,
                num_tiles,
                read_addr, read_data, write_addr,
                write_data, noc_recv_load,
                send_to_noc_load_request_pkt, send_to_noc_store_pkt):

    s.num_banks = num_banks
    s.rd_tiles = rd_tiles
    s.wr_tiles = wr_tiles
    s.recv_raddr = [TestSrcRTL(DataAddrType, read_addr[i])
                    for i in range(rd_tiles)]
    s.send_rdata = [TestSinkRTL(DataType, read_data[i])
                    for i in range(rd_tiles)]

    s.recv_waddr = [TestSrcRTL(DataAddrType, write_addr[i])
                    for i in range(wr_tiles)]
    s.recv_wdata = [TestSrcRTL(DataType, write_data[i])
                    for i in range(wr_tiles)]

    s.recv_from_noc = TestSrcRTL(NocPktType, noc_recv_load)

    s.send_to_noc_load_request_pkt = TestSinkRTL(NocPktType, send_to_noc_load_request_pkt)
    s.send_to_noc_store_pkt = TestSinkRTL(NocPktType, send_to_noc_store_pkt)

    s.mem_controller = DataMemControllerRTL(NocPktType,
                                        CgraPayloadType,
                                        DataType,
                                        data_mem_size_global,
                                        data_mem_size_per_bank,
                                        num_banks,
                                        rd_tiles,
                                        wr_tiles,
                                        num_cgra_rows,
                                        num_cgra_columns,
                                        num_tiles,
                                        mem_access_is_combinational = True)

    for i in range(rd_tiles):
      s.mem_controller.recv_raddr[i] //= s.recv_raddr[i].send
      s.mem_controller.send_rdata[i] //= s.send_rdata[i].recv

    for i in range(wr_tiles):
      s.mem_controller.recv_waddr[i] //= s.recv_waddr[i].send
      s.mem_controller.recv_wdata[i] //= s.recv_wdata[i].send

    s.mem_controller.recv_from_noc_load_response_pkt //= s.recv_from_noc.send
    s.mem_controller.send_to_noc_load_request_pkt //= s.send_to_noc_load_request_pkt.recv
    s.mem_controller.send_to_noc_store_pkt //= s.send_to_noc_store_pkt.recv

    s.mem_controller.address_lower //= 0
    s.mem_controller.address_upper //= 31

    s.cgra_id = 0

  def done(s):
    for i in range(s.rd_tiles):
      if not s.recv_raddr[i].done() or not s.send_rdata[i].done():
        return False

    for i in range(s.wr_tiles):
      if not s.recv_waddr[i].done() or not s.recv_wdata[i].done():
        return False

    if not s.send_to_noc_load_request_pkt.done() or \
       not s.send_to_noc_store_pkt.done() or \
       not s.recv_from_noc.done():
      return False

    return True

  def line_trace(s):
    return s.mem_controller.line_trace()

def run_sim(test_harness, max_cycles = 40):
  test_harness.apply(DefaultPassGroup())
  test_harness.sim_reset()

  # Run simulation

  ncycles = 0
  print()
  print("{}:{}".format(ncycles, test_harness.line_trace()))
  while not test_harness.done() and ncycles < max_cycles:
    test_harness.sim_tick()
    ncycles += 1
    print("{}:{}".format(ncycles, test_harness.line_trace()))

  # Check timeout
  assert ncycles < max_cycles

  test_harness.sim_tick()
  test_harness.sim_tick()
  test_harness.sim_tick()

def test_mem_controller(cmdline_opts):
  data_nbits = 32
  predicate_nbits = 1
  DataType = mk_data(data_nbits, predicate_nbits)
  data_mem_size_global = 64
  data_mem_size_per_bank = 16
  num_banks = 2

  num_registers_per_reg_bank = 16
  num_cgra_columns = 1
  num_cgra_rows = 1
  num_tiles = 4
  rd_tiles = 4
  wr_tiles = 4
  ctrl_mem_size = 6
  num_tile_inports  = 4
  num_tile_outports =4
  num_fu_inports = 4
  num_fu_outports = 2

  DataAddrType = mk_bits(clog2(data_mem_size_global))
  CtrlAddrType = mk_bits(clog2(ctrl_mem_size))

  CtrlType = mk_ctrl(num_fu_inports,
                     num_fu_outports,
                     num_tile_inports,
                     num_tile_outports,
                     num_registers_per_reg_bank)

  CgraPayloadType = mk_cgra_payload(DataType,
                                    DataAddrType,
                                    CtrlType,
                                    CtrlAddrType)

  InterCgraPktType = mk_inter_cgra_pkt(num_cgra_columns,
                                       num_cgra_rows,
                                       num_tiles,
                                       rd_tiles,
                                       CgraPayloadType)

  # test_meta_data = [
  #     # addr:  0     1     2     3     4     5     6     7     8     9    10    11    12    13    14    15
  #          [0x00, 0x00, 0xa8, 0xa9, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
  #     # addr: 16    17    18    19    20    21    22    23    24    25    26    27    28    29    30    31
  #          [0x00, 0x00, 0x00, 0x00, 0xc6, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xd7]]

  # Input write requests.
  write_addr = [
                [DataAddrType(2),  DataAddrType(31), DataAddrType(45)],
                [DataAddrType(40), DataAddrType(31)],
                [DataAddrType(2),  DataAddrType(3)],
                [DataAddrType(2)]
               ]
  write_data = [
                [DataType(0x00a8, 1), DataType(0x00d7, 1), DataType(0xd545, 1)],
                [DataType(0xd040, 1), DataType(0x0d70, 1)],
                [DataType(0x0a80, 1), DataType(0x00a9, 1)],
                [DataType(0xa800, 1)]
               ]
  # Input read requests.
  read_addr = [
               [DataAddrType(42), DataAddrType(2),  DataAddrType(31), DataAddrType(3), DataAddrType(3)],
               [DataAddrType(30), DataAddrType(17), DataAddrType(31), DataAddrType(2)],
               [],
               [DataAddrType(2),  DataAddrType(2),  DataAddrType(2),  DataAddrType(25)]
              ]
  # Expected response.
  read_data = [
               [DataType(0xbbbb, 1), DataType(0x00a8, 1), DataType(0x00d7, 1), DataType(0x0000, 0), DataType(0x00a9, 1)],
               [DataType(0x0000, 0), DataType(0x0000, 0), DataType(0x0d70, 1), DataType(0xa800, 1)],
               [],
               [DataType(0x0000, 0), DataType(0x0a80, 1), DataType(0xa800, 1), DataType(0x0000, 0)]
              ]

  # Input data.
  send_to_noc_load_request_pkt = [
                     # src  dst src_x src_y dst_x dst_y src_tile dst_tile remote_src_port opq vc
      InterCgraPktType(0,   0,  0,    0,    0,    0,    0,       0,       0,              0,  0, CgraPayloadType(CMD_LOAD_REQUEST, data_addr = 42)),
  ]

  noc_recv_load = [
      InterCgraPktType(0,   0,  0,    0,    0,    0,    0,       0,       0,              0,  0, CgraPayloadType(CMD_LOAD_RESPONSE, DataType(0xbbbb, 1)))
  ]

  # Expected.
  send_to_noc_store_pkt = [
                     # src  dst src_x src_y dst_x dst_y src_tile dst_tile remote_src_port opq vc                                                         data_addr
      InterCgraPktType(0,   0,  0,    0,    0,    0,    0,       0,       1,              0,  0, CgraPayloadType(CMD_STORE_REQUEST, DataType(0xd040, 1), 40)),
      InterCgraPktType(0,   0,  0,    0,    0,    0,    0,       0,       0,              0,  0, CgraPayloadType(CMD_STORE_REQUEST, DataType(0xd545, 1), 45)),
  ]

  th = TestHarness(InterCgraPktType,
                   CgraPayloadType,
                   DataType,
                   DataAddrType,
                   data_mem_size_global,
                   data_mem_size_per_bank,
                   num_banks,
                   rd_tiles,
                   wr_tiles,
                   num_cgra_rows,
                   num_cgra_columns,
                   num_tiles,
                   read_addr,
                   read_data,
                   write_addr,
                   write_data,
                   noc_recv_load,
                   send_to_noc_load_request_pkt,
                   send_to_noc_store_pkt)

  th.elaborate()
  th.mem_controller.set_metadata(VerilogTranslationPass.explicit_module_name,
                                 f'DataMemControllerRTL_translation')
  th = config_model_with_cmdline_opts( th, cmdline_opts, duts=['mem_controller'] )

  run_sim(th)

