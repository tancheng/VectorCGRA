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

class TestHarness(Component):

  def construct(s, DataType, ConfigType, reg_bank_id, num_registers,
                src_opt, src_msgs, sink_msgs):

    s.sink = TestSinkRTL(DataType, sink_msgs)

    s.reg_bank = RegisterBankRTL(DataType, ConfigType, reg_bank_id,
                                 num_registers)

    s.reg_bank.inport_wdata[PORT_INDEX_ROUTING_CROSSBAR] //= src_msgs[PORT_INDEX_ROUTING_CROSSBAR]
    s.reg_bank.inport_wdata[PORT_INDEX_FU_CROSSBAR] //= src_msgs[PORT_INDEX_FU_CROSSBAR]
    s.reg_bank.inport_wdata[PORT_INDEX_CONST] //= src_msgs[PORT_INDEX_CONST]
    s.reg_bank.inport_valid[PORT_INDEX_ROUTING_CROSSBAR] //= 1
    s.reg_bank.inport_valid[PORT_INDEX_FU_CROSSBAR] //= 1
    s.reg_bank.inport_valid[PORT_INDEX_CONST] //= 1
    s.reg_bank.inport_opt //= src_opt
    s.reg_bank.inport_ctrl_proceed //= 0
    s.reg_bank.send_data //= s.sink.recv

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

  ConfigType = mk_ctrl(num_fu_inports,
                       num_fu_outports,
                       num_tile_inports,
                       num_tile_outports,
                       num_registers_per_reg_bank)
  FuInType = mk_bits(clog2(num_fu_inports + 1))
  pickRegister = [FuInType(x + 1) for x in range(num_fu_inports)]

  src_opt = ConfigType(OPT_ADD_CONST, pickRegister)
  src_opt.write_reg_from[reg_bank_id] = b2(2)
  # Writes data into reg[15].
  src_opt.write_reg_idx[reg_bank_id] = b4(15)
  # read_reg_towards: 0=nothing, 1=FU, 2=routing_xbar, 3=both
  src_opt.read_reg_towards[reg_bank_id] = b2(1)
  # Reads data from reg[15].
  src_opt.read_reg_idx[reg_bank_id] = b4(15) # read after write

  write_data = [DataType(10, 1), DataType(11, 1), DataType(12, 1)]
  expected_read_data = [DataType(0, 0), DataType(11, 1), DataType(11, 1)]

  th = TestHarness(DataType, ConfigType, reg_bank_id, num_registers_per_reg_bank,
                   src_opt, write_data, expected_read_data)
  run_sim(th)


def test_same_address_read_is_held_until_control_proceeds():
  DataType = mk_data(16, 1)
  ConfigType = mk_ctrl(4, 2, 4, 4, 16)
  dut = RegisterBankRTL(DataType, ConfigType, reg_bank_id=0,
                        num_registers=16)
  dut.elaborate()
  dut.apply(DefaultPassGroup())
  dut.sim_reset()

  write_only = ConfigType()
  write_only.write_reg_from[0] = b2(PORT_ROUTING_CROSSBAR)
  write_only.write_reg_idx[0] = b4(5)
  dut.inport_opt @= write_only
  dut.inport_wdata[PORT_INDEX_ROUTING_CROSSBAR] @= DataType(10, 1)
  dut.inport_valid[PORT_INDEX_ROUTING_CROSSBAR] @= 1
  dut.inport_valid[PORT_INDEX_FU_CROSSBAR] @= 0
  dut.inport_valid[PORT_INDEX_CONST] @= 0
  dut.inport_ctrl_proceed @= 1
  dut.send_data.rdy @= 0
  dut.sim_tick()

  read_write = ConfigType()
  read_write.read_reg_towards[0] = b2(READ_TOWARDS_FU)
  read_write.read_reg_idx[0] = b4(5)
  read_write.write_reg_from[0] = b2(PORT_ROUTING_CROSSBAR)
  read_write.write_reg_idx[0] = b4(5)
  dut.inport_opt @= read_write
  dut.inport_wdata[PORT_INDEX_ROUTING_CROSSBAR] @= DataType(20, 1)
  dut.inport_valid[PORT_INDEX_ROUTING_CROSSBAR] @= 1
  dut.inport_ctrl_proceed @= 0
  dut.sim_eval_combinational()
  assert dut.send_data.msg == DataType(10, 1)
  dut.sim_tick()

  # The register now contains 20, but the stalled control must continue to
  # observe the old value 10 until the whole control step completes.
  dut.inport_valid[PORT_INDEX_ROUTING_CROSSBAR] @= 0
  dut.sim_eval_combinational()
  assert dut.reg_file.regs[5] == DataType(20, 1)
  assert dut.send_data.msg == DataType(10, 1)

  dut.inport_ctrl_proceed @= 1
  dut.sim_tick()
  dut.inport_ctrl_proceed @= 0
  dut.sim_eval_combinational()
  assert dut.send_data.msg == DataType(20, 1)
