'''
=========================================================================
ControllerRTL_test.py
=========================================================================
Simple test for ControllerRTL.

Author : Cheng Tan
  Date : Dec 15, 2024
'''

from pymtl3 import *
from pymtl3.stdlib.test_utils import config_model_with_cmdline_opts

from ..ControllerRTL import ControllerRTL
from ...lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ...lib.cmd_type import *
from ...lib.messages import *
from ...lib.opt_type import *
from ...noc.PyOCN.pymtl3_net.ocnlib.test.stream_sinks import NetSinkRTL as TestNetSinkRTL


#-------------------------------------------------------------------------
# TestHarness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, ControllerIdType, CpuPktType, CmdType, MsgType,
                AddrType, PktType, controller_id,
                from_tile_load_request_pkt_msgs,
                from_tile_load_response_pkt_msgs,
                from_tile_store_request_pkt_msgs,
                expected_to_tile_load_request_addr_msgs,
                expected_to_tile_load_response_data_msgs,
                expected_to_tile_store_request_addr_msgs,
                expected_to_tile_store_request_data_msgs,
                from_noc_pkts,
                expected_to_noc_pkts,
                controller2addr_map,
                idTo2d_map, num_terminals,
                complete_ctrl_pkt):

    cmp_func = lambda a, b : a == b # a.data == b.data

    s.src_from_tile_load_request_pkt_en_rdy = TestSrcRTL(PktType, from_tile_load_request_pkt_msgs)
    s.src_from_tile_load_response_pkt_en_rdy = TestSrcRTL(PktType, from_tile_load_response_pkt_msgs)
    s.src_from_tile_store_request_pkt_en_rdy = TestSrcRTL(PktType, from_tile_store_request_pkt_msgs)

    s.sink_to_tile_load_request_addr_en_rdy = TestSinkRTL(AddrType, expected_to_tile_load_request_addr_msgs)
    s.sink_to_tile_load_response_data_en_rdy = TestSinkRTL(MsgType, expected_to_tile_load_response_data_msgs)
    s.sink_to_tile_store_request_addr_en_rdy = TestSinkRTL(AddrType, expected_to_tile_store_request_addr_msgs)
    s.sink_to_tile_store_request_data_en_rdy = TestSinkRTL(MsgType, expected_to_tile_store_request_data_msgs)

    s.src_from_noc_val_rdy = TestSrcRTL(PktType, from_noc_pkts)
    s.sink_to_noc_val_rdy = TestNetSinkRTL(PktType, expected_to_noc_pkts, cmp_fn = cmp_func)
    s.execution_complete_cmd = TestSinkRTL(CpuPktType, complete_ctrl_pkt)

    s.dut = ControllerRTL(ControllerIdType, CmdType, CpuPktType,
                          PktType, MsgType, AddrType,
                          # Number of controllers globally (x/y dimension).
                          1, num_terminals,
                          controller2addr_map,
                          idTo2d_map)

    # Connections
    s.dut.controller_id //= controller_id
    s.src_from_tile_load_request_pkt_en_rdy.send //= s.dut.recv_from_tile_load_request_pkt
    s.src_from_tile_load_response_pkt_en_rdy.send //= s.dut.recv_from_tile_load_response_pkt
    s.src_from_tile_store_request_pkt_en_rdy.send //= s.dut.recv_from_tile_store_request_pkt

    s.dut.send_to_tile_load_request_addr //= s.sink_to_tile_load_request_addr_en_rdy.recv
    s.dut.send_to_tile_load_response_data //= s.sink_to_tile_load_response_data_en_rdy.recv
    s.dut.send_to_tile_store_request_addr //= s.sink_to_tile_store_request_addr_en_rdy.recv
    s.dut.send_to_tile_store_request_data //= s.sink_to_tile_store_request_data_en_rdy.recv

    s.src_from_noc_val_rdy.send //= s.dut.recv_from_noc
    s.dut.send_to_noc //= s.sink_to_noc_val_rdy.recv

    s.dut.recv_from_cpu_pkt.val //= 0
    s.dut.recv_from_cpu_pkt.msg //= CpuPktType()
    s.dut.send_to_ctrl_ring_pkt.rdy //= 0
    s.execution_complete_cmd.recv //= s.dut.send_to_cpu_pkt

  def done(s):
    return s.src_from_tile_load_request_pkt_en_rdy.done() and \
           s.src_from_tile_load_response_pkt_en_rdy.done() and \
           s.src_from_tile_store_request_pkt_en_rdy.done() and \
           s.sink_to_tile_load_request_addr_en_rdy.done() and \
           s.sink_to_tile_load_response_data_en_rdy.done() and \
           s.sink_to_tile_store_request_addr_en_rdy.done() and \
           s.sink_to_tile_store_request_data_en_rdy.done() and \
           s.src_from_noc_val_rdy.done() and \
           s.sink_to_noc_val_rdy.done()

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

def mk_src_pkts(nterminals, lst):
  src_pkts = [[] for _ in range(nterminals)]
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
DataType = mk_data(data_nbits, predicate_nbits)

nterminals = 4
ntiles = 4
CmdType = NUM_CMDS
cgra_id_nbits = 2
ControllerIdType = mk_bits(cgra_id_nbits)
num_commands = NUM_CMDS
ctrl_mem_size = 16
num_ctrl_operations = NUM_OPTS
num_fu_inports = 2
num_fu_outports = 2
num_tile_inports = 4
num_tile_outports = 4
data_mem_size_global = 16
addr_nbits = clog2(data_mem_size_global)
AddrType = mk_bits(addr_nbits)
num_registers_per_reg_bank = 16
controller_id = 1

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

CpuPktType = mk_intra_cgra_pkt(ntiles,
                                     cgra_id_nbits,
                                     num_commands,
                                     ctrl_mem_size,
                                     num_ctrl_operations,
                                     num_fu_inports,
                                     num_fu_outports,
                                     num_tile_inports,
                                     num_tile_outports,
                                     num_registers_per_reg_bank,
                                     addr_nbits,
                                     data_nbits,
                                     predicate_nbits)

Pkt = mk_multi_cgra_noc_pkt(nterminals, 1, ntiles,
                            addr_nbits = addr_nbits,
                            data_nbits = data_nbits,
                            predicate_nbits = predicate_nbits,
                            ctrl_actions = num_commands,
                            ctrl_mem_size = ctrl_mem_size,
                            ctrl_operations = num_ctrl_operations,
                            ctrl_fu_inports = num_fu_inports,
                            ctrl_fu_outports = num_fu_outports,
                            ctrl_tile_inports = num_tile_inports,
                            ctrl_tile_outports = num_tile_outports)

from_tile_load_request_pkts = [
    #   src  dst src_x src_y dst_x dst_y tile_id opq vc  addr data predicate payload ctrl_action       ctrl_addr ctrl_op ctrl_pred ctrl_fu ctrl_rou_xbar ctrl_fu_xbar ctrl_rou_pred
    Pkt(0,   0,  0,    0,    0,    0,    0,      0,  0,  1,   0,   1,        0,      CMD_LOAD_REQUEST, 0,        0,      0,        0,      0,               0,              0),
    Pkt(0,   0,  0,    0,    0,    0,    0,      0,  0,  8,   0,   1,        0,      CMD_LOAD_REQUEST, 0,        0,      0,        0,      0,               0,              0),
    Pkt(0,   0,  0,    0,    0,    0,    0,      0,  0,  13,  0,   1,        0,      CMD_LOAD_REQUEST, 0,        0,      0,        0,      0,               0,              0),
]

from_tile_load_response_pkts = [
    #   src  dst src_x src_y dst_x dst_y tile_id opq vc  addr data predicate payload ctrl_action       ctrl_addr ctrl_op ctrl_pred ctrl_fu ctrl_rou_xbar ctrl_fu_xbar ctrl_rou_pred
    Pkt(0,   0,  0,    0,    0,    0,    0,      0,  0,  11,  11,  1,        0,      CMD_LOAD_RESPONSE, 0,        0,      0,        0,      0,               0,              0),
    Pkt(0,   0,  0,    0,    0,    0,    0,      0,  0,  14,  14,  1,        0,      CMD_LOAD_RESPONSE, 0,        0,      0,        0,      0,               0,              0),
    Pkt(0,   0,  0,    0,    0,    0,    0,      0,  0,  12,  12,  1,        0,      CMD_LOAD_RESPONSE, 0,        0,      0,        0,      0,               0,              0),
]

from_tile_store_request_pkts = [
    #   src  dst src_x src_y dst_x dst_y tile_id opq vc  addr data predicate payload ctrl_action       ctrl_addr ctrl_op ctrl_pred ctrl_fu ctrl_rou_xbar ctrl_fu_xbar ctrl_rou_pred
    Pkt(0,   0,  0,    0,    0,    0,    0,      0,  0,  11,  110, 1,        0,      CMD_STORE_REQUEST, 0,        0,      0,        0,      0,               0,              0),
    Pkt(0,   0,  0,    0,    0,    0,    0,      0,  0,  3,   300, 1,        0,      CMD_STORE_REQUEST, 0,        0,      0,        0,      0,               0,              0),
    Pkt(0,   0,  0,    0,    0,    0,    0,      0,  0,  15,  150, 1,        0,      CMD_STORE_REQUEST, 0,        0,      0,        0,      0,               0,              0),
]

expected_to_tile_load_request_addr_msgs =  [AddrType(2)]
expected_to_tile_load_response_addr_msgs = [AddrType(8),     AddrType(9)]
expected_to_tile_load_response_data_msgs = [DataType(80, 1), DataType(90, 1)]
expected_to_tile_store_request_addr_msgs = [AddrType(5)]
expected_to_tile_store_request_data_msgs = [DataType(50, 1)]

from_noc_pkts = [
    #   src  dst src_x src_y dst_x dst_y tile_id opq vc addr data predicate payload ctrl_action        ctrl_addr ctrl_op ctrl_pred ctrl_fu ctrl_rou_xbar ctrl_fu_xbar ctrl_rou_pred
    Pkt(1,   0,  1,    0,    0,    0,    0,      0,  0, 2,   0,   1,        0,      CMD_LOAD_REQUEST,  0,        0,      0,        0,      0,               0,              0),
    Pkt(2,   1,  2,    0,    1,    0,    0,      0,  0, 8,   80,  1,        0,      CMD_LOAD_RESPONSE, 0,        0,      0,        0,      0,               0,              0),
    Pkt(0,   1,  0,    0,    1,    0,    0,      0,  0, 5,   50,  1,        0,      CMD_STORE_REQUEST, 0,        0,      0,        0,      0,               0,              0),
    Pkt(0,   1,  0,    0,    1,    0,    0,      0,  0, 9,   90,  1,        0,      CMD_LOAD_RESPONSE, 0,        0,      0,        0,      0,               0,              0),
]

expected_to_noc_pkts = [
    #   src  dst src_x src_y dst_x dst_y tile_id opq vc addr data predicate payload ctrl_action        ctrl_addr ctrl_op ctrl_pred ctrl_fu ctrl_rou_xbar ctrl_fu_xbar ctrl_rou_pred
    Pkt(1,   0,  1,    0,    0,    0,    0,      0,  0, 1,   0,   1,        0,      CMD_LOAD_REQUEST,  0,        0,      0,        0,      0,               0,              0),
    Pkt(1,   2,  1,    0,    2,    0,    0,      0,  0, 11,  11,  1,        0,      CMD_LOAD_RESPONSE, 0,        0,      0,        0,      0,               0,              0),
    Pkt(1,   2,  1,    0,    2,    0,    0,      0,  0, 11,  110, 1,        0,      CMD_STORE_REQUEST, 0,        0,      0,        0,      0,               0,              0),

    Pkt(1,   2,  1,    0,    2,    0,    0,      0,  0, 8,   0,   1,        0,      CMD_LOAD_REQUEST,  0,        0,      0,        0,      0,               0,              0),
    Pkt(1,   3,  1,    0,    3,    0,    0,      0,  0, 14,  14,  1,        0,      CMD_LOAD_RESPONSE, 0,        0,      0,        0,      0,               0,              0),
    Pkt(1,   0,  1,    0,    0,    0,    0,      0,  0, 3,   300, 1,        0,      CMD_STORE_REQUEST, 0,        0,      0,        0,      0,               0,              0),

    Pkt(1,   3,  1,    0,    3,    0,    0,      0,  0, 13,  0,   1,        0,      CMD_LOAD_REQUEST,  0,        0,      0,        0,      0,               0,              0),
    Pkt(1,   3,  1,    0,    3,    0,    0,      0,  0, 12,  12,  1,        0,      CMD_LOAD_RESPONSE, 0,        0,      0,        0,      0,               0,              0),
    Pkt(1,   3,  1,    0,    3,    0,    0,      0,  0, 15,  150, 1,        0,      CMD_STORE_REQUEST, 0,        0,      0,        0,      0,               0,              0),
]
complete_ctrl_pkt = [CpuPktType(0, 0, 0, 0, 0, ctrl_action = CMD_COMPLETE)]

def test_simple(cmdline_opts):
  print("controller2addr_map: ", controller2addr_map)
  th = TestHarness(ControllerIdType,
                   CpuPktType,
                   CmdType,
                   DataType,
                   AddrType,
                   Pkt,
                   controller_id,
                   from_tile_load_request_pkts,
                   from_tile_load_response_pkts,
                   from_tile_store_request_pkts,
                   # from_tile_load_response_data_msgs,
                   # from_tile_store_request_addr_msgs,
                   # from_tile_store_request_data_msgs,
                   expected_to_tile_load_request_addr_msgs,
                   expected_to_tile_load_response_data_msgs,
                   expected_to_tile_store_request_addr_msgs,
                   expected_to_tile_store_request_data_msgs,
                   from_noc_pkts,
                   expected_to_noc_pkts,
                   controller2addr_map,
                   idTo2d_map,
                   nterminals,
                   complete_ctrl_pkt)
  th.elaborate()
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)
