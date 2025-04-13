"""
==========================================================================
CtrlMemDynamicRTL_test.py
==========================================================================
Test cases for control memory with command-based action handling.

Author : Cheng Tan
  Date : Dec 21, 2024
"""
from ..CtrlMemDynamicRTL import CtrlMemDynamicRTL
from ....fu.single.AdderRTL import AdderRTL
from ....lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ....lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ....lib.cmd_type import *
from ....lib.messages import *
from ....lib.opt_type import *

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, MemUnit, DataType, PredicateType, CtrlPktType,
                CgraPayloadType, CtrlSignalType, ctrl_mem_size,
                data_mem_size, num_fu_inports, num_fu_outports,
                num_tile_inports, num_tile_outports, src0_msgs,
                src1_msgs, ctrl_pkts, sink_msgs, num_tiles,
                complete_signal_sink_out):

    AddrType = mk_bits(clog2(ctrl_mem_size))

    s.src_data0 = TestSrcRTL(DataType, src0_msgs)
    s.src_data1 = TestSrcRTL(DataType, src1_msgs)
    s.src_pkt = TestSrcRTL(CtrlPktType, ctrl_pkts)
    s.sink_out = TestSinkRTL(DataType, sink_msgs)
    s.complete_signal_sink_out = TestSinkRTL(CtrlPktType, complete_signal_sink_out)

    s.alu = AdderRTL(DataType, PredicateType, CtrlSignalType, 2, 2,
                     data_mem_size)
    s.ctrl_mem = MemUnit(CtrlPktType, CgraPayloadType, CtrlSignalType,
                         ctrl_mem_size, num_fu_inports, num_fu_outports,
                         num_tile_inports, num_tile_outports, 1, num_tiles,
                         len(ctrl_pkts) - 1, len(ctrl_pkts) - 1)

    s.alu.recv_opt //= s.ctrl_mem.send_ctrl
    s.src_pkt.send //= s.ctrl_mem.recv_pkt_from_controller
    s.complete_signal_sink_out.recv //= s.ctrl_mem.send_pkt_to_controller
    s.src_data0.send //= s.alu.recv_in[0]
    s.src_data1.send //= s.alu.recv_in[1]
    s.alu.send_out[0] //= s.sink_out.recv

  def done(s):
    return s.src_data0.done() and s.src_data1.done() and \
        s.src_pkt.done() and s.sink_out.done() and s.complete_signal_sink_out.done()

  def line_trace(s):
    return s.alu.line_trace() + " || " +s.ctrl_mem.line_trace()

def run_sim(test_harness, max_cycles = 20):
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
    print( "{}:{}".format(ncycles, test_harness.line_trace()))

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
  num_tiles = 4

  cgra_id_nbits = 4
  data_nbits = 32
  data_mem_size_global = 16
  addr_nbits = clog2(data_mem_size_global)
  DataAddrType = mk_bits(addr_nbits)
  predicate_nbits = 1
  num_registers_per_reg_bank = 16
  num_cgra_columns = 1
  num_cgra_rows = 1

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
                                       CgraPayloadType)

  IntraCgraPktType = mk_intra_cgra_pkt(num_cgra_columns,
                                       num_cgra_rows,
                                       num_tiles,
                                       CgraPayloadType)

  FuInType = mk_bits(clog2(num_fu_inports + 1))
  pick_register = [FuInType(x + 1) for x in range(num_fu_inports)]
  AddrType = mk_bits(clog2(ctrl_mem_size))
  src_data0 = [DataType(1, 1), DataType(5, 1), DataType(7, 1), DataType(6, 1)]
  src_data1 = [DataType(6, 1), DataType(1, 1), DataType(2, 1), DataType(3, 1)]
                                 # src dst src/dst x/y       opq vc ctrl_action ctrl_addr ctrl_operation ctrl_predicate ctrl_fu_in...
  src_ctrl_pkt = [IntraCgraPktType(0,  1,  0, 0, 0, 0, 0, 0, 0,  0, CgraPayloadType(CMD_CONFIG, ctrl = CtrlType(OPT_ADD, 0, pick_register), ctrl_addr = 0)),
                  IntraCgraPktType(0,  1,  0, 0, 0, 0, 0, 0, 0,  0, CgraPayloadType(CMD_CONFIG, ctrl = CtrlType(OPT_SUB, 0, pick_register), ctrl_addr = 1)),
                  IntraCgraPktType(0,  1,  0, 0, 0, 0, 0, 0, 0,  0, CgraPayloadType(CMD_CONFIG, ctrl = CtrlType(OPT_SUB, 0, pick_register), ctrl_addr = 2)),
                  IntraCgraPktType(0,  1,  0, 0, 0, 0, 0, 0, 0,  0, CgraPayloadType(CMD_CONFIG, ctrl = CtrlType(OPT_ADD, 0, pick_register), ctrl_addr = 3)),
                  IntraCgraPktType(0,  1,  0, 0, 0, 0, 0, 0, 0,  0, CgraPayloadType(CMD_LAUNCH, ctrl = CtrlType(OPT_NAH, 0, pick_register), ctrl_addr = 0))]

  sink_out = [DataType(7, 1), DataType(4, 1), DataType(5, 1), DataType(9, 1)]
  complete_signal_sink_out = [
      IntraCgraPktType(0,  num_tiles,  0, 0, 0, 0, 0, 0, 0,  0, CgraPayloadType(CMD_COMPLETE))]

  th = TestHarness(MemUnit,
                   DataType,
                   PredicateType,
                   IntraCgraPktType,
                   CgraPayloadType,
                   CtrlType,
                   ctrl_mem_size,
                   data_mem_size,
                   num_fu_inports,
                   num_fu_outports,
                   num_tile_inports,
                   num_tile_outports,
                   src_data0,
                   src_data1,
                   src_ctrl_pkt,
                   sink_out,
                   num_tiles,
                   complete_signal_sink_out)
  run_sim(th)

