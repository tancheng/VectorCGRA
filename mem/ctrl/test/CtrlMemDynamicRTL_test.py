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
from ....fu.single.RetRTL import RetRTL
from ....lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ....lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ....lib.cmd_type import *
from ....lib.messages import *
from ....lib.opt_type import *

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------
class TestHarness(Component):
  def construct(s, MemUnit, DataType, CtrlPktType,
                CgraPayloadType, CtrlSignalType, ctrl_mem_size,
                data_mem_size, num_fu_inports, num_fu_outports,
                num_tile_inports, num_tile_outports, src0_msgs,
                src1_msgs, ctrl_pkts, sink_msgs, num_tiles,
                complete_signal_sink_out, ctrl_count_per_iter,
                total_ctrl_steps_val, FuType):

    s.src_data0 = TestSrcRTL(DataType, src0_msgs)
    s.src_data1 = TestSrcRTL(DataType, src1_msgs)
    s.src_pkt = TestSrcRTL(CtrlPktType, ctrl_pkts)
    s.sink_out = TestSinkRTL(DataType, sink_msgs)
    s.complete_signal_sink_out = TestSinkRTL(CtrlPktType, complete_signal_sink_out)

    s.fu = FuType(DataType, CtrlSignalType, 2, 2,
                  data_mem_size, ctrl_mem_size)
    s.ctrl_mem = MemUnit(CtrlPktType, CgraPayloadType,
                         ctrl_mem_size, num_fu_inports, num_fu_outports,
                         num_tile_inports, num_tile_outports, 1, num_tiles,
                         ctrl_count_per_iter, total_ctrl_steps_val)

    # Connections.
    if isinstance(s.fu, RetRTL):
      s.fu.send_to_ctrl_mem //= s.ctrl_mem.recv_from_element
    s.fu.recv_opt //= s.ctrl_mem.send_ctrl
    s.src_pkt.send //= s.ctrl_mem.recv_pkt_from_controller
    s.complete_signal_sink_out.recv //= s.ctrl_mem.send_pkt_to_controller
    s.src_data0.send //= s.fu.recv_in[0]
    s.src_data1.send //= s.fu.recv_in[1]
    s.fu.send_out[0] //= s.sink_out.recv

  def done(s):
    return s.src_data0.done() and s.src_data1.done() and \
           s.src_pkt.done() and s.sink_out.done() and s.complete_signal_sink_out.done()

  def line_trace(s):
    return s.fu.line_trace() + " || " +s.ctrl_mem.line_trace()

def run_sim(test_harness, max_cycles = 20):
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
    print( "{}:{}".format(ncycles, test_harness.line_trace()))

  # Checks timeout.
  assert ncycles < max_cycles

  test_harness.sim_tick()
  test_harness.sim_tick()
  test_harness.sim_tick()

def test_ctrl():
  MemUnit = CtrlMemDynamicRTL
  data_nbits = 16
  DataType = mk_data(data_nbits, 1)
  PredicateType = mk_predicate(1, 1)
  ctrl_mem_size = 16
  num_fu_inports = 2
  num_fu_outports = 2
  num_tile_inports = 4
  num_tile_outports = 4
  num_tiles = 4

  cgra_id_nbits = 4
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

  IntraCgraPktType = mk_intra_cgra_pkt(num_cgra_columns,
                                       num_cgra_rows,
                                       num_tiles,
                                       CgraPayloadType)

  FuInType = mk_bits(clog2(num_fu_inports + 1))
  pick_register = [FuInType(x + 1) for x in range(num_fu_inports)]
  src_data0 = [DataType(1, 1), DataType(5, 1), DataType(7, 1), DataType(6, 1)]
  src_data1 = [DataType(6, 1), DataType(1, 1), DataType(2, 1), DataType(3, 1)]
                                 # src dst src/dst x/y       opq vc ctrl_action ctrl_addr ctrl_operation ctrl_predicate ctrl_fu_in...
  src_ctrl_pkt = [IntraCgraPktType(0,  1,  0, 0, 0, 0, 0, 0, 0,  0, CgraPayloadType(CMD_CONFIG, ctrl = CtrlType(OPT_ADD, pick_register), ctrl_addr = 0)),
                  IntraCgraPktType(0,  1,  0, 0, 0, 0, 0, 0, 0,  0, CgraPayloadType(CMD_CONFIG, ctrl = CtrlType(OPT_SUB, pick_register), ctrl_addr = 1)),
                  IntraCgraPktType(0,  1,  0, 0, 0, 0, 0, 0, 0,  0, CgraPayloadType(CMD_CONFIG, ctrl = CtrlType(OPT_SUB, pick_register), ctrl_addr = 2)),
                  IntraCgraPktType(0,  1,  0, 0, 0, 0, 0, 0, 0,  0, CgraPayloadType(CMD_CONFIG, ctrl = CtrlType(OPT_ADD, pick_register), ctrl_addr = 3)),
                  IntraCgraPktType(0,  1,  0, 0, 0, 0, 0, 0, 0,  0, CgraPayloadType(CMD_LAUNCH, ctrl = CtrlType(OPT_NAH, pick_register), ctrl_addr = 0))]

  sink_out = [DataType(7, 1), DataType(4, 1), DataType(5, 1), DataType(9, 1)]
  complete_signal_sink_out = [
      IntraCgraPktType(0,  num_tiles,  0, 0, 0, 0, 0, 0, 0,  0, CgraPayloadType(CMD_COMPLETE))]
  
  ctrl_count_per_iter = len(src_ctrl_pkt) - 1
  total_ctrl_steps_val = len(src_ctrl_pkt) - 1

  th = TestHarness(MemUnit,
                   DataType,
                   IntraCgraPktType,
                   CgraPayloadType,
                   CtrlType,
                   ctrl_mem_size,
                   data_mem_size_global,
                   num_fu_inports,
                   num_fu_outports,
                   num_tile_inports,
                   num_tile_outports,
                   src_data0,
                   src_data1,
                   src_ctrl_pkt,
                   sink_out,
                   num_tiles,
                   complete_signal_sink_out,
                   ctrl_count_per_iter,
                   total_ctrl_steps_val,
                   AdderRTL)
  run_sim(th)

def test_ctrl_bound():
  MemUnit = CtrlMemDynamicRTL
  data_nbits = 16
  DataType = mk_data(data_nbits, 1)
  ctrl_mem_size = 16
  num_fu_inports = 2
  num_fu_outports = 2
  num_tile_inports = 4
  num_tile_outports = 4
  num_tiles = 4

  cgra_id_nbits = 4
  data_mem_size_global = 16
  addr_nbits = clog2(data_mem_size_global)
  DataAddrType = mk_bits(addr_nbits)
  predicate_nbits = 1
  num_registers_per_reg_bank = 16
  num_cgra_columns = 1
  num_cgra_rows = 1

  # 1 iter has 2 ctrl signals.
  ctrl_count_per_iter = 2
  # Only executes for 1 iter.
  total_ctrl_steps_val = 2


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

  IntraCgraPktType = mk_intra_cgra_pkt(num_cgra_columns,
                                       num_cgra_rows,
                                       num_tiles,
                                       CgraPayloadType)

  FuInType = mk_bits(clog2(num_fu_inports + 1))
  pick_register = [FuInType(x + 1) for x in range(num_fu_inports)]
  src_data0 = [DataType(1, 1), DataType(5, 1)]
  src_data1 = [DataType(6, 1), DataType(1, 1)]
                                 # src dst src/dst x/y       opq vc ctrl_action ctrl_addr ctrl_operation ctrl_predicate ctrl_fu_in...
  src_ctrl_pkt = [IntraCgraPktType(0,  1,  0, 0, 0, 0, 0, 0, 0,  0, CgraPayloadType(CMD_CONFIG, ctrl = CtrlType(OPT_ADD, pick_register), ctrl_addr = 0)),
                  IntraCgraPktType(0,  1,  0, 0, 0, 0, 0, 0, 0,  0, CgraPayloadType(CMD_CONFIG, ctrl = CtrlType(OPT_SUB, pick_register), ctrl_addr = 1)),
                  IntraCgraPktType(0,  1,  0, 0, 0, 0, 0, 0, 0,  0, CgraPayloadType(CMD_CONFIG, ctrl = CtrlType(OPT_SUB, pick_register), ctrl_addr = 2)),
                  IntraCgraPktType(0,  1,  0, 0, 0, 0, 0, 0, 0,  0, CgraPayloadType(CMD_CONFIG, ctrl = CtrlType(OPT_ADD, pick_register), ctrl_addr = 3)),
                  # Although there are 4 ctrl signals shown above, this testcase only selects 2 of them by specifying CMD_CONFIG_COUNT_PER_ITER = 2 (predicate = 1).
                  IntraCgraPktType(0,  1,  0, 0, 0, 0, 0, 0, 0,  0, CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(ctrl_count_per_iter, 1))),
                  # Then specifies the start address of the selected ctrl signals using CMD_CONFIG_CTRL_LOWER_BOUND.
                  # Here, CMD_CONFIG_CTRL_LOWER_BOUND = 1 represents that ctrl signals whose ctrl_addr among
                  # [CMD_CONFIG_CTRL_LOWER_BOUND, CMD_CONFIG_CTRL_LOWER_BOUND + CMD_CONFIG_COUNT_PER_ITER), i.e., [1, 3) in this case
                  # are selected and send to the tile iteratively.
                  IntraCgraPktType(0,  1,  0, 0, 0, 0, 0, 0, 0,  0, CgraPayloadType(CMD_CONFIG_CTRL_LOWER_BOUND, data = DataType(1, 1))),
                  IntraCgraPktType(0,  1,  0, 0, 0, 0, 0, 0, 0,  0, CgraPayloadType(CMD_LAUNCH, ctrl = CtrlType(OPT_NAH, pick_register), ctrl_addr = 0))]

  # As ctrl signals with ctrl_addr = 1 and ctrl_addr = 2 are both OPT_SUB,
  # The outputs are    1-6              5-1
  sink_out = [DataType(-5, 1), DataType(4, 1)]
  complete_signal_sink_out = [
      IntraCgraPktType(0,  num_tiles,  0, 0, 0, 0, 0, 0, 0,  0, CgraPayloadType(CMD_COMPLETE))]
  
  th = TestHarness(MemUnit,
                   DataType,
                   IntraCgraPktType,
                   CgraPayloadType,
                   CtrlType,
                   ctrl_mem_size,
                   data_mem_size_global,
                   num_fu_inports,
                   num_fu_outports,
                   num_tile_inports,
                   num_tile_outports,
                   src_data0,
                   src_data1,
                   src_ctrl_pkt,
                   sink_out,
                   num_tiles,
                   complete_signal_sink_out,
                   ctrl_count_per_iter,
                   total_ctrl_steps_val,
                   AdderRTL)
  run_sim(th)

def test_return():
  MemUnit = CtrlMemDynamicRTL
  data_nbits = 16
  DataType = mk_data(data_nbits, 1)
  ctrl_mem_size = 16
  num_fu_inports = 2
  num_fu_outports = 2
  num_tile_inports = 4
  num_tile_outports = 4
  num_tiles = 4

  cgra_id_nbits = 4
  data_mem_size_global = 16
  addr_nbits = clog2(data_mem_size_global)
  DataAddrType = mk_bits(addr_nbits)
  predicate_nbits = 1
  num_registers_per_reg_bank = 16
  num_cgra_columns = 1
  num_cgra_rows = 1

  # 1 iter has 3 ctrl signals.
  ctrl_count_per_iter = 3
  # Only executes for 1 iter.
  total_ctrl_steps_val = 3


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

  IntraCgraPktType = mk_intra_cgra_pkt(num_cgra_columns,
                                       num_cgra_rows,
                                       num_tiles,
                                       CgraPayloadType)

  FuInType = mk_bits(clog2(num_fu_inports + 1))
  pick_register = [FuInType(x + 1) for x in range(num_fu_inports)]
  src_data0 = [DataType(5, 0), DataType(6, 1)]
  src_data1 = []
                                 # src dst src/dst x/y       opq vc ctrl_action ctrl_addr ctrl_operation ctrl_predicate ctrl_fu_in...
  src_ctrl_pkt = [IntraCgraPktType(0,  1,  0, 0, 0, 0, 0, 0, 0,  0, CgraPayloadType(CMD_CONFIG, ctrl = CtrlType(OPT_ADD, pick_register), ctrl_addr = 0)),
                  IntraCgraPktType(0,  1,  0, 0, 0, 0, 0, 0, 0,  0, CgraPayloadType(CMD_CONFIG, ctrl = CtrlType(OPT_RET, pick_register), ctrl_addr = 1)),
                  IntraCgraPktType(0,  1,  0, 0, 0, 0, 0, 0, 0,  0, CgraPayloadType(CMD_CONFIG, ctrl = CtrlType(OPT_RET, pick_register), ctrl_addr = 2)),
                  IntraCgraPktType(0,  1,  0, 0, 0, 0, 0, 0, 0,  0, CgraPayloadType(CMD_CONFIG, ctrl = CtrlType(OPT_ADD, pick_register), ctrl_addr = 3)),
                  # Although there are 4 ctrl signals shown above, this testcase only selects 2 of them by specifying CMD_CONFIG_COUNT_PER_ITER = 3 (predicate = 1).
                  IntraCgraPktType(0,  1,  0, 0, 0, 0, 0, 0, 0,  0, CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(ctrl_count_per_iter, 1))),
                  # Then specifies the start address of the selected ctrl signals using CMD_CONFIG_CTRL_LOWER_BOUND.
                  # Here, CMD_CONFIG_CTRL_LOWER_BOUND = 1 represents that ctrl signals whose ctrl_addr among
                  # [CMD_CONFIG_CTRL_LOWER_BOUND, CMD_CONFIG_CTRL_LOWER_BOUND + CMD_CONFIG_COUNT_PER_ITER), i.e., [1, 4) in this case
                  # are selected and send to the tile iteratively.
                  IntraCgraPktType(0,  1,  0, 0, 0, 0, 0, 0, 0,  0, CgraPayloadType(CMD_CONFIG_CTRL_LOWER_BOUND, data = DataType(1, 1))),
                  IntraCgraPktType(0,  1,  0, 0, 0, 0, 0, 0, 0,  0, CgraPayloadType(CMD_LAUNCH, ctrl = CtrlType(OPT_NAH, pick_register), ctrl_addr = 0))]

  # This test only has RetRTL is connected to ctrl mem, so cannot
  # perform other functionalities.
  sink_out = []
  # Though we have two RET opcodes/instructions need to be executed,
  # only the second one has the predicate as true, leadint to single
  # expected output.
  complete_signal_sink_out = [
      IntraCgraPktType(0,  num_tiles,  0, 0, 0, 0, 0, 0, 0,  0, CgraPayloadType(CMD_COMPLETE, DataType(6, 1, 0, 0), ctrl = CtrlType(OPT_RET, pick_register)))]

  th = TestHarness(MemUnit,
                   DataType,
                   IntraCgraPktType,
                   CgraPayloadType,
                   CtrlType,
                   ctrl_mem_size,
                   data_mem_size_global,
                   num_fu_inports,
                   num_fu_outports,
                   num_tile_inports,
                   num_tile_outports,
                   src_data0,
                   src_data1,
                   src_ctrl_pkt,
                   sink_out,
                   num_tiles,
                   complete_signal_sink_out,
                   ctrl_count_per_iter,
                   total_ctrl_steps_val,
                   RetRTL)
  run_sim(th)
