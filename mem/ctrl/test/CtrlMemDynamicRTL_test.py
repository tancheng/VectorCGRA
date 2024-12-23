"""
==========================================================================
CtrlMemDynamicRTL_test.py
==========================================================================
Test cases for control memory with command-based action handling.

Author : Cheng Tan
  Date : Dec 21, 2024
"""

from pymtl3 import *
from ..CtrlMemDynamicRTL import CtrlMemDynamicRTL
from ....fu.single.AdderRTL import AdderRTL
from ....lib.basic.en_rdy.test_sinks import TestSinkRTL
from ....lib.basic.en_rdy.test_srcs import TestSrcRTL
from ....lib.basic.val_rdy.SourceRTL import SourceRTL as ValRdyTestSrcRTL
from ....lib.messages import *
from ....lib.cmd_type import *
from ....lib.opt_type import *

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness( Component ):

  def construct( s, MemUnit, DataType, PredicateType, CtrlPktType,
                 CtrlSignalType, ctrl_mem_size, data_mem_size,
                 num_fu_inports, num_fu_outports, num_tile_inports,
                 num_tile_outports, src0_msgs, src1_msgs, ctrl_pkts,
                 sink_msgs):

    AddrType = mk_bits(clog2(ctrl_mem_size))

    s.src_data0 = TestSrcRTL(DataType, src0_msgs)
    s.src_data1 = TestSrcRTL(DataType, src1_msgs)
    # s.src_waddr = TestSrcRTL(AddrType, ctrl_waddr )
    # s.src_wdata = TestSrcRTL(ConfigType, ctrl_msgs  )
    s.src_pkt = ValRdyTestSrcRTL(CtrlPktType, ctrl_pkts)
    s.sink_out = TestSinkRTL(DataType, sink_msgs)

    s.alu = AdderRTL(DataType, PredicateType, CtrlSignalType, 2, 2,
                     data_mem_size )
    s.ctrl_mem = MemUnit(CtrlPktType, CtrlSignalType, ctrl_mem_size,
                         num_fu_inports, num_fu_outports, num_tile_inports,
                         num_tile_outports, len(ctrl_pkts), len(ctrl_pkts))

    s.alu.recv_in_count[0] //= 1
    s.alu.recv_in_count[1] //= 1

    connect(s.alu.recv_opt, s.ctrl_mem.send_ctrl)

    # connect(s.src_waddr.send, s.ctrl_mem.recv_waddr)
    # connect(s.src_wdata.send, s.ctrl_mem.recv_ctrl)
    connect(s.src_pkt.send, s.ctrl_mem.recv_pkt)

    connect(s.src_data0.send, s.alu.recv_in[0])
    connect(s.src_data1.send, s.alu.recv_in[1])
    connect(s.alu.send_out[0], s.sink_out.recv)

  def done(s):
    return s.src_data0.done() and s.src_data1.done() and \
           s.src_pkt.done() and s.sink_out.done()

  def line_trace( s ):
    return s.alu.line_trace() + " || " +s.ctrl_mem.line_trace()

def run_sim( test_harness, max_cycles=20 ):
  test_harness.elaborate()
  test_harness.apply( DefaultPassGroup() )
  test_harness.sim_reset()

  # Run simulation

  ncycles = 0
  print()
  print( "{}:{}".format( ncycles, test_harness.line_trace() ))
  while not test_harness.done() and ncycles < max_cycles:
    test_harness.sim_tick()
    ncycles += 1
    print( "{}:{}".format( ncycles, test_harness.line_trace() ))

  # Check timeout

  assert ncycles < max_cycles

  test_harness.sim_tick()
  test_harness.sim_tick()
  test_harness.sim_tick()

def test_Ctrl():
  MemUnit = CtrlMemDynamicRTL
  DataType = mk_data(16, 1)
  PredicateType = mk_predicate(1, 1)
  ctrl_mem_size = 16
  ctrl_addr_nbits = clog2(ctrl_mem_size)
  data_mem_size = 8
  num_fu_inports = 2
  num_fu_outports = 2
  num_tile_inports = 4
  num_tile_outports = 4
  num_terminals = 4
  num_ctrl_actions = 6
  ctrl_action_nbits = clog2(num_ctrl_actions)
  num_ctrl_operations = 64
  CtrlPktType = mk_ring_across_tiles_pkt(num_terminals,
                                         num_ctrl_actions,
                                         ctrl_mem_size,
                                         num_ctrl_operations,
                                         num_fu_inports,
                                         num_fu_outports,
                                         num_tile_inports,
                                         num_tile_outports)
  CtrlSignalType = mk_separate_ctrl(num_ctrl_operations,
                                    num_fu_inports,
                                    num_fu_outports,
                                    num_tile_inports,
                                    num_tile_outports)
  FuInType = mk_bits(clog2(num_fu_inports + 1))
  pickRegister = [FuInType(x + 1) for x in range(num_fu_inports)]
  AddrType = mk_bits(clog2(ctrl_mem_size))
  src_data0 = [DataType(1, 1), DataType(5, 1), DataType(7, 1), DataType(6, 1)]
  src_data1 = [DataType(6, 1), DataType(1, 1), DataType(2, 1), DataType(3, 1)]

  src_ctrl_pkt = [CtrlPktType(0, 1, 0, 0, CMD_CONFIG, 0, OPT_ADD, b1(0), pickRegister),
                  CtrlPktType(0, 1, 0, 0, CMD_CONFIG, 1, OPT_SUB, b1(0), pickRegister),
                  CtrlPktType(0, 1, 0, 0, CMD_CONFIG, 2, OPT_SUB, b1(0), pickRegister),
                  CtrlPktType(0, 1, 0, 0, CMD_CONFIG, 3, OPT_ADD, b1(0), pickRegister),
                  CtrlPktType(0, 1, 0, 0, CMD_LAUNCH, 0, OPT_ADD, b1(0), pickRegister)]

  sink_out = [DataType(7, 1), DataType(4, 1), DataType(5, 1), DataType(9, 1)]
  th = TestHarness(MemUnit, DataType, PredicateType, CtrlPktType, CtrlSignalType,
                   ctrl_mem_size, data_mem_size, num_fu_inports, num_fu_outports,
                   num_tile_inports, num_tile_outports, src_data0, src_data1,
                   src_ctrl_pkt, sink_out)
  run_sim(th)

