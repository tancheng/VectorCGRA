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
from ....lib.util.common import (
  READ_TOWARDS_NOTHING,
  READ_TOWARDS_FU,
  READ_TOWARDS_ROUTING_XBAR,
  READ_TOWARDS_BOTH,
  PORT_ROUTING_CROSSBAR,
  PORT_FU_CROSSBAR,
  PORT_CONST,
)

# Local bitwidth helpers (avoid relying on optional pymtl3.stdlib modules)
Bits2 = mk_bits(2)
Bits4 = mk_bits(4)

def b2(v):
  return Bits2(v)

def b4(v):
  return Bits4(v)

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
  src_opt.write_reg_from[reg_bank_id] = b2(PORT_FU_CROSSBAR + 1)
  # Writes data into reg[15].
  src_opt.write_reg_idx[reg_bank_id] = b4(15)
  # read_reg_towards: 0=nothing, 1=FU, 2=routing_xbar, 3=both
  src_opt.read_reg_towards[reg_bank_id] = b2(READ_TOWARDS_FU)
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
        # Routing of 10 and 11 are overwritten by read_reg.
       [DataType(0, 0), DataType(0, 0), DataType(12, 1)],
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

#-------------------------------------------------------------------------
# Extended test harness that also sinks send_data_to_routing_crossbar
#-------------------------------------------------------------------------

class TestHarnessWithXbarSink(Component):

  def construct(s, DataType, ConfigType, num_reg_banks, num_registers,
                src_opt, src_msgs_routing_xbar, src_msgs_fu_xbar,
                src_msgs_const, sink_msgs_fu, sink_msgs_xbar):

    s.num_reg_banks = num_reg_banks
    s.src_opt = Wire(ConfigType)

    s.src_routing_xbar = [TestSrcRTL(DataType, src_msgs_routing_xbar[i])
                          for i in range(num_reg_banks)]
    s.src_fu_xbar      = [TestSrcRTL(DataType, src_msgs_fu_xbar[i])
                          for i in range(num_reg_banks)]
    s.src_const        = [TestSrcRTL(DataType, src_msgs_const[i])
                          for i in range(num_reg_banks)]

    s.sink_fu   = [TestSinkRTL(DataType, sink_msgs_fu[i])
                   for i in range(num_reg_banks)]
    s.sink_xbar = [TestSinkRTL(DataType, sink_msgs_xbar[i])
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
      s.reg_cluster.send_data_to_fu[i]              //= s.sink_fu[i].recv
      s.reg_cluster.send_data_to_routing_crossbar[i] //= s.sink_xbar[i].recv

  def done(s):
    for i in range(s.num_reg_banks):
      if not s.sink_fu[i].done() or not s.sink_xbar[i].done():
        return False
    return True

  def line_trace(s):
    return s.reg_cluster.line_trace()

#-------------------------------------------------------------------------
# test: read_reg_towards=2 => data goes to routing_xbar only, not FU
#-------------------------------------------------------------------------

def test_reg_cluster_read_towards_routing_xbar():
  """
  Writes a value into reg[3] of bank 0 via the FU-crossbar path, then on
  the next control word set read_reg_towards[0]=2 (READ_TOWARDS_ROUTING_XBAR).
  Expects the value to appear on send_data_to_routing_crossbar[0] and
  nothing on send_data_to_fu[0].
  """
  DataType   = mk_data(16, 1)
  num_fu_inports             = 4
  num_fu_outports            = 2
  num_tile_inports           = 4
  num_tile_outports          = 4
  num_registers_per_reg_bank = 16
  num_reg_banks              = 4

  ConfigType = mk_ctrl(num_fu_inports, num_fu_outports,
                       num_tile_inports, num_tile_outports,
                       num_registers_per_reg_bank)
  FuInType   = mk_bits(clog2(num_fu_inports + 1))

  # Control word: write bank-0 reg[3] from FU-crossbar (write_reg_from=2),
  # then read it towards routing_xbar (read_reg_towards=2).
  src_opt = ConfigType(OPT_ADD_CONST, [FuInType(x + 1) for x in range(num_fu_inports)])
  src_opt.write_reg_from[0]    = b2(PORT_FU_CROSSBAR + 1)   # write from FU-crossbar
  src_opt.write_reg_idx[0]     = b4(3)
  src_opt.read_reg_towards[0]  = b2(READ_TOWARDS_ROUTING_XBAR)
  src_opt.read_reg_idx[0]      = b4(3)

  # Bank 0 receives one value via FU-crossbar; all others empty.
  src_data_from_routing_xbar = [[] for _ in range(num_reg_banks)]
  src_data_from_fu_xbar      = [[DataType(77, 1)], [], [], []]
  src_data_from_const        = [[] for _ in range(num_reg_banks)]

  # FU sink: bank 0 gets nothing because read_reg_towards=2 means the
  # register data is NOT forwarded to FU.
  # Routing-xbar sink: TestSrcRTL starts sending in cycle 2 (1 cycle after
  # reset), so the write lands at end of cycle 2 and the value is readable
  # in cycle 3 — two leading DataType(0,0) before DataType(77,1).
  sink_msgs_fu   = [[] for _ in range(num_reg_banks)]
  sink_msgs_xbar = [[DataType(0, 0), DataType(0, 0), DataType(77, 1)], [], [], []]

  th = TestHarnessWithXbarSink(
      DataType, ConfigType, num_reg_banks, num_registers_per_reg_bank,
      src_opt,
      src_data_from_routing_xbar,
      src_data_from_fu_xbar,
      src_data_from_const,
      sink_msgs_fu,
      sink_msgs_xbar)
  run_sim(th, max_cycles = 15)

#-------------------------------------------------------------------------
# test: read_reg_towards=3 => data goes to BOTH FU and routing_xbar
#-------------------------------------------------------------------------

def test_reg_cluster_read_towards_both():
  """
  Writes a value into reg[7] of bank 2 via the routing-crossbar path, then
  set read_reg_towards[2]=3 (READ_TOWARDS_BOTH).
  Expects the same value on both send_data_to_fu[2] and
  send_data_to_routing_crossbar[2].
  """
  DataType   = mk_data(16, 1)
  num_fu_inports             = 4
  num_fu_outports            = 2
  num_tile_inports           = 4
  num_tile_outports          = 4
  num_registers_per_reg_bank = 16
  num_reg_banks              = 4

  ConfigType = mk_ctrl(num_fu_inports, num_fu_outports,
                       num_tile_inports, num_tile_outports,
                       num_registers_per_reg_bank)
  FuInType   = mk_bits(clog2(num_fu_inports + 1))

  src_opt = ConfigType(OPT_ADD_CONST, [FuInType(x + 1) for x in range(num_fu_inports)])
  src_opt.write_reg_from[2]   = b2(PORT_ROUTING_CROSSBAR + 1)   # write from routing-crossbar
  src_opt.write_reg_idx[2]    = b4(7)
  src_opt.read_reg_towards[2] = b2(READ_TOWARDS_BOTH)
  src_opt.read_reg_idx[2]     = b4(7)

  src_data_from_routing_xbar = [[], [], [DataType(55, 1)], []]
  src_data_from_fu_xbar      = [[] for _ in range(num_reg_banks)]
  src_data_from_const        = [[] for _ in range(num_reg_banks)]

  # Bank 2: reg data (55) goes to both FU and routing_xbar.
  # TestSrcRTL starts sending in cycle 2, write lands at end of cycle 2,
  # value readable in cycle 3 — two leading DataType(0,0) on both paths.
  sink_msgs_fu   = [[], [], [DataType(0, 0), DataType(0, 0), DataType(55, 1)], []]
  sink_msgs_xbar = [[], [], [DataType(0, 0), DataType(0, 0), DataType(55, 1)], []]

  th = TestHarnessWithXbarSink(
      DataType, ConfigType, num_reg_banks, num_registers_per_reg_bank,
      src_opt,
      src_data_from_routing_xbar,
      src_data_from_fu_xbar,
      src_data_from_const,
      sink_msgs_fu,
      sink_msgs_xbar)
  run_sim(th, max_cycles = 15)

#-------------------------------------------------------------------------
# test: read_reg_towards=1 => data goes to FU only, xbar output stays idle
#-------------------------------------------------------------------------

def test_reg_cluster_read_towards_fu_no_xbar_output():
  """
  Sets read_reg_towards[1]=1 (READ_TOWARDS_FU).
  Verifies send_data_to_routing_crossbar[1] never fires (empty sink).
  """
  DataType   = mk_data(16, 1)
  num_fu_inports             = 4
  num_fu_outports            = 2
  num_tile_inports           = 4
  num_tile_outports          = 4
  num_registers_per_reg_bank = 16
  num_reg_banks              = 4

  ConfigType = mk_ctrl(num_fu_inports, num_fu_outports,
                       num_tile_inports, num_tile_outports,
                       num_registers_per_reg_bank)
  FuInType   = mk_bits(clog2(num_fu_inports + 1))

  src_opt = ConfigType(OPT_ADD_CONST, [FuInType(x + 1) for x in range(num_fu_inports)])
  src_opt.write_reg_from[1]   = b2(PORT_FU_CROSSBAR + 1)   # write from FU-crossbar
  src_opt.write_reg_idx[1]    = b4(0)
  src_opt.read_reg_towards[1] = b2(READ_TOWARDS_FU)
  src_opt.read_reg_idx[1]     = b4(0)

  src_data_from_routing_xbar = [[] for _ in range(num_reg_banks)]
  src_data_from_fu_xbar      = [[], [DataType(33, 1)], [], []]
  src_data_from_const        = [[] for _ in range(num_reg_banks)]

  # FU sink for bank 1: TestSrcRTL starts sending in cycle 2, write lands
  # at end of cycle 2, value readable in cycle 3 — two leading DataType(0,0).
  # Xbar sink stays empty because read_reg_towards=1 (FU only).
  sink_msgs_fu   = [[], [DataType(0, 0), DataType(0, 0), DataType(33, 1)], [], []]
  sink_msgs_xbar = [[] for _ in range(num_reg_banks)]

  th = TestHarnessWithXbarSink(
      DataType, ConfigType, num_reg_banks, num_registers_per_reg_bank,
      src_opt,
      src_data_from_routing_xbar,
      src_data_from_fu_xbar,
      src_data_from_const,
      sink_msgs_fu,
      sink_msgs_xbar)
  run_sim(th, max_cycles = 15)

