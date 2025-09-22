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

from ..STEP_TokenizerRTL import STEP_TokenizerRTL
from ...lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ...lib.messages import *
from ...lib.opt_type import *
from ...lib.basic.TimedWriteSource import TimedWriteSource


#-------------------------------------------------------------------------
# TestHarness
#-------------------------------------------------------------------------

class TestHarness(Component):

    def construct(s):
        num_credits = 4
        max_delay = 4
        num_test_credits = 5
        # Configure source
        s.send_credit = TestSrcRTL(Bits1, [1, 0] * num_test_credits, 0)

        # Configure sinks
        cmp_fn = lambda a, b : a == b
        s.recv_credit = TestSinkRTL(Bits1, [1] * num_test_credits, cmp_fn = cmp_fn)
        s.recv_credit_avail = TestSinkRTL(Bits1, [1] * 6, cmp_fn = cmp_fn)

        s.dut = STEP_TokenizerRTL(num_credits,
                                    max_delay
                                    )

        # Connections
        s.dut.take_credit //= s.send_credit.send.msg
        s.send_credit.send.rdy //= 1
        s.dut.out_credit //= s.recv_credit.recv.msg
        s.dut.out_credit //= s.recv_credit.recv.val
        s.dut.credit_avail //= s.recv_credit_avail.recv.msg
        s.dut.credit_avail //= s.recv_credit_avail.recv.val

    def done(s):
        return s.send_credit.done() and s.recv_credit.done() and s.recv_credit_avail.done()

    def line_trace(s):
        return s.dut.line_trace()

def init_param():
    #-------------------------------------------------------------------------
    # Test cases
    #-------------------------------------------------------------------------

    th = TestHarness()
    return th

def test_simple(cmdline_opts):
    th = init_param()
    
    th.elaborate()
    th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                       ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                        'ALWCOMBORDER'])
    th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
    run_sim(th)  # Added max_cycles to prevent infinite simulation