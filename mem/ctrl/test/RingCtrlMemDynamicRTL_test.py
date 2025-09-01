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

class TestHarness(Component):

  def construct(s, DUT, DataType, PredicateType, CtrlPktType,
                CgraPayloadType, CtrlSignalType, ctrl_mem_size,
                width, height, data_mem_size, num_fu_inports,
                num_fu_outports, num_tile_inports, num_tile_outports,
                ctrl_pkts, sink_msgs):

    s.width = width
    s.height = height
    s.src_pkt = TestSrcRTL(CtrlPktType, ctrl_pkts)
    s.sink_out = [TestSinkRTL(CtrlSignalType, sink_msgs[i])
                  for i in range(width * height)]

    s.dut = \
        DUT(CtrlPktType, CgraPayloadType, DataType, CtrlSignalType,
            width, height, ctrl_mem_size,
            num_fu_inports, num_fu_outports,
            num_tile_inports, num_tile_outports,
            len(ctrl_pkts), len(ctrl_pkts))

    s.src_pkt.send //= s.dut.recv_pkt_from_controller
    for i in range(width * height):
      s.dut.send_ctrl[i] //= s.sink_out[i].recv

    s.dut.send_to_controller_pkt.rdy //= 0

  def done(s):
    if not s.src_pkt.done():
      return False
    for i in range(s.width * s.height):
      if not s.sink_out[i].done():
        return False
    return True

  def line_trace(s):
    return s.dut.line_trace()

def run_sim(test_harness, max_cycles = 40):
  test_harness.elaborate()
  test_harness.apply(DefaultPassGroup())
  test_harness.sim_reset()

  # Runs simulation.
  ncycles = 0
  print()
  print("{}:{}".format(ncycles, test_harness.line_trace()))
  while not test_harness.done() and ncycles < max_cycles:
    test_harness.sim_tick()
    ncycles += 1
    print("{}:{}".format( ncycles, test_harness.line_trace()))

  # Checks timeout.
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
  num_tiles = width * height
  num_commands = NUM_CMDS
  ctrl_action_nbits = clog2(num_commands)
  num_ctrl_operations = NUM_OPTS
  cgra_id_nbits = 4
  data_nbits = 32
  data_mem_size_global = 16
  addr_nbits = clog2(data_mem_size_global)
  predicate_nbits = 1
  num_registers_per_reg_bank = 16

  num_cgra_columns = 1
  num_cgra_rows = 1

  CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
  DataAddrType = mk_bits(addr_nbits)

  CtrlType = mk_ctrl(num_fu_inports,
                     num_fu_outports,
                     num_tile_inports,
                     num_tile_outports,
                     num_registers_per_reg_bank)

  CgraPayloadType = mk_cgra_payload(DataType,
                                    DataAddrType,
                                    CtrlType,
                                    CtrlAddrType)

  IntraCgraPktType = mk_intra_cgra_pkt(num_cgra_columns,
                                       num_cgra_rows,
                                       num_tiles,
                                       CgraPayloadType)

  FuInType = mk_bits(clog2(num_fu_inports + 1))
  pickRegister = [FuInType(x + 1) for x in range(num_fu_inports)]

  src_ctrl_pkt = [               # src dst                  opq vc
                  IntraCgraPktType(0,  0, 0, 0, 0, 0, 0, 0, 0,  0, CgraPayloadType(CMD_CONFIG, ctrl = CtrlType(OPT_ADD, pickRegister), ctrl_addr = 0)),
                  IntraCgraPktType(0,  1, 0, 0, 0, 0, 0, 0, 0,  0, CgraPayloadType(CMD_CONFIG, ctrl = CtrlType(OPT_SUB, pickRegister), ctrl_addr = 1)),
                  IntraCgraPktType(0,  2, 0, 0, 0, 0, 0, 0, 0,  0, CgraPayloadType(CMD_CONFIG, ctrl = CtrlType(OPT_SUB, pickRegister), ctrl_addr = 0)),
                  IntraCgraPktType(0,  3, 0, 0, 0, 0, 0, 0, 0,  0, CgraPayloadType(CMD_CONFIG, ctrl = CtrlType(OPT_ADD, pickRegister), ctrl_addr = 1)),
                  IntraCgraPktType(0,  3, 0, 0, 0, 0, 0, 0, 0,  0, CgraPayloadType(CMD_CONFIG, ctrl = CtrlType(OPT_SUB, pickRegister), ctrl_addr = 0)),
                  IntraCgraPktType(0,  0, 0, 0, 0, 0, 0, 0, 0,  0, CgraPayloadType(CMD_CONFIG, ctrl = CtrlType(OPT_SUB, pickRegister), ctrl_addr = 1)),
                  IntraCgraPktType(0,  0, 0, 0, 0, 0, 0, 0, 0,  0, CgraPayloadType(CMD_LAUNCH, ctrl = CtrlType(OPT_SUB, pickRegister), ctrl_addr = 0)),
                  IntraCgraPktType(0,  1, 0, 0, 0, 0, 0, 0, 0,  0, CgraPayloadType(CMD_CONFIG, ctrl = CtrlType(OPT_ADD, pickRegister), ctrl_addr = 0)),
                  IntraCgraPktType(0,  1, 0, 0, 0, 0, 0, 0, 0,  0, CgraPayloadType(CMD_LAUNCH, ctrl = CtrlType(OPT_SUB, pickRegister), ctrl_addr = 0)),
                  IntraCgraPktType(0,  2, 0, 0, 0, 0, 0, 0, 0,  0, CgraPayloadType(CMD_CONFIG, ctrl = CtrlType(OPT_ADD, pickRegister), ctrl_addr = 1)),
                  IntraCgraPktType(0,  2, 0, 0, 0, 0, 0, 0, 0,  0, CgraPayloadType(CMD_LAUNCH, ctrl = CtrlType(OPT_ADD, pickRegister), ctrl_addr = 0)),
                  IntraCgraPktType(0,  3, 0, 0, 0, 0, 0, 0, 0,  0, CgraPayloadType(CMD_LAUNCH, ctrl = CtrlType(OPT_ADD, pickRegister), ctrl_addr = 0))]

  sink_out = [
              [CtrlType(OPT_ADD, pickRegister),
               CtrlType(OPT_SUB, pickRegister)],
              # Ctrl memory 1 first write into address 1, then address 0.
              [CtrlType(OPT_ADD, pickRegister),
               CtrlType(OPT_SUB, pickRegister)],

              [CtrlType(OPT_SUB, pickRegister),
               CtrlType(OPT_ADD, pickRegister)],

              [CtrlType(OPT_SUB, pickRegister),
               CtrlType(OPT_ADD, pickRegister)]]

  th = TestHarness(MemUnit,
                   DataType,
                   PredicateType,
                   IntraCgraPktType,
                   CgraPayloadType,
                   CtrlType,
                   ctrl_mem_size,
                   width,
                   height,
                   data_mem_size,
                   num_fu_inports,
                   num_fu_outports,
                   num_tile_inports,
                   num_tile_outports,
                   src_ctrl_pkt,
                   sink_out)
  run_sim(th)

