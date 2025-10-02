from pymtl3.passes.backends.verilog import (VerilogVerilatorImportPass)
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)

from ..STEP_CgraRTL import STEP_CgraRTL
from ...lib.basic.AxiSourceRTL import AxiLdSourceRTL, AxiStSourceRTL
from ...lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ...lib.messages import *
from ...lib.opt_type import *


#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------
# Global Parameters. Fixed for now TODO @darrenl
num_tile_inports = 4
num_tile_outports = 4
num_fu_inports = 3
num_fu_outports = 1
num_register_banks = 2
num_registers = 16
num_pred_registers = 16

class TestHarness(Component):
    def construct(s,
            # Types
            CpuPktType,
            CfgType,
            CfgBitstreamType,
            CfgMetadataType,
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
            cpu_to_cgra_msgs,
            cgra_to_cpu_msgs
            ):
        # Configure for done comparison
        s.num_ld_ports = num_ld_ports
        s.num_st_ports = num_st_ports

        # Configure Sources
        ld_axi_msgs = [[] for _ in range(num_ld_ports - 1)] + [[5]*2]
        st_axi_msgs = [[] for _ in range(num_st_ports - 1)] + [[1]*2]
        s.cpu_to_cgra_pkts = TestSrcRTL(CpuPktType, cpu_to_cgra_msgs)
        s.ld_axi_pkts = [AxiLdSourceRTL(DataType, ld_axi_msgs[i], num_empty=0, initial_delay=12) for i in range(num_ld_ports)]
        s.st_axi_pkts = [AxiStSourceRTL(DataType, st_axi_msgs[i], initial_delay=40) for i in range(num_st_ports)]

        # Configure Sinks
        cmp_fn = lambda a, b : a == b
        s.cgra_to_cpu_pkts = TestSinkRTL(CpuPktType, cgra_to_cpu_msgs)

        s.dut = STEP_CgraRTL(
            CpuPktType,
            CfgType,
            CfgBitstreamType,
            CfgMetadataType,
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
        )

        # Axi Interfaces
        for i in range(num_ld_ports):
            s.dut.ld_axi[i] //= s.ld_axi_pkts[i].send
        for i in range(num_st_ports):
            s.dut.st_axi[i] //= s.st_axi_pkts[i].send

        # CPU Interfaces
        s.dut.recv_from_cpu_pkt //= s.cpu_to_cgra_pkts.send
        s.dut.send_to_cpu_pkt //= s.cgra_to_cpu_pkts.recv

    def done(s):
        for i in range(s.num_ld_ports):
            if not s.ld_axi_pkts[i].done():
                return False
        for i in range(s.num_st_ports):
            if not s.st_axi_pkts[i].done():
                return False
        return s.cpu_to_cgra_pkts.done() and s.cgra_to_cpu_pkts.done()

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
    num_rd_ports = num_tile_rows
    num_wr_ports = num_tile_rows
    num_ld_ports = num_tile_cols // 2
    num_st_ports = num_tile_cols // 2
    num_consts = 4
    thread_count = 2
    num_taker_ports = num_rd_ports
    num_returner_ports = num_wr_ports + num_ld_ports + num_st_ports

    DataType = mk_bits(8)
    OperationType = mk_bits( clog2(NUM_OPTS) )
    TilePortType = mk_bits( clog2(num_tile_inports + 1) ) # +1 for no connection
    TileOutType = mk_bits( num_tile_outports )
    RegAddrType = mk_bits( clog2(num_registers) )
    PredAddrType = mk_bits( clog2(num_pred_registers) )

    PortRouteType = mk_bits( num_returner_ports )
    CfgTokenizerType = mk_cfg_tokenizer_pkt(num_taker_ports,
                                            num_returner_ports,
                                            num_tiles,
                                            PortRouteType
                                            )
    
    TileBitstreamType = mk_tile_bitstream_pkt(num_tile_inports,
                                                num_tile_outports,
                                                num_fu_inports,
                                                num_fu_outports,
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
    CfgType = mk_cfg_pkt(CfgBitstreamType, CfgMetadataType)

    CpuPktType = mk_cpu_pkt(CfgType)

    # Setup a row of PEs to do No op
    no_op_row = [TileBitstreamType(
            opt_type = OPT_NAH) for _ in range(num_tile_cols)]

    load_row = [TileBitstreamType(
            opt_type = OPT_NAH) for _ in range(num_tile_cols - 2)] \
            + \
            [TileBitstreamType(
            tile_in_route = [TilePortType(PORT_EAST + 1), TilePortType(0), TilePortType(0)],
            tile_out_route = TileOutType(0b1000),
            tile_pred_route= TileOutType(0b1000),
            const_val = DataType(0),
            opt_type = OPT_ADD_CONST)] \
            + \
            [TileBitstreamType(
            tile_in_route = [TilePortType(PORT_EAST + 1), TilePortType(0), TilePortType(0)],
            tile_out_route = TileOutType(0b0010),
            tile_pred_route= TileOutType(0b0010),
            const_val = DataType(0x10),
            opt_type = OPT_ADD_CONST)]

    mul_row = [TileBitstreamType(
            opt_type = OPT_NAH) for _ in range(num_tile_cols - 1)] \
            + \
            [TileBitstreamType(
            tile_in_route = [TilePortType(PORT_EAST + 1), TilePortType(0), TilePortType(0)],
            tile_out_route = TileOutType(0b0100),
            tile_pred_route= TileOutType(0b0100),
            const_val = DataType(2),
            opt_type = OPT_MUL_CONST)]

    # TODO: @darrenl OPT_PAS still needs some type of trigger and can't be valid for all clock cycles
    store_row = [TileBitstreamType(
            opt_type = OPT_NAH) for _ in range(num_tile_cols - 2)] \
            + \
            [TileBitstreamType(
            tile_in_route = [TilePortType(PORT_EAST + 1), TilePortType(0), TilePortType(0)],
            tile_out_route = TileOutType(0b0100),
            tile_pred_route= TileOutType(0b0100),
            const_val = DataType(0x10),
            opt_type = OPT_PAS)] \
            + \
            [TileBitstreamType(
            tile_in_route = [TilePortType(PORT_EAST + 1), TilePortType(PORT_NORTH + 1), TilePortType(0)],
            tile_out_route = TileOutType(0b0111),
            tile_pred_route= TileOutType(0b0111),
            opt_type = OPT_ADD)]

    ### Full Bitstream Pkt ###
    bitstreams = [
        CfgBitstreamType(bitstream=(load_row + no_op_row * (num_tile_rows - 1))),
        CfgBitstreamType(bitstream=(no_op_row * (num_tile_rows - 2) + mul_row + store_row))
    ]

    ### Tokenizer Cfg Pkt ###
    cfg_tokenizer_pkt = [
        CfgTokenizerType(token_route_sink_enable=
            [PortRouteType(0b0100) if i == 0 else PortRouteType(0) for i in range(num_rd_ports)],
            token_route_delay_to_sink=[PortDelayType(0) for _ in range(num_wr_ports)] \
                + \
                [PortDelayType(0), PortDelayType(1)]
                + \
                [PortDelayType(0) for _ in range(num_st_ports)]
        ),
        CfgTokenizerType(token_route_sink_enable=[
                PortRouteType(0),
                PortRouteType(0),
                PortRouteType(0b0001),
                PortRouteType(0b10001),
            ],
            token_route_delay_to_sink=[PortDelayType(0) for _ in range(num_wr_ports)] \
                + \
                [PortDelayType(0), PortDelayType(1)]
                + \
                [PortDelayType(0) for _ in range(num_st_ports)]
        )
    ]

    ### Inputs into dut ###
    cfg_metadata = [
        CfgMetadataType(
                        pred_tile_valid = [b1(1) for _ in range(num_tiles)],
                        in_regs = [RegAddrType(0) for _ in range(num_tile_cols)],
                        in_regs_val = [b1(1)] + [b1(0) for _ in range(num_tile_cols - 1)],
                        out_regs = [RegAddrType(0) for _ in range(num_tile_cols)],
                        out_regs_val = [b1(0) for _ in range(num_tile_cols)],
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
                        pred_tile_valid = [b1(1) for _ in range(num_tiles)],
                        in_regs = [RegAddrType(0) for _ in range(num_tile_cols)],
                        in_regs_val = [b1(0) for _ in range(num_tile_cols - 2)] + [b1(1)] * 2,
                        out_regs = [RegAddrType(i) for i in range(num_tile_cols)],
                        out_regs_val = [b1(0) for _ in range(num_tile_cols - 1)] + [b1(1)],
                        st_enable = [b1(0) for _ in range(num_st_ports - 1)] + [b1(1)],
                        tokenizer_cfg = cfg_tokenizer_pkt[1],
                        cfg_id = 1,
                        br_id = 0,
                        thread_count = thread_count,
                        start_cfg = 0,
                        end_cfg = 1,
                    ),
    ]

    # Ensure same # Bitstreams and Cfg Metadata
    assert(len(bitstreams) == len(cfg_metadata))

    cpu_to_cgra_msgs = [CpuPktType(cmd=CMD_CONFIG, cfg=CfgType(bitstream=bitstreams[i], 
                                metadata=cfg_metadata[i])) for i in range(len(bitstreams))] \
            + \
            [CpuPktType(cmd=CMD_LAUNCH, cfg = CfgType(
                bitstream = CfgBitstreamType(),
                metadata = CfgMetadataType()))]
    
    cgra_to_cpu_msgs = [CpuPktType(cmd=CMD_COMPLETE)]

    th = TestHarness(# Types
                        CpuPktType,
                        CfgType,
                        CfgBitstreamType,
                        CfgMetadataType,
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
                        cpu_to_cgra_msgs,
                        cgra_to_cpu_msgs
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