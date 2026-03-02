"""
==========================================================================
RegisterBankRTL_test.py
==========================================================================
Test cases for RegisterBankRTL.

Author : Cheng Tan
  Date : Feb 7, 2025
"""

from pymtl3.passes.backends.verilog import (VerilogVerilatorImportPass)
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)

from ..STEP_BRAMRTL import STEP_BRAMRTL
from ....lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ....lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ....lib.messages import *
from ....lib.opt_type import *
from ....lib.util.common import *

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness( Component ):

    def construct(s, num_registers, DataType, AddrType,
                rd_addr_msgs, wr_addr_msgs, wr_en_msgs, wr_data_msgs, expected_rd_data_msgs):
        # Configure Sources
        s.rd_addr_pkts = TestSrcRTL(AddrType, rd_addr_msgs)
        s.wr_addr_pkts = TestSrcRTL(AddrType, wr_addr_msgs)
        s.wr_en_pkts = TestSrcRTL(b1, wr_en_msgs)
        s.wr_data_pkts = TestSrcRTL(DataType, wr_data_msgs)

        # Configure Sinks
        s.expected_rd_data_pkts = TestSinkRTL(DataType, expected_rd_data_msgs, 1)

        # Instantiate DUT
        s.dut = STEP_BRAMRTL(DataType, num_registers)
        
        # Interfaces
        s.dut.raddr //= s.rd_addr_pkts.send.msg
        s.rd_addr_pkts.send.rdy //= 1
        s.dut.waddr //= s.wr_addr_pkts.send.msg
        s.wr_addr_pkts.send.rdy //= 1
        s.dut.wen   //= s.wr_en_pkts.send.msg
        s.wr_en_pkts.send.rdy //= 1
        s.dut.wdata //= s.wr_data_pkts.send.msg
        s.wr_data_pkts.send.rdy //= 1
        s.dut.rdata //= s.expected_rd_data_pkts.recv.msg
        s.expected_rd_data_pkts.recv.val //= 1

    def done(s):
        return s.rd_addr_pkts.done() and \
                s.wr_addr_pkts.done() and \
                s.wr_en_pkts.done() and \
                s.wr_data_pkts.done() and \
                s.expected_rd_data_pkts.done()

    def line_trace(s):
        return s.dut.line_trace()

def test_simple(cmdline_opts):
    num_registers = 16
    DataType = mk_bits(16)
    AddrType = mk_bits(clog2(num_registers))

    rd_addr_msgs = [ AddrType(0), AddrType(13), AddrType(15), AddrType(2) ]
    wr_addr_msgs = [ AddrType(2), AddrType(2), AddrType(15) ]
    wr_en_msgs = [ b1(1), b1(1), b1(1), b1(0) ]
    wr_data_msgs = [ DataType(10), DataType(10), DataType(12) ]
    expected_rd_data_msgs = [ DataType(0), DataType(0), DataType(0), DataType(10) ]

    th = TestHarness(num_registers, DataType, AddrType,
            rd_addr_msgs, wr_addr_msgs, wr_en_msgs, wr_data_msgs, expected_rd_data_msgs)
    th.elaborate()
    th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                       ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                        'ALWCOMBORDER'])
    th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
    run_sim(th)

