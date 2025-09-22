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
from ..tile.STEP_TileRTL import STEP_TileRTL


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
                    ):

        # Tile ID
        # 0 1
        # 2 3
        # 
        # Current Architecture only has IO ports to Tiles on the East Side Only
        # in order to communicate with register file
        s.recv_east_data_port = [ RecvIfcRTL(DataType) for _ in range(num_tile_rows) ]
        s.send_east_data_port = [ SendIfcRTL(DataType) for _ in range(num_tile_rows) ]
        s.send_east_pred_port = [ OutPort(Bits1) for _ in range(num_tile_rows) ]
        
        # South ST Connections
        s.send_south_data_port = [ SendIfcRTL(DataType) for _ in range(num_tile_cols) ]
        s.send_south_pred_port = [ OutPort(Bits1) for _ in range(num_tile_cols) ]

        # North LD Connections
        s.send_north_data_port = [ SendIfcRTL(DataType) for _ in range(num_tile_cols) ]
        s.send_north_pred_port = [ OutPort(Bits1) for _ in range(num_tile_cols) ]

        # Bistream IO
        s.recv_fabric_bitstream = RecvIfcRTL(BitStreamType)
        s.bitstream_rdy = Wire(Bits1)

        # Predicate
        num_tiles = num_tile_cols * num_tile_rows
        s.recv_from_rf_pred = [ InPort(Bits1) for _ in range(num_tiles) ]

        # Fabric Declaration
        s.tiles = [[STEP_TileRTL(num_tile_inports,
                                num_tile_outports,
                                num_fu_inports,
                                num_fu_outports,
                                DataType,
                                TileBitstreamType,
                                OperationType,
                                RegAddrType,
                                PredRegAddrType,
                                ) for _ in range(num_tile_cols)] for _ in range(num_tile_rows)]
        
        #### TEST CONNECTIONS delete me TODO: @darrenl
        s.fu_in = [ OutPort(DataType) for _ in range(num_fu_inports) ]
        s.fu_out = [ OutPort(DataType) for _ in range(num_fu_outports) ]
        s.ready_to_fire = OutPort(Bits1)
        s.in_buffer = [ OutPort(DataType) for _ in range(num_tile_inports) ]
        s.in_buffer_val = [ OutPort(Bits1) for _ in range(num_tile_inports) ]
        DirectionType = mk_bits( clog2(num_tile_inports + 1))
        s.should_forward = OutPort(DirectionType)
        
        s.tile_bitstream_cmd = OutPort(OperationType)
        s.tile_bitstream_cmd //= s.tiles[0][1].tile_bitstream.opt_type
        s.tile_bitstream_loc = OutPort(Bits3)
        s.tile_bitstream_loc //= (s.tiles[0][1].tile_bitstream.tile_in_route[0])
        s.tile_in_test = [ OutPort(DataType) for _ in range(num_tile_inports) ]

        s.tiles_in_pred_from_rf = [OutPort(1) for _ in range(num_tiles)]
        s.tiles_in_pred_val = [OutPort(1) for _ in range(num_tiles)]
        for i in range(num_tile_rows):
            for j in range(num_tile_cols):
                s.tiles[i][j].tile_in_pred_port_rf_buffer //= s.tiles_in_pred_from_rf[i * num_tile_cols + j]
                s.tiles[i][j].pred_in_val //= s.tiles_in_pred_val[i * num_tile_cols + j]

        s.ready_to_fire //= s.tiles[0][1].ready_to_fire
        s.should_forward //= s.tiles[0][1].should_forward
        for i in range(num_fu_inports):
            s.fu_in[i] //= s.tiles[0][1].fu_in[i]
        for i in range(num_fu_outports):
            s.fu_out[i] //= s.tiles[0][1].fu_out[i]
        for i in range(num_tile_inports):
            s.in_buffer[i] //= s.tiles[0][1].in_buffer[i]
            s.in_buffer_val[i] //= s.tiles[0][1].in_buffer_val[i]
            s.tile_in_test[i] //= s.tiles[0][1].tile_in_test[i]
        
        s.tile_pred_out_test = OutPort(1)
        s.tile_pred_out_test //= s.tiles[0][3].tile_out_pred_port[PORT_WEST]
        
        #####


        for i in range(num_tile_rows):
            for j in range(num_tile_cols):
                # North Connections
                if i > 0:
                    s.tiles[i][j].tile_in_data_port[PORT_NORTH] //= s.tiles[i-1][j].tile_out_data_port[PORT_SOUTH]
                    s.tiles[i][j].tile_out_data_port[PORT_NORTH] //= s.tiles[i-1][j].tile_in_data_port[PORT_SOUTH]
                    s.tiles[i][j].tile_in_pred_port[PORT_NORTH] //= s.tiles[i-1][j].tile_out_pred_port[PORT_SOUTH]
                    s.tiles[i][j].tile_out_pred_port[PORT_NORTH] //= s.tiles[i-1][j].tile_in_pred_port[PORT_SOUTH]
                else:
                    # Connect North Ports to LD
                    s.tiles[i][j].tile_in_data_port[PORT_NORTH].msg //= DataType()
                    s.tiles[i][j].tile_in_data_port[PORT_NORTH].val //= 0
                    s.tiles[i][j].tile_out_data_port[PORT_NORTH] //= s.send_north_data_port[j]
                    s.tiles[i][j].tile_in_pred_port[PORT_NORTH] //= 0
                    s.tiles[i][j].tile_out_pred_port[PORT_NORTH] //= s.send_north_pred_port[j]

                if j > 0:
                    s.tiles[i][j].tile_in_data_port[PORT_WEST] //= s.tiles[i][j-1].tile_out_data_port[PORT_EAST]
                    s.tiles[i][j].tile_out_data_port[PORT_WEST] //= s.tiles[i][j-1].tile_in_data_port[PORT_EAST]
                    s.tiles[i][j].tile_in_pred_port[PORT_WEST] //= s.tiles[i][j-1].tile_out_pred_port[PORT_EAST]
                    s.tiles[i][j].tile_out_pred_port[PORT_WEST] //= s.tiles[i][j-1].tile_in_pred_port[PORT_EAST]
                else:
                    s.tiles[i][j].tile_in_data_port[PORT_WEST].msg //= DataType()
                    s.tiles[i][j].tile_in_data_port[PORT_WEST].val //= 0
                    s.tiles[i][j].tile_out_data_port[PORT_WEST].rdy //= 0
                    s.tiles[i][j].tile_in_pred_port[PORT_WEST] //= 0

                # Connect East Ports to fabric I/O
                if j == num_tile_cols - 1:
                    s.tiles[i][j].tile_in_data_port[PORT_EAST] //= s.recv_east_data_port[i]
                    s.tiles[i][j].tile_out_data_port[PORT_EAST] //= s.send_east_data_port[i]
                    # Pred in will always be 1 as to fire. If predicated, will take its own rf predication
                    s.tiles[i][j].tile_in_pred_port[PORT_EAST] //= s.recv_east_data_port[i].val
                    s.tiles[i][j].tile_out_pred_port[PORT_EAST] //= s.send_east_pred_port[i]
                
                # Connect South Ports to Ld/St Unit
                if i == num_tile_rows - 1:
                    s.tiles[i][j].tile_in_data_port[PORT_SOUTH].msg //= DataType()
                    s.tiles[i][j].tile_in_data_port[PORT_SOUTH].val //= 0
                    s.tiles[i][j].tile_out_data_port[PORT_SOUTH] //= s.send_south_data_port[j]
                    s.tiles[i][j].tile_in_pred_port[PORT_SOUTH] //= 0
                    s.tiles[i][j].tile_out_pred_port[PORT_SOUTH] //= s.send_south_pred_port[j]

        # Connect Tile Bitstreams    
        for i in range(num_tile_rows):
            for j in range(num_tile_cols):
                s.tiles[i][j].recv_tile_bitstream.msg //= s.recv_fabric_bitstream.msg.bitstream[i * num_tile_cols + j]
                s.tiles[i][j].recv_tile_bitstream.val //= s.recv_fabric_bitstream.val
                s.tiles[i][j].tile_in_pred_port_rf //= s.recv_from_rf_pred[i * num_tile_cols + j]
        
        # Connect Fabric Bitstream Readiness
        @update
        def update_bitstream_readiness():
            bitstream_rdy @= 1
            for i in range(num_tile_rows):
                for j in range(num_tile_cols):
                    bitstream_rdy = bitstream_rdy & s.tiles[i][j].recv_tile_bitstream.rdy
            s.recv_fabric_bitstream.rdy @= bitstream_rdy