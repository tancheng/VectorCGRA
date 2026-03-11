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

from ..STEP_ControllerRTL import STEP_ControllerRTL
from ...lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ...lib.messages import *
from ...lib.opt_type import *


#-------------------------------------------------------------------------
# TestHarness
#-------------------------------------------------------------------------

class TestHarness(Component):

    def construct(s,
                    CpuPktType,
                    from_cpu_pkt_msgs,
                    send_cpu_pkt_msgs,
                    CfgBitstreamType,
                    send_tile_cfg_pkt_msgs,
                    CfgPayloadType,
                    CfgMetadataType,
                    send_cfg_to_rf_msgs,
                    rf_cfg_done_msgs
                    ):

        # Configure sources - recv_from_cpu_pkt launches every cycle
        s.recv_from_cpu_pkt = TestSrcRTL(CpuPktType, from_cpu_pkt_msgs)
        # s.recv_from_cpu_pkt.send.rdy.v = 1  # Always ready to send every cycle
        
        s.send_rf_cfg_done = TestSrcRTL(Bits1, rf_cfg_done_msgs)

        # Configure sinks with comparison functions
        cmp_fn = lambda a, b : a == b
        s.send_to_cpu_pkt = TestSinkRTL(CpuPktType, send_cpu_pkt_msgs)
        s.send_cfg_to_tiles = TestSinkRTL(CfgBitstreamType, send_tile_cfg_pkt_msgs, cmp_fn = cmp_fn)
        s.send_cfg_to_rf = TestSinkRTL(CfgMetadataType, send_cfg_to_rf_msgs, cmp_fn = cmp_fn)

        s.dut = STEP_ControllerRTL(CpuPktType,
                                    CfgBitstreamType,
                                    CfgPayloadType,
                                    CfgMetadataType
                                    )

        # Connections
        s.dut.recv_from_cpu_pkt //= s.recv_from_cpu_pkt.send
        s.dut.send_to_cpu_pkt //= s.send_to_cpu_pkt.recv
        s.dut.send_cfg_to_tiles //= s.send_cfg_to_tiles.recv
        s.dut.send_cfg_to_rf //= s.send_cfg_to_rf.recv
        s.dut.rf_cfg_done //= s.send_rf_cfg_done.send.msg
        s.send_rf_cfg_done.send.rdy //= 1

    def done(s):
        return (s.recv_from_cpu_pkt.done() and
                s.send_to_cpu_pkt.done() and
                s.send_cfg_to_tiles.done() and
                s.send_cfg_to_rf.done() and
                s.send_rf_cfg_done.done())

    def line_trace(s):
        return s.dut.line_trace()

def init_param():
    #-------------------------------------------------------------------------
    # Test cases
    #-------------------------------------------------------------------------

    num_tiles = 4
    num_consts = 2
    num_rd_regs = 4
    num_wr_regs = 4
    iteration_threads = 2
    num_pred_registers = 16

    DataType = mk_bits(8)
    OperationType = mk_bits( clog2(NUM_OPTS) )
    RegAddrType = mk_bits(clog2(num_rd_regs))
    PredAddrType = mk_bits( clog2(num_pred_registers) )

    PredMathType = mk_pred_math_pkt(PredAddrType,
                                    DataType,
                                    OperationType
                                )

    CfgMetadataType = mk_cfg_metadata_pkt(num_tiles,
                                            num_consts,
                                            num_rd_regs,
                                            num_wr_regs,
                                            DataType,
                                            RegAddrType,
                                            PredAddrType,
                                            PredMathType,
                                        )

    # TODO: @darrenl fix this into actual config
    TileBitstreamType = mk_bits(3)

    CfgBitstreamType = mk_bitstream_pkt(num_tiles, TileBitstreamType)

    CfgPayloadType = mk_cfg_pkt(CfgBitstreamType,
                                CfgMetadataType)

    CpuPktType = mk_cpu_pkt(CfgPayloadType)

    # Metadata and bitstream pkts
    metadatas = [
        CfgMetadataType(cfg_id = 0,
                        br_id = 1,
                        thread_count_min = 0,
                        thread_count_max = iteration_threads,
                        start_cfg = 1,
                        end_cfg = 0),
        CfgMetadataType(cfg_id = 1,
                        br_id = 2,
                        thread_count_min = 0,
                        thread_count_max = iteration_threads,
                        start_cfg = 0,
                        end_cfg = 0),
        CfgMetadataType(cfg_id = 2,
                        br_id = 0,
                        thread_count_min = 0,
                        thread_count_max = iteration_threads,
                        start_cfg = 0,
                        end_cfg = 1)
    ]

    bitstreams = [
        CfgBitstreamType(bitstream = [TileBitstreamType(0) for _ in range(num_tiles)])
        for i in range(len(metadatas))
    ]

    # Multiple CPU packets to be sent every cycle
    from_cpu_pkt_msgs = [
        CpuPktType(cmd = CMD_CONFIG, cfg = CfgPayloadType(
                bitstream = bitstreams[i],
                metadata = metadatas[i])) for i in range(len(metadatas))
    ] + [
        CpuPktType(cmd = CMD_LAUNCH, cfg = CfgPayloadType(
                bitstream = CfgBitstreamType(),
                metadata = CfgMetadataType()))
    ]

    # Expected single response CPU packet at the end
    send_cpu_pkt_msgs = [
        CpuPktType(cmd = CMD_COMPLETE, cfg = CfgPayloadType(
                bitstream = CfgBitstreamType(),
                metadata = CfgMetadataType()))
    ]

    # Create rf_cfg_done signal that goes high 2 cycles after cfg packets are sent
    # We'll send it high for multiple cycles to ensure it's caught
    rf_cfg_done_msgs = [0] * len(from_cpu_pkt_msgs)
    for _ in range(len(metadatas)):
        rf_cfg_done_msgs.extend([0] * iteration_threads + [1])
    # additional padding at end to extend test
    rf_cfg_done_msgs.extend([0] * 5)

    # Single tile configuration packet expected
    send_tile_cfg_pkt_msgs = bitstreams  # Expect the last bitstream

    # Single RF configuration packet expected
    send_cfg_to_rf_msgs = metadatas

    th = TestHarness(CpuPktType,
                        from_cpu_pkt_msgs,
                        send_cpu_pkt_msgs,
                        CfgBitstreamType,
                        send_tile_cfg_pkt_msgs,
                        CfgPayloadType,
                        CfgMetadataType,
                        send_cfg_to_rf_msgs,
                        rf_cfg_done_msgs
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
