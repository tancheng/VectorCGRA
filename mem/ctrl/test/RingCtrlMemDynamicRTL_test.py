"""
==========================================================================
CtrlMemDynamicRTL_test.py
==========================================================================
Test cases for control memory with command-based action handling.

Author : Cheng Tan
  Date : Dec 21, 2024
"""

from pymtl3 import *
from ..RingMultiCtrlMemDynamicRTL import RingMultiCtrlMemDynamicRTL
from ....fu.single.AdderRTL import AdderRTL
from ....lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ....lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ....lib.messages import *
from ....lib.cmd_type import *
from ....lib.opt_type import *

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness( Component ):

  def construct( s, DUT, DataType, PredicateType, CtrlPktType,
                 CtrlSignalType, ctrl_mem_size, width, height,
                 data_mem_size, num_fu_inports, num_fu_outports,
                 num_tile_inports, num_tile_outports, ctrl_pkts,
                 sink_msgs, complete_signal_sink_out):

    s.width = width
    s.height = height
    s.src_pkt = TestSrcRTL(CtrlPktType, ctrl_pkts)
    s.sink_out = [TestSinkRTL(CtrlSignalType, sink_msgs[i])
                  for i in range(width * height)]
    s.complete_signal_sink_out = TestSinkRTL(CtrlPktType, complete_signal_sink_out)

    s.dut = \
        DUT(CtrlPktType, CtrlSignalType, width, height,
            ctrl_mem_size, num_fu_inports, num_fu_outports,
            num_tile_inports, num_tile_outports,
            len(ctrl_pkts), len(ctrl_pkts))

    connect(s.src_pkt.send, s.dut.recv_pkt_from_controller)
    s.complete_signal_sink_out.recv //= s.dut.send_to_controller_pkt
    for i in range(width * height):
      connect(s.dut.send_ctrl[i], s.sink_out[i].recv)

  def done(s):
    if not s.src_pkt.done():
      return False
    for i in range(s.width * s.height):
      if not s.sink_out[i].done():
        return False
    return s.complete_signal_sink_out.done()

  def line_trace(s):
    return s.dut.line_trace()

def run_sim(test_harness, max_cycles = 40):
  test_harness.elaborate()
  test_harness.apply(DefaultPassGroup())
  test_harness.sim_reset()

  # Run simulation
  ncycles = 0
  print()
  print("{}:{}".format(ncycles, test_harness.line_trace()))
  while not test_harness.done() and ncycles < max_cycles:
    test_harness.sim_tick()
    ncycles += 1
    print("{}:{}".format( ncycles, test_harness.line_trace()))

  # Check timeout

  assert ncycles < max_cycles

  test_harness.sim_tick()
  test_harness.sim_tick()
  test_harness.sim_tick()

def test_Ctrl():
  MemUnit = RingMultiCtrlMemDynamicRTL
  DataType = mk_data(16, 1)
  PredicateType = mk_predicate(1, 1)
  ctrl_mem_size = 16
  ctrl_addr_nbits = clog2(ctrl_mem_size)
  data_mem_size = 8
  num_fu_inports = 2
  num_fu_outports = 2
  num_tile_inports = 4
  num_tile_outports = 4
  width = 2
  height = 2
  num_terminals = width * height
  num_commands = NUM_CMDS
  ctrl_action_nbits = clog2(num_commands)
  num_ctrl_operations = NUM_OPTS
  cgra_id_nbits = 4
  data_nbits = 32
  data_mem_size_global = 16
  addr_nbits = clog2(data_mem_size_global)
  predicate_nbits = 1
  num_registers_per_reg_bank = 16

  CtrlPktType = \
        mk_intra_cgra_pkt(num_terminals,
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

  CtrlSignalType = mk_separate_reg_ctrl(num_ctrl_operations,
                                        num_fu_inports,
                                        num_fu_outports,
                                        num_tile_inports,
                                        num_tile_outports,
                                        num_registers_per_reg_bank)
  FuInType = mk_bits(clog2(num_fu_inports + 1))
  pickRegister = [FuInType(x + 1) for x in range(num_fu_inports)]

  src_ctrl_pkt = [          # dst_cgra_id src dst opaque vc_id ctrl_action ctrl_addr ctrl_operation ctrl_predicate ctrl_fu_in...
                  CtrlPktType(0,          0,  0,  0,     0,    CMD_CONFIG, 0,        OPT_ADD,       b1(0),         pickRegister),
                  CtrlPktType(0,          0,  1,  0,     0,    CMD_CONFIG, 1,        OPT_SUB,       b1(0),         pickRegister),
                  CtrlPktType(0,          0,  2,  0,     0,    CMD_CONFIG, 0,        OPT_SUB,       b1(0),         pickRegister),
                  CtrlPktType(0,          0,  3,  0,     0,    CMD_CONFIG, 1,        OPT_ADD,       b1(0),         pickRegister),
                  CtrlPktType(0,          0,  3,  0,     0,    CMD_CONFIG, 0,        OPT_SUB,       b1(0),         pickRegister),
                  CtrlPktType(0,          0,  0,  0,     0,    CMD_CONFIG, 1,        OPT_SUB,       b1(0),         pickRegister),
                  CtrlPktType(0,          0,  0,  0,     0,    CMD_LAUNCH, 0,        OPT_SUB,       b1(0),         pickRegister),
                  CtrlPktType(0,          0,  1,  0,     0,    CMD_CONFIG, 0,        OPT_ADD,       b1(0),         pickRegister),
                  CtrlPktType(0,          0,  1,  0,     0,    CMD_LAUNCH, 0,        OPT_SUB,       b1(0),         pickRegister),
                  CtrlPktType(0,          0,  2,  0,     0,    CMD_CONFIG, 1,        OPT_ADD,       b1(0),         pickRegister),
                  CtrlPktType(0,          0,  2,  0,     0,    CMD_LAUNCH, 0,        OPT_ADD,       b1(0),         pickRegister),
                  CtrlPktType(0,          0,  3,  0,     0,    CMD_LAUNCH, 0,        OPT_ADD,       b1(0),         pickRegister)]

  sink_out = [
              [CtrlSignalType(OPT_ADD, 0, pickRegister),
               CtrlSignalType(OPT_SUB, 0, pickRegister)],
              # Ctrl memory 1 first write into address 1, then address 0.
              [CtrlSignalType(OPT_ADD, 0, pickRegister),
               CtrlSignalType(OPT_SUB, 0, pickRegister)],

              [CtrlSignalType(OPT_SUB, 0, pickRegister),
               CtrlSignalType(OPT_ADD, 0, pickRegister)],

              [CtrlSignalType(OPT_SUB, 0, pickRegister),
               CtrlSignalType(OPT_ADD, 0, pickRegister)]]

  # vc_id needs to be 1 due to the message might traverse across the date line via ring.
  #                                       dst_cgra_id, src, dst,           opaque, vc, ctrl_action
  complete_signal_sink_out = [CtrlPktType(0,           0,   num_terminals, 0,      1,  ctrl_action = CMD_COMPLETE)]
  th = TestHarness(MemUnit, DataType, PredicateType, CtrlPktType, CtrlSignalType,
                   ctrl_mem_size, width, height, data_mem_size, num_fu_inports,
                   num_fu_outports, num_tile_inports, num_tile_outports,
                   src_ctrl_pkt, sink_out, complete_signal_sink_out)
  run_sim(th)

