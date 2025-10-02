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
        num_tokens = 4
        max_delay = 16
        num_test_tokens = 5
        # Configure source
        s.send_token_take = TestSrcRTL(Bits1, [1, 0] * num_test_tokens, 0)
        s.token_return = TestSrcRTL(Bits1, [1] + [0] * 7 + [1, 0], 2)
        s.token_delay = TestSrcRTL(mk_bits(clog2(max_delay)), [2], 0)

        # Configure sinks
        cmp_fn = lambda a, b : a == b
        s.recv_token = TestSinkRTL(Bits1, [1] * num_test_tokens, cmp_fn = cmp_fn)
        s.recv_token_avail = TestSinkRTL(Bits1, [], cmp_fn = cmp_fn)

        s.dut = STEP_TokenizerRTL(num_tokens,
                                    max_delay
                                    )

        # Connections
        s.dut.token_take //= s.send_token_take.send.msg
        s.send_token_take.send.rdy //= 1
        s.dut.token_return //= s.token_return.send.msg
        s.token_return.send.rdy //= 1
        s.dut.token_shifter_out //= s.recv_token.recv.msg
        s.dut.token_shifter_out //= s.recv_token.recv.val
        s.dut.token_avail //= s.recv_token_avail.recv.msg
        s.dut.token_avail //= s.recv_token_avail.recv.val
        s.dut.token_delay //= s.token_delay.send.msg
        s.token_delay.send.rdy //= 1

    def done(s):
        return s.send_token_take.done() and s.recv_token.done() and s.recv_token_avail.done()

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