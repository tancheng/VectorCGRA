"""
==========================================================================
ContextSwitchRTL_test.py
==========================================================================
Test cases for context switch module.

Author : Yufei Yang
  Date : Aug 11, 2025
"""
from ..ContextSwitchRTL import ContextSwitchRTL
from ....lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ....lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ....lib.cmd_type import *
from ....lib.messages import *
from ....lib.opt_type import *

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, Module, DataType, CtrlType, CgraPayloadType, src_cmds, src_opts, src_progress_in, sink_progress_out, num_status = 3):

    s.src_cmds = TestSrcRTL(CgraPayloadType, src_cmds)
    s.src_opts = TestSrcRTL(CtrlType, src_opts)
    s.src_progress_in = TestSrcRTL(DataType, src_progress_in)
    s.sink_progress_out = TestSinkRTL(DataType, sink_progress_out)

    s.context_switch = Module(CgraPayloadType, DataType, CtrlType, num_status)

    s.src_cmds.send //= s.context_switch.recv_cmd
    s.src_opts.send //= s.context_switch.recv_opt
    s.src_progress_in.send //= s.context_switch.progress_in
    s.sink_progress_out.recv //= s.context_switch.progress_out

  def done(s):
    return s.src_cmds.done() and s.src_opts.done() and \
        s.src_progress_in.done() and s.sink_progress_out.done()

  def line_trace(s):
    return s.context_switch.line_trace()

def run_sim(test_harness, max_cycles = 20):
  test_harness.elaborate()
  test_harness.apply(DefaultPassGroup())
  #test_harness.sim_reset()

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

def test():
  Module = ContextSwitchRTL
  DataType = mk_data(16, 1)
  ctrl_mem_size = 16
  num_fu_inports = 2
  num_fu_outports = 2
  num_tile_inports = 4
  num_tile_outports = 4

  data_mem_size_global = 16
  addr_nbits = clog2(data_mem_size_global)
  DataAddrType = mk_bits(addr_nbits)
  num_registers_per_reg_bank = 16

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

  src_cmds = [# Simulates the PAUSE command to record the progress.
              CgraPayloadType(CMD_PAUSE),
              # Simulates some random commands.
              CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT),
              CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER),
              CgraPayloadType(CMD_CONFIG_CTRL_LOWER_BOUND),
              # Simulates the RESUME command to recover the progress.
              CgraPayloadType(CMD_RESUME),
              # Simulates some random commands.
              CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT),
              CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER),
              CgraPayloadType(CMD_CONFIG_CTRL_LOWER_BOUND)
              ]
  src_opts = [
              # Simulates some random operations.
              CtrlType(OPT_NAH),
              CtrlType(OPT_NAH),
              # Simulates the clock cycle when FU executes PHI_CONST
              # for the first time after receiving PAUSE command.
              CtrlType(OPT_PHI_CONST),
              # Simulates some random operations.
              CtrlType(OPT_NAH),
              CtrlType(OPT_NAH),
              CtrlType(OPT_NAH),
              # Simulates the clock cycle when FU executes PHI_CONST
              # for the first time after receiving RESUME command.
              CtrlType(OPT_PHI_CONST),
              # Simulates some random operations.
              CtrlType(OPT_NAH)
              ]
  src_progress_in = [
                     # Simulates some random FU's outputs.
                     DataType(0,1),
                     DataType(0,1),
                     # Simulates the output iteration (progress) of FU
                     # when executing OPT_PHI_CONST for the first time
                     # after receiving PAUSE command.
                     DataType(1234,1),
                     # Simulates some random FU's outputs.
                     DataType(0,1),
                     DataType(0,1),
                     DataType(0,1),
                     DataType(0,1),
                     DataType(0,1)
                     ]
  sink_progress_out = [
                       DataType(0,0),
                       DataType(0,0),
                       DataType(0,0),
                       DataType(0,0),
                       DataType(0,0),
                       DataType(0,0),
                       # ContextSiwtch module should output the progress
                       # when executing OPT_PHI_CONST for the first time
                       # after receiving RESUME command.
                       DataType(1234,1),
                       DataType(0,0)
                      ]

  th = TestHarness(Module, 
                   DataType, 
                   CtrlType, 
                   CgraPayloadType, 
                   src_cmds, 
                   src_opts, 
                   src_progress_in, 
                   sink_progress_out, 
                   num_status = 3)

  run_sim(th)
