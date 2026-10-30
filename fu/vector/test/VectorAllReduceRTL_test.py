"""
==========================================================================
VectorAllReduceRTL_test.py
==========================================================================
Test case for VectorAllReduceRTL functional unit.

Author : Cheng Tan
  Date : April 23, 2022
"""

from pymtl3 import *
from ..VectorAllReduceRTL import VectorAllReduceRTL
from ....lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ....lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ....lib.opt_type import *
from ....lib.messages import *

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, FunctionUnit, IntraCgraPktType, DataType, CtrlType,
                num_inports, num_outports, data_mem_size,
                src0_msgs, src1_msgs, ctrl_msgs, sink_msgs0):

    s.src_in0       = TestSrcRTL (DataType, src0_msgs )
    s.src_in1       = TestSrcRTL (DataType, src1_msgs )
    s.src_opt       = TestSrcRTL (CtrlType, ctrl_msgs )
    s.sink_out0     = TestSinkRTL(DataType, sink_msgs0)

    s.dut = FunctionUnit(IntraCgraPktType,
                         num_inports, num_outports)

    connect(s.src_in0.send,    s.dut.recv_in[0])
    connect(s.src_in1.send,    s.dut.recv_in[1])
    connect(s.src_opt.send,    s.dut.recv_opt  )
    connect(s.dut.send_out[0], s.sink_out0.recv)

  def done(s):
    return s.src_in0.done() and s.src_opt.done() and s.sink_out0.done()

  def line_trace(s):
    return s.dut.line_trace()

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

def test_vector_all_reduce():
  FU            = VectorAllReduceRTL
  data_width    = 16
  DataType      = mk_data(data_width, 1)
  PredType      = mk_predicate(1, 1)
  num_inports   = 2
  num_outports  = 1
  CtrlType      = mk_ctrl(num_inports, num_outports)
  data_mem_size = 8
  ctrl_mem_size = 8
  DataAddrType  = mk_bits(clog2(data_mem_size))
  CtrlAddrType  = mk_bits(clog2(ctrl_mem_size))
  CgraPayloadType = mk_cgra_payload(DataType, DataAddrType, CtrlType, CtrlAddrType)
  IntraCgraPktType = mk_intra_cgra_pkt(1, 1, 1, CgraPayloadType)

  FuInType      = mk_bits(clog2(num_inports + 1))
  pickRegister  = [FuInType(x + 1) for x in range(num_inports)]

  src_in0  = [DataType(0x3402,1), DataType(0x1177,1), DataType(0x0002,1)]
  src_in1  = [DataType(0x32f3,1), DataType(0x89,  1), DataType(0x0003,1)]
  sink_out = [DataType(0x9,   1), DataType(0x31,  1), DataType(0x0,   1)]
  src_opt  = [CtrlType(OPT_VEC_REDUCE_ADD, pickRegister),
              CtrlType(OPT_VEC_REDUCE_MUL, pickRegister),
              CtrlType(OPT_VEC_REDUCE_MUL, pickRegister)]

  th = TestHarness(FU, IntraCgraPktType, DataType, CtrlType,
                   num_inports, num_outports,
                   data_mem_size,
                   src_in0, src_in1, src_opt, sink_out)
  run_sim(th)

class GlobalTestHarness(Component):

  def construct(s, FunctionUnit, IntraCgraPktType, DataType, CtrlType,
                CgraPayloadType, num_inports, num_outports,
                src0_msg, src1_msg, ctrl_msg, sink_msg0,
                response_msg, response_delay, hold_inputs):

    s.hold_inputs = hold_inputs
    s.src_opt = TestSrcRTL(CtrlType, [ctrl_msg])
    s.sink_out0 = TestSinkRTL(DataType, [sink_msg0])
    s.src_response = TestSrcRTL(CgraPayloadType, [response_msg],
                                initial_delay = response_delay)

    s.dut = FunctionUnit(IntraCgraPktType,
                         num_inports, num_outports)

    connect(s.src_opt.send, s.dut.recv_opt)
    connect(s.src_response.send, s.dut.recv_from_ctrl_mem)
    s.dut.send_to_ctrl_mem.rdy //= 1

    if hold_inputs:
      # Register-sourced operands stay valid for the whole ctrl step and
      # ignore rdy.
      @update
      def hold_operands():
        s.dut.recv_in[0].val @= 1
        s.dut.recv_in[0].msg @= src0_msg
        s.dut.recv_in[1].val @= 1
        s.dut.recv_in[1].msg @= src1_msg
    else:
      s.src_in0 = TestSrcRTL(DataType, [src0_msg])
      s.src_in1 = TestSrcRTL(DataType, [src1_msg])
      connect(s.src_in0.send, s.dut.recv_in[0])
      connect(s.src_in1.send, s.dut.recv_in[1])

    # Like the FU crossbar, only accepts the output once it is valid, since
    # the FU derives recv_opt.rdy from send_out.rdy.
    @update
    def drive_sink():
      s.sink_out0.recv.val @= s.dut.send_out[0].val
      s.sink_out0.recv.msg @= s.dut.send_out[0].msg
      s.dut.send_out[0].rdy @= s.sink_out0.recv.rdy & s.dut.send_out[0].val

  def done(s):
    inputs_done = s.hold_inputs or (s.src_in0.done() and s.src_in1.done())
    return inputs_done and s.src_opt.done() and \
           s.src_response.done() and s.sink_out0.done()

  def line_trace(s):
    return s.dut.line_trace()

def run_global_test(operation, hold_inputs, expected_cmd, expected_partial,
                    response_cmd, response_value, expected_out):
  FU            = VectorAllReduceRTL
  data_width    = 16
  DataType      = mk_data(data_width, 1)
  num_inports   = 2
  num_outports  = 1
  CtrlType      = mk_ctrl(num_inports, num_outports)
  data_mem_size = 8
  ctrl_mem_size = 8
  DataAddrType  = mk_bits(clog2(data_mem_size))
  CtrlAddrType  = mk_bits(clog2(ctrl_mem_size))
  CgraPayloadType = mk_cgra_payload(DataType, DataAddrType, CtrlType, CtrlAddrType)
  IntraCgraPktType = mk_intra_cgra_pkt(1, 1, 1, CgraPayloadType)

  FuInType      = mk_bits(clog2(num_inports + 1))
  pickRegister  = [FuInType(x + 1) for x in range(num_inports)]
  ctrl          = CtrlType(operation, pickRegister)

  # Lanes of src_in0 (low to high): 4, 3, 2, 1.
  src_in0  = DataType(0x1234, 1)
  src_in1  = DataType(3, 1)
  response = CgraPayloadType(response_cmd, DataType(response_value, 1))
  response_delay = 4
  #                                    cmd,          data,                          data addr, ctrl, ctrl addr
  expected_partials = [CgraPayloadType(expected_cmd, DataType(expected_partial, 1), 0,         ctrl, 0)]

  th = GlobalTestHarness(FU, IntraCgraPktType, DataType, CtrlType,
                         CgraPayloadType, num_inports, num_outports,
                         src_in0, src_in1, ctrl, DataType(expected_out, 1),
                         response, response_delay, hold_inputs)
  th.elaborate()
  th.apply(DefaultPassGroup())
  th.sim_reset()

  max_cycles = 20
  partials = []
  ncycles = 0
  print()
  while not th.done() and ncycles < max_cycles:
    if th.dut.send_to_ctrl_mem.val:
      partials.append(th.dut.send_to_ctrl_mem.msg.clone())
    th.sim_tick()
    ncycles += 1
    print("{}:{}".format(ncycles, th.line_trace()))

  assert ncycles < max_cycles
  assert partials == expected_partials

def test_vector_all_reduce_add_base_global():
  #               operation,                      hold inputs, partial cmd,           partial, response cmd,                   response, output
  run_global_test(OPT_VEC_REDUCE_ADD_BASE_GLOBAL, False,       CMD_GLOBAL_REDUCE_ADD, 10,      CMD_GLOBAL_REDUCE_ADD_RESPONSE, 100,      100 + 3)

def test_vector_all_reduce_mul_base_global():
  #               operation,                      hold inputs, partial cmd,           partial, response cmd,                   response, output
  run_global_test(OPT_VEC_REDUCE_MUL_BASE_GLOBAL, False,       CMD_GLOBAL_REDUCE_MUL, 24,      CMD_GLOBAL_REDUCE_MUL_RESPONSE, 7,        7 * 3)

# Operands held valid while the response is pending must not be sent again.
def test_vector_all_reduce_base_global_sends_once():
  #               operation,                      hold inputs, partial cmd,           partial, response cmd,                   response, output
  run_global_test(OPT_VEC_REDUCE_ADD_BASE_GLOBAL, True,        CMD_GLOBAL_REDUCE_ADD, 10,      CMD_GLOBAL_REDUCE_ADD_RESPONSE, 100,      100 + 3)
