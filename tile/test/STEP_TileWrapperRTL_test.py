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

from ..STEP_TileWrapperRTL import STEP_TileWrapperRTL
from ...lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ...lib.messages import *
from ...lib.opt_type import *
from ...lib.basic.TimedWriteSource import TimedWriteSource


#-------------------------------------------------------------------------
# TestHarness
#-------------------------------------------------------------------------

class TestHarness(Component):

    def construct(s,
                    num_tile_cols,
                    num_tile_rows,
                    num_tile_inports,
                    num_tile_outports,
                    num_fu_inports,
                    num_fu_outports,
                    DataType,
                    TileBitstreamType,
                    CfgBitstreamType,
                    OperationType,
                    RegAddrType,
                    PredRegAddrType,
                    full_bitstream_msgs,
                    data_in_msgs,
                    data_out_msgs,
                    ):
        s.num_tile_cols = num_tile_cols
        s.num_tile_rows = num_tile_rows
        num_tiles = num_tile_cols * num_tile_rows
        s.num_tiles = num_tiles

        # Configure sources - recv_from_cpu_pkt launches every cycle
        def delay_func(i):
            return 2 + 2*i
        interval_delay = 10 + num_tile_cols
        s.data_in_pkts = [TestSrcRTL(DataType, data_in_msgs[i][j], 2, interval_delay) for i in range(num_tile_rows) for j in range(2)]
        s.fabric_bitstream = TestSrcRTL(CfgBitstreamType, full_bitstream_msgs, 0, interval_delay)
        s.pred_in_rf_pkts = [TestSrcRTL(Bits1, [Bits1(1)], 2, interval_delay) for _ in range(num_tiles)]
        s.pred_out_pkts = [TestSinkRTL(Bits1, [Bits1(1)], delay_func(i), interval_delay) for i in range(num_tile_rows * 2)]
        s.recv_from_rf_pred = [TestSrcRTL(Bits1, [Bits1(1)], 2, interval_delay) for _ in range(num_tiles)]

        # Configure sinks
        cmp_fn = lambda a, b : a == b
        s.data_out_pkts = [TestSinkRTL(DataType, data_out_msgs[i][j], 5, interval_delay, cmp_fn = cmp_fn) for i in range(num_tile_rows) for j in range(2)]

        s.dut = STEP_TileWrapperRTL(
                                num_tile_cols,
                                num_tile_rows,
                                num_tile_inports,
                                num_tile_outports,
                                num_fu_inports,
                                num_fu_outports,
                                DataType,
                                TileBitstreamType,
                                CfgBitstreamType,
                                OperationType,
                                RegAddrType,
                                PredRegAddrType,
                            )

        # Connections
        for i in range(num_tile_rows):
            s.dut.recv_west_data_port[i] //= s.data_in_pkts[2*i].send.msg
            s.dut.recv_east_data_port[i] //= s.data_in_pkts[2*i+1].send.msg
            s.data_in_pkts[i].send.rdy //= 1
            # Data connection
            s.dut.send_west_data_port[i] //= s.data_out_pkts[2*i].recv.msg
            s.dut.send_east_data_port[i] //= s.data_out_pkts[2*i+1].recv.msg
    
            # Predicate connections
            s.dut.send_west_pred_port[i] //= s.pred_out_pkts[2*i].recv.msg
            s.dut.send_west_pred_port[i] //= s.pred_out_pkts[2*i].recv.val
            s.dut.send_east_pred_port[i] //= s.pred_out_pkts[2*i+1].recv.msg
            s.dut.send_east_pred_port[i] //= s.pred_out_pkts[2*i+1].recv.val
        for i in range(num_tiles):
            s.dut.recv_from_rf_pred[i] //= s.recv_from_rf_pred[i].send.msg
            s.recv_from_rf_pred[i].send.rdy //= 1
        s.dut.recv_fabric_bitstream //= s.fabric_bitstream.send

        # @update
        # def data_valid():
        #     # Assume data is valid if > 0
        #     for i in range(num_tile_rows):
        #         s.data_out_pkts[i].recv.val @= s.dut.send_east_data_port[i] > 0

    def done(s):
        for i in range(s.num_tile_cols):
            if not s.data_in_pkts[i].done() \
                or not s.data_out_pkts[i].done():
                return False
        return s.fabric_bitstream.done()

    def line_trace(s):
        return s.dut.line_trace()

def init_param():
    #-------------------------------------------------------------------------
    # Test cases
    #-------------------------------------------------------------------------

    # Fixed for now... @darrenl
    num_tile_inports = 8
    num_tile_outports = 8
    num_fu_inports = 3
    num_fu_outports = 1

    # Parameterizable
    num_iterations = 12
    num_regs = 16
    num_pred_regs = 16
    num_tile_cols = 4
    num_tile_rows = 4
    num_tiles = num_tile_cols * num_tile_rows

    DataType = mk_bits(8)
    OperationType = mk_bits( clog2(NUM_OPTS) )
    TilePortType = mk_bits( clog2(num_tile_inports + 1) ) # +1 for no connection
    TileOutType = mk_bits( num_tile_outports ) # Binary for each direction if valid
    RegAddrType = mk_bits( clog2(num_regs) )
    PredRegAddrType = mk_bits( clog2(num_pred_regs) )

    TileBitstreamType = mk_tile_bitstream_pkt(num_tile_inports,
                                                num_tile_outports,
                                                num_fu_inports,
                                                num_fu_outports,
                                                OperationType,
                                                DataType,
                                                RegAddrType,
                                                PredRegAddrType,
                                                )
    
    CfgBitstreamType = mk_bitstream_pkt(num_tiles, TileBitstreamType)

    # Setup a row of PEs to do No op
    no_op_row = [TileBitstreamType(opt_type = OPT_NAH) for _ in range(num_tile_cols)]
    
    # Setup a row of PEs where only right has an add
    add_op_send_south_east_row = [TileBitstreamType(
            tile_in_route = [TilePortType(PORT_WEST + 1), TilePortType(PORT_WEST + 1), TilePortType(0)],
            tile_out_route = TileOutType(0b00000010),
            tile_pred_route = TileOutType(0b00000010),
            opt_type = OPT_ADD)] \
            + \
            [TileBitstreamType(opt_type = OPT_NAH)] * (num_tile_cols - 1)

    add_op_send_east_row = [TileBitstreamType(opt_type = OPT_NAH)] \
            + \
            [TileBitstreamType(
            tile_in_route = [TilePortType(PORT_NORTHWEST + 1), TilePortType(PORT_NORTHWEST + 1), TilePortType(0)],
            tile_out_route = TileOutType(0b00010000),
            tile_pred_route = TileOutType(0b00010000),
            opt_type = OPT_ADD)] \
            + \
            [TileBitstreamType(
            tile_in_route = [TilePortType(PORT_WEST + 1), TilePortType(PORT_WEST + 1), TilePortType(0)],
            tile_out_route = TileOutType(0b00010000),
            tile_pred_route = TileOutType(0b00010000),
            opt_type = OPT_ADD)] * (num_tile_cols - 2)
    

    # Setup a row of PEs where only right has a mul
    mul_op_send_east_row = [TileBitstreamType(opt_type = OPT_NAH)] \
            + \
            [TileBitstreamType(
            tile_in_route = [TilePortType(PORT_NORTHWEST + 1), TilePortType(PORT_NORTHWEST + 1), TilePortType(0)],
            tile_out_route = TileOutType(0b00010000),
            tile_pred_route = TileOutType(0b00010000),
            opt_type = OPT_MUL)] \
            + \
            [TileBitstreamType(
            tile_in_route = [TilePortType(PORT_WEST + 1), TilePortType(PORT_WEST + 1), TilePortType(0)],
            tile_out_route = TileOutType(0b00010000),
            tile_pred_route = TileOutType(0b00010000),
            opt_type = OPT_MUL)] * (num_tile_cols - 2)

    # Full Bitstream Pkt
    full_bitstream_msgs = [
        CfgBitstreamType(bitstream = (add_op_send_south_east_row + add_op_send_east_row + no_op_row * 2)),
        CfgBitstreamType(bitstream = (add_op_send_south_east_row + mul_op_send_east_row + no_op_row * 2))
    ]

    data_in_msgs = [
        [
            # Row 0 W
            [DataType(1), DataType(3)],
            # Row 0 E
            []
        ],
        # Row 1
        [[],[]],
        # Row 2
        [[],[]],
        # Row 3
        [[],[]],
    ]

    data_out_msgs = [
        # Row 0
        [[],[]],
        [
            # Row 1 W
            [DataType(4), DataType(36)],
            # Row 1 E
            []
        ],
        # Row 2
        [[],[]],
        # Row 3
        [[],[]],
    ]

    th = TestHarness(
                    num_tile_cols,
                    num_tile_rows,
                    num_tile_inports,
                    num_tile_outports,
                    num_fu_inports,
                    num_fu_outports,
                    DataType,
                    TileBitstreamType,
                    CfgBitstreamType,
                    OperationType,
                    RegAddrType,
                    PredRegAddrType,
                    full_bitstream_msgs,
                    data_in_msgs,
                    data_out_msgs,
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