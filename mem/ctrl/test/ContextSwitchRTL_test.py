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

  def construct(s, Module, data_nbits, ctrl_addr_nbits, src_cmds, src_opts, src_init_phi_addr, src_ctrl_mem_rd_addr, src_progress_in, sink_overwrite_fu_outport):
    
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
    s.sink_overwrite_fu_outport = TestSinkRTL(DataType, sink_overwrite_fu_outport)
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
      s.sink_overwrite_fu_outport.recv.val @= 1
      s.sink_overwrite_fu_outport.recv.msg @= s.context_switch.overwrite_fu_outport.msg

  def done(s):
    return s.src_cmds.done() and s.src_opts.done() and s.src_init_phi_addr.done() and s.src_ctrl_mem_rd_addr.done() and s.src_progress_in.done() and s.sink_overwrite_fu_outport.done()

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

# testcase for PHI_CONST that is responsible for iteration.
def test_pause_resume_iteration():
  Module = ContextSwitchRTL
  data_nbits = 16
  ctrl_addr_nbits = 16
  CmdType = mk_bits(clog2(NUM_CMDS))
  DataType = mk_data(data_nbits)
  CtrlAddrType = mk_bits(ctrl_addr_nbits)
  OptType = mk_bits(clog2(NUM_OPTS))

  # All input commands are registered by ContextSwitchRTL for 1 cycle,
  # so as to make timing right when interacting with CtrlMemDynamicRTL. 
  src_cmds = [# Preloads the ctrl mem address of DFG's initial PHI_CONST at clock cycle 1.
              CmdType(CMD_RECORD_INIT_PHI_ADDR), # cycle 1
              # Tile receives the PAUSE command at clock cycle 2, processes the command at cycle 3,
              # and is in pausing status at cycle 4.
              CmdType(CMD_PAUSE), # cycle 2
              # Some random commands that might be issued during pausing.
              CmdType(CMD_CONST), # cycle 3
              CmdType(CMD_CONST), # cycle 4
              # Tile receives the RESUME command at clock cycle 5, processes the command at cycle 6,
              # and is in resuming status at cycle 7.
              CmdType(CMD_RESUME), # cycle 5
              # Some random commands that might be issued during resuming.
              CmdType(CMD_CONST), # cycle 6
              CmdType(CMD_CONST), # cycle 7
              CmdType(CMD_CONST), # cycle 8
              CmdType(CMD_CONST)  # cycle 9
              ]
  
  # All inputs provided by CtrlMemDynamicRTL have 1-cycle delay because of recv_pkt_queue.
  src_opts = [
              # Simulates 1-cycle delay comapred to src_cmds.
              OptType(OPT_NAH),
              # Some random operations executed in FU.
              OptType(OPT_NAH),
              OptType(OPT_NAH),
              # FU executes PHI_CONST at clock cycle 4.
              OptType(OPT_PHI_CONST),
              # FU executes the initial PHI_CONST at clock cycle 5
              # for the first time duing PAUSING status.
              OptType(OPT_PHI_CONST),
              # Some random operations executed in FU.
              OptType(OPT_NAH),
              OptType(OPT_NAH),
              # FU executes PHI_CONST at clock cycle 8
              OptType(OPT_PHI_CONST),
              # FU executes the initial PHI_CONST at clock cycle 9
              # for the first time during RESUMING status.
              OptType(OPT_PHI_CONST),
              ]
  
  # Ctrl mem has 4 configurations, 
  # so ctrl mem address iterates bewteen 0 and 3.
  # Address 2 contains PHI_CONST (Output other data, i.e., the operand of +=).
  # Address 3 contains the initial PHI_CONST (Output iteration indexs).
  src_ctrl_mem_rd_addr = [
                         # Simulates 1-cycle delay comapred to src_cmds.
                         CtrlAddrType(0),
                         # Starts execution.
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
                         # Simulates 1-cycle delay comapred to src_cmds.
                         CtrlAddrType(0),
                         # Starts execution.
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
                     # Simulates 1-cycle delay comapred to src_cmds.
                     DataType(0, 0),
                     # The following are ground truth values:
                     # A fake progress "4321", should not be recorded because not in the PAUSING status.
                     DataType(4321, 1),
                     # Some random FU's outputs.
                     DataType(0, 0),
                     # A fake progress "8765", should not be recorded 
                     # because FU is not executing the initial PHI_CONST at address 3 and in PAUSING status.
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
  
  sink_overwrite_fu_outport  = [
                       # Simulates 1-cycle delay comapred to src_cmds.
                       DataType(0, 0),
                       # The following are ground truth values:
                       # msg:DataType(0, 0) with val:0 have no effects to FU's output
                       DataType(0, 0),
                       DataType(0, 0),
                       DataType(0, 0),
                       # msg:DataType(0, 0) with val:1 replace FU's outport to stop task execution.
                       DataType(0, 0),
                       DataType(0, 0),
                       DataType(0, 0),
                       DataType(0, 0),
                       # ContextSiwtch module should output the target progress
                       # when FU executes the initail PHI_CONST for the first time 
                       # during the RESUMING status at cycle 8. 
                       # msg:DataType(1234, 1) with val:1 replace FU's outport to resume task progress.
                       DataType(1234, 1)
                      ]
  
  th = TestHarness(Module, 
                   data_nbits,
                   ctrl_addr_nbits,
                   src_cmds, 
                   src_opts, 
                   src_init_phi_addr,
                   src_ctrl_mem_rd_addr,
                   src_progress_in, 
                   sink_overwrite_fu_outport)

  run_sim(th)

# testcase for PHI_CONST that is responsible for accumulation.
def test_pause_resume_accumulation():
  Module = ContextSwitchRTL
  data_nbits = 16
  ctrl_addr_nbits = 16
  CmdType = mk_bits(clog2(NUM_CMDS))
  DataType = mk_data(data_nbits)
  CtrlAddrType = mk_bits(ctrl_addr_nbits)
  OptType = mk_bits(clog2(NUM_OPTS))

  # All input commands are registered by ContextSwitchRTL for 1 cycle,
  # so as to make timing right when interacting with CtrlMemDynamicRTL. 
  src_cmds = [# Preloads the ctrl mem address of DFG's initial PHI_CONST at clock cycle 1.
              CmdType(CMD_RECORD_INIT_PHI_ADDR), # cycle 1
              # Tile receives the PRESERVE command at clock cycle 2, processes the command at cycle 3,
              # and is in preserving status at cycle 4.
              CmdType(CMD_PRESERVE), # cycle 2
              # Some random commands that might be issued during preserving.
              CmdType(CMD_CONST), # cycle 3
              CmdType(CMD_CONST), # cycle 4
              CmdType(CMD_CONST), # cycle 5
              CmdType(CMD_CONST), # cycle 6
              CmdType(CMD_CONST), # cycle 7
              CmdType(CMD_CONST), # cycle 8
              # Tile receives the RESUME command at clock cycle 9, processes the command at cycle 10,
              # and is in resuming status at cycle 11.
              CmdType(CMD_RESUME), # cycle 9
              # Some random commands that might be issued during resuming.
              CmdType(CMD_CONST), # cycle 10
              CmdType(CMD_CONST), # cycle 11
              CmdType(CMD_CONST), # cycle 12
              CmdType(CMD_CONST)  # cycle 13
              ]
  
  # All inputs provided by CtrlMemDynamicRTL have 1-cycle delay because of recv_pkt_queue.
  src_opts = [
              # Simulates 1-cycle delay comapred to src_cmds.
              OptType(OPT_NAH),
              # Some random operations executed in FU.
              OptType(OPT_NAH),
              OptType(OPT_NAH),
              # FU executes PHI_CONST at clock cycle 4 & 5
              # for twice during PRESERVING status.
              OptType(OPT_PHI_CONST),
              OptType(OPT_PHI_CONST),
              # Some random operations executed in FU.
              OptType(OPT_NAH),
              OptType(OPT_NAH),
              # FU executes PHI_CONST at clock cycle 8 & 9
              # for twice during PRESERVING status.
              OptType(OPT_PHI_CONST),
              OptType(OPT_PHI_CONST),
              # Some random operations executed in FU.
              OptType(OPT_NAH),
              OptType(OPT_NAH),
              # FU executes PHI_CONST at clock cycle 12
              OptType(OPT_PHI_CONST),
              # FU executes the PHI_CONST at clock cycle 13
              # for the first time during RESUMING status.
              OptType(OPT_PHI_CONST),
              ]
  
  # Ctrl mem has 4 configurations, 
  # so ctrl mem address iterates bewteen 0 and 3.
  # Address 2 contains PHI_CONST (Output accumulation results).
  # Address 3 contains PHI_CONST (Output iteration indexs).
  src_ctrl_mem_rd_addr = [
                         # Simulates 1-cycle delay comapred to src_cmds.
                         CtrlAddrType(0),
                         # Starts execution.
                         CtrlAddrType(0),
                         CtrlAddrType(1),
                         CtrlAddrType(2),
                         CtrlAddrType(3),
                         CtrlAddrType(0),
                         CtrlAddrType(1),
                         CtrlAddrType(2),
                         CtrlAddrType(3),
                         CtrlAddrType(0),
                         CtrlAddrType(1),
                         CtrlAddrType(2),
                         CtrlAddrType(3)
                         ]

  # Preloads the address 2 of the PHI_CONST.
  src_init_phi_addr = [
                         # Simulates 1-cycle delay comapred to src_cmds.
                         CtrlAddrType(0),
                         # Starts execution.
                         CtrlAddrType(2),
                         CtrlAddrType(0),
                         CtrlAddrType(0),
                         CtrlAddrType(0),
                         CtrlAddrType(0),
                         CtrlAddrType(0),
                         CtrlAddrType(0),
                         CtrlAddrType(0),
                         CtrlAddrType(0),
                         CtrlAddrType(0),
                         CtrlAddrType(0),
                         CtrlAddrType(0)
                        ]

  src_accumulation_in = [
                     # Simulates 1-cycle delay comapred to src_cmds.
                     DataType(0, 0),
                     # The following are ground truth values:
                     # A fake accumulation "4321", should not be recorded because not in the RESERVING status.
                     DataType(4321, 1),
                     # Some random FU's outputs.
                     DataType(0, 0),
                     # A target accumulation "8765" with predicate=1, should be recorded 
                     # as FU is executing the PHI_CONST at address 2 and in PRESERVING status.
                     DataType(8765, 1),
                     # Some random FU's outputs.
                     DataType(0, 0),
                     DataType(0, 0),
                     DataType(0, 0),
                     # A target accumulation "1357" with predicate=1, should be recorded 
                     # as FU is executing the PHI_CONST at address 2 and in PRESERVING status.
                     # (8765, 1) will be covered by (1357, 1)
                     DataType(1357, 1),
                     DataType(0, 0),
                     DataType(0, 0),
                     DataType(0, 0),
                     DataType(0, 0),
                     DataType(0, 0)
                     ]
  
  sink_overwrite_fu_outport  = [
                       # Simulates 1-cycle delay comapred to src_cmds.
                       DataType(0, 0),
                       # The following are ground truth values:
                       DataType(0, 0),
                       DataType(0, 0),
                       DataType(0, 0),
                       DataType(0, 0),
                       DataType(0, 0),
                       DataType(0, 0),
                       DataType(0, 0),
                       DataType(0, 0),
                       DataType(0, 0),
                       DataType(0, 0),
                       # ContextSiwtch module should output the target accumulation
                       # when FU executes the PHI_CONST for the first time 
                       # during the RESUMING status at cycle 8. 
                       # msg:DataType(1357, 1) with val:1 replace FU's outport to resume accumulation.
                       DataType(1357, 1),
                       DataType(0, 0)
                      ]
  
  th = TestHarness(Module, 
                   data_nbits,
                   ctrl_addr_nbits,
                   src_cmds, 
                   src_opts, 
                   src_init_phi_addr,
                   src_ctrl_mem_rd_addr,
                   src_accumulation_in, 
                   sink_overwrite_fu_outport)

  run_sim(th)
