"""
==========================================================================
LoopCounterRTL.py
==========================================================================
Test cases for functional unit LoopCounter.

Author : Shangkun Li
  Date : January 21, 2026
"""

from pymtl3 import *
from ..LoopCounterRTL import LoopCounterRTL
from ....lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ....lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ....lib.messages import *
from ....lib.opt_type import *
from ....lib.cmd_type import *

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):
    def construct(s, FunctionUnit, DataType, CtrlType, CgraPayloadType,
                  num_inports, num_outports,
                  data_mem_size, ctrl_mem_size,
                  src_const, src_opt, src_from_ctrl, sink_out, sink_to_ctrl, ctrl_addrs,
                  opt_initial_delay=0):
        s.src_const = TestSrcRTL(DataType, src_const)
        s.src_opt = TestSrcRTL(CtrlType, src_opt, initial_delay=opt_initial_delay)
        s.src_from_ctrl = TestSrcRTL(CgraPayloadType, src_from_ctrl)
        s.sink_out = TestSinkRTL(DataType, sink_out)
        s.sink_to_ctrl = TestSinkRTL(CgraPayloadType, sink_to_ctrl)
        
        s.dut = FunctionUnit(DataType, CtrlType, num_inports, num_outports,
                            data_mem_size, ctrl_mem_size)
        
        s.ctrl_addrs = ctrl_addrs
        s.cycle_count = Wire(mk_bits(32))
        
        connect(s.src_const.send, s.dut.recv_const)
        connect(s.src_opt.send, s.dut.recv_opt)
        connect(s.src_from_ctrl.send, s.dut.recv_from_ctrl_mem)
        connect(s.dut.send_out[0], s.sink_out.recv)
        connect(s.dut.send_to_ctrl_mem, s.sink_to_ctrl.recv)
    
        @update_ff
        def update_cycle():
            if s.reset:
                s.cycle_count <<= 0
            else:
                s.cycle_count <<= s.cycle_count + 1
            
        @update
        def set_ctrl_addr():
            if s.cycle_count < len(s.ctrl_addrs):
                s.dut.ctrl_addr_inport @= s.ctrl_addrs[s.cycle_count]
            else:
                s.dut.ctrl_addr_inport @= s.ctrl_addrs[-1] if s.ctrl_addrs else 0
    
    def done(s):
        return (s.src_const.done() and s.src_opt.done() and s.src_from_ctrl.done() and 
                s.sink_out.done() and s.sink_to_ctrl.done())
    
    def line_trace(s):
        return s.dut.line_trace()

def run_sim(test_harness, max_cycles = 100):
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
    print("{}:{}".format( ncycles, test_harness.line_trace()))

  # Check timeout
  assert ncycles < max_cycles

  test_harness.sim_tick()
  test_harness.sim_tick()
  test_harness.sim_tick()
  
#-------------------------------------------------------------------------
# Test cases
#-------------------------------------------------------------------------

def test_leaf_counter_basic():
    """Test basic counter: for(i=0; i<5; i++) at ctrl_addr=0"""
    
    num_inports = 4
    num_outports = 2
    data_mem_size = 8
    ctrl_mem_size = 8
    DataType = mk_data(32, 1)
    CtrlType = mk_ctrl(num_inports, num_outports, num_inports, num_outports)
    
    AddrType = mk_bits(clog2(data_mem_size))
    CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
    CgraPayloadType = mk_cgra_payload(DataType, AddrType, CtrlType, CtrlAddrType)
    
    # Constants are NO LONGER used for configuration.
    src_const = []
    
    # Expected output has 10 items. So we should send 10 OPTs.
    src_opt = [CtrlType(OPT_LOOP_COUNT)] * 10
    
    # Configure via CMDs from control memory.
    src_from_ctrl = [
        # Cycle 0: Set Lower Bound = 0
        CgraPayloadType(CMD_CONFIG_LOOP_LOWER, DataType(0, 1), 0, CtrlType(0), 0),
        # Cycle 1: Set Upper Bound = 5
        CgraPayloadType(CMD_CONFIG_LOOP_UPPER, DataType(5, 1), 0, CtrlType(0), 0),
        # Cycle 2: Set Step = 1
        CgraPayloadType(CMD_CONFIG_LOOP_STEP, DataType(1, 1), 0, CtrlType(0), 0),
    ]
    
    sink_out = [
        DataType(0, 1),   # i=0, predicate=1
        DataType(1, 1),   # i=1, predicate=1
        DataType(2, 1),   # i=2, predicate=1
        DataType(3, 1),   # i=3, predicate=1
        DataType(4, 1),   # i=4, predicate=1
        DataType(5, 0),   # i=5>=upper, predicate=0
        DataType(5, 0),   # stays at 5, pred=0
        DataType(5, 0),
        DataType(5, 0),
        DataType(5, 0),
    ]
    
    sink_to_ctrl = [
        CgraPayloadType(CMD_LEAF_COUNTER_COMPLETE, DataType(0,0), 0, CtrlType(OPT_LOOP_COUNT), 0)
    ]
    
    ctrl_addrs = [0]*10
    
    th = TestHarness(LoopCounterRTL, DataType, CtrlType, CgraPayloadType,
                     num_inports, num_outports,
                     data_mem_size, ctrl_mem_size,
                     src_const, src_opt, src_from_ctrl, sink_out, sink_to_ctrl, ctrl_addrs,
                     opt_initial_delay=3)
    
    run_sim(th)
    
def test_loop_counter_with_step():
    """Test counter with step: for(i=0; i<10; i+=2)"""
    
    num_inports = 4
    num_outports = 2
    data_mem_size = 8
    ctrl_mem_size = 8
    DataType = mk_data(32, 1)
    CtrlType = mk_ctrl(num_inports, num_outports, num_inports, num_outports)
    
    AddrType = mk_bits(clog2(data_mem_size))
    CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
    CgraPayloadType = mk_cgra_payload(DataType, AddrType, CtrlType, CtrlAddrType)
    
    src_const = []
    
    src_opt = [CtrlType(OPT_LOOP_COUNT)] * 8
    
    # Reset/Configure for ctrl_addr=1
    src_from_ctrl = [
        CgraPayloadType(CMD_CONFIG_LOOP_LOWER, DataType(0, 1), 0, CtrlType(0), 1),
        CgraPayloadType(CMD_CONFIG_LOOP_UPPER, DataType(10, 1), 0, CtrlType(0), 1),
        CgraPayloadType(CMD_CONFIG_LOOP_STEP, DataType(2, 1), 0, CtrlType(0), 1),
    ]
    
    sink_out = [
        DataType(0, 1),
        DataType(2, 1),
        DataType(4, 1),
        DataType(6, 1),
        DataType(8, 1),
        DataType(10, 0),
        DataType(10, 0),
        DataType(10, 0)
    ]
    sink_to_ctrl = [
        CgraPayloadType(CMD_LEAF_COUNTER_COMPLETE, DataType(0,0), 0, CtrlType(OPT_LOOP_COUNT), 1)
    ]
    
    ctrl_addrs = [1]*20
    
    th = TestHarness(LoopCounterRTL, DataType, CtrlType, CgraPayloadType,
                     num_inports, num_outports,
                     data_mem_size, ctrl_mem_size,
                     src_const, src_opt, src_from_ctrl, sink_out, sink_to_ctrl, ctrl_addrs,
                     opt_initial_delay=3)
    
    run_sim(th)
    

def test_shadow_register_basic():
    """Test shadow register at ctrl_addr=2"""
    
    num_inports = 4
    num_outports = 2
    data_mem_size = 8
    ctrl_mem_size = 8
    DataType = mk_data(32, 1)
    CtrlType = mk_ctrl(num_inports, num_outports, num_inports, num_outports)
    
    AddrType = mk_bits(clog2(data_mem_size))
    CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
    CgraPayloadType = mk_cgra_payload(DataType, AddrType, CtrlType, CtrlAddrType)
    
    src_const = []
    
    # Execute OPT_LOOP_DELIVERY operations
    src_opt = [
        CtrlType(OPT_LOOP_DELIVERY),  # Output shadow[2]
        CtrlType(OPT_LOOP_DELIVERY),  # Output shadow[2] (updated value)
        CtrlType(OPT_LOOP_DELIVERY),  # Output shadow[2]
        CtrlType(OPT_LOOP_DELIVERY),  # Output shadow[2]
    ]
    
    # AC updates shadow register at ctrl_addr=2
    src_from_ctrl = [
        # Update shadow[2] = 5
        CgraPayloadType(CMD_UPDATE_COUNTER_SHADOW_VALUE, DataType(5, 1), 0, CtrlType(0), 2),
        # Update shadow[2] = 10
        CgraPayloadType(CMD_UPDATE_COUNTER_SHADOW_VALUE, DataType(10, 1), 0, CtrlType(0), 2),
    ]
    
    # Expected outputs
    sink_out = [
        DataType(5, 1),   # Output shadow[2] = 5
        DataType(10, 1),  # Output shadow[2] = 10 (updated)
        DataType(10, 1),  # Continue shadow[2] = 10
        DataType(10, 1),  # Continue shadow[2] = 10
    ]
    
    sink_to_ctrl = []
    
    # All operations target ctrl_addr = 2
    ctrl_addrs = [2] * 20
    
    th = TestHarness(LoopCounterRTL, DataType, CtrlType, CgraPayloadType,
                     num_inports, num_outports,
                     data_mem_size, ctrl_mem_size,
                     src_const, src_opt, src_from_ctrl, sink_out, sink_to_ctrl,
                     ctrl_addrs)
    
    run_sim(th)
    
def test_counter_reset():
    """Test resetting leaf counter via AC command"""
    
    num_inports = 4
    num_outports = 2
    data_mem_size = 8
    ctrl_mem_size = 8
    DataType = mk_data(32, 1)
    CtrlType = mk_ctrl(num_inports, num_outports, num_inports, num_outports)
    
    AddrType = mk_bits(clog2(data_mem_size))
    CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
    CgraPayloadType = mk_cgra_payload(DataType, AddrType, CtrlType, CtrlAddrType)
    
    
    src_const = []
    
    src_opt = [CtrlType(OPT_LOOP_COUNT)] * 12
    
    # Reset counter after it reaches 2
    # Timing analysis:
    # - Config: cycles 1-3 (output starts at cycle 4)
    # - Execution: cycle 4(out=0), 5(out=1), 6(out=2), 7(out=3, expect reset to 0)
    # - Reset at cycle 7 will take effect in cycle 8 output
    # Need to keep src_from_ctrl alive with dummy messages
    src_from_ctrl = [
        CgraPayloadType(CMD_CONFIG_LOOP_LOWER, DataType(0, 1), 0, CtrlType(0), 0),
        CgraPayloadType(CMD_CONFIG_LOOP_UPPER, DataType(5, 1), 0, CtrlType(0), 0),
        CgraPayloadType(CMD_CONFIG_LOOP_STEP, DataType(1, 1), 0, CtrlType(0), 0),
        # Placeholders for cycles 4-7 (won't affect ctrl_addr=0)
        CgraPayloadType(0, DataType(0, 0), 0, CtrlType(0), 0),
        CgraPayloadType(0, DataType(0, 0), 0, CtrlType(0), 0),
        CgraPayloadType(0, DataType(0, 0), 0, CtrlType(0), 0),
        # Actual reset for ctrl_addr=0 at cycle 7
        CgraPayloadType(CMD_RESET_LEAF_COUNTER, DataType(0, 0), 0, CtrlType(0), 0)
    ]
    
    # Expected: 0,1,2, then reset to 0, then 1,2,3,4,5(pred=0)
    sink_out = [
        DataType(0, 1),   # First iteration
        DataType(1, 1),
        DataType(2, 1),
        DataType(3, 1),   # Reset by AC
        DataType(0, 1),
        DataType(1, 1),
        DataType(2, 1),
        DataType(3, 1),
        DataType(4, 1),
        DataType(5, 0),
        DataType(5, 0),
        DataType(5, 0),
    ]
    
    sink_to_ctrl = [
        CgraPayloadType(CMD_LEAF_COUNTER_COMPLETE, DataType(0,0), 0, CtrlType(OPT_LOOP_COUNT), 0),
    ]
    
    ctrl_addrs = [0] * 20
    
    th = TestHarness(LoopCounterRTL, DataType, CtrlType, CgraPayloadType,
                     num_inports, num_outports,
                     data_mem_size, ctrl_mem_size,
                     src_const, src_opt, src_from_ctrl, sink_out, sink_to_ctrl,
                     ctrl_addrs,
                     opt_initial_delay=3)
    
    run_sim(th)