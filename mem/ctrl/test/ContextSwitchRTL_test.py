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

  def construct(s, Module, data_nbits, ctrl_addr_nbits, src_cmds, src_opts, src_init_phi_addr, src_ctrl_mem_rd_addr, src_progress_in, sink_progress_out, sink_overwrite_fu_output_predicate):
    
    CmdType = mk_bits(clog2(NUM_CMDS))
    StatusType = mk_bits(clog2(NUM_STATUS))
    DataType = mk_data(data_nbits)
    CtrlAddrType = mk_bits(ctrl_addr_nbits)
    ValidType = mk_bits(1)
    OptType = mk_bits(clog2(NUM_OPTS))

    s.src_cmds = TestSrcRTL(CmdType, src_cmds)
    s.src_opts = TestSrcRTL(OptType, src_opts)
    s.src_init_phi_addr = TestSrcRTL(CtrlAddrType, src_init_phi_addr)
    s.src_ctrl_mem_rd_addr = TestSrcRTL(CtrlAddrType, src_ctrl_mem_rd_addr)
    s.src_progress_in = TestSrcRTL(DataType, src_progress_in)
    s.sink_progress_out = TestSinkRTL(DataType, sink_progress_out)
    s.sink_overwrite_fu_output_predicate = TestSinkRTL(ValidType, sink_overwrite_fu_output_predicate)
  
    s.context_switch = Module(data_nbits, ctrl_addr_nbits)

    @update
    def issue_inputs():
      s.context_switch.recv_cmd_vld @= s.src_cmds.send.val
      s.context_switch.recv_cmd @= s.src_cmds.send.msg
      s.src_cmds.send.rdy @= 1
      s.context_switch.recv_opt @= s.src_opts.send.msg
      s.src_opts.send.rdy @= 1
      s.context_switch.progress_in @= s.src_progress_in.send.msg
      s.src_progress_in.send.rdy @= 1
      s.context_switch.init_phi_addr @= s.src_init_phi_addr.send.msg
      s.src_init_phi_addr.send.rdy @= 1
      s.context_switch.ctrl_mem_rd_addr @= s.src_ctrl_mem_rd_addr.send.msg
      s.src_ctrl_mem_rd_addr.send.rdy @= 1
      s.sink_progress_out.recv.val @= 1
      s.sink_progress_out.recv.msg @= s.context_switch.progress_out
      s.sink_overwrite_fu_output_predicate.recv.val @= 1
      s.sink_overwrite_fu_output_predicate.recv.msg @= s.context_switch.overwrite_fu_output_predicate

  def done(s):
    return s.src_cmds.done() and s.src_opts.done() and s.src_init_phi_addr.done() and s.src_ctrl_mem_rd_addr.done() and s.src_progress_in.done() and s.sink_progress_out.done() and s.sink_overwrite_fu_output_predicate.done()

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
  ctrl_addr_nbits = 16
  CmdType = mk_bits(clog2(NUM_CMDS))
  DataType = mk_data(data_nbits)
  CtrlAddrType = mk_bits(ctrl_addr_nbits)
  OptType = mk_bits(clog2(NUM_OPTS))

  src_cmds = [# Preloads the ctrl mem address of DFG's initial PHI_CONST at clock cycle 1.
              CmdType(CMD_TERMINATE), # cycle 1
              # Tile receives the PAUSE command at clock cycle 2.
              CmdType(CMD_PAUSE), # cycle 2
              # Some random commands that might be issued during pausing.
              CmdType(CMD_CONST), # cycle 3
              CmdType(CMD_CONST), # cycle 4
              # Tile receives the RESUME command at clock cycle 5.
              CmdType(CMD_RESUME), # cycle 5
              # Some random commands that might be issued during resuming.
              CmdType(CMD_CONST), # cycle 6
              CmdType(CMD_CONST), # cycle 7
              CmdType(CMD_CONST) # cycle 8
              ]

  src_opts = [
              # Some random operations executed in FU.
              OptType(OPT_NAH),
              OptType(OPT_NAH),
              # FU executes PHI_CONST at clock cycle 3.
              OptType(OPT_PHI_CONST),
              # FU executes the initial PHI_CONST at clock cycle 4
              # for the first time duing PAUSING status.
              OptType(OPT_PHI_CONST),
              # Some random operations executed in FU.
              OptType(OPT_NAH),
              OptType(OPT_NAH),
              # FU executes PHI_CONST at clock cycle 7
              OptType(OPT_PHI_CONST),
              # FU executes the initial PHI_CONST at clock cycle 8
              # for the first time during RESUMING status.
              OptType(OPT_PHI_CONST),
              ]
  
  # Ctrl mem has 4 configurations, 
  # so ctrl mem address iterates bewteen 0 and 3.
  # Address 2 contains PHI_CONST (Output other data, i.e., the operand of +=).
  # Address 3 contains the initial PHI_CONST (Output iteration indexs).
  src_ctrl_mem_rd_addr = [
                         CtrlAddrType(0),
                         CtrlAddrType(1),
                         CtrlAddrType(2),
                         CtrlAddrType(3),
                         CtrlAddrType(0),
                         CtrlAddrType(1),
                         CtrlAddrType(2),
                         CtrlAddrType(3)
                         ]

  # Preloads the address 3 of the initial PHI_CONST.
  src_init_phi_addr = [
                         CtrlAddrType(3),
                         CtrlAddrType(0),
                         CtrlAddrType(0),
                         CtrlAddrType(0),
                         CtrlAddrType(0),
                         CtrlAddrType(0),
                         CtrlAddrType(0),
                         CtrlAddrType(0)
                        ]

  src_progress_in = [
                     # A fake progress "4321", should not be recorded because not in the PAUSING status.
                     DataType(4321, 1),
                     # Some random FU's outputs.
                     DataType(0, 0),
                     # A fake progress "8765", should not be recorded 
                     # because FU is executing PHI_CONST.
                     DataType(8765, 1),
                     # The target progress (loop iteration) 
                     # output by FU when executing the initial PHI_CONST for 
                     # the first time during the PAUSING status.
                     # Should be recorded to progress register at the rising
                     # edge of clock cycle 5
                     DataType(1234, 1),
                     # Some random FU's outputs.
                     DataType(0, 0),
                     DataType(0, 0),
                     DataType(0, 0),
                     DataType(0, 0)
                     ]
  
  sink_progress_out = [
                       DataType(0, 0),
                       DataType(0, 0),
                       DataType(0, 0),
                       DataType(0, 0),
                       DataType(0, 0),
                       DataType(0, 0),
                       DataType(0, 0),
                       # ContextSiwtch module should output the target progress
                       # when FU executes the initail PHI_CONST for the first time 
                       # during the RESUMING status at cycle 8. 
                       # The 'predicate' bit alone can inidicates that the progress_out is valid,
                       # we therefore omit the 'valid' bit for simplicity.
                       DataType(1234, 1)
                      ]
  
  sink_overwrite_fu_output_predicate = [
                                    0,
                                    0,
                                    0,
                                    # clock cycle 4 has overwrite_fu_output_predicate = 1, 
                                    # as in the PAUSING status and executing the initial PHI_CONST.
                                    1,
                                    0,
                                    0,
                                    0,
                                    0
                                   ]

  th = TestHarness(Module, 
                   data_nbits,
                   ctrl_addr_nbits,
                   src_cmds, 
                   src_opts, 
                   src_init_phi_addr,
                   src_ctrl_mem_rd_addr,
                   src_progress_in, 
                   sink_progress_out, 
                   sink_overwrite_fu_output_predicate)

  run_sim(th)
