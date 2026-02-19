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

from ..STEP_TileRTL import STEP_TileRTL
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
                    num_tile_inports,
                    num_tile_outports,
                    num_fu_inports,
                    num_fu_outports,
                    DataType,
                    TileBitstreamType,
                    OperationType,
                    RegAddrType,
                    PredRegAddrType,
                    tile_in_bitstream_msgs,
                    data_in_msgs,
                    data_out_msgs,
                    pred_in_rf_msgs,
                    ):
        s.num_tile_inports = num_tile_inports
        s.num_tile_outports = num_tile_outports

        # Configure sources - recv_from_cpu_pkt launches every cycle
        initial_delay = 1
        interval_delay = 3
        s.data_in_pkts = [TestSrcRTL(DataType, data_in_msgs[i], initial_delay) for i in range(num_tile_inports)]
        s.tile_bitstream = TestSrcRTL(TileBitstreamType, tile_in_bitstream_msgs, 0, interval_delay)
        s.pred_in_rf_pkts = TestSrcRTL(Bits1, pred_in_rf_msgs, initial_delay, interval_delay)
        s.pred_in_pkts = [TestSrcRTL(Bits1, [Bits1(i < 2)], initial_delay) for i in range(num_tile_inports)]

        # Configure sinks
        cmp_fn = lambda a, b : a == b
        s.data_out_pkts = [TestSinkRTL(DataType, data_out_msgs[i], initial_delay + 1, cmp_fn = cmp_fn) for i in range(num_tile_outports)]
        s.pred_out_pkts = [TestSinkRTL(Bits1, [Bits1(i < 1 or i == 6)], initial_delay) for i in range(num_tile_outports)]

        s.dut = STEP_TileRTL(num_tile_inports,
                                num_tile_outports,
                                num_fu_inports,
                                num_fu_outports,
                                DataType,
                                TileBitstreamType,
                                OperationType,
                                RegAddrType,
                                PredRegAddrType,
                            )

        # Connections
        for i in range(num_tile_inports):
            s.dut.tile_in_data_port[i] //= s.data_in_pkts[i].send.msg
            s.dut.tile_in_pred_port[i] //= s.pred_in_pkts[i].send.msg
            s.data_in_pkts[i].send.rdy //= 1
            s.pred_in_pkts[i].send.rdy //= 1
        for i in range(num_tile_outports):
            s.dut.tile_out_data_port[i] //= s.data_out_pkts[i].recv.msg
            s.dut.tile_out_pred_port[i] //= s.pred_out_pkts[i].recv.msg
            s.data_out_pkts[i].recv.val //= 1
            s.pred_out_pkts[i].recv.val //= 1
        s.dut.recv_tile_bitstream //= s.tile_bitstream.send
        s.dut.tile_in_pred_port_rf //= s.pred_in_rf_pkts.send.msg

    def done(s):
        for i in range(s.num_tile_inports):
            if not s.data_in_pkts[i].done():
                return False
        for i in range(s.num_tile_outports):
            if not s.data_out_pkts[i].done():
                return False
        return s.tile_bitstream.done()

    def line_trace(s):
        return s.dut.line_trace()

def init_param():
    #-------------------------------------------------------------------------
    # Test cases
    #-------------------------------------------------------------------------

    # Fixed for now... @darrenl
    # Out & In ports must match and be in [4,8]
    num_tile_inports = 8
    num_tile_outports = 8
    num_fu_inports = 3
    num_fu_outports = 1

    # Parameterizable
    num_regs = 16
    num_pred_regs = 16

    DataType = mk_bits(8)
    OperationType = mk_bits( clog2(NUM_OPTS) )
    TilePortType = mk_bits( clog2(num_tile_inports + 1) ) # +1 for no connection
    TileOutType = mk_bits( num_tile_outports ) # Binary for each direction if valid
    RegAddrType = mk_bits( clog2(num_regs) )
    PredRegAddrType = mk_bits( clog2(num_pred_regs) )
    ShiftAmountType = mk_bits( clog2(SHIFT_REGISTER_SIZE) )

    TileBitstreamType = mk_tile_bitstream_pkt(num_tile_inports,
                                                num_tile_outports,
                                                num_fu_inports,
                                                num_fu_outports,
                                                OperationType,
                                                DataType,
                                                RegAddrType,
                                                PredRegAddrType,
                                                )

    # Single cycle shift
    shift_amount = 0
    SCSAmount = ShiftAmountType(shift_amount)
    SCSAmountRow = [SCSAmount] * num_tile_outports
    shiftData = [0] * shift_amount

    # Empty TileOutType
    emptyTileOut = TileOutType(0)

    # Bitstream Pkt
    tile_in_bitstream_msgs = [
        TileBitstreamType(
            tile_in_route = [TilePortType(PORT_NORTH + 1), TilePortType(PORT_SOUTH + 1), TilePortType(0)],
            tile_out_route = TileOutType(0b10000010),
            tile_pred_route = TileOutType(0b10000010),
            tile_fwd_route = [TileOutType(0b00100000), emptyTileOut, emptyTileOut, TileOutType(0b00000100)] + [emptyTileOut] * 4,
            tile_out_shift_amounts = SCSAmountRow,
            opt_type = OPT_ADD),
        TileBitstreamType(
            tile_in_route = [TilePortType(PORT_NORTH + 1), TilePortType(PORT_WEST + 1), TilePortType(0)],
            tile_out_route = TileOutType(0b01000000),
            tile_pred_route = TileOutType(0b01000000),
            tile_out_shift_amounts = SCSAmountRow,
            opt_type = OPT_MUL),
        TileBitstreamType(
            tile_in_route = [TilePortType(PORT_NORTH + 1), TilePortType(PORT_NORTH + 1), TilePortType(0)],
            tile_out_route = TileOutType(0b00100000),
            tile_pred_route = TileOutType(0b00100000),
            tile_out_shift_amounts = SCSAmountRow,
            opt_type = OPT_ADD),
    ]

    data_in_msgs = [
        # North
        [DataType(2), DataType(5)] + [0] * 2 + [DataType(4)] + [0] * 3 + [DataType(3), DataType(7)] + [0],
        # South
        [DataType(1), DataType(2)] + [0],
        # West
        [0] * 4 + [DataType(2)] + [0],
        # East
        [DataType(8), DataType(3)],
        # NW
        [],
        # NE
        [],
        # SE
        [],
        # SW
        [],
    ]

    data_out_msgs = [
        # North
        shiftData + [DataType(3), DataType(7)],
        # South
        shiftData + [0] * 4 + [DataType(8)] + [0] * 3,
        # West
        shiftData + [DataType(2), DataType(5)] + [0] * 6 + [DataType(6), DataType(14)],
        # East
        [],
        # NW
        [],
        # NE
        shiftData + [DataType(8), DataType(3)],
        # SE
        shiftData + [DataType(3), DataType(7)],
        # SW
        [],
    ]

    pred_in_rf_msgs = [ Bits1(1) ]

    th = TestHarness(
                    num_tile_inports,
                    num_tile_outports,
                    num_fu_inports,
                    num_fu_outports,
                    DataType,
                    TileBitstreamType,
                    OperationType,
                    RegAddrType,
                    PredRegAddrType,
                    tile_in_bitstream_msgs,
                    data_in_msgs,
                    data_out_msgs,
                    pred_in_rf_msgs,
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