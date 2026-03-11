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
from ...lib.util.bram_translate import translate_design_with_bram
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
        wr_data_delay = 2
        ld_data_delay = wr_data_delay + 1
        ld_data_end_delay = ld_data_delay + max([len(recv_ld_data_msgs) for i in range(num_ld_ports)])
        s.recv_wr_data = [TestSrcRTL(RegDataType, recv_wr_data_msgs[i], wr_data_delay) for i in range(num_wr_ports)]
        s.recv_cfg_from_ctrl = TriggeredConfigSource(CfgMetadataType, recv_cfg_from_ctrl_msgs, False)
        s.recv_ld_data = [TestSrcRTL(RegDataType, recv_ld_data_msgs[i], ld_data_delay) for i in range(num_ld_ports)]
        s.recv_ld_data_id = [TestSrcRTL(mk_bits(clog2(MAX_THREAD_COUNT)), recv_ld_data_id_msgs[i], ld_data_delay) for i in range(num_ld_ports)]
        s.recv_ld_st_complete = TestSrcRTL(Bits1, [1], ld_data_end_delay)
        s.recv_tile_token_avail = [TestSrcRTL(Bits1, [1]) for _ in range(num_rd_ports)]
        s.recv_tile_token_shifter_out = [TestSrcRTL(Bits1, [1] * len(recv_wr_data_msgs[i]) + [0], wr_data_delay) for i in range(num_rd_ports)]

        # Configure sinks
        cmp_fn = lambda a, b : a == b
        s.send_rd_data = [TestSinkRTL(RegDataType, send_rd_data_msgs[i], ld_data_end_delay, cmp_fn = cmp_fn) for i in range(num_rd_ports)]
        s.send_cfg_done = TestSinkRTL(Bits1, send_cfg_done_msgs, cmp_fn = cmp_fn)
        s.send_tile_token_take = [TestSinkRTL(Bits1, [1]) for _ in range(num_rd_ports)]
        s.send_tile_token_return = [TestSinkRTL(Bits1, [1]) for _ in range(num_rd_ports)]

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
            s.dut.wr_data[i] //= s.recv_wr_data[i].send.msg
            s.recv_wr_data[i].send.rdy //= 1
        for i in range(num_rd_ports):
            s.dut.rd_data[i] //= s.send_rd_data[i].recv.msg
            s.send_rd_data[i].recv.val //= 1
            s.dut.tile_token_take[i] //= s.send_tile_token_take[i].recv.msg
            s.dut.tile_token_take[i] //= s.send_tile_token_take[i].recv.val
            s.dut.tile_token_return[i] //= s.send_tile_token_return[i].recv.msg
            s.dut.tile_token_return[i] //= s.send_tile_token_return[i].recv.val
            s.dut.tile_token_avail[i] //= s.recv_tile_token_avail[i].send.msg
            s.dut.tile_token_shifter_out[i] //= s.recv_tile_token_shifter_out[i].send.msg
            s.recv_tile_token_avail[i].send.rdy //= 1
            s.recv_tile_token_shifter_out[i].send.rdy //= 1
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
    num_tile_cols = 4
    num_tile_rows = 4
    num_tiles = num_tile_cols * num_tile_rows
    num_banks = 4
    num_rd_ports = num_tile_rows * 2
    num_wr_ports = num_tile_rows * 2
    num_ld_ports = num_tile_cols // 2
    num_st_ports = num_tile_cols // 2
    num_registers = 16
    num_threads = 2
    num_pred_registers = 16
    ThreadIdxType = mk_bits(clog2(MAX_THREAD_COUNT))
    num_taker_ports = num_rd_ports
    num_returner_ports = num_wr_ports + num_ld_ports + num_st_ports

    DataType = mk_bits(8)
    OperationType = mk_bits( clog2(NUM_OPTS) )
    RegAddrType = mk_bits(clog2(num_registers))
    PredAddrType = mk_bits( clog2(num_pred_registers) )

    PortRouteType = mk_bits( num_returner_ports )
    PortDelayType = mk_bits( clog2(num_tiles) )
    CfgTokenizerType = mk_cfg_tokenizer_pkt(num_taker_ports,
                                            num_returner_ports,
                                            num_tiles,
                                            PortRouteType,
                                            PortDelayType
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
                                            CfgTokenizerType,
                                        )

    # Inputs into dut
    recv_cfg_from_ctrl_msgs = [
        CfgMetadataType(cmd = CMD_CONFIG,
                        in_regs = [RegAddrType(i) for i in range(num_rd_ports)],
                        in_regs_val = [b1(0), b1(1)] * 2 + [b1(0)] * (num_rd_ports - 4),
                        out_regs = [RegAddrType(i) for i in range(num_wr_ports)],
                        out_regs_val = [b1(0)] * 3 + [b1(1)] + [b1(0)] * (num_wr_ports - 4),
                        ld_enable = [b1(0), b1(1)],
                        st_enable = [b1(0), b1(0)],
                        ld_reg_addr = [RegAddrType(0), RegAddrType(1)],
                        cfg_id = 0,
                        br_id = 1,
                        start_cfg = 1,
                        end_cfg = 0,
                        thread_count_min = 0,
                        thread_count_max = num_threads
                        ),
        CfgMetadataType(cmd = CMD_CONFIG,
                        in_regs = [RegAddrType(i) for i in range(num_rd_ports)],
                        in_regs_val = [b1(0), b1(1)] * 2 + [b1(0)] * (num_rd_ports - 4),
                        out_regs = [RegAddrType(i) for i in range(num_wr_ports)],
                        out_regs_val = [b1(0)] * num_wr_ports,
                        ld_enable = [b1(0), b1(0)],
                        st_enable = [b1(0), b1(0)],
                        cfg_id = 1,
                        br_id = 0,
                        start_cfg = 0,
                        end_cfg = 1,
                        thread_count_min = 0,
                        thread_count_max = num_threads
                        )
    ]

    # From Fabric to RF Controller
    recv_wr_data = [
        # Row 0
        [], [],
        # Row 1
        [], [RegDataType(1), RegDataType(2)],
        # Row 2
        [], [],
        # Row 3
        [], [],
    ]

    # Outputs of dut
    send_rd_data = [
        # Row 0
        [], [RegDataType(0), RegDataType(0), RegDataType(0), RegDataType(5),RegDataType(7)], 
        # Row 1
        [], [RegDataType(0), RegDataType(0), RegDataType(0), RegDataType(1), RegDataType(2)],
        # Row 2
        [], [],
        # Row 3
        [], [],
    ]

    recv_ld_data = [
        [],
        [RegDataType(5), RegDataType(7)],
    ]

    recv_ld_data_id = [
        [],
        [ThreadIdxType(i) for i in range(num_threads)],
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
    # translate_design_with_bram(th.dut, add_bram_attrs=True)
    th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                       ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                        'ALWCOMBORDER'])
    th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
    run_sim(th)  # Added max_cycles to prevent infinite simulation
