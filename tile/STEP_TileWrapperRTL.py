"""
=========================================================================
CgraRTL.py
=========================================================================

Author : Cheng Tan
  Date : Dec 22, 2024
"""

from ..fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from ..fu.single.AdderRTL import AdderRTL
from ..fu.single.BranchRTL import BranchRTL
from ..fu.single.CompRTL import CompRTL
from ..fu.single.MemUnitRTL import MemUnitRTL
from ..fu.single.MulRTL import MulRTL
from ..fu.single.PhiRTL import PhiRTL
from ..lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ..lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ..lib.opt_type import *
from ..lib.util.common import *
from .STEP_TileRTL import STEP_TileRTL
from .STEP_ScanChainRTL import STEP_ScanChainRTL

class STEP_TileWrapperRTL(Component):

    def construct(s,
                    num_tile_cols,
                    num_tile_rows,
                    num_tile_inports,
                    num_tile_outports,
                    num_fu_inports,
                    num_fu_outports,
                    DataType,
                    TileBitstreamType,
                    BitStreamType,
                    OperationType,
                    RegAddrType,
                    PredRegAddrType,
                    debug = False,
                    enable_double_buffering = False
                    ):
        TileIdType = mk_bits(clog2(num_tile_cols * num_tile_rows))
        TileCountType = mk_bits(clog2(num_tile_cols * num_tile_rows + 1))
        assert(num_tile_inports == num_tile_outports)
        assert(num_tile_inports in [4,8])
        # Tile ID
        # 0 1
        # 2 3
        # 
        # Current Architecture only has IO ports to Tiles on the East Side Only
        # in order to communicate with register file
        s.recv_west_data_port = [ InPort(DataType) for _ in range(num_tile_rows * 2) ]
        s.send_west_data_port = [ OutPort(DataType) for _ in range(num_tile_rows) ]
        s.recv_east_data_port = [ InPort(DataType) for _ in range(num_tile_rows * 2) ]
        s.send_east_data_port = [ OutPort(DataType) for _ in range(num_tile_rows) ]
        s.send_west_pred_port = [ OutPort(1) for _ in range(num_tile_rows) ]
        s.send_east_pred_port = [ OutPort(1) for _ in range(num_tile_rows) ]
        
        # South ST Connections
        s.send_south_data_port = [ OutPort(DataType) for _ in range(num_tile_cols) ]
        s.send_south_pred_port = [ OutPort(1) for _ in range(num_tile_cols) ]

        # North LD Connections
        s.send_north_data_port = [ OutPort(DataType) for _ in range(num_tile_cols) ]
        s.send_north_pred_port = [ OutPort(1) for _ in range(num_tile_cols) ]

        # Predicate
        num_tiles = num_tile_cols * num_tile_rows
        s.recv_from_rf_pred = [ InPort(1) for _ in range(num_tiles) ]

        # Bistream IO
        s.recv_tile_bitstreams = RecvIfcRTL(TileBitstreamType)
        s.cfg_bank_commit = InPort(1)
        s.cfg_packets_applied = OutPort(TileCountType)
        s.cfg_active_sel_w = Wire(1)
        s.cfg_load_sel_w = Wire(1)
        s.cfg_swap_w = Wire(1)
        if enable_double_buffering:
            s.cfg_active_sel = InPort(1)
            s.cfg_load_sel = InPort(1)
            s.cfg_swap = InPort(1)
            @update
            def cfg_select_wires():
                s.cfg_active_sel_w @= s.cfg_active_sel
                s.cfg_load_sel_w @= s.cfg_load_sel
                s.cfg_swap_w @= s.cfg_swap
        else:
            @update
            def cfg_select_wires():
                s.cfg_active_sel_w @= Bits1(0)
                s.cfg_load_sel_w @= Bits1(0)
                s.cfg_swap_w @= Bits1(0)

        # Fabric Declaration
        s.tiles = [[STEP_TileRTL(
                                id=i*num_tile_cols + j,
                                num_tile_inports=num_tile_inports,
                                num_tile_outports=num_tile_outports,
                                num_fu_inports=num_fu_inports,
                                num_fu_outports=num_fu_outports,
                                DataType=DataType,
                                TileBitstreamType=TileBitstreamType,
                                OperationType=OperationType,
                                RegAddrType=RegAddrType,
                                PredRegAddrType=PredRegAddrType,
                                debug=debug,
                                enable_double_buffering=enable_double_buffering
                                ) for j in range(num_tile_cols)] for i in range(num_tile_rows)]
        
        # Scan Chain Declaration
        s.scan_chain = STEP_ScanChainRTL(TileBitstreamType, num_tiles)
        
        #### TEST CONNECTIONS delete me TODO: @darrenl
        if debug:
            check_row = 1
            check_col = 3
            check_tile_id = check_row * num_tile_cols + check_col
            s.fu_in = [ OutPort(DataType) for _ in range(num_fu_inports) ]
            s.fu_out = [ OutPort(DataType) for _ in range(num_fu_outports) ]
            
            s.tile_bitstream_cmd = OutPort(OperationType)
            s.tile_bitstream_cmd //= s.tiles[check_row][check_col].tile_bitstream.opt_type
            s.tile_bitstream_in_route = OutPort(Bits4)
            s.tile_bitstream_in_route //= (s.tiles[check_row][check_col].tile_bitstream.tile_in_route[0])
            s.tile_in_test = [ OutPort(DataType) for _ in range(num_tile_inports) ]
            s.tile_new_bitstream_ingested = OutPort(1)
            s.tile_new_bitstream_ingested //= s.tiles[check_row][check_col].ingest_new_bitstream
            s.tile_id_matched = OutPort(1)
            s.tile_id_matched //= s.tiles[check_row][check_col].id_matched
            s.tile_id_received = OutPort(TileIdType)
            s.tile_id_received //= s.tiles[check_row][check_col].id_received

            # Snake like scanchain
            # IE
            #  0 1 2
            #  5 4 3
            #  6 7 8
            scan_col = check_col if check_row % 2 == 0 else num_tile_cols - check_col - 1
            s.tile_new_bitstream_tile_id = OutPort(TileIdType)
            s.tile_new_bitstream_tile_id //= s.scan_chain.scan_pts[check_row*num_tile_rows + scan_col].tile_id
            s.tile_new_bitstream_val = OutPort(1)
            s.tile_new_bitstream_val //= s.scan_chain.scan_pts_val[check_row*num_tile_rows + scan_col]
            s.tile_wrapper_id_matched = OutPort(1)
            @update
            def check_id():
                s.tile_wrapper_id_matched @= s.scan_chain.scan_pts[check_row*num_tile_rows + scan_col].tile_id == check_tile_id

            # More tests
            s.tile_pred_in = [OutPort(1) for _ in range(num_tile_outports)]
            for i in range(num_fu_inports):
                s.fu_in[i] //= s.tiles[check_row][check_col].fu_in[i]
            for i in range(num_fu_outports):
                s.fu_out[i] //= s.tiles[check_row][check_col].fu_out[i]
            for i in range(num_tile_inports):
                s.tile_in_test[i] //= s.tiles[check_row][check_col].tile_in_test[i]
                s.tile_pred_in[i] //= s.tiles[check_row][check_col].tile_input_pred_port[i]
            
            s.tile_data_out = [OutPort(DataType) for _ in range(num_tile_outports)]
            for i in range(num_tile_outports):
                s.tile_data_out[i] //= s.tiles[check_row][check_col].tile_out_data_port[i]
            s.tile_pred_out = [OutPort(1) for _ in range(num_tile_outports)]
            for i in range(num_tile_outports):
                s.tile_pred_out[i] //= s.tiles[check_row][check_col].tile_out_pred_port[i]
        #####

        # Bitstream Scan Chain Connection
        for i in range(num_tile_rows):
            sj = 0 if i % 2 == 0 else num_tile_cols - 1
            ej = num_tile_cols if i % 2 == 0 else -1
            stride = 1 if i % 2 == 0 else -1
            scan_col = 0
            for j in range(sj, ej, stride):
                s.scan_chain.scan_pts[i*num_tile_cols + scan_col] //= s.tiles[i][j].recv_tile_bitstream.msg
                s.scan_chain.scan_pts_val[i*num_tile_cols + scan_col] //= s.tiles[i][j].recv_tile_bitstream.val
                scan_col += 1
        s.scan_chain.scan_in //= s.recv_tile_bitstreams

        @update
        def count_cfg_packet_applies():
            applied = TileCountType(0)
            for row in range(num_tile_rows):
                for col in range(num_tile_cols):
                    if s.tiles[row][col].cfg_packet_applied:
                        applied = applied + TileCountType(1)
            s.cfg_packets_applied @= applied
        
        # Connect RF Predicates
        for i in range(num_tile_rows):
            for j in range(num_tile_cols):
                s.tiles[i][j].tile_in_pred_port_rf //= s.recv_from_rf_pred[i * num_tile_cols + j]
                if enable_double_buffering:
                    s.tiles[i][j].cfg_active_sel //= s.cfg_active_sel_w
                    s.tiles[i][j].cfg_load_sel //= s.cfg_load_sel_w
                    s.tiles[i][j].cfg_swap //= s.cfg_swap_w
        
        # Connect Fabric Bitstream Rst
        for i in range(num_tile_rows):
            for j in range(num_tile_cols):
                s.tiles[i][j].cfg_bank_commit //= s.cfg_bank_commit

        # Fabric Internal Connections
        for i in range(num_tile_rows):
            for j in range(num_tile_cols):
                if i > 0:
                    # North Connections
                    s.tiles[i][j].tile_in_data_port[PORT_NORTH] //= s.tiles[i-1][j].tile_out_data_port[PORT_SOUTH]
                    s.tiles[i][j].tile_out_data_port[PORT_NORTH] //= s.tiles[i-1][j].tile_in_data_port[PORT_SOUTH]
                    s.tiles[i][j].tile_in_pred_port[PORT_NORTH] //= s.tiles[i-1][j].tile_out_pred_port[PORT_SOUTH]
                    s.tiles[i][j].tile_out_pred_port[PORT_NORTH] //= s.tiles[i-1][j].tile_in_pred_port[PORT_SOUTH]
                    if (num_tile_inports == 8):
                        # North West Connections
                        if j > 0:
                            s.tiles[i][j].tile_in_data_port[PORT_NORTHWEST] //= s.tiles[i-1][j-1].tile_out_data_port[PORT_SOUTHEAST]
                            s.tiles[i][j].tile_out_data_port[PORT_NORTHWEST] //= s.tiles[i-1][j-1].tile_in_data_port[PORT_SOUTHEAST]
                            s.tiles[i][j].tile_in_pred_port[PORT_NORTHWEST] //= s.tiles[i-1][j-1].tile_out_pred_port[PORT_SOUTHEAST]
                            s.tiles[i][j].tile_out_pred_port[PORT_NORTHWEST] //= s.tiles[i-1][j-1].tile_in_pred_port[PORT_SOUTHEAST]
                        # North East Connections
                        if j < num_tile_cols - 1:
                            s.tiles[i][j].tile_in_data_port[PORT_NORTHEAST] //= s.tiles[i-1][j+1].tile_out_data_port[PORT_SOUTHWEST]
                            s.tiles[i][j].tile_out_data_port[PORT_NORTHEAST] //= s.tiles[i-1][j+1].tile_in_data_port[PORT_SOUTHWEST]
                            s.tiles[i][j].tile_in_pred_port[PORT_NORTHEAST] //= s.tiles[i-1][j+1].tile_out_pred_port[PORT_SOUTHWEST]
                            s.tiles[i][j].tile_out_pred_port[PORT_NORTHEAST] //= s.tiles[i-1][j+1].tile_in_pred_port[PORT_SOUTHWEST]
                        if i == num_tile_rows - 1:
                            # Tie off Diagonal Connections
                            if (num_tile_inports == 8):
                                if j > 0:
                                    # South West tie off
                                    s.tiles[i][j].tile_in_data_port[PORT_SOUTHWEST] //= s.recv_west_data_port[2*i+1]
                                    s.tiles[i][j].tile_in_pred_port[PORT_SOUTHWEST] //= 1
                                if j < num_tile_cols - 1:
                                    # South East tie off
                                    s.tiles[i][j].tile_in_data_port[PORT_SOUTHEAST] //= s.recv_east_data_port[2*i+1]
                                    s.tiles[i][j].tile_in_pred_port[PORT_SOUTHEAST] //= 1
                else:
                    # Connect North Ports to LD
                    s.tiles[i][j].tile_in_data_port[PORT_NORTH] //= DataType()
                    s.tiles[i][j].tile_out_data_port[PORT_NORTH] //= s.send_north_data_port[j]
                    s.tiles[i][j].tile_in_pred_port[PORT_NORTH] //= 0
                    s.tiles[i][j].tile_out_pred_port[PORT_NORTH] //= s.send_north_pred_port[j]
                    # Tie off Diagonal Connections
                    if (num_tile_inports == 8):
                        if j > 0:
                            # North West tie off
                            s.tiles[i][j].tile_in_data_port[PORT_NORTHWEST] //= DataType()
                            s.tiles[i][j].tile_in_pred_port[PORT_NORTHWEST] //= 0
                        if j < num_tile_cols - 1:
                            # North East tie off
                            s.tiles[i][j].tile_in_data_port[PORT_NORTHEAST] //= DataType()
                            s.tiles[i][j].tile_in_pred_port[PORT_NORTHEAST] //= 0

                if j > 0:
                    # West Connections
                    s.tiles[i][j].tile_in_data_port[PORT_WEST] //= s.tiles[i][j-1].tile_out_data_port[PORT_EAST]
                    s.tiles[i][j].tile_out_data_port[PORT_WEST] //= s.tiles[i][j-1].tile_in_data_port[PORT_EAST]
                    s.tiles[i][j].tile_in_pred_port[PORT_WEST] //= s.tiles[i][j-1].tile_out_pred_port[PORT_EAST]
                    s.tiles[i][j].tile_out_pred_port[PORT_WEST] //= s.tiles[i][j-1].tile_in_pred_port[PORT_EAST]
                else:
                    s.tiles[i][j].tile_in_data_port[PORT_WEST] //= s.recv_west_data_port[2*i]
                    s.tiles[i][j].tile_out_data_port[PORT_WEST] //= s.send_west_data_port[i]
                    s.tiles[i][j].tile_out_pred_port[PORT_WEST] //= s.send_west_pred_port[i]
                    # Pred in will always be 1 as to fire. If predicated, will take its own rf predication
                    s.tiles[i][j].tile_in_pred_port[PORT_WEST] //= 1
                    # Tie off Diagonal Connections
                    if num_tile_inports == 8:# and i > 0 and i < num_tile_rows - 1:
                        # North West tie off
                        s.tiles[i][j].tile_in_data_port[PORT_NORTHWEST] //= DataType()
                        s.tiles[i][j].tile_in_pred_port[PORT_NORTHWEST] //= 0
                        # South West tie off
                        s.tiles[i][j].tile_in_data_port[PORT_SOUTHWEST] //= s.recv_west_data_port[2*i+1]
                        s.tiles[i][j].tile_in_pred_port[PORT_SOUTHWEST] //= 1

                # Connect East Ports to fabric I/O
                if j == num_tile_cols - 1:
                    s.tiles[i][j].tile_in_data_port[PORT_EAST] //= s.recv_east_data_port[2*i]
                    s.tiles[i][j].tile_in_pred_port[PORT_EAST] //= 1
                    s.tiles[i][j].tile_out_data_port[PORT_EAST] //= s.send_east_data_port[i]
                    s.tiles[i][j].tile_out_pred_port[PORT_EAST] //= s.send_east_pred_port[i]
                    # Tie off Diagonal Connections
                    if num_tile_inports == 8: # and i > 0 and i < num_tile_rows - 1:
                        # North East tie off
                        s.tiles[i][j].tile_in_data_port[PORT_NORTHEAST] //= DataType()
                        s.tiles[i][j].tile_in_pred_port[PORT_NORTHEAST] //= 0
                        # South East tie off
                        s.tiles[i][j].tile_in_data_port[PORT_SOUTHEAST] //= s.recv_east_data_port[2*i+1]
                        s.tiles[i][j].tile_in_pred_port[PORT_SOUTHEAST] //= 1
                
                # Connect South Ports to Ld/St Unit
                if i == num_tile_rows - 1:
                    s.tiles[i][j].tile_in_data_port[PORT_SOUTH] //= DataType()
                    s.tiles[i][j].tile_out_data_port[PORT_SOUTH] //= s.send_south_data_port[j]
                    s.tiles[i][j].tile_in_pred_port[PORT_SOUTH] //= 0
                    s.tiles[i][j].tile_out_pred_port[PORT_SOUTH] //= s.send_south_pred_port[j]

        # Connect Tile Bitstreams    
        # for i in range(num_tile_rows):
        #     for j in range(num_tile_cols):
        #         s.tiles[i][j].recv_tile_bitstream.msg //= s.recv_tile_bitstreams[i * num_tile_cols + j]
        #         s.tiles[i][j].recv_tile_bitstream.val //= s.recv_tile_bitstreams_val
        #         s.tiles[i][j].tile_in_pred_port_rf //= s.recv_from_rf_pred[i * num_tile_cols + j]
