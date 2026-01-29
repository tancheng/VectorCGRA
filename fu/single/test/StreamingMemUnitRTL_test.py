"""
==========================================================================
StreamingMemUnitRTL_test.py
==========================================================================
Test cases for functional unit.

Author : Yufei Yang
  Date : Jan 29, 2026
"""

from pymtl3 import *

from ..StreamingMemUnitRTL import StreamingMemUnitRTL
from ....lib.messages import *
from ....lib.opt_type import *
from ....lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ....lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ....mem.data.DataMemCL import DataMemCL
from ....mem.data.DataMemRTL import DataMemRTL
from pymtl3.stdlib.test_utils import (run_sim, config_model_with_cmdline_opts)

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------
# TODO: connect recv_const

class TestHarness(Component):

  def construct(s, FunctionUnit, DataUnit, CtrlPktType, DataType, DataAddrType,
                CtrlType, CtrlAddrType, num_inports, num_outports, data_mem_size,
                ctrl_mem_size, src_waddr_msgs, src_wdata_msgs, src_ctrl_msgs, 
                src_opt_msgs, src_ctrl_addr_msgs, sink_msgs):

    s.src_waddr = TestSrcRTL(DataAddrType, src_waddr_msgs)
    s.src_wdata = TestSrcRTL(DataType, src_wdata_msgs)
    s.src_ctrl = TestSrcRTL(CtrlPktType, src_ctrl_msgs)
    s.src_opt = TestSrcRTL(CtrlType, src_opt_msgs)
    s.src_ctrl_addr = TestSrcRTL(CtrlAddrType, src_ctrl_addr_msgs)
    s.sink_out = TestSinkRTL(DataType, sink_msgs)

    s.dut = FunctionUnit(CtrlPktType, DataType, CtrlType,
                         num_inports, num_outports, data_mem_size, ctrl_mem_size)
    s.data_mem = DataUnit(DataType, data_mem_size)

    connect(s.dut.to_mem_raddr,   s.data_mem.recv_raddr[0])
    connect(s.dut.from_mem_rdata, s.data_mem.send_rdata[0])
    connect(s.src_waddr.send,   s.data_mem.recv_waddr[0])
    connect(s.src_wdata.send,   s.data_mem.recv_wdata[0])
    connect(s.src_ctrl.send, s.dut.recv_from_controller_pkt)
    connect(s.src_opt.send, s.dut.recv_opt)
    connect(s.dut.send_out[0], s.sink_out.recv)

    @update
    def ctrl_addr_inport():
      s.dut.ctrl_addr_inport @= s.src_ctrl_addr.send.msg
      s.src_ctrl_addr.send.rdy @= 1

  def done(s):
    return s.src_waddr.done() and s.src_wdata.done() and s.src_ctrl.done() and \
           s.src_opt.done() and s.sink_out.done()

  def line_trace(s):
    return s.data_mem.line_trace() + ' || ' + s.dut.line_trace()

def run_sim(test_harness, max_cycles = 20):
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

def test_streaming_load(cmdline_opts):
  FU = StreamingMemUnitRTL
  DataUnit = DataMemRTL
  DataType = mk_data(16, 1)
  data_mem_size = 8
  ctrl_mem_size = 8
  num_inports = 2
  num_outports = 1
  DataAddrType = mk_bits(clog2(data_mem_size))
  CtrlType = mk_ctrl(num_inports, num_outports)
  CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
  CgraPayloadType = mk_cgra_payload(DataType, DataAddrType, CtrlType, CtrlAddrType)
  CtrlPktType = mk_intra_cgra_pkt(1, 1, 1, CgraPayloadType)
  FuInType = mk_bits(clog2(num_inports + 1))
  pickRegister = [FuInType(x + 1) for x in range(num_inports)]
  src_ctrl_pkt = [
    # 4 useless commands to wait for 4 data preloading.
    CtrlPktType(0, 0, payload = CgraPayloadType(CMD_CONST, data = DataType(0, 1))),
    CtrlPktType(0, 0, payload = CgraPayloadType(CMD_CONST, data = DataType(0, 1))),
    CtrlPktType(0, 0, payload = CgraPayloadType(CMD_CONST, data = DataType(0, 1))),
    CtrlPktType(0, 0, payload = CgraPayloadType(CMD_CONST, data = DataType(0, 1))),
    # Config streaming parameters.
    CtrlPktType(0, 0, payload = CgraPayloadType(CMD_CONFIG_STREAMING_LD_START_ADDR, data = DataType(0, 1))),
    CtrlPktType(0, 0, payload = CgraPayloadType(CMD_CONFIG_STREAMING_LD_STRIDE, data = DataType(1, 1))),
    CtrlPktType(0, 0, payload = CgraPayloadType(CMD_CONFIG_STREAMING_LD_END_ADDR, data = DataType(3, 1))),
  ]
  src_waddr = [DataAddrType(0), DataAddrType(1), DataAddrType(2), DataAddrType(3)] # Preloading write address.
  src_wdata = [DataType(9, 1), DataType(8, 1), DataType(7, 1), DataType(6, 1)] # Preloading data.
  sink_out =  [DataType(9, 1), DataType(8, 1), DataType(7, 1), DataType(6, 1)] # Streaming load responses.
  src_opt =   [CtrlType(OPT_STREAM_LD,  pickRegister)]
  src_ctrl_addr = [# Waits for data preloading.
                   CtrlAddrType(0), 
                   CtrlAddrType(0),
                   CtrlAddrType(0),
                   CtrlAddrType(0),
                   # Waits for streaming configuration.
                   CtrlAddrType(0),
                   CtrlAddrType(0),
                   CtrlAddrType(0),
                   # Starts streaming load.
                   CtrlAddrType(1)]
  th = TestHarness(FU, DataUnit, CtrlPktType, DataType, DataAddrType, 
                   CtrlType, CtrlAddrType, num_inports, 
                   num_outports, data_mem_size, ctrl_mem_size,
                   src_waddr, src_wdata, src_ctrl_pkt, src_opt,
                   src_ctrl_addr, sink_out)
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)
