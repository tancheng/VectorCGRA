"""
==========================================================================
RegisterClusterRTL_test.py
==========================================================================
Test cases for RegisterClusterRTL.

Author : Cheng Tan
  Date : Feb 7, 2025
"""

from pymtl3 import *
from ..RegisterClusterRTL import RegisterClusterRTL
from ....lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ....lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ....lib.messages import *
from ....lib.opt_type import *

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, DataType, ConfigType, num_reg_banks, num_registers,
                src_opt, src_msgs_routing_xbar, src_msgs_fu_xbar,
                src_msgs_const, sink_msgs):

    s.num_reg_banks = num_reg_banks
    s.src_opt = Wire(ConfigType)

    s.src_routing_xbar = [TestSrcRTL(DataType, src_msgs_routing_xbar[i])
                          for i in range(num_reg_banks)]
    s.src_fu_xbar = [TestSrcRTL(DataType, src_msgs_fu_xbar[i])
                     for i in range(num_reg_banks)]
    s.src_const = [TestSrcRTL(DataType, src_msgs_const[i])
                   for i in range(num_reg_banks)]

    s.sink = [TestSinkRTL(DataType, sink_msgs[i])
              for i in range(num_reg_banks)]

    s.reg_cluster = RegisterClusterRTL(DataType, ConfigType, num_reg_banks,
                                       num_registers)

    s.src_opt //= src_opt
    for i in range(num_reg_banks):
      s.reg_cluster.inport_opt //= s.src_opt
      s.reg_cluster.recv_data_from_routing_crossbar[i] //= \
          s.src_routing_xbar[i].send
      s.reg_cluster.recv_data_from_fu_crossbar[i] //= \
          s.src_fu_xbar[i].send
      s.reg_cluster.recv_data_from_const[i] //= \
          s.src_const[i].send
      s.reg_cluster.send_data_to_fu[i] //= \
          s.sink[i].recv

  def done(s):
    for i in range(s.num_reg_banks):
      if not s.sink[i].done():
        return False
    return True

  def line_trace(s):
    return s.reg_cluster.line_trace()

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
  num_reg_banks = 4
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
  src_opt.read_reg_from[reg_bank_id] = b1(1)
  # Reads data from reg[15].
  src_opt.read_reg_idx[reg_bank_id] = b4(15) # read after write

  src_data_from_routing_xbar = \
      [[DataType(5, 1)],
       [DataType(10, 1), DataType(11, 1)],
       [],
       [DataType(42, 1)]
      ]
  src_data_from_fu_xbar = \
      [[],
       [DataType(12, 1)],
       [],
       []
      ]
  src_data_from_const = \
      [[],
       [DataType(13, 1)],
       [],
       []
      ]

  expected_sink_data = \
      [[DataType(5, 1)],
       [DataType(0, 0), DataType(10, 1), DataType(11, 1), DataType(12, 1)],
       [],
       [DataType(42, 1)]
      ]

  th = TestHarness(DataType, ConfigType, num_reg_banks,
                   num_registers_per_reg_bank, src_opt,
                   src_data_from_routing_xbar,
                   src_data_from_fu_xbar,
                   src_data_from_const,
                   expected_sink_data)
  run_sim(th)

