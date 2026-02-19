'''
=========================================================================
ControllerRTL_test.py
=========================================================================
Simple test for ControllerRTL.

Author : Cheng Tan
  Date : Dec 15, 2024
'''
from pymtl3.passes.backends.verilog import (VerilogVerilatorImportPass)
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)

from ..STEP_TileShiftRegisterRTL import STEP_TileShiftRegisterRTL
from ...lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ...lib.messages import *
from ...lib.opt_type import *
from ...lib.basic.TimedWriteSource import TimedWriteSource


#-------------------------------------------------------------------------
# TestHarness
#-------------------------------------------------------------------------
interval_delay = 7

class TestHarness(Component):

    def construct(s,
                    DataType,
                    ShiftAmountType,
                    data_in_msgs,
                    data_out_msgs,
                    shift_amount_in_msgs
                    ):

        # Configure sources - recv_from_cpu_pkt launches every cycle
        s.data_in_pkts = TestSrcRTL(DataType, data_in_msgs)
        s.shift_amount_in_pkts = TestSrcRTL(ShiftAmountType, shift_amount_in_msgs)

        # Configure sinks
        cmp_fn = lambda a, b : a == b
        s.data_out_pkts = TestSinkRTL(DataType, data_out_msgs, cmp_fn = cmp_fn)

        # Device Under Test
        s.dut = STEP_TileShiftRegisterRTL(DataType)

        # Input Connections
        s.dut.data_in //= s.data_in_pkts.send.msg
        s.data_in_pkts.send.rdy //= 1
        s.dut.shift_amount_in //= s.shift_amount_in_pkts.send.msg
        s.shift_amount_in_pkts.send.rdy //= 1

        # Output Connections
        s.dut.data_out //= s.data_out_pkts.recv.msg
        s.data_out_pkts.recv.val //= 1

    def done(s):
        return s.data_in_pkts.done() and s.data_out_pkts.done()

    def line_trace(s):
        return s.dut.line_trace()

def init_param():
    #-------------------------------------------------------------------------
    # Test cases
    #-------------------------------------------------------------------------
    # Parameterizable
    DataType = mk_bits(8)
    ShiftAmountType = mk_bits( clog2(SHIFT_REGISTER_SIZE) )
    shift_amount = 2

    data_in_msgs = [DataType(0x01), DataType(0x02), DataType(0x03)]
    shift_amount_in_msgs = [ShiftAmountType(shift_amount)]
    
    data_out_msgs = [DataType(0x00) for _ in range(shift_amount + 2)]
    data_out_msgs += data_in_msgs

    th = TestHarness(DataType,
                    ShiftAmountType,
                    data_in_msgs,
                    data_out_msgs,
                    shift_amount_in_msgs
                    )
    return th

def test_simple(cmdline_opts):
    th = init_param()
    
    th.elaborate()
    th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                       ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                        'ALWCOMBORDER'])
    th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
    run_sim(th)  # Added max_cycles to prevent infinite simulation