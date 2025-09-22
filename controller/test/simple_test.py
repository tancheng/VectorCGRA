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

from ..STEP_RegisterFileControllerRTL import STEP_RegisterFileControllerRTL
from ...lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ...lib.basic.TimedWriteSource import TimedWriteSource
from ...lib.basic.TriggeredConfigSource import TriggeredConfigSource
from ...lib.messages import *
from ...lib.opt_type import *


#-------------------------------------------------------------------------
# TestHarness
#-------------------------------------------------------------------------

class TestHarness(Component):

    def construct(s,
                    RegDataType,
                    RegAddrType,
                    CfgMetadataType,
                    num_banks,
                    num_rd_ports,
                    num_wr_ports,
                    num_registers,
                    ):
        
        # Configure sources
        s.input = TestSrcRTL(Bits1, [0] * 20)

        s.dut = STEP_RegisterFileControllerRTL(RegDataType,
                                                RegAddrType,
                                                CfgMetadataType,
                                                num_banks,
                                                num_rd_ports,
                                                num_wr_ports,
                                                num_registers
                                                )

        s.dut.input //= s.input.send

    def done(s):
        return s.input.done()

    def line_trace(s):
        return s.dut.line_trace()

def init_param():
    #-------------------------------------------------------------------------
    # Test cases
    #-------------------------------------------------------------------------

    RegDataType = mk_bits(8)
    num_consts = 1
    num_banks = 4
    num_rd_ports = 4
    num_wr_ports = 4
    num_registers = 16
    thread_count = 2
    ThreadCountType = mk_bits(clog2(MAX_THREAD_COUNT))
    thread_count_val = ThreadCountType(thread_count)

    ConstDataType = mk_bits(8)
    RegAddrType = mk_bits(clog2(num_registers))
    

    CfgMetadataType = mk_cfg_metadata_pkt(num_consts,
                                            num_rd_ports,
                                            num_wr_ports,
                                            ConstDataType,
                                            RegAddrType)


    th = TestHarness(RegDataType,
                        RegAddrType,
                        CfgMetadataType,
                        num_banks,
                        num_rd_ports,
                        num_wr_ports,
                        num_registers,
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