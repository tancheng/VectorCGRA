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
                    num_tiles,
                    RegDataType,
                    RegAddrType,
                    PredAddrType,
                    CfgMetadataType,
                    num_ld_ports,
                    num_st_ports,
                    num_banks,
                    num_rd_ports,
                    num_wr_ports,
                    num_registers,
                    recv_wr_data_msgs,
                    recv_cfg_from_ctrl_msgs,
                    send_rd_data_msgs,
                    recv_ld_data_msgs,
                    recv_ld_data_id_msgs,
                    send_cfg_done_msgs
                    ):
        # Configure sources
        s.recv_wr_data = [TestSrcRTL(RegDataType, recv_wr_data_msgs[i], 4) for i in range(num_wr_ports)]
        s.recv_cfg_from_ctrl = TriggeredConfigSource(CfgMetadataType, recv_cfg_from_ctrl_msgs)
        s.recv_ld_data = [TestSrcRTL(RegDataType, recv_ld_data_msgs[i], 10) for i in range(num_ld_ports)]
        s.recv_ld_data_id = [TestSrcRTL(mk_bits(clog2(MAX_THREAD_COUNT)), recv_ld_data_id_msgs[i], 10) for i in range(num_ld_ports)]
        s.recv_ld_st_complete = TestSrcRTL(Bits1, [1], 12)

        # Configure sinks
        cmp_fn = lambda a, b : a == b
        s.send_rd_data = [TestSinkRTL(RegDataType, send_rd_data_msgs[i], cmp_fn = cmp_fn) for i in range(num_rd_ports)]
        s.send_cfg_done = TestSinkRTL(Bits1, send_cfg_done_msgs, cmp_fn = cmp_fn)

        s.dut = STEP_RegisterFileControllerRTL(num_tiles,
                                                RegDataType,
                                                RegAddrType,
                                                PredAddrType,
                                                CfgMetadataType,
                                                num_ld_ports,
                                                num_st_ports,
                                                num_banks,
                                                num_rd_ports,
                                                num_wr_ports,
                                                num_registers,
                                                num_registers,
                                            )
        
        s.num_wr_ports = num_wr_ports
        s.num_rd_ports = num_rd_ports

        # Connections
        for i in range(num_wr_ports):
            s.dut.wr_data[i] //= s.recv_wr_data[i].send
        for i in range(num_rd_ports):
            s.dut.rd_data[i] //= s.send_rd_data[i].recv
        for i in range(num_ld_ports):
            s.dut.ld_data[i] //= s.recv_ld_data[i].send.msg
            s.dut.ld_data_valid[i] //= s.recv_ld_data[i].send.val
            s.recv_ld_data[i].send.rdy //= 1
            s.dut.ld_data_id[i] //= s.recv_ld_data_id[i].send.msg
            s.recv_ld_data_id[i].send.rdy //= 1

        s.dut.ld_st_complete //= s.recv_ld_st_complete.send.msg
        s.recv_ld_st_complete.send.rdy //= 1
        s.dut.recv_cfg_from_ctrl //= s.recv_cfg_from_ctrl.send
        s.dut.cfg_done //= s.send_cfg_done.recv.msg
        s.dut.cfg_done //= s.send_cfg_done.recv.val

        # Logic to trigger next config message when cfg_done is received
        s.recv_cfg_from_ctrl.cfg_done_received //= s.dut.cfg_done

    def done(s):
        for i in range(s.num_wr_ports):
            if not s.recv_wr_data[i].done():
                return False
        for i in range(s.num_rd_ports):
            if not s.send_rd_data[i].done():
                return False
        return s.recv_cfg_from_ctrl.done() & s.send_cfg_done.done()

    def line_trace(s):
        return s.dut.line_trace()

def init_param():
    #-------------------------------------------------------------------------
    # Test cases
    #-------------------------------------------------------------------------

    RegDataType = mk_bits(8)
    num_consts = 1
    num_tiles = 4
    num_banks = 4
    num_rd_ports = 4
    num_wr_ports = 4
    num_ld_ports = 2
    num_st_ports = 2
    num_registers = 16
    thread_count = 2
    num_pred_registers = 16
    ThreadCountType = mk_bits(clog2(MAX_THREAD_COUNT))

    DataType = mk_bits(8)
    OperationType = mk_bits( clog2(NUM_OPTS) )
    RegAddrType = mk_bits(clog2(num_registers))
    PredAddrType = mk_bits( clog2(num_pred_registers) )

    PredMathType = mk_pred_math_pkt(PredAddrType,
                                    DataType,
                                    OperationType
                                )
    

    CfgMetadataType = mk_cfg_metadata_pkt(num_tiles,
                                            num_consts,
                                            num_rd_ports,
                                            num_wr_ports,
                                            num_ld_ports,
                                            num_st_ports,
                                            DataType,
                                            RegAddrType,
                                            PredAddrType,
                                            PredMathType,
                                        )

    # Inputs into dut
    recv_cfg_from_ctrl_msgs = [
        CfgMetadataType(in_regs = [RegAddrType(i) for i in range(num_rd_ports)],
                        in_regs_val = [b1(1), b1(1), b1(0), b1(0)],
                        out_regs = [RegAddrType(i) for i in range(num_wr_ports)],
                        out_regs_val = [b1(0), b1(1), b1(0), b1(0)],
                        ld_enable = [b1(0), b1(1)],
                        st_enable = [b1(1), b1(0)],
                        ld_reg_addr = [RegAddrType(2), RegAddrType(0)],
                        cfg_id = 0,
                        br_id = 1,
                        start_cfg = 1,
                        end_cfg = 0,
                        thread_count = thread_count
                        ),
        CfgMetadataType(in_regs = [RegAddrType(i) for i in range(num_rd_ports)],
                        in_regs_val = [b1(1), b1(1), b1(0), b1(0)],
                        out_regs = [RegAddrType(i) for i in range(num_wr_ports)],
                        out_regs_val = [b1(0), b1(0), b1(0), b1(0)],
                        ld_enable = [b1(0), b1(0)],
                        st_enable = [b1(0), b1(0)],
                        cfg_id = 1,
                        br_id = 0,
                        start_cfg = 0,
                        end_cfg = 1,
                        thread_count = thread_count
                        ),
    ]

    recv_wr_data = [
        # Write data for reg addr 0
        [], 
        # Write data for reg addr 1
        [RegDataType(1), RegDataType(1)],
        # Write data for reg addr 2
        [],
        # Write data for reg addr 3
        []
    ]

    # Outputs of dut
    send_rd_data = [
        # Read data for reg addr 0
        [RegDataType(0),RegDataType(0), RegDataType(5),RegDataType(7)], 
        # Read data for reg addr 1
        [RegDataType(0),RegDataType(0), RegDataType(1), RegDataType(1)],
        # Read data for reg addr 2
        [],
        # Read data for reg addr 3
        []
    ]

    recv_ld_data = [
        [],
        [RegDataType(5), RegDataType(7)],
    ]

    recv_ld_data_id = [
        [],
        [ThreadCountType(0), ThreadCountType(1)],
    ]

    send_cfg_done = [1] * len(recv_cfg_from_ctrl_msgs)

    th = TestHarness(num_tiles,
                        RegDataType,
                        RegAddrType,
                        PredAddrType,
                        CfgMetadataType,
                        num_ld_ports,
                        num_st_ports,
                        num_banks,
                        num_rd_ports,
                        num_wr_ports,
                        num_registers,
                        recv_wr_data,
                        recv_cfg_from_ctrl_msgs,
                        send_rd_data,
                        recv_ld_data,
                        recv_ld_data_id,
                        send_cfg_done
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