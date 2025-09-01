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
                    send_cfg_to_rf_msgs
                    ):

        send_rf_cfg_done = [1 for _ in range(len(send_cfg_to_rf_msgs))]

        s.recv_from_cpu_pkt = TestSrcRTL(CpuPktType, from_cpu_pkt_msgs)
        s.send_rf_cfg_done = TestSrcRTL(Bits1, send_rf_cfg_done)

        cmp_fn = lambda a, b : a.payload == b.payload
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


    def done(s):
        return (s.send_to_cpu_pkt.done() and
           s.send_cfg_to_tiles.done() and
           s.send_cfg_to_rf.done())

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

    ConstDataType = mk_bits(8)
    RegAddrType = mk_bits(clog2(num_rd_regs))

    CfgMetadataType = mk_cfg_metadata_pkt(num_consts,
                                            num_rd_regs,
                                            num_wr_regs,
                                            ConstDataType,
                                            RegAddrType)

    # TODO: @darrenl fix this into actual config
    TileBitstreamType = mk_bits(3)

    CfgBitstreamType = mk_bitstream_pkt(num_tiles, TileBitstreamType)

    CfgPayloadType = mk_cfg_pkt(CfgBitstreamType,
                                CfgMetadataType)

    CpuPktType = mk_cpu_pkt(CfgPayloadType)

    bitstreams = [
        CfgBitstreamType(bitstream = [TileBitstreamType(0) for _ in range(num_tiles)])
    ]

    metadatas = [
        CfgMetadataType(const_vals = 0,
                        cfg_id = 0,
                        br_id = 1,
                        thread_count = 12,
                        start_cfg = 1,
                        end_cfg = 0)
    ]

    # Default to tiles doing 0.
    from_cpu_pkt_msgs = [
        CpuPktType(cmd = CMD_CONFIG, cfg = CfgPayloadType(
                bitstream = bitstreams[0],
                metadata = metadatas[0]))
    ]

    send_cpu_pkt_msgs = [
        CpuPktType(cmd = CMD_COMPLETE, cfg = CfgPayloadType(
                bitstream = CfgBitstreamType(),
                metadata = CfgMetadataType()))
    ]

    send_tile_cfg_pkt_msgs = bitstreams

    send_cfg_to_rf_msgs = [
        CfgMetadataType(const_vals = 0,
                        in_regs = [0 for _ in range(num_rd_regs)],
                        in_regs_val = [0 for _ in range(num_rd_regs)],
                        cfg_id = 0,
                        br_id = 1,
                        thread_count = 12,
                        start_cfg = 1,
                        end_cfg = 0)
    ]

    th = TestHarness(CpuPktType,
                        from_cpu_pkt_msgs,
                        send_cpu_pkt_msgs,
                        CfgBitstreamType,
                        send_tile_cfg_pkt_msgs,
                        CfgPayloadType,
                        CfgMetadataType,
                        send_cfg_to_rf_msgs)
    return th

def test_simple(cmdline_opts):
    th = init_param()
    
    th.elaborate()
    th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                       ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                        'ALWCOMBORDER'])
    th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
    run_sim(th)

