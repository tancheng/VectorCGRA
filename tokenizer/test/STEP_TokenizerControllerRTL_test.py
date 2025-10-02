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

from ..STEP_TokenizerControllerRTL import STEP_TokenizerControllerRTL
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
        num_test_tokens = 5
        num_rd_ports = num_wr_ports = 4
        num_ld_ports = num_st_ports = 2
        max_delay = num_rd_ports * num_rd_ports
        num_returner_ports = num_wr_ports + num_ld_ports + num_st_ports
        num_taker_ports = num_rd_ports
        s.num_taker_ports = num_taker_ports
        s.num_rd_ports = num_rd_ports
        s.num_returner_ports = num_returner_ports

        PortRouteType = mk_bits( num_wr_ports + num_ld_ports + num_st_ports )
        PortDelayType = mk_bits( clog2(max_delay) )
        TokenizerCfgType = mk_cfg_tokenizer_pkt(num_taker_ports,
                                                num_returner_ports,
                                                max_delay,
                                                PortRouteType,
                                                PortDelayType
                                                )
        test_fabric_delay = 1
        test_token_return_delay = 4
        
        tokenizer_cfg_msgs = [
            TokenizerCfgType(token_route_sink_enable=[PortRouteType(0b00000101) if i == 0 else PortRouteType(0) for i in range(num_rd_ports)],
                            token_route_delay_to_sink=[PortDelayType(test_fabric_delay) for i in range(num_returner_ports)]
                            )
        ]

        # Configure source
        s.send_token_take = [TestSrcRTL(Bits1, [1, 0] * num_test_tokens, 1) if i == 0 else TestSrcRTL(Bits1, []) for i in range(num_taker_ports)]
        s.token_return = [TestSrcRTL(Bits1, [1] + [0] * 7 + [1, 0], test_token_return_delay) if i in [5,7] else TestSrcRTL(Bits1, []) for i in range(num_returner_ports)]
        s.cc_cfg_to_tokenizer = TestSrcRTL(TokenizerCfgType, tokenizer_cfg_msgs)

        # Configure sinks
        cmp_fn = lambda a, b : a == b
        s.recv_token_shifter_out = [TestSinkRTL(Bits1, [1] * num_test_tokens, cmp_fn = cmp_fn) if i in [5,7] else TestSinkRTL(Bits1, []) for i in range(num_returner_ports)]
        s.recv_token_avail = [TestSinkRTL(Bits1, [1] * 6, cmp_fn = cmp_fn) if i == 0 else TestSinkRTL(Bits1, []) for i in range(num_taker_ports)]

        s.dut = STEP_TokenizerControllerRTL(TokenizerCfgType,
                                            num_rd_ports,
                                            num_wr_ports,
                                            num_ld_ports,
                                            num_st_ports,
                                            num_tokens,
                                            max_delay
                                            )

        # Connections
        s.dut.recv_cfg_from_ctrl //= s.cc_cfg_to_tokenizer.send
        for i in range(num_taker_ports):
            s.dut.token_take[i] //= s.send_token_take[i].send.msg
            s.send_token_take[i].send.rdy //= 1
            s.dut.token_avail[i] //= s.recv_token_avail[i].recv.msg
            s.dut.token_avail[i] //= s.recv_token_avail[i].recv.val
        for i in range(num_returner_ports):
            s.dut.token_shifter_out[i] //= s.recv_token_shifter_out[i].recv.msg
            s.dut.token_shifter_out[i] //= s.recv_token_shifter_out[i].recv.val
            s.dut.token_return[i] //= s.token_return[i].send.msg
            s.token_return[i].send.rdy //= 1


    def done(s):
        for i in range(s.num_taker_ports):
            if not s.send_token_take[i].done():
                return False
            if not s.recv_token_avail[i].done():
                return False
        for i in range(s.num_returner_ports):
            if not s.token_return[i].done():
                return False
            if not s.recv_token_shifter_out[i].done():
                return False
        return True

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