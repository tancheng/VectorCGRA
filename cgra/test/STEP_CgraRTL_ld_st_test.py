from pymtl3.passes.backends.verilog import (VerilogVerilatorImportPass)
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)

from ..STEP_CgraRTL import STEP_CgraRTL
from ..CgraTrackedPktChunked import CgraTrackedPktChunked
from ...lib.basic.AxiSourceRTL import AxiLdSourceRTL, AxiLdSourceTriggeredRTL, AxiStSourceRTL, AxiStSourceTriggeredRTL
from ...lib.basic.SourceTriggeredRTL import SourceTriggeredRTL
from ...lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ...lib.messages import *
from ...lib.opt_type import *


#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------
# Global Parameters. Fixed for now TODO @darrenl
num_tile_inports = 8
num_tile_outports = 8
num_fu_inports = 3
num_fu_outports = 1
num_register_banks = 2
num_registers = 16
num_pred_registers = 16

class TestHarness(Component):
    def construct(s,
            # Top Level Pkt Types
            CfgMetadataType,
            CfgBitstreamType,

            # Configuration Types
            CfgTokenizerType,
            TileBitstreamType,
            OperationType,
            DataType,
            RegAddrType,
            PredAddrType,

            # CGRA Parameters
            num_tile_cols,
            num_tile_rows,
            num_ld_ports,
            num_st_ports,
            
            #  Messages
            cpu_to_cgra_bitstream_msgs,
            cpu_to_cgra_metadata_msgs
            ):
        # Configure for done comparison
        s.num_ld_ports = num_ld_ports
        s.num_st_ports = num_st_ports
        s.num_tiles = num_tile_cols * num_tile_rows

        # Configure Sources
        ld_axi_msgs = [[] for _ in range(num_ld_ports - 1)] + [[5,5,5,5]]
        st_counts = [0, 1]
        s.cpu_to_cgra_metadata_pkts = TestSrcRTL(CfgMetadataType, cpu_to_cgra_metadata_msgs)
        s.cpu_to_cgra_bitstream_pkts = SourceTriggeredRTL(TileBitstreamType, cpu_to_cgra_bitstream_msgs, chunk_size=s.num_tiles, delay=1)
        s.ld_axi_pkts = [AxiLdSourceTriggeredRTL(DataType, ld_axi_msgs[i]) for i in range(num_ld_ports)]
        s.st_axi_pkts = [AxiStSourceTriggeredRTL(DataType, st_counts[i]) for i in range(num_st_ports)]

        # Configure Sinks
        cmp_fn = lambda a, b : a == b
        s.cgra_to_cpu_signal = TestSinkRTL(Bits1, [1])

        s.dut = STEP_CgraRTL(
            CfgMetadataType,
            CfgBitstreamType,
            CfgTokenizerType,
            TileBitstreamType,
            OperationType,
            DataType,
            RegAddrType,
            PredAddrType,
            num_tile_cols,
            num_tile_rows,
            num_register_banks,
            num_registers,
            num_pred_registers,
            debug = True
        )

        # Axi Interfaces
        for i in range(num_ld_ports):
            s.dut.ld_axi[i] //= s.ld_axi_pkts[i].send
        for i in range(num_st_ports):
            s.dut.st_axi[i] //= s.st_axi_pkts[i].send

        # CPU Interfaces
        s.dut.recv_from_cpu_metadata_pkt //= s.cpu_to_cgra_metadata_pkts.send
        s.dut.send_to_cpu_done //= s.cgra_to_cpu_signal.recv.msg
        s.dut.send_to_cpu_done //= s.cgra_to_cpu_signal.recv.val
        s.dut.recv_from_cpu_bitstream_pkt //= s.cpu_to_cgra_bitstream_pkts.send
        s.dut.pc_req_trigger //= s.cpu_to_cgra_bitstream_pkts.trigger_in

    def done(s):
        for i in range(s.num_ld_ports):
            if not s.ld_axi_pkts[i].done():
                return False
        for i in range(s.num_st_ports):
            if not s.st_axi_pkts[i].done():
                return False
        return s.cpu_to_cgra_bitstream_pkts.done() and s.cpu_to_cgra_metadata_pkts.done() and s.cgra_to_cpu_signal.done()

    def line_trace(s):
        return s.dut.line_trace()

def init_param():
    #-------------------------------------------------------------------------
    # Test cases
    #-------------------------------------------------------------------------
    # Parameterizable
    num_tile_cols = 4
    num_tile_rows = 4
    assert(num_tile_cols % 2 == 0) # Ensure even number of columns for LD/ST ports
    num_tiles = num_tile_cols * num_tile_rows
    num_rd_ports = num_tile_rows * 2 * 2
    num_wr_ports = num_tile_rows * 2
    num_ld_ports = num_tile_cols // 2
    num_st_ports = num_tile_cols // 2
    num_consts = 4
    thread_count = 2
    num_taker_ports = num_rd_ports
    num_returner_ports = num_wr_ports + num_ld_ports + num_st_ports

    DataType = mk_bits(8)
    TileIdType = mk_bits( clog2(num_tiles) )
    OperationType = mk_bits( clog2(NUM_OPTS) )
    TilePortType = mk_bits( clog2(num_tile_inports + 1) ) # +1 for no connection
    TileOutType = mk_bits( num_tile_outports )
    RegAddrType = mk_bits( clog2(num_registers) )
    PredAddrType = mk_bits( clog2(num_pred_registers) )
    ShiftAmountType = mk_bits( clog2(SHIFT_REGISTER_SIZE) )

    PortRouteType = mk_bits( num_returner_ports )
    PortDelayType = mk_bits( clog2(num_tiles) )
    CfgTokenizerType = mk_cfg_tokenizer_pkt(num_taker_ports,
                                            num_returner_ports,
                                            num_tiles,
                                            PortRouteType,
                                            PortDelayType
                                            )
    
    TileBitstreamType = mk_tile_bitstream_pkt(num_tile_inports,
                                                num_tile_outports,
                                                num_fu_inports,
                                                num_fu_outports,
                                                TileIdType,
                                                OperationType,
                                                DataType,
                                                RegAddrType,
                                                PredAddrType,
                                            )
    
    CfgBitstreamType = mk_bitstream_pkt(num_tiles, TileBitstreamType)

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

    # Setup a row of PEs to do No op
    def genNoOpFromOffset(offset, length):
        return [TileBitstreamType(
            tile_id = TileIdType(offset + i),
            opt_type = OPT_NAH) for i in range(length)]

    load_row = [TileBitstreamType(
            tile_id = TileIdType(i),
            tile_in_route = [TilePortType(PORT_WEST + 1), TilePortType(0), TilePortType(0)],
            tile_out_route = TileOutType(0b00010000),
            tile_pred_route= TileOutType(0b00010000),
            const_val = DataType(0x1),
            opt_type = OPT_ADD_CONST) for i in range(num_tile_cols - 2)] \
            + \
            [TileBitstreamType(
            tile_id = TileIdType(num_tile_cols-2),
            tile_in_route = [TilePortType(PORT_WEST + 1), TilePortType(0), TilePortType(0)],
            tile_out_route = TileOutType(0b10000000),
            tile_pred_route= TileOutType(0b10000000),
            const_val = DataType(0x10),
            opt_type = OPT_ADD_CONST)] \
            + \
            [TileBitstreamType(tile_id = TileIdType(num_tile_cols-1), opt_type = OPT_NAH)]

    mul_row = [TileBitstreamType(
            tile_id = TileIdType(i + num_tile_cols*2),
            tile_in_route = [TilePortType(PORT_WEST + 1), TilePortType(0), TilePortType(0)],
            tile_out_route = TileOutType(0b00010000),
            tile_pred_route= TileOutType(0b00010000),
            const_val = DataType(0),
            opt_type = OPT_ADD_CONST) for i in range(num_tile_cols - 1)] \
            + \
            [TileBitstreamType(
            tile_id = TileIdType(num_tile_cols*3-1),
            tile_in_route = [TilePortType(PORT_WEST + 1), TilePortType(0), TilePortType(0)],
            tile_out_shift_amounts = [ShiftAmountType(0)] * 3 + [ShiftAmountType(1)] + [ShiftAmountType(0)] * (num_tile_outports - 4),
            tile_out_route = TileOutType(0b01010000),
            tile_pred_route= TileOutType(0b01010000),
            const_val = DataType(3),
            opt_type = OPT_MUL_CONST)]

    # TODO: @darrenl OPT_PAS still needs some type of trigger and can't be valid for all clock cycles
    # Above comment is changed and handled the tokenizer
    store_row = [TileBitstreamType(
            tile_id = TileIdType(num_tile_cols*3+i),
            opt_type = OPT_NAH) for i in range(num_tile_cols - 2)] \
            + \
            [TileBitstreamType(
            tile_id = TileIdType(num_tile_cols*3+num_tile_cols-2),
            tile_in_route = [TilePortType(0), TilePortType(0), TilePortType(0)],
            tile_out_route = TileOutType(0b01000000),
            tile_pred_route= TileOutType(0b01000000),
            const_val = DataType(0x10),
            opt_type = OPT_PAS)] \
            + \
            [TileBitstreamType(
            tile_id = TileIdType(num_tile_cols*3+num_tile_cols-1),
            tile_in_route = [TilePortType(PORT_NORTH + 1), TilePortType(PORT_NORTH + 1), TilePortType(0)],
            tile_out_route = TileOutType(0b01010000),
            tile_pred_route= TileOutType(0b01010000),
            opt_type = OPT_ADD)]

    ### Full Bitstream Pkt ###
    bitstreams = [
        load_row + genNoOpFromOffset(num_tile_cols, num_tile_cols * (num_tile_rows - 1)),
        genNoOpFromOffset(0, num_tile_cols * (num_tile_rows - 2)) + mul_row + store_row,
        load_row + genNoOpFromOffset(num_tile_cols, num_tile_cols * (num_tile_rows - 1)),
    ]

    # Funnel individual tile pkts
    cpu_to_cgra_bitstream_msgs = []
    for bitstream in bitstreams:
        cpu_to_cgra_bitstream_msgs += list(reversed(bitstream))

    ### Tokenizer Cfg Pkt ###
    cfg_tokenizer_pkt = [
        CfgTokenizerType(token_route_sink_enable=
            [PortRouteType(0b0100) if i == 0 else PortRouteType(0) for i in range(num_rd_ports)],
            token_route_delay_to_sink=[PortDelayType(0) for _ in range(num_wr_ports)] \
                + \
                [PortDelayType(0), PortDelayType(num_tile_cols - 1)]
                + \
                [PortDelayType(0) for _ in range(num_st_ports)]
        ),
        CfgTokenizerType(token_route_sink_enable=[
                # Row 0
                PortRouteType(0),
                PortRouteType(0),
                PortRouteType(0),
                PortRouteType(0),
                # Row 1
                PortRouteType(0),
                PortRouteType(0),
                PortRouteType(0),
                PortRouteType(0),
                # Row 2
                PortRouteType(0b1010001),
                PortRouteType(0),
                PortRouteType(0),
                PortRouteType(0),
                # Row 3
                PortRouteType(0),
                PortRouteType(0),
                PortRouteType(0),
                PortRouteType(0),
            ],
            token_route_delay_to_sink=[PortDelayType(0) for _ in range(num_wr_ports - 3)] \
                + \
                [PortDelayType(num_tile_cols + 1), PortDelayType(0), PortDelayType(num_tile_cols + 1)]
                + \
                [PortDelayType(0) for _ in range(num_ld_ports)]
                + \
                [PortDelayType(0), PortDelayType(num_tile_cols + 2)]
        ),
        CfgTokenizerType(token_route_sink_enable=
            [PortRouteType(0b0100) if i == 0 else PortRouteType(0) for i in range(num_rd_ports)],
            token_route_delay_to_sink=[PortDelayType(0) for _ in range(num_wr_ports)] \
                + \
                [PortDelayType(0), PortDelayType(num_tile_cols - 2)]
                + \
                [PortDelayType(0) for _ in range(num_st_ports)]
        ),
    ]

    ### Inputs into dut ###
    cpu_to_cgra_metadata_msgs = [
        CfgMetadataType(
                        cmd = CMD_CONFIG,
                        pred_tile_valid = [b1(1) for _ in range(num_tiles)],
                        in_regs = [RegAddrType(0) for _ in range(num_rd_ports)],
                        in_regs_val = [b1(1)] + [b1(0) for _ in range(num_rd_ports - 1)],
                        in_tid_enable = [b1(1)] + [b1(0) for _ in range(num_rd_ports - 1)],
                        out_regs = [RegAddrType(0) for _ in range(num_wr_ports)],
                        out_regs_val = [b1(0) for _ in range(num_wr_ports)],
                        ld_enable = [b1(0) for _ in range(num_ld_ports - 1)] + [b1(1)],
                        ld_reg_addr = [RegAddrType(0) for _ in range(num_ld_ports)],
                        tokenizer_cfg = cfg_tokenizer_pkt[0],
                        cfg_id = 0,
                        br_id = 1,
                        thread_count = thread_count,
                        start_cfg = 1,
                        end_cfg = 0,
                    ),
        CfgMetadataType(
                        cmd = CMD_CONFIG,
                        pred_tile_valid = [b1(1) for _ in range(num_tiles)],
                        in_regs = [RegAddrType(0) for _ in range(num_rd_ports)],
                        in_regs_val = [b1(0) for _ in range(num_rd_ports - 8)] + [b1(1), b1(0)] + [b1(0), b1(0)] * 3,
                        out_regs = [RegAddrType(i) for i in range(num_wr_ports)],
                        out_regs_val = [b1(0) for _ in range(num_wr_ports - 4)] + [b1(0), b1(1), b1(0), b1(1)],
                        st_enable = [b1(0) for _ in range(num_st_ports - 1)] + [b1(1)],
                        tokenizer_cfg = cfg_tokenizer_pkt[1],
                        cfg_id = 1,
                        br_id = 2,
                        thread_count = thread_count,
                        start_cfg = 0,
                        end_cfg = 0,
                    ),
        CfgMetadataType(
                        cmd = CMD_CONFIG,
                        pred_tile_valid = [b1(1) for _ in range(num_tiles)],
                        in_regs = [RegAddrType(0) for _ in range(num_rd_ports)],
                        in_regs_val = [b1(1)] + [b1(0) for _ in range(num_rd_ports - 1)],
                        out_regs = [RegAddrType(0) for _ in range(num_wr_ports)],
                        out_regs_val = [b1(0) for _ in range(num_wr_ports)],
                        ld_enable = [b1(0) for _ in range(num_ld_ports - 1)] + [b1(1)],
                        ld_reg_addr = [RegAddrType(0) for _ in range(num_ld_ports)],
                        tokenizer_cfg = cfg_tokenizer_pkt[2],
                        cfg_id = 2,
                        br_id = 0,
                        thread_count = thread_count,
                        start_cfg = 0,
                        end_cfg = 1,
                    ),
        CfgMetadataType(cmd = CMD_LAUNCH),
    ]

    th = TestHarness(
                        # Top Level Pkt Types
                        CfgMetadataType,
                        CfgBitstreamType,

                        # Configuration Types
                        CfgTokenizerType,
                        TileBitstreamType,
                        OperationType,
                        DataType,
                        RegAddrType,
                        PredAddrType,

                        # CGRA Parameters
                        num_tile_cols,
                        num_tile_rows,
                        num_ld_ports,
                        num_st_ports,
                        
                        #  Messages
                        cpu_to_cgra_bitstream_msgs,
                        cpu_to_cgra_metadata_msgs
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