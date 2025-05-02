'''
=========================================================================
ControllerRTL_test.py
=========================================================================
Simple test for ControllerRTL.

Author : Cheng Tan
  Date : Dec 15, 2024
'''

from pymtl3.stdlib.test_utils import config_model_with_cmdline_opts

from ..ControllerRTL import ControllerRTL
from ...lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ...lib.messages import *
from ...lib.opt_type import *


#-------------------------------------------------------------------------
# TestHarness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s,
                ControllerIdType,
                CpuPktType,
                MsgType,
                AddrType,
                PktType,
                cgra_id,
                from_tile_load_request_pkt_msgs,
                from_tile_load_response_pkt_msgs,
                from_tile_store_request_pkt_msgs,
                expected_to_mem_load_request_msgs,
                expected_to_mem_load_response,
                expected_to_mem_store_request_msgs,
                from_noc_pkts,
                expected_to_noc_pkts,
                controller2addr_map,
                idTo2d_map,
                num_cgras,
                num_tiles):

    s.src_from_tile_load_request_pkt = TestSrcRTL(PktType, from_tile_load_request_pkt_msgs)
    s.src_from_tile_load_response_pkt = TestSrcRTL(PktType, from_tile_load_response_pkt_msgs)
    s.src_from_tile_store_request_pkt = TestSrcRTL(PktType, from_tile_store_request_pkt_msgs)

    # s.sink_to_mem_load_request_addr = TestSinkRTL(AddrType, expected_to_mem_load_request_addr_msgs)
    cmp_fn = lambda a, b : a.payload.data == b.payload.data and a.payload.cmd == b.payload.cmd
    s.sink_to_mem_load_request = TestSinkRTL(PktType, expected_to_mem_load_request_msgs, cmp_fn = cmp_fn)

    s.sink_to_mem_load_response = TestSinkRTL(PktType, expected_to_mem_load_response, cmp_fn = cmp_fn)
    # s.sink_to_mem_store_request_addr = TestSinkRTL(AddrType, expected_to_mem_store_request_addr_msgs)
    # s.sink_to_mem_store_request_data = TestSinkRTL(MsgType, expected_to_mem_store_request_data_msgs)
    s.sink_to_mem_store_request = TestSinkRTL(PktType, expected_to_mem_store_request_msgs, cmp_fn = cmp_fn)

    s.src_from_noc = TestSrcRTL(PktType, from_noc_pkts)
    s.sink_to_noc = TestSinkRTL(PktType, expected_to_noc_pkts)

    s.dut = ControllerRTL(ControllerIdType,
                          CpuPktType,
                          PktType,
                          MsgType,
                          AddrType,
                          1, # Number of controllers globally (x/y dimension).
                          num_cgras,
                          num_tiles,
                          controller2addr_map,
                          idTo2d_map)

    # Connections
    s.dut.cgra_id //= cgra_id
    s.src_from_tile_load_request_pkt.send //= s.dut.recv_from_tile_load_request_pkt
    s.src_from_tile_load_response_pkt.send //= s.dut.recv_from_tile_load_response_pkt
    s.src_from_tile_store_request_pkt.send //= s.dut.recv_from_tile_store_request_pkt

    # s.dut.send_to_mem_store_request_addr //= s.sink_to_mem_store_request_addr.recv
    # s.dut.send_to_mem_store_request_data //= s.sink_to_mem_store_request_data.recv
    s.dut.send_to_mem_store_request //= s.sink_to_mem_store_request.recv

    s.dut.send_to_tile_load_response //= s.sink_to_mem_load_response.recv

    # s.dut.send_to_mem_load_request_addr  //= s.sink_to_mem_load_request_addr.recv
    # s.dut.send_to_mem_load_request_src_cgra.rdy //= 1
    # s.dut.send_to_mem_load_request_src_tile.rdy //= 1
    s.dut.send_to_mem_load_request //= s.sink_to_mem_load_request.recv

    s.src_from_noc.send //= s.dut.recv_from_inter_cgra_noc
    s.dut.send_to_inter_cgra_noc //= s.sink_to_noc.recv

    s.dut.recv_from_cpu_pkt.val //= 0
    s.dut.recv_from_cpu_pkt.msg //= CpuPktType()
    s.dut.send_to_ctrl_ring_pkt.rdy //= 0
    s.dut.send_to_cpu_pkt.rdy //= 0
    s.dut.recv_from_ctrl_ring_pkt.val //= 0
    s.dut.recv_from_ctrl_ring_pkt.msg //= CpuPktType()

  def done(s):
    return s.src_from_tile_load_request_pkt.done()  and \
           s.src_from_tile_load_response_pkt.done() and \
           s.src_from_tile_store_request_pkt.done() and \
           s.sink_to_mem_load_request.done()  and \
           s.sink_to_mem_load_response.done() and \
           s.sink_to_mem_store_request.done() and \
           s.src_from_noc.done() and \
           s.sink_to_noc.done()

  def line_trace(s):
    return s.dut.line_trace()

#-------------------------------------------------------------------------
# run_rtl_sim
#-------------------------------------------------------------------------

def run_sim(test_harness, max_cycles = 20):

  # Create a simulator
  test_harness.elaborate()
  test_harness.apply( DefaultPassGroup() )
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

#-------------------------------------------------------------------------
# Test cases
#-------------------------------------------------------------------------

def mk_src_pkts(num_cgras, lst):
  src_pkts = [[] for _ in range(num_cgras)]
  src = 0
  for pkt in lst:
    if hasattr(pkt, 'fl_type'):
      if pkt.fl_type == 0:
        src = pkt.src
    else:
      src = pkt.src
    src_pkts[src].append(pkt)
  return src_pkts

data_nbits = 32
predicate_nbits = 1

num_cgra_columns = 4
num_cgra_rows = 1
num_cgras = num_cgra_columns * num_cgra_rows
num_tiles = 4
cgra_id_nbits = clog2(num_cgras)
ControllerIdType = mk_bits(cgra_id_nbits)
ctrl_mem_size = 16
num_fu_inports = 2
num_fu_outports = 2
num_tile_inports = 4
num_tile_outports = 4
data_mem_size_global = 16
addr_nbits = clog2(data_mem_size_global)
num_registers_per_reg_bank = 16
cgra_id = 0

idTo2d_map = {
        0: [0, 0],
        1: [1, 0],
        2: [2, 0],
        3: [3, 0]
}

controller2addr_map = {
        0: [0, 3],
        1: [4, 7],
        2: [8, 11],
        3: [12, 15],
}

DataType = mk_data(data_nbits, predicate_nbits)
DataAddrType = mk_bits(addr_nbits)

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

from_tile_load_request_pkts = [
                   # src  dst src_x src_y dst_x dst_y src_tile dst_tile opq vc                 cmd
    InterCgraPktType(0,   0,  0,    0,    0,    0,    0,       0,       0,  0, CgraPayloadType(CMD_LOAD_REQUEST, data_addr = 1)),
    InterCgraPktType(0,   0,  0,    0,    0,    0,    0,       0,       0,  0, CgraPayloadType(CMD_LOAD_REQUEST, data_addr = 8)),
    InterCgraPktType(0,   0,  0,    0,    0,    0,    0,       0,       0,  0, CgraPayloadType(CMD_LOAD_REQUEST, data_addr = 13)),
]

from_tile_load_response_pkts = [
    InterCgraPktType(payload = CgraPayloadType(cmd = CMD_LOAD_RESPONSE, data = DataType(11, 1), data_addr = 11)),
    InterCgraPktType(payload = CgraPayloadType(cmd = CMD_LOAD_RESPONSE, data = DataType(14, 1), data_addr = 14)),
    InterCgraPktType(payload = CgraPayloadType(cmd = CMD_LOAD_RESPONSE, data = DataType(12, 1), data_addr = 12)),
]

from_tile_store_request_pkts = [
    InterCgraPktType(payload = CgraPayloadType(cmd = CMD_STORE_REQUEST, data = DataType(110, 1), data_addr = 11)),
    InterCgraPktType(payload = CgraPayloadType(cmd = CMD_STORE_REQUEST, data = DataType(300, 1), data_addr = 3)),
    InterCgraPktType(payload = CgraPayloadType(cmd = CMD_STORE_REQUEST, data = DataType(150, 1), data_addr = 15)),
]

# expected_to_mem_load_request_addr_msgs =  [DataAddrType(2)]
expected_to_mem_load_request_msgs =  [InterCgraPktType(payload = CgraPayloadType(cmd = CMD_LOAD_REQUEST,  data = DataType(0,  1), data_addr = 2))]

expected_to_mem_load_response_addr_msgs = [DataAddrType(8), DataAddrType(9)]
expected_to_mem_load_response = [
    InterCgraPktType(0,   0,  0,    0,    0,    0,    0,       0,       0,  0, CgraPayloadType(CMD_LOAD_RESPONSE, DataType(80, 1), data_addr = 8)),
    InterCgraPktType(0,   0,  0,    0,    0,    0,    0,       0,       0,  0, CgraPayloadType(CMD_LOAD_RESPONSE, DataType(90, 1), data_addr = 9))
]
# expected_to_mem_store_request_addr_msgs = [DataAddrType(5)]
# expected_to_mem_store_request_data_msgs = [DataType(50, 1)]
expected_to_mem_store_request_msgs =  [InterCgraPktType(payload = CgraPayloadType(cmd = CMD_STORE_REQUEST,  data = DataType(50,  1), data_addr = 5))]

from_noc_pkts = [
                   # src  dst src_x src_y dst_x dst_y src_tile dst_tile opq vc                 cmd
    InterCgraPktType(1,   0,  1,    0,    0,    0,    0,       0,       0,  0, CgraPayloadType(CMD_LOAD_REQUEST,  data = DataType(0,  1), data_addr = 2)),
    InterCgraPktType(2,   1,  2,    0,    1,    0,    0,       0,       0,  0, CgraPayloadType(CMD_LOAD_RESPONSE, data = DataType(80, 1), data_addr = 8)),
    InterCgraPktType(0,   1,  0,    0,    1,    0,    0,       0,       0,  0, CgraPayloadType(CMD_STORE_REQUEST, data = DataType(50, 1), data_addr = 5)),
    InterCgraPktType(0,   1,  0,    0,    1,    0,    0,       0,       0,  0, CgraPayloadType(CMD_LOAD_RESPONSE, data = DataType(90, 1), data_addr = 9)),

]

expected_to_noc_pkts = [
                   # src  dst src_x src_y dst_x dst_y src_tile dst_tile opq vc                 cmd
    InterCgraPktType(0,   0,  0,    0,    0,    0,    0,       0,       0,  0, CgraPayloadType(CMD_LOAD_REQUEST,  data = DataType(0,   0), data_addr = 1)),
    InterCgraPktType(0,   0,  0,    0,    0,    0,    0,       0,       0,  0, CgraPayloadType(CMD_LOAD_RESPONSE, data = DataType(11,  1), data_addr = 11)),
    InterCgraPktType(0,   2,  0,    0,    2,    0,    0,       0,       0,  0, CgraPayloadType(CMD_STORE_REQUEST, data = DataType(110, 1), data_addr = 11)),

    InterCgraPktType(0,   2,  0,    0,    2,    0,    0,       0,       0,  0, CgraPayloadType(CMD_LOAD_REQUEST,  data = DataType(0,   0), data_addr = 8)),
    InterCgraPktType(0,   0,  0,    0,    0,    0,    0,       0,       0,  0, CgraPayloadType(CMD_LOAD_RESPONSE, data = DataType(14,  1), data_addr = 14)),
    InterCgraPktType(0,   0,  0,    0,    0,    0,    0,       0,       0,  0, CgraPayloadType(CMD_STORE_REQUEST, data = DataType(300, 1), data_addr = 3)),

    InterCgraPktType(0,   3,  0,    0,    3,    0,    0,       0,       0,  0, CgraPayloadType(CMD_LOAD_REQUEST,  data = DataType(0,   0), data_addr = 13)),
    InterCgraPktType(0,   0,  0,    0,    0,    0,    0,       0,       0,  0, CgraPayloadType(CMD_LOAD_RESPONSE, data = DataType(12,  1), data_addr = 12)),
    InterCgraPktType(0,   3,  0,    0,    3,    0,    0,       0,       0,  0, CgraPayloadType(CMD_STORE_REQUEST, data = DataType(150, 1), data_addr = 15)),
]

def test_simple(cmdline_opts):
  print("[LOG] controller2addr_map: ", controller2addr_map)
  th = TestHarness(ControllerIdType,
                   IntraCgraPktType,
                   DataType,
                   DataAddrType,
                   InterCgraPktType,
                   cgra_id,
                   from_tile_load_request_pkts,
                   from_tile_load_response_pkts,
                   from_tile_store_request_pkts,
                   expected_to_mem_load_request_msgs,
                   expected_to_mem_load_response,
                   expected_to_mem_store_request_msgs,
                   from_noc_pkts,
                   expected_to_noc_pkts,
                   controller2addr_map,
                   idTo2d_map,
                   num_cgras,
                   num_tiles)
  th.elaborate()
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)

