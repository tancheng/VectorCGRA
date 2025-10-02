# STEP Imports
from ..controller.STEP_ControllerRTL import STEP_ControllerRTL
from ..controller.STEP_RegisterFileControllerRTL import STEP_RegisterFileControllerRTL
from ..mem.STEP_LD_ST.STEP_LoadStoreRTL import STEP_LoadStoreRTL
from ..tile.STEP_TileWrapperRTL import STEP_TileWrapperRTL
from ..tokenizer.STEP_TokenizerControllerRTL import STEP_TokenizerControllerRTL
from ..lib.basic.AxiInterface import SendAxiReadLoadAddrIfcRTL, SendAxiReadStoreAddrIfcRTL, \
                            RecvAxiLoadIfcRTL, RecvAxiStoreIfcRTL

# PyMtl3 Imports
from ..lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ..lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ..lib.cmd_type import *
from ..lib.opt_type import *
from ..lib.util.common import *

class STEP_CgraRTL(Component):
    def construct(s,
            # CPU Type
            CpuPktType,

            # Configuration Types
            CfgType,
            CfgBitstreamType,
            CfgMetadataType,
            CfgTokenizerType,
            TileBitstreamType,
            OperationType,

            # Data Type
            DataType,
            
            # Address Types
            RegAddrType,
            PredRegAddrType,

            # CGRA Parameters
            num_tile_cols,
            num_tile_rows,
            num_register_banks = 2,
            num_registers = 16,
            num_pred_registers = 16,
        ):
        
        # Default CGRA Parameters
        num_tiles = num_tile_cols * num_tile_rows
        num_tile_inports = 4
        num_tile_outports = 4
        num_fu_inports = 3
        num_fu_outports = 1
        num_rd_ports = num_tile_rows
        num_wr_ports = num_tile_rows
        num_ld_ports = num_tile_cols // 2
        num_st_ports = num_tile_cols // 2
        ld_st_queue_depth = 8
        num_tokens = ld_st_queue_depth
        max_delay = num_tiles
        num_taker_ports = num_rd_ports
        num_returner_ports = num_wr_ports + num_ld_ports + num_st_ports

        # Additional Type
        AxiAddrType = mk_bits( AXI_ADDR_BITWIDTH )

        # CGRA Top-Level IOs
        s.recv_from_cpu_pkt = RecvIfcRTL(CpuPktType)
        s.send_to_cpu_pkt = SendIfcRTL(CpuPktType)
        s.send_to_cpu_pkt_last = OutPort(Bits1)

        @update
        def update_last_pkt():
            s.send_to_cpu_pkt_last @= 0
            if s.send_to_cpu_pkt.val & (s.send_to_cpu_pkt.msg.cmd == CMD_COMPLETE):
                s.send_to_cpu_pkt_last @= 1

        # Instantiate Components
        s.core_controller = STEP_ControllerRTL(
            CpuPktType,
            CfgBitstreamType,
            CfgType,
            CfgMetadataType,
            CfgTokenizerType
        )

        s.rf_controller = STEP_RegisterFileControllerRTL(
            num_tiles,
            DataType,
            RegAddrType,
            PredRegAddrType,
            CfgMetadataType,
            num_register_banks,
            num_ld_ports,
            num_st_ports,
            num_rd_ports,
            num_wr_ports,
            num_registers,
            num_pred_registers,
        )
        
        s.ld_st_unit = STEP_LoadStoreRTL(
            DataType,
            num_ports=num_tile_cols // 2,
            queue_depth=ld_st_queue_depth
        )

        s.tile_fabric = STEP_TileWrapperRTL(
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

        s.tokenizer = STEP_TokenizerControllerRTL(
            CfgTokenizerType,
            num_rd_ports,
            num_wr_ports,
            num_ld_ports,
            num_st_ports,
            num_tokens,
            max_delay
        )

        ### Wire Connections ###
        ##### Core Controller Connections
        s.core_controller.recv_from_cpu_pkt //= s.recv_from_cpu_pkt # cpu -> core
        s.core_controller.send_to_cpu_pkt //= s.send_to_cpu_pkt # core -> cpu
        
        ##### Core Controller & Fabric Connections
        s.core_controller.send_cfg_to_tiles //= s.tile_fabric.recv_fabric_bitstream # core -> fabric

        ##### Core Controller & RF Controller Connections
        s.core_controller.send_cfg_to_rf //= s.rf_controller.recv_cfg_from_ctrl # core -> rf
        s.core_controller.rf_cfg_done //= s.rf_controller.cfg_done # rf -> core

        ##### RF Controller & Fabric Connections
        for i in range(num_tiles):
            s.rf_controller.send_tile_preds[i] //= s.tile_fabric.recv_from_rf_pred[i] # rf -> fabric
        for i in range(num_tile_rows):
            s.rf_controller.rd_data[i] //= s.tile_fabric.recv_west_data_port[i] # rf -> fabric
            s.rf_controller.wr_data[i] //= s.tile_fabric.send_east_data_port[i] # fabric -> rf
            s.rf_controller.recv_pred_port[i] //= s.tile_fabric.send_east_pred_port[i] # fabric -> rf
        
        ##### RF Controller & Load/Store Connections
        for i in range(num_tile_cols // 2):
            s.rf_controller.ld_enable[i]        //= s.ld_st_unit.ld_enable[i] # rf -> ld/st
            s.rf_controller.st_enable[i]        //= s.ld_st_unit.st_enable[i] # rf -> ld/st
            s.rf_controller.ld_data[i]          //= s.ld_st_unit.ld_ifc[i].o_data # ld/st -> rf
            s.rf_controller.ld_data_valid[i]    //= s.ld_st_unit.ld_ifc[i].o_done # ld/st -> rf
            s.rf_controller.ld_data_id[i]       //= s.ld_st_unit.ld_ifc[i].o_data_id # ld/st -> rf
        s.rf_controller.send_thread_count //= s.ld_st_unit.thread_count # rf -> ld/st
        s.rf_controller.ld_st_complete //= s.ld_st_unit.ld_st_complete # ld/st -> rf

        ##### Load/Store & Fabric Connections
        for i in range(num_tile_cols // 2):
            # TODO @darrenl make sure works for differently timed data and addr
            # Predicates
            s.ld_st_unit.ld_tile_pred[i] //= s.tile_fabric.send_north_pred_port[i*2] # fabric -> ld/st
            s.ld_st_unit.st_tile_pred[i] //= s.tile_fabric.send_south_pred_port[i*2] # fabric -> ld/st


            # Data and Control Store - SOUTH ONLY
            s.ld_st_unit.st_ifc[i].i_data //= s.tile_fabric.send_south_data_port[i*2+1] # fabric -> ld/st
            # s.ld_st_unit.st_ifc[i].o_rdy //= s.tile_fabric.send_south_data_port[i*2].rdy # ld/st -> fabric
            # s.ld_st_unit.st_ifc[i].o_rdy //= s.tile_fabric.send_south_data_port[i*2+1].rdy # ld/st -> fabric

        # Internal Ld/St Fabric Wire extension connections
        s.north_addr_wire = [Wire(AxiAddrType) for _ in range(num_ld_ports)]
        for i in range(num_ld_ports):
            # NORTH Load ONLY - Addr at Even tile columns
            s.north_addr_wire[i] //= s.ld_st_unit.ld_ifc[i].i_addr

        s.south_addr_wire = [Wire(AxiAddrType) for _ in range(num_st_ports)]
        for i in range(num_st_ports):
            # NORTH Load ONLY - Addr at Even tile columns
            s.south_addr_wire[i] //= s.ld_st_unit.st_ifc[i].i_addr
        
        # Load/Store & Fabric Update Connections
        @update
        def update_ld_st_fabric():
            for i in range(num_ld_ports):
                # NORTH Load ONLY - Addr at Even tile columns
                s.north_addr_wire[i] @= AxiAddrType(s.tile_fabric.send_north_data_port[i*2]) # ld/st -> fabric

                # SOUTH Store ONLY - Addr at Even tile columns, Data at Odd tile columns
                s.south_addr_wire[i] @= AxiAddrType(s.tile_fabric.send_south_data_port[i*2]) # ld/st -> fabric
        
        ##### Load/Store External Connections
        # Load Axis
        s.ld_axi = [SendAxiReadLoadAddrIfcRTL(DataType) for _ in range(num_ld_ports)]
        for i in range(num_ld_ports):
            s.ld_axi[i] //= s.ld_st_unit.ld_axi[i]
        # Store Axis
        s.st_axi = [SendAxiReadStoreAddrIfcRTL(DataType) for _ in range(num_st_ports)]
        for i in range(num_st_ports):
            s.st_axi[i] //= s.ld_st_unit.st_axi[i]

        ###### Tokenizer & Core Controller
        s.core_controller.send_cfg_to_tokenizer //= s.tokenizer.recv_cfg_from_ctrl

        ###### Tokenizer & Rf
        for i in range(num_taker_ports):
            s.tokenizer.token_take[i] //= s.rf_controller.tile_token_take[i] # rf -> tokenizer
            s.tokenizer.token_return[i] //= s.rf_controller.tile_token_return[i] # rf -> tokenizer [initial slots]
            s.tokenizer.token_shifter_out[i] //= s.rf_controller.tile_token_shifter_out[i] # tokenizer -> rf
            s.tokenizer.token_avail[i] //= s.rf_controller.tile_token_avail[i] # tokenizer -> rf
        
        ##### Tokenizer & Ld/St Connections
        for i in range(num_taker_ports, num_returner_ports - num_ld_ports):
            s.tokenizer.token_return[i] //= s.ld_st_unit.ld_token_return[i - num_taker_ports]
            s.tokenizer.token_return[i + num_ld_ports] //= s.ld_st_unit.st_token_return[i - num_taker_ports]

        for i in range(num_ld_ports):
            # Data and Control Load - North ONLY
            s.tokenizer.token_shifter_out[i + num_wr_ports] //= s.ld_st_unit.ld_ifc[i].i_req # tokenizer -> ld/st
            # s.ld_st_unit.ld_ifc[i].o_rdy //=  # fabric -> ld/st

            # Data and Control Store - SOUTH ONLY
            s.tokenizer.token_shifter_out[i + num_wr_ports + num_ld_ports] //= s.ld_st_unit.st_ifc[i].i_req # tokenizer -> ld/st

        #### Test Connections ###
        # TODO @darrenl to remove
        # Cfg Tests
        s.cc_cfg_to_tiles = OutPort(CfgBitstreamType)
        s.cc_cfg_to_tiles_val = OutPort(Bits1)
        s.cc_cfg_to_rf = OutPort(CfgMetadataType)
        s.cc_cfg_to_rf_val = OutPort(Bits1)
        s.cc_cfg_to_rf_rdy = OutPort(Bits1)

        s.cc_cfg_to_tiles //= s.core_controller.send_cfg_to_tiles.msg
        s.cc_cfg_to_tiles_val //= s.core_controller.send_cfg_to_tiles.val
        s.cc_cfg_to_rf //= s.core_controller.send_cfg_to_rf.msg
        s.cc_cfg_to_rf_val //= s.core_controller.send_cfg_to_rf.val
        s.cc_cfg_to_rf_rdy //= s.rf_controller.recv_cfg_from_ctrl.rdy

        
        # Ld St Test
        s.ld_st_complete = OutPort(Bits1)
        s.ld_st_complete //= s.ld_st_unit.ld_st_complete
        s.ld_complete = [OutPort(1) for _ in range(num_ld_ports)]
        s.st_complete = [OutPort(1) for _ in range(num_st_ports)]
        s.ld_pred_in = [OutPort(1) for _ in range(num_ld_ports)]
        for i in range(num_ld_ports):
            s.ld_complete[i] //= s.ld_st_unit.ld_complete[i]
            s.ld_pred_in[i] //= s.tile_fabric.send_north_pred_port[i*2]
        for i in range(num_st_ports):
            s.st_complete[i] //= s.ld_st_unit.st_complete[i]
        s.outstanding_reqs = [ OutPort( clog2(ld_st_queue_depth + 1) ) for _ in range(num_ld_ports) ]
        s.loads_in_tile     = [ OutPort( clog2(ld_st_queue_depth + 1) ) for _ in range(num_ld_ports) ]
        s.store_queue_rdy   = [ OutPort(1) for _ in range(num_ld_ports) ]
        s.outstanding_stores= [ OutPort( clog2(ld_st_queue_depth + 1) ) for _ in range(num_ld_ports) ]
        s.stores_in_tile    = [ OutPort( clog2(ld_st_queue_depth + 1) ) for _ in range(num_ld_ports) ]
        for i in range(num_ld_ports):
            s.outstanding_reqs[i] //= s.ld_st_unit.outstanding_reqs[i]
            s.loads_in_tile[i] //= s.ld_st_unit.loads_in_tile[i]
            s.store_queue_rdy[i] //= s.ld_st_unit.store_queue_rdy[i]
            s.outstanding_stores[i] //= s.ld_st_unit.outstanding_stores[i]
            s.stores_in_tile[i] //= s.ld_st_unit.stores_in_tile[i]
        s.recv_ld_st_thread_count = OutPort( clog2(MAX_THREAD_COUNT) )
        s.recv_ld_st_thread_count //= s.rf_controller.send_thread_count
        s.ld_tile_last_seen = [OutPort(1) for _ in range(num_ld_ports)]
        for i in range(num_ld_ports):
            s.ld_tile_last_seen[i] //= s.ld_st_unit.ld_tile_last_seen[i]
        s.st_i_req = [OutPort(1) for _ in range(num_st_ports)]
        s.st_i_data = [OutPort(DataType) for _ in range(num_st_ports)]
        s.st_i_addr = [OutPort(AxiAddrType) for _ in range(num_st_ports)]
        for i in range(num_st_ports):
            s.st_i_req[i] //= s.tokenizer.token_shifter_out[num_taker_ports + i] # fabric -> ld/st
            s.st_i_data[i] //= s.tile_fabric.send_south_data_port[i*2+1] # fabric -> ld/st
        @update
        def test_st_addr():
            for i in range(num_st_ports):
                s.st_i_addr[i] @= AxiAddrType(s.tile_fabric.send_south_data_port[i*2]) 

        # RF Controller Test
        s.rf_cfg_done = OutPort(Bits1)
        s.rf_cfg_done //= s.rf_controller.cfg_done
        s.rf_fabric_done = OutPort(Bits1)
        s.rf_fabric_done //= s.rf_controller.fabric_done
        s.rf_fabric_complete = OutPort(Bits1)
        s.rf_fabric_complete //= s.rf_controller.fabric_complete

        # RF & Fabric Test
        s.rf_to_fabric_msg = [ OutPort(DataType) for _ in range(num_rd_ports)]
        for i in range(num_rd_ports):
            s.rf_to_fabric_msg[i] //= s.rf_controller.rd_data[i]
        s.rf_from_fabric_msg = [ OutPort(DataType) for _ in range(num_wr_ports)]
        for i in range(num_wr_ports):
            s.rf_from_fabric_msg[i] //= s.tile_fabric.send_east_data_port[i]

        # Fabric Tests
        # s.tiles_in_pred_from_rf = [ OutPort(1) for _ in range(num_tiles) ]
        # for i in range(num_tiles):
        #     s.tiles_in_pred_from_rf[i] //= s.tile_fabric.recv_from_rf_pred[i]
        s.tiles_north_pred_out = [ OutPort(1) for _ in range(num_tile_cols) ]
        for i in range(num_tile_cols):
            s.tiles_north_pred_out[i] //= s.tile_fabric.send_north_pred_port[i]
        s.tiles_south_pred_out = [ OutPort(1) for _ in range(num_tile_cols) ]
        for i in range(num_tile_cols):
            s.tiles_south_pred_out[i] //= s.tile_fabric.send_south_pred_port[i]

        # Tokenizer Tests
        s.tokenizer_shifter_out = [ OutPort(1) for _ in range(num_returner_ports) ]
        s.tokenizer_count = [ OutPort(mk_bits(clog2(num_tokens + 1))) for _ in range(num_returner_ports) ]
        for i in range(num_returner_ports):
            s.tokenizer_shifter_out[i] //= s.tokenizer.token_shifter_out[i]
            s.tokenizer_count[i] //= s.tokenizer.tokenizer_count[i]

        s.tokenizer_token_take = [ OutPort(1) for _ in range(num_taker_ports) ]
        for i in range(num_taker_ports):
            s.tokenizer_token_take[i] //= s.rf_controller.tile_token_take[i]