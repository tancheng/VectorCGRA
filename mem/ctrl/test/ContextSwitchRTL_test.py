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

  def construct(s, Module, data_nbits, src_cmds, src_opts, src_progress_in, sink_progress_out, sink_progress_out_vld, sink_predicate):
    
    CmdType = mk_bits(clog2(NUM_CMDS))
    StatusType = mk_bits(clog2(NUM_STATUS))
    DataType = mk_bits(data_nbits)
    ValidType = mk_bits(1)
    OptType = mk_bits(clog2(NUM_OPTS))
    PredicateType = mk_bits(1)

    s.src_cmds = TestSrcRTL(CmdType, src_cmds)
    s.src_opts = TestSrcRTL(OptType, src_opts)
    s.src_progress_in = TestSrcRTL(DataType, src_progress_in)
    s.sink_progress_out = TestSinkRTL(DataType, sink_progress_out)
    s.sink_progress_out_vld = TestSinkRTL(ValidType, sink_progress_out_vld)
    s.sink_predicate = TestSinkRTL(PredicateType, sink_predicate)

    s.context_switch = Module(data_nbits)

    @update
    def issue_inputs():
      s.context_switch.recv_cmd @= s.src_cmds.send.msg
      s.src_cmds.send.rdy @= 1
      s.context_switch.recv_cmd_vld @= 1
      s.context_switch.recv_opt @= s.src_opts.send.msg
      s.src_opts.send.rdy @= 1
      s.context_switch.progress_in @= s.src_progress_in.send.msg
      s.src_progress_in.send.rdy @= 1
      s.context_switch.progress_in_vld @= 1
      s.sink_progress_out.recv.val @= 1
      s.sink_progress_out.recv.msg @= s.context_switch.progress_out
      s.sink_progress_out_vld.recv.val @= 1
      s.sink_progress_out_vld.recv.msg @= s.context_switch.progress_out_vld
      s.sink_predicate.recv.val @= 1
      s.sink_predicate.recv.msg @= s.context_switch.predicate

  def done(s):
    return s.src_cmds.done() and s.src_opts.done() and s.src_progress_in.done() and s.sink_progress_out.done() and s.sink_progress_out_vld.done() and s.sink_predicate.done()

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
  sink_predicate = [
                    1,
                    1,
                    # clock cycle 3 has predicate=0, as in the PAUSING status and executing the PHI_CONST.
                    0,
                    1,
                    1,
                    1,
                    1,
                    1
                    ]

  th = TestHarness(Module, 
                   data_nbits,
                   src_cmds, 
                   src_opts, 
                   src_progress_in, 
                   sink_progress_out, 
                   sink_progress_out_vld,
                   sink_predicate)

  run_sim(th)
