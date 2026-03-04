from pymtl3.passes.backends.verilog import (VerilogVerilatorImportPass)
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)

from pymtl3 import *

from ..STEP_CgraRTL import STEP_CgraRTL
from ...lib.basic.AxiSourceRTL import AxiLdSourceRTL
from ...lib.basic.SourceTriggeredRTL import SourceTriggeredRTL
from ...lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ...lib.basic.val_rdy.queues import NormalQueueRTL
from ...lib.basic.AxiInterface import RecvAxiReadStoreAddrIfcRTL
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
THREAD_COUNT = 4
LOOP_MAX = 2


class AxiStCaptureRTL( Component ):
    def construct( s, DataType, delay = 1 ):
        assert(delay >= 1)
        s.send = RecvAxiReadStoreAddrIfcRTL( DataType )

        ThreadIdxType = mk_bits(clog2(MAX_THREAD_COUNT))
        s.q_data = NormalQueueRTL( Bits2, delay + 1 )
        s.q_id = NormalQueueRTL( ThreadIdxType, delay + 1 )

        s.captured_data = []
        s.captured_addr = []
        s.count = 0

        s.send.addr_rdy //= s.q_data.recv.rdy
        s.send.resp //= Bits2(0)
        s.send.resp_last //= Bits1(0)
        s.q_data.send.rdy //= s.send.resp_ready
        s.q_id.send.rdy //= s.send.resp_ready

        s.fire = OutPort(Bits1)
        @update
        def comb_fire():
            s.fire @= s.send.addr_val & s.send.data_valid & s.send.addr_rdy

        @update_ff
        def up_sink():
            if s.reset:
                s.count = 0
            s.q_data.recv.msg <<= 0
            s.q_id.recv.msg <<= 0
            s.q_data.recv.val <<= 0
            s.q_id.recv.val <<= 0

            if s.fire:
                s.captured_data.append(int(s.send.data))
                s.captured_addr.append(int(s.send.addr))
                s.count += 1
                s.q_data.recv.msg <<= Bits2(1)
                s.q_data.recv.val <<= 1
                s.q_id.recv.msg <<= s.send.id
                s.q_id.recv.val <<= 1

            s.send.resp_valid <<= s.q_data.send.val
            s.send.resp_id <<= s.q_id.send.msg


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
        s.cpu_to_cgra_metadata_pkts = TestSrcRTL(CfgMetadataType, cpu_to_cgra_metadata_msgs)
        s.cpu_to_cgra_bitstream_pkts = SourceTriggeredRTL(TileBitstreamType, cpu_to_cgra_bitstream_msgs, chunk_size=s.num_tiles, delay=1)
        s.ld_axi_pkts = [AxiLdSourceRTL(DataType, [], 0, 0) for _ in range(num_ld_ports)]
        s.st_axi_pkts = [AxiStCaptureRTL(DataType, delay=1) for _ in range(num_st_ports)]

        # Configure Sinks
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
        if s.dut.send_to_cpu_done:
            return True
        return s.cpu_to_cgra_metadata_pkts.done() and s.cgra_to_cpu_signal.done()

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
    thread_count = THREAD_COUNT
    loop_max = LOOP_MAX
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

    def mk_noop_tiles():
        return [TileBitstreamType(
            tile_id = TileIdType(i),
            opt_type = OPT_NAH) for i in range(num_tiles)]

    def set_tile(tiles, tile_id, **kwargs):
        tiles[tile_id] = TileBitstreamType(tile_id = TileIdType(tile_id), **kwargs)

    def mk_token_route_for_returner(returner_idx):
        bit_pos = num_returner_ports - 1 - returner_idx
        return PortRouteType(1 << bit_pos)

    def mk_tokenizer_cfg(route_mask, taker_idx=0):
        base_delay = PortDelayType(1)
        store_delay = PortDelayType(1)
        return CfgTokenizerType(
            token_route_sink_enable=[route_mask if i == taker_idx else PortRouteType(0) for i in range(num_rd_ports)],
            token_route_delay_to_sink=(
                [base_delay for _ in range(num_wr_ports)]
                + [base_delay for _ in range(num_ld_ports)]
                + [store_delay for _ in range(num_st_ports)]
            )
        )

    # Tile routing bitmasks (order: N, S, W, E, NW, NE, SE, SW)
    ROUTE_SOUTH = TileOutType(0b01000000)
    ROUTE_WEST = TileOutType(0b00100000)
    ROUTE_EAST = TileOutType(0b00010000)

    # Config A: generate predicate from tid compare in tile (0,0), send pred to RF (row 0 west)
    cfg_a_tiles = mk_noop_tiles()
    set_tile(
        cfg_a_tiles,
        0,
        tile_in_route = [TilePortType(PORT_WEST + 1), TilePortType(0), TilePortType(0)],
        tile_out_route = ROUTE_WEST,
        tile_pred_route = ROUTE_WEST,
        tile_out_shift_amounts = [ShiftAmountType(0)] * num_tile_outports,
        const_val = DataType(0x00),
        pred_gen = Bits1(1),
        opt_type = OPT_EQ_CONST,
    )

    # Config B: true branch store (addr=0x10+tid, data=0xB1+tid) on st port 0 (cols 0/1)
    cfg_b_tiles = mk_noop_tiles()
    set_tile(
        cfg_b_tiles,
        12,
        tile_in_route = [TilePortType(PORT_WEST + 1), TilePortType(0), TilePortType(0)],
        tile_out_route = ROUTE_SOUTH,
        tile_pred_route = ROUTE_SOUTH,
        tile_out_shift_amounts = [ShiftAmountType(0)] * num_tile_outports,
        const_val = DataType(0x10),
        opt_type = OPT_ADD_CONST,
    )
    set_tile(
        cfg_b_tiles,
        13,
        tile_in_route = [TilePortType(PORT_WEST + 1), TilePortType(0), TilePortType(0)],
        tile_out_route = ROUTE_SOUTH,
        tile_pred_route = ROUTE_SOUTH,
        tile_out_shift_amounts = [ShiftAmountType(0)] * num_tile_outports,
        const_val = DataType(0xB1),
        opt_type = OPT_ADD_CONST,
    )

    # Config C: false branch store (addr=0x10+tid, data=0xC1+tid)
    cfg_c_tiles = mk_noop_tiles()
    set_tile(
        cfg_c_tiles,
        12,
        tile_in_route = [TilePortType(PORT_WEST + 1), TilePortType(0), TilePortType(0)],
        tile_out_route = ROUTE_SOUTH,
        tile_pred_route = ROUTE_SOUTH,
        tile_out_shift_amounts = [ShiftAmountType(0)] * num_tile_outports,
        const_val = DataType(0x10),
        opt_type = OPT_ADD_CONST,
    )
    set_tile(
        cfg_c_tiles,
        13,
        tile_in_route = [TilePortType(PORT_WEST + 1), TilePortType(0), TilePortType(0)],
        tile_out_route = ROUTE_SOUTH,
        tile_pred_route = ROUTE_SOUTH,
        tile_out_shift_amounts = [ShiftAmountType(0)] * num_tile_outports,
        const_val = DataType(0xC1),
        opt_type = OPT_ADD_CONST,
    )

    # Config D: reconverge + loop control (no-op fabric)
    cfg_d_tiles = mk_noop_tiles()

    # Config E: final block (no-op fabric)
    cfg_e_tiles = mk_noop_tiles()

    ### Full Bitstream Pkt ###
    bitstreams = []
    for _ in range(loop_max):
        bitstreams += [cfg_a_tiles, cfg_b_tiles, cfg_c_tiles, cfg_d_tiles]
    bitstreams += [cfg_e_tiles]

    # Funnel individual tile pkts
    cpu_to_cgra_bitstream_msgs = []
    for bitstream in bitstreams:
        cpu_to_cgra_bitstream_msgs += list(reversed(bitstream))

    ### Tokenizer Cfg Pkt ###
    route_to_wr0 = mk_token_route_for_returner(0)
    st0_returner_idx = num_wr_ports + num_ld_ports
    route_to_st0 = mk_token_route_for_returner(st0_returner_idx)

    cfg_tokenizer_pkt = []
    for _ in range(loop_max):
        cfg_tokenizer_pkt += [
            mk_tokenizer_cfg(route_to_wr0, taker_idx=0),
            mk_tokenizer_cfg(route_to_st0),
            mk_tokenizer_cfg(route_to_st0),
            mk_tokenizer_cfg(PortRouteType(0)),
        ]
    cfg_tokenizer_pkt += [mk_tokenizer_cfg(PortRouteType(0))]

    pred_tile_valid = [b1(0) for _ in range(num_tiles)]
    pred_tile_valid[0] = b1(1)

    ### Inputs into dut ###
    cpu_to_cgra_metadata_msgs = []
    for it in range(loop_max):
        base = it * 4
        cfg_a_id = base
        cfg_b_id = base + 1
        cfg_c_id = base + 2
        cfg_d_id = base + 3
        tokenizer_base = it * 4
        cpu_to_cgra_metadata_msgs += [
            CfgMetadataType(
                            cmd = CMD_CONFIG,
                            pred_tile_valid = pred_tile_valid,
                            in_regs = [RegAddrType(0) for _ in range(num_rd_ports)],
                            in_regs_val = [b1(1)] + [b1(0) for _ in range(num_rd_ports - 1)],
                            in_tid_enable = [b1(1)] + [b1(0) for _ in range(num_rd_ports - 1)],
                            out_regs = [RegAddrType(0) for _ in range(num_wr_ports)],
                            out_regs_val = [b1(1)] + [b1(0) for _ in range(num_wr_ports - 1)],
                            tokenizer_cfg = cfg_tokenizer_pkt[tokenizer_base + 0],
                            cfg_id = cfg_a_id,
                            br_id = cfg_b_id,
                            thread_count = thread_count,
                            start_cfg = b1(1) if it == 0 else b1(0),
                            end_cfg = 0,
                            branch_en = b1(1),
                            pred_reg_id = PredAddrType(0),
                            branch_true_cfg_id = cfg_b_id,
                            branch_false_cfg_id = cfg_c_id,
                            reconverge_cfg_id = cfg_d_id,
                        ),
            CfgMetadataType(
                            cmd = CMD_CONFIG,
                            pred_tile_valid = [b1(0) for _ in range(num_tiles)],
                            in_regs = [RegAddrType(0) for _ in range(num_rd_ports)],
                            in_regs_val = [b1(1)] + [b1(0) for _ in range(num_rd_ports - 1)],
                            in_tid_enable = [b1(1)] + [b1(0) for _ in range(num_rd_ports - 1)],
                            out_regs = [RegAddrType(0) for _ in range(num_wr_ports)],
                            out_regs_val = [b1(0) for _ in range(num_wr_ports)],
                            st_enable = [b1(1)] + [b1(0) for _ in range(num_st_ports - 1)],
                            tokenizer_cfg = cfg_tokenizer_pkt[tokenizer_base + 1],
                            cfg_id = cfg_b_id,
                            br_id = cfg_c_id,
                            thread_count = thread_count,
                            start_cfg = 0,
                            end_cfg = 0,
                        ),
            CfgMetadataType(
                            cmd = CMD_CONFIG,
                            pred_tile_valid = [b1(0) for _ in range(num_tiles)],
                            in_regs = [RegAddrType(0) for _ in range(num_rd_ports)],
                            in_regs_val = [b1(1)] + [b1(0) for _ in range(num_rd_ports - 1)],
                            in_tid_enable = [b1(1)] + [b1(0) for _ in range(num_rd_ports - 1)],
                            out_regs = [RegAddrType(0) for _ in range(num_wr_ports)],
                            out_regs_val = [b1(0) for _ in range(num_wr_ports)],
                            st_enable = [b1(1)] + [b1(0) for _ in range(num_st_ports - 1)],
                            tokenizer_cfg = cfg_tokenizer_pkt[tokenizer_base + 2],
                            cfg_id = cfg_c_id,
                            br_id = cfg_d_id,
                            thread_count = thread_count,
                            start_cfg = 0,
                            end_cfg = 0,
                        ),
            CfgMetadataType(
                            cmd = CMD_CONFIG,
                            pred_tile_valid = [b1(0) for _ in range(num_tiles)],
                            in_regs = [RegAddrType(0) for _ in range(num_rd_ports)],
                            in_regs_val = [b1(0) for _ in range(num_rd_ports)],
                            out_regs = [RegAddrType(0) for _ in range(num_wr_ports)],
                            out_regs_val = [b1(0) for _ in range(num_wr_ports)],
                            tokenizer_cfg = cfg_tokenizer_pkt[tokenizer_base + 3],
                            cfg_id = cfg_d_id,
                            br_id = cfg_d_id,
                            thread_count = thread_count,
                            start_cfg = 0,
                            end_cfg = 0,
                        ),
        ]

    final_cfg_id = loop_max * 4
    cpu_to_cgra_metadata_msgs += [
        CfgMetadataType(
                        cmd = CMD_CONFIG,
                        pred_tile_valid = [b1(0) for _ in range(num_tiles)],
                        in_regs = [RegAddrType(0) for _ in range(num_rd_ports)],
                        in_regs_val = [b1(0) for _ in range(num_rd_ports)],
                        out_regs = [RegAddrType(0) for _ in range(num_wr_ports)],
                        out_regs_val = [b1(0) for _ in range(num_wr_ports)],
                        tokenizer_cfg = cfg_tokenizer_pkt[-1],
                        cfg_id = final_cfg_id,
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


def test_predicated_branch(cmdline_opts):
    th = init_param()
    
    th.elaborate()
    th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                       ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                        'ALWCOMBORDER'])
    th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
    run_sim(th)

    # Validate both branch stores observed across loop iterations
    st0 = th.st_axi_pkts[0]
    true_vals = {0xB1 + i for i in range(THREAD_COUNT)}
    false_vals = {0xC1 + i for i in range(THREAD_COUNT)}
    assert any(v in true_vals for v in st0.captured_data)
    assert any(v in false_vals for v in st0.captured_data)
    assert len(st0.captured_data) == THREAD_COUNT * LOOP_MAX * 2
