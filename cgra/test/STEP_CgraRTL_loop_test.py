from pymtl3.passes.backends.verilog import (VerilogVerilatorImportPass)
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)
from pymtl3 import DefaultPassGroup

from ..STEP_CgraRTL import STEP_CgraRTL
from ..CgraTrackedPktChunked import CgraTrackedPktChunked
from ...lib.basic.AxiSourceRTL import AxiLdSourceRTL, AxiLdSourceTriggeredRTL, AxiStSourceRTL, AxiStSourceTriggeredMatchRTL
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
thread_count = 20

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
        ld_axi_msgs = [[] for _ in range(num_ld_ports)]
        st_axi_msgs = [[], [1]*thread_count + [2] * thread_count + [3] * thread_count + [5]*thread_count]
        s.cpu_to_cgra_metadata_pkts = TestSrcRTL(CfgMetadataType, cpu_to_cgra_metadata_msgs)
        s.cpu_to_cgra_bitstream_pkts = SourceTriggeredRTL(
            TileBitstreamType, cpu_to_cgra_bitstream_msgs, s.num_tiles, delay=1
        )
        s.ld_axi_pkts = [AxiLdSourceTriggeredRTL(DataType, ld_axi_msgs[i]) for i in range(num_ld_ports)]
        s.st_axi_pkts = [AxiStSourceTriggeredMatchRTL(DataType, st_axi_msgs[i]) for i in range(num_st_ports)]

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
        s.dut.pc_req_trigger_count //= s.cpu_to_cgra_bitstream_pkts.trigger_count
        s.dut.pc_req_trigger_complete //= s.cpu_to_cgra_bitstream_pkts.trigger_complete

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
    num_taker_ports = num_rd_ports
    num_returner_ports = num_wr_ports + num_ld_ports + num_st_ports

    DataType = mk_bits(8)
    TileIdType = mk_bits( clog2(num_tiles) )
    TileCountType = mk_bits( clog2(num_tiles + 1) )
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

    ROUTE_WEST  = TileOutType(0b00100000)
    ROUTE_EAST  = TileOutType(0b00010000)
    ROUTE_SOUTH = TileOutType(0b01000000)

    cfg_a_row = [TileBitstreamType(
            tile_id = TileIdType(0),
            tile_in_route = [TilePortType(PORT_WEST + 1), TilePortType(0), TilePortType(0)],
            tile_out_route = ROUTE_WEST,
            tile_pred_route= ROUTE_WEST,
            const_val = DataType(0x3),
            pred_gen = b1(1),
            opt_type = OPT_EQ_CONST)] \
            + \
            [TileBitstreamType(
            tile_id = TileIdType(num_tile_cols - 1),
            tile_in_route = [TilePortType(PORT_EAST + 1), TilePortType(0), TilePortType(0)],
            tile_out_route = ROUTE_EAST,
            tile_pred_route= ROUTE_EAST,
            const_val = DataType(1),
            opt_type = OPT_ADD_CONST)]

    cfg_b_row = [TileBitstreamType(
            tile_id = TileIdType(12),
            tile_in_route = [TilePortType(PORT_WEST + 1), TilePortType(0), TilePortType(0)],
            tile_out_route = ROUTE_SOUTH,
            tile_pred_route= ROUTE_SOUTH,
            const_val = DataType(0x0),
            opt_type = OPT_ADD_CONST)]

    cfg_c_row = [TileBitstreamType(
            tile_id = TileIdType(12),
            tile_in_route = [TilePortType(PORT_WEST + 1), TilePortType(0), TilePortType(0)],
            tile_out_route = ROUTE_SOUTH,
            tile_pred_route= ROUTE_SOUTH,
            const_val = DataType(0x5),
            opt_type = OPT_ADD_CONST)]

    ### Full Bitstream Pkt ###
    bitstreams = [
        cfg_a_row,
        cfg_b_row,
        cfg_c_row,
    ]

    # Funnel individual tile pkts
    cpu_to_cgra_bitstream_msgs = []
    for bitstream in bitstreams:
        cpu_to_cgra_bitstream_msgs += list(reversed(bitstream))

    ### Tokenizer Cfg Pkt ###
    cfg_tokenizer_pkt = [
        CfgTokenizerType(token_route_sink_enable=
            [PortRouteType(0b100000000000), PortRouteType(0)] + \
            [PortRouteType(0b001000000000), PortRouteType(0)] + \
            [PortRouteType(0) for i in range(num_rd_ports - 4)],
            token_route_delay_to_sink=[PortDelayType(0) for _ in range(num_wr_ports)] \
                + \
                [PortDelayType(1), PortDelayType(0)]
                + \
                [PortDelayType(0) for _ in range(num_st_ports)]
        ),
        CfgTokenizerType(token_route_sink_enable=
            [PortRouteType(0b0010) if i == 12 else PortRouteType(0) for i in range(num_rd_ports)],
            token_route_delay_to_sink=[PortDelayType(0) for _ in range(num_wr_ports)] \
                + \
                [PortDelayType(0), PortDelayType(0)]
                + \
                [PortDelayType(1), PortDelayType(0)]
        ),
        CfgTokenizerType(token_route_sink_enable=
            [PortRouteType(0b0010) if i == 12 else PortRouteType(0) for i in range(num_rd_ports)],
            token_route_delay_to_sink=[PortDelayType(0) for _ in range(num_wr_ports)] \
                + \
                [PortDelayType(0), PortDelayType(0)]
                + \
                [PortDelayType(1), PortDelayType(0)]
        ),
    ]

    ### Inputs into dut ###
    cpu_to_cgra_metadata_msgs = [
        CfgMetadataType(
                        cmd = CMD_CONFIG,
                        tile_load_count = TileCountType(2),
                        pred_tile_valid = [b1(1) for _ in range(num_tiles)],
                        in_regs = [RegAddrType(0) for _ in range(num_rd_ports)],
                        in_regs_val = [b1(1), b1(0), b1(1)] + [b1(0) for _ in range(num_rd_ports - 3)],
                        in_tid_enable = [b1(1)] + [b1(0) for _ in range(num_rd_ports - 1)],
                        out_regs = [RegAddrType(0) for i in range(num_wr_ports)],
                        out_regs_val = [b1(0), b1(1)] + [b1(0) for _ in range(num_wr_ports - 2)],
                        out_pred_regs = [PredAddrType(0) for _ in range(num_wr_ports)],
                        out_pred_regs_val = [b1(1)] + [b1(0) for _ in range(num_wr_ports - 1)],
                        ld_enable = [b1(0) for _ in range(num_ld_ports)],
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
                        tile_load_count = TileCountType(1),
                        pred_tile_valid = [b1(1) for _ in range(num_tiles)],
                        in_regs = [RegAddrType(0) for _ in range(num_rd_ports)],
                        in_regs_val = [b1(0) for _ in range(num_rd_ports - 2)] + [b1(1), b1(0)],
                        out_regs = [RegAddrType(i) for i in range(num_wr_ports)],
                        out_regs_val = [b1(0) for _ in range(num_wr_ports)],
                        st_enable = [b1(1)] + [b1(0) for _ in range(num_st_ports - 1)],
                        tokenizer_cfg = cfg_tokenizer_pkt[1],
                        cfg_id = 1,
                        br_id = 2,
                        thread_count = thread_count,
                        start_cfg = 0,
                        end_cfg = 0,
                        branch_en = b1(1),
                        branch_has_else = b1(1),
                        branch_backedge_sel = b2(2),
                        pred_reg_id = PredAddrType(0),
                        branch_true_cfg_id = 2,
                        branch_false_cfg_id = 0,
                        reconverge_cfg_id = 2,
                    ),
        CfgMetadataType(
                        cmd = CMD_CONFIG,
                        tile_load_count = TileCountType(1),
                        pred_tile_valid = [b1(1) for _ in range(num_tiles)],
                        in_regs = [RegAddrType(0) for _ in range(num_rd_ports)],
                        in_regs_val = [b1(0) for _ in range(num_rd_ports - 2)] + [b1(1), b1(0)],
                        out_regs = [RegAddrType(i) for i in range(num_wr_ports)],
                        out_regs_val = [b1(0) for _ in range(num_wr_ports)],
                        st_enable = [b1(1)] + [b1(0) for _ in range(num_st_ports - 1)],
                        tokenizer_cfg = cfg_tokenizer_pkt[1],
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
