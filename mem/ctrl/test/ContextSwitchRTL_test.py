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
from ....lib.status_type import *

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, Module, data_nbits, src_cmds, src_opts, src_progress_in, sink_progress_out, sink_progress_out_vld):

    s.src_cmds = src_cmds
    s.src_opts = src_opts
    s.src_progress_in = src_progress_in
    s.sink_progress_out = sink_progress_out
    s.sink_progress_out_vld = sink_progress_out_vld

    s.context_switch = Module(data_nbits)

    s.src_cmds //= s.context_switch.recv_cmd
    s.context_switch.recv_cmd_vld = 1
    s.src_opts //= s.context_switch.recv_opt
    s.src_progress_in //= s.context_switch.progress_in
    s.context_switch.progress_in_vld = 1
    s.sink_progress_out //= s.context_switch.progress_out
    s.sink_progress_out_vld //= s.context_switch.progress_out_vld

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
  data_nbits = 16
  CmdType = mk_bits(clog2(NUM_CMDS))
  DataType = mk_bits(data_nbits)
  OptType = mk_bits(clog2(NUM_OPTS))

  src_cmds = [# Assumes that tile receives the PAUSE command at clock cycle 1.
              CmdType(CMD_PAUSE), # cycle 1
              # Some random commands that might be issued during pausing.
              CmdType(CMD_CONFIG_TOTAL_CTRL_COUNT), # cycle 2
              CmdType(CMD_CONFIG_COUNT_PER_ITER), # cycle 3
              CmdType(CMD_CONFIG_CTRL_LOWER_BOUND), # cycle 4
              # Assumes that tile receives the RESUME command at clock cycle 5.
              CmdType(CMD_RESUME), # cycle 5
              # Some random commands that might be issued during resuming.
              CmdType(CMD_CONFIG_TOTAL_CTRL_COUNT), # cycle 6
              CmdType(CMD_CONFIG_COUNT_PER_ITER), # cycle 7
              CmdType(CMD_CONFIG_CTRL_LOWER_BOUND) # cycle 8
              ]
  src_opts = [
              # Some random operations executed in FU,
              OptType(OPT_NAH),
              OptType(OPT_NAH),
              # Assumes that FU executes PHI_CONST at clock cycle 3
              # for the first time after receiving PAUSE command.
              OptType(OPT_PHI_CONST),
              # Some random operations executed in FU.
              OptType(OPT_NAH),
              OptType(OPT_NAH),
              OptType(OPT_NAH),
              # Assumes that FU executes PHI_CONST at clock cycle 7
              # for the first time after receiving RESUME command.
              OptType(OPT_PHI_CONST),
              # Simulates some random operations.
              OptType(OPT_NAH)
              ]
  src_progress_in = [
                     # A fake progress "4321", should not be recorded.
                     DataType(4321),
                     # Some random FU's outputs.
                     DataType(0),
                     # The target progress (loop iteration) 
                     # output by FU when executing PHI_CONST for 
                     # the first time after receiving PAUSE command.
                     # Should be recorded to progress register at the rising
                     # edge of clock cycle 4
                     DataType(1234),
                     # Some random FU's outputs.
                     DataType(0),
                     DataType(0),
                     DataType(0),
                     DataType(0),
                     DataType(0)
                     ]
  sink_progress_out = [
                       DataType(0),
                       DataType(0),
                       DataType(0),
                       DataType(0),
                       DataType(0),
                       DataType(0),
                       # ContextSiwtch module should output the target progress
                       # when executing PHI_CONST for the first time after
                       # receiving RESUME command.
                       DataType(1234),
                       DataType(0)
                      ]
  sink_progress_out_vld = [
                          0,
                          0,
                          0,
                          0,
                          0,
                          0,
                          # The output progress is valid duing clock cycle 7
                          1,
                          0
                          ]

  th = TestHarness(Module, 
                   data_nbits,
                   src_cmds, 
                   src_opts, 
                   src_progress_in, 
                   sink_progress_out, 
                   sink_progress_out_vld)

  run_sim(th)
