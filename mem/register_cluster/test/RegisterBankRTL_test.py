"""
==========================================================================
RegisterBankRTL_test.py
==========================================================================
Test cases for RegisterBankRTL.

Author : Cheng Tan
  Date : Feb 7, 2025
"""

from pymtl3 import *
from ..RegisterBankRTL import RegisterBankRTL
from ....lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ....lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ....lib.messages import *
from ....lib.opt_type import *
from ....lib.util.common import *

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness( Component ):

  def construct(s, DataType, ConfigType, reg_bank_id, num_registers,
                src_opt, src_msgs, sink_msgs):

    s.sink = TestSinkRTL(DataType, sink_msgs)

    s.reg_bank = RegisterBankRTL(DataType, ConfigType, reg_bank_id,
                                 num_registers)

    s.reg_bank.inport_wdata[PORT_ROUTING_CROSSBAR] //= src_msgs[PORT_ROUTING_CROSSBAR]
    s.reg_bank.inport_wdata[PORT_FU_CROSSBAR] //= src_msgs[PORT_FU_CROSSBAR]
    s.reg_bank.inport_wdata[PORT_CONST] //= src_msgs[PORT_CONST]
    s.reg_bank.inport_valid[PORT_ROUTING_CROSSBAR] //= 1
    s.reg_bank.inport_valid[PORT_FU_CROSSBAR] //= 1
    s.reg_bank.inport_valid[PORT_CONST] //= 1
    s.reg_bank.inport_opt //= src_opt
    s.reg_bank.send_data_to_fu //= s.sink.recv

  def done(s):
    return s.sink.done()

  def line_trace(s):
    return s.reg_bank.line_trace()

def run_sim(test_harness, max_cycles = 10):
  test_harness.elaborate()
  test_harness.apply(DefaultPassGroup())
  test_harness.sim_reset()

  # Run simulation
  ncycles = 0
  print()
  print("{}:{}".format( ncycles, test_harness.line_trace()))
  while not test_harness.done() and ncycles < max_cycles:
    test_harness.sim_tick()
    ncycles += 1
    print("{}:{}".format(ncycles, test_harness.line_trace()))

  # Check timeout
  assert ncycles < max_cycles

  test_harness.sim_tick()
  test_harness.sim_tick()
  test_harness.sim_tick()

def test_reg_bank():
  DataType = mk_data(16, 1)
  data_mem_size = 20
  AddrType = mk_bits(clog2(data_mem_size))
  preloadData = [DataType(i, 1) for i in range(data_mem_size)]

  num_ctrl_operations = 64
  num_fu_inports = 4
  num_fu_outports = 2
  num_tile_inports = 4
  num_tile_outports = 4
  num_registers_per_reg_bank = 16
  reg_bank_id = 1

  ConfigType = mk_separate_reg_ctrl(num_ctrl_operations,
                                    num_fu_inports,
                                    num_fu_outports,
                                    num_tile_inports,
                                    num_tile_outports,
                                    num_registers_per_reg_bank)
  FuInType = mk_bits(clog2(num_fu_inports + 1))
  pickRegister = [FuInType(x + 1) for x in range(num_fu_inports)]

  src_opt = ConfigType(OPT_ADD_CONST, b1(1), pickRegister)
  src_opt.write_reg_from[reg_bank_id] = b2(2)
  # Writes data into reg[15].
  src_opt.write_reg_idx[reg_bank_id] = b4(15)
  src_opt.read_reg_from[reg_bank_id] = b1(1)
  # Reads data from reg[15].
  src_opt.read_reg_idx[reg_bank_id] = b4(15) # read after write

  write_data = [DataType(10, 1), DataType(11, 1), DataType(12, 1)]
  expected_read_data = [DataType(0, 0), DataType(11, 1), DataType(11, 1)]

  th = TestHarness(DataType, ConfigType, reg_bank_id, num_registers_per_reg_bank,
                   src_opt, write_data, expected_read_data)
  run_sim(th)

