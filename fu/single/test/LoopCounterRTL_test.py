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
                  src_const, src_opt, src_from_ctrl, sink_out, sink_to_ctrl, ctrl_addrs):
        s.src_const = TestSrcRTL(DataType, src_const)
        s.src_opt = TestSrcRTL(CtrlType, src_opt)
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
    
    # Configuration constants: lower=0, upper=5, step=1
    src_const = [
        DataType(0, 1),   # lower_bound = 0
        DataType(5, 1),   # upper_bound = 5
        DataType(1, 1),   # step = 1
    ]
    
    # Operations: keeps executing OPT_LOOP_COUNT
    src_opt = [CtrlType(OPT_LOOP_COUNT)] * 10
    
    # No messages from control memory for leaf counter.
    src_from_ctrl = []
    
    # Expected output: 0,1,2,3,4 (pred=1), then 5,5,5... (pred=0)
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
        CgraPayloadType(CMD_COMPLETE, DataType(0,0), 0, CtrlType(OPT_LOOP_COUNT), 0)
    ]
    
    ctrl_addrs = [0]*20
    
    th = TestHarness(LoopCounterRTL, DataType, CtrlType, CgraPayloadType,
                     num_inports, num_outports,
                     data_mem_size, ctrl_mem_size,
                     src_const, src_opt, src_from_ctrl, sink_out, sink_to_ctrl, ctrl_addrs)
    
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
    
    src_const = [
        DataType(0, 1),
        DataType(10, 1),
        DataType(2, 1),
    ]
    
    src_opt = [CtrlType(OPT_LOOP_COUNT)] * 8
    src_from_ctrl = []
    
    sink_out = [
        DataType(0, 1),
        DataType(2, 1),
        DataType(4, 1),
        DataType(6, 1),
        DataType(8, 1),
        DataType(10, 0),
        DataType(10, 0),
        DataType(10, 0),
    ]
    sink_to_ctrl = [
        CgraPayloadType(CMD_COMPLETE, DataType(0,0), 0, CtrlType(OPT_LOOP_COUNT), 1)
    ]
    
    ctrl_addrs = [1]*20
    
    th = TestHarness(LoopCounterRTL, DataType, CtrlType, CgraPayloadType,
                     num_inports, num_outports,
                     data_mem_size, ctrl_mem_size,
                     src_const, src_opt, src_from_ctrl, sink_out, sink_to_ctrl, ctrl_addrs)
    
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
    
    # No constants needed for shadow register
    src_const = []
    
    # Execute OPT_LOOP_PROVIDE operations
    src_opt = [
        CtrlType(OPT_LOOP_PROVIDE),  # Output shadow[2]
        CtrlType(OPT_LOOP_PROVIDE),  # Output shadow[2] (updated value)
        CtrlType(OPT_LOOP_PROVIDE),  # Output shadow[2]
        CtrlType(OPT_LOOP_PROVIDE),  # Output shadow[2]
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

def test_multiple_counters():
    """Test interleaved operations on different counters"""
    
    num_inports = 4
    num_outports = 2
    data_mem_size = 8
    ctrl_mem_size = 8
    DataType = mk_data(32, 1)
    CtrlType = mk_ctrl(num_inports, num_outports, num_inports, num_outports)
    
    AddrType = mk_bits(clog2(data_mem_size))
    CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
    CgraPayloadType = mk_cgra_payload(DataType, AddrType, CtrlType, CtrlAddrType)
    
    # Configure leaf counter at ctrl_addr=0: for(i=0; i<3; i++)
    src_const = [
        DataType(0, 1),   # lower=0
        DataType(3, 1),   # upper=3
        DataType(1, 1),   # step=1
    ]
    
    # Interleaved operations:
    # - During config (cycles 1-4), first OPT is NOT consumed (recv_opt.rdy=0)
    # - At cycle 5 (DONE), first OPT gets consumed, we need new OPTs for each subsequent cycle
    # - So we need: 1 for config + 4 for execution (0,1,2,3) + 3 for shadow = 8 total
    # But src_opt is consumed only when recv_opt.rdy=1, so timing matters
    src_opt = [
        CtrlType(OPT_LOOP_COUNT),    # Consumed at cycle 5: output 0
        CtrlType(OPT_LOOP_PROVIDE),  # Consumed at cycle 6: shadow[1]
        CtrlType(OPT_LOOP_COUNT),    # Consumed at cycle 7: output 1
        CtrlType(OPT_LOOP_PROVIDE),  # Consumed at cycle 8: shadow[1]
        CtrlType(OPT_LOOP_COUNT),    # Consumed at cycle 9: output 2
        CtrlType(OPT_LOOP_PROVIDE),  # Consumed at cycle 10: shadow[1]
        CtrlType(OPT_LOOP_COUNT),    # Consumed at cycle 11: output 3
    ]
    
    #Update shadow[1] from AC
    src_from_ctrl = [
        CgraPayloadType(CMD_UPDATE_COUNTER_SHADOW_VALUE, DataType(100, 1), 0, CtrlType(0), 1),
    ]
    
    # Expected outputs
    sink_out = [
        DataType(0, 1),    # cycle 5: leaf counter[0] = 0
        DataType(100, 1),  # cycle 6: shadow[1] = 100
        DataType(1, 1),    # cycle 7: leaf counter[0] = 1
        DataType(100, 1),  # cycle 8: shadow[1] = 100
        DataType(2, 1),    # cycle 9: leaf counter[0] = 2
        DataType(100, 1),  # cycle 10: shadow[1] = 100
        DataType(3, 0),    # cycle 11: leaf counter[0] = 3 (pred=0)
    ]
    
    sink_to_ctrl = [
        CgraPayloadType(CMD_COMPLETE, DataType(0,0), 0, CtrlType(OPT_LOOP_COUNT), 0)
    ]
    
    # ctrl_addr sequence
    # Config takes 4 cycles: WAIT(1), LOWER(2), UPPER(3), STEP(4) -> DONE at cycle 5
    # So keep addr=0 for cycles 0-4, first output at cycle 5
    ctrl_addrs = [
        0,  # Cycle 0: IDLE
        0,  # Cycle 1: WAIT
        0,  # Cycle 2: LOWER
        0,  # Cycle 3: UPPER
        0,  # Cycle 4: STEP
        0,  # Cycle 5: DONE, output 0
        1,  # Cycle 6: shadow[1]
        0,  # Cycle 7: output 1
        1,  # Cycle 8: shadow[1]
        0,  # Cycle 9: output 2
        1,  # Cycle 10: shadow[1]
        0,  # Cycle 11: output 3
    ] + [0] * 10
    
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
    
    # Configure: for(i=0; i<5; i++)
    src_const = [
        DataType(0, 1),
        DataType(5, 1),
        DataType(1, 1),
    ]
    
    src_opt = [CtrlType(OPT_LOOP_COUNT)] * 12
    
    # Reset counter after it reaches 2
    # Timing analysis:
    # - Config: cycles 1-4 (output starts at cycle 5)
    # - Execution: cycle 5(out=0), 6(out=1), 7(out=2), 8(expect reset to 0)
    # - Reset  at cycle 7 will take effect in cycle 8 output
    # Need to keep src_from_ctrl alive with dummy messages
    src_from_ctrl = [
        # Placeholders for cycles 1-6 (won't affect ctrl_addr=0)
        CgraPayloadType(CMD_RESET_LEAF_COUNTER, DataType(0, 0), 0, CtrlType(0), 7),  # cycle 1
        CgraPayloadType(CMD_RESET_LEAF_COUNTER, DataType(0, 0), 0, CtrlType(0), 7),  # cycle 2
        CgraPayloadType(CMD_RESET_LEAF_COUNTER, DataType(0, 0), 0, CtrlType(0), 7),  # cycle 3
        CgraPayloadType(CMD_RESET_LEAF_COUNTER, DataType(0, 0), 0, CtrlType(0), 7),  # cycle 4
        CgraPayloadType(CMD_RESET_LEAF_COUNTER, DataType(0, 0), 0, CtrlType(0), 7),  # cycle 5
        CgraPayloadType(CMD_RESET_LEAF_COUNTER, DataType(0, 0), 0, CtrlType(0), 7),  # cycle 6
        # Actual reset for ctrl_addr=0 at cycle 7
        CgraPayloadType(CMD_RESET_LEAF_COUNTER, DataType(0, 0), 0, CtrlType(0), 0),  # cycle 7
        # More dummy messages to keep source alive
    ] + [CgraPayloadType(CMD_RESET_LEAF_COUNTER, DataType(0, 0), 0, CtrlType(0), 7) for _ in range(20)]
    
    # Expected: 0,1,2, then reset to 0, then 1,2,3,4,5(pred=0)
    sink_out = [
        DataType(0, 1),   # First iteration
        DataType(1, 1),
        DataType(2, 1),
        DataType(0, 1),   # Reset by AC
        DataType(1, 1),
        DataType(2, 1),
        DataType(3, 1),
        DataType(4, 1),
        DataType(5, 0),   # Terminated
        DataType(5, 0),
        DataType(5, 0),
        DataType(5, 0),
    ]
    
    sink_to_ctrl = [
        CgraPayloadType(CMD_COMPLETE, DataType(0,0), 0, CtrlType(OPT_LOOP_COUNT), 0),
    ]
    
    ctrl_addrs = [0] * 20
    
    th = TestHarness(LoopCounterRTL, DataType, CtrlType, CgraPayloadType,
                     num_inports, num_outports,
                     data_mem_size, ctrl_mem_size,
                     src_const, src_opt, src_from_ctrl, sink_out, sink_to_ctrl,
                     ctrl_addrs)
    
    run_sim(th)