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
            cgra_def,
            # Top Level Pkt Types
            CfgMetadataType,
            CfgBitstreamType,

            # Configuration Types
            CfgTokenizerType,
            TileBitstreamType,
            OperationType,

            # Data Type
            DataType,
            
            # Address Types
            RegAddrType,
            PredRegAddrType,

            # CGRA Parameters
            num_tile_cols = 4,
            num_tile_rows = 4,
            num_register_banks = 2,
            num_registers = 16,
            num_pred_registers = 16,
            debug = True
        ):
        # Validation Checks
        ld_st_locs = [1,0,0,1]
        if cgra_def['ld_locs'] != ld_st_locs or cgra_def['st_locs'] != ld_st_locs:
            raise NotImplementedError(f"Only support ld/st port locations {ld_st_locs} for now, but got ld: {cgra_def['ld_locs']} and st: {cgra_def['st_locs']}")
        
        # Default CGRA Parameters
        num_tiles = num_tile_cols * num_tile_rows
        num_tile_inports = 8
        num_tile_outports = 8
        num_fu_inports = 3
        num_fu_outports = 1
        num_rd_ports = num_tile_rows * 2 * 2
        num_wr_ports = num_tile_rows * 2
        num_ld_ports = num_tile_cols // 2
        num_st_ports = num_tile_cols // 2
        ld_st_queue_depth = 8
        num_tokens = ld_st_queue_depth
        max_delay = num_tiles
        num_taker_ports = num_rd_ports
        num_returner_ports = num_wr_ports + num_ld_ports + num_st_ports

        # Additional Type
        AxiAddrType = mk_bits( AXI_ADDR_BITWIDTH )
        BitstreamAddrType = mk_bits(clog2(MAX_BITSTREAM_COUNT))
        TileCountType = mk_bits(clog2(num_tiles + 1))

        # CGRA Top-Level IOs
        s.recv_from_cpu_bitstream_pkt = RecvIfcRTL(TileBitstreamType)
        s.recv_from_cpu_metadata_pkt = RecvIfcRTL(CfgMetadataType)
        s.send_to_cpu_done = OutPort(Bits1)
        s.pc_req_trigger = OutPort(Bits1)
        s.pc_req_trigger_count = OutPort(TileCountType)
        s.pc_req_trigger_complete = InPort(1)
        s.pc_req = OutPort(BitstreamAddrType)

        s.ld_axi = [SendAxiReadLoadAddrIfcRTL(DataType) for _ in range(num_ld_ports)]
        s.st_axi = [SendAxiReadStoreAddrIfcRTL(DataType) for _ in range(num_st_ports)]

        # Instantiate Components
        s.core_controller = STEP_ControllerRTL(
            CfgBitstreamType,
            CfgMetadataType,
            CfgTokenizerType,
            TileBitstreamType,
            num_tiles,
            num_pred_registers,
            debug
        )

        s.rf_controller = STEP_RegisterFileControllerRTL(
            num_tiles,
            DataType,
            RegAddrType,
            PredRegAddrType,
            CfgMetadataType,
            num_ld_ports,
            num_st_ports,
            num_register_banks,
            num_rd_ports,
            num_wr_ports,
            num_registers,
            num_pred_registers,
            True,
            debug,
        )
        
        s.ld_st_unit = STEP_LoadStoreRTL(
            DataType,
            num_ports=num_tile_cols // 2,
            queue_depth=ld_st_queue_depth,
            debug=debug
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
            debug,
            True,
        )

        s.tokenizer = STEP_TokenizerControllerRTL(
            CfgTokenizerType,
            num_rd_ports,
            num_wr_ports,
            num_ld_ports,
            num_st_ports,
            num_tokens,
            max_delay,
            True,
        )

        ### Wire Connections ###
        if debug:
            s.cfg_active_sel = OutPort(Bits1)
            s.cfg_load_sel = OutPort(Bits1)
            s.cfg_swap = OutPort(Bits1)
            s.cfg_relaunch = OutPort(Bits1)
        else:
            s.cfg_active_sel = Wire(Bits1)
            s.cfg_load_sel = OutPort(Bits1)
            s.cfg_swap = Wire(Bits1)
            s.cfg_relaunch = Wire(Bits1)
        ##### Core Controller Connections
        s.core_controller.recv_from_cpu_bitstream_pkt //= s.recv_from_cpu_bitstream_pkt
        s.core_controller.recv_from_cpu_metadata_pkt //= s.recv_from_cpu_metadata_pkt # cpu -> core
        s.core_controller.send_to_cpu_done //= s.send_to_cpu_done # core -> cpu
        s.core_controller.pc_req_trigger //= s.pc_req_trigger # core -> cpu
        s.core_controller.pc_req //= s.pc_req # core -> cpu
        s.core_controller.pc_req_trigger_count //= s.pc_req_trigger_count # core -> cpu
        s.core_controller.pc_req_trigger_complete //= s.pc_req_trigger_complete # core -> cpu
        s.cfg_active_sel //= s.core_controller.cfg_active_sel
        s.cfg_load_sel //= s.core_controller.cfg_load_sel
        s.cfg_swap //= s.core_controller.cfg_swap
        s.cfg_relaunch //= s.core_controller.cfg_relaunch
        s.cfg_bank_commit = Wire(1)
        s.cfg_bank_commit //= s.core_controller.cfg_bank_commit
        
        ##### Core Controller & Fabric Connections
        s.core_controller.send_cfg_to_tiles //= s.tile_fabric.recv_tile_bitstreams # core -> fabric
        s.core_controller.fabric_cfg_packets_applied //= s.tile_fabric.cfg_packets_applied
        s.tile_fabric.cfg_active_sel //= s.cfg_active_sel
        s.tile_fabric.cfg_load_sel //= s.cfg_load_sel
        s.tile_fabric.cfg_swap //= s.cfg_swap
        s.cfg_bank_commit //= s.tile_fabric.cfg_bank_commit # core -> fabric

        ##### Core Controller & RF Controller Connections
        s.core_controller.send_cfg_to_rf //= s.rf_controller.recv_cfg_from_ctrl # core -> rf
        s.core_controller.send_cfg_to_rf_thread_mask //= s.rf_controller.recv_cfg_thread_mask
        s.core_controller.rf_cfg_done //= s.rf_controller.cfg_done # rf -> core
        s.core_controller.rf_cfg_issue_ready //= s.rf_controller.cfg_issue_ready # rf -> core
        s.core_controller.rf_dep_mode //= s.rf_controller.dep_mode_out # rf -> core
        s.rf_controller.cfg_active_sel //= s.cfg_active_sel
        s.rf_controller.cfg_load_sel //= s.cfg_load_sel
        s.rf_controller.cfg_swap //= s.cfg_swap
        s.rf_controller.cfg_dep_start //= s.core_controller.rf_dep_start
        for i in range(num_pred_registers):
            s.core_controller.pred_any_true[i] //= s.rf_controller.pred_any_true[i]
            s.core_controller.pred_any_false[i] //= s.rf_controller.pred_any_false[i]
            s.core_controller.pred_complete[i] //= s.rf_controller.pred_complete[i]
            s.core_controller.pred_true_count[i] //= s.rf_controller.pred_true_count[i]
            s.core_controller.pred_false_count[i] //= s.rf_controller.pred_false_count[i]
            s.core_controller.pred_true_mask[i] //= s.rf_controller.pred_true_mask[i]
            s.core_controller.pred_false_mask[i] //= s.rf_controller.pred_false_mask[i]

        ##### RF Controller & Fabric Connections
        for i in range(num_tiles):
            s.rf_controller.send_tile_preds[i] //= s.tile_fabric.recv_from_rf_pred[i] # rf -> fabric
        for i in range(num_tile_rows):
            rd_base_idx = 4 * i
            # Keep a uniform RF read-port mapping for every row:
            # west ports = base, base+1; east ports = base+2, base+3.
            s.rf_controller.rd_data[rd_base_idx]   //= s.tile_fabric.recv_west_data_port[2*i] # rf -> fabric
            s.rf_controller.rd_data[rd_base_idx+1] //= s.tile_fabric.recv_west_data_port[2*i+1] # rf -> fabric
            s.rf_controller.rd_data[rd_base_idx+2] //= s.tile_fabric.recv_east_data_port[2*i] # rf -> fabric
            s.rf_controller.rd_data[rd_base_idx+3] //= s.tile_fabric.recv_east_data_port[2*i+1] # rf -> fabric
            s.rf_controller.wr_data[2*i] //= s.tile_fabric.send_west_data_port[i] # fabric -> rf
            s.rf_controller.wr_data[2*i+1] //= s.tile_fabric.send_east_data_port[i] # fabric -> rf
            s.rf_controller.recv_pred_port[2*i] //= s.tile_fabric.send_west_pred_port[i] # fabric -> rf
            s.rf_controller.recv_pred_port[2*i+1] //= s.tile_fabric.send_east_pred_port[i] # fabric -> rf
        
        ##### RF Controller & Load/Store Connections
        s.ld_req_accepted = [Wire(Bits1) for _ in range(num_ld_ports)]
        s.st_req_accepted = [Wire(Bits1) for _ in range(num_st_ports)]
        for i in range(num_tile_cols // 2):
            s.rf_controller.ld_enable[i]        //= s.ld_st_unit.ld_enable[i] # rf -> ld/st
            s.rf_controller.st_enable[i]        //= s.ld_st_unit.st_enable[i] # rf -> ld/st
            s.rf_controller.ld_issue_tid[i]     //= s.ld_st_unit.ld_issue_tid[i] # rf -> ld/st
            s.rf_controller.st_issue_tid[i]     //= s.ld_st_unit.st_issue_tid[i] # rf -> ld/st
            s.rf_controller.ld_data[i]          //= s.ld_st_unit.ld_ifc[i].o_data # ld/st -> rf
            s.rf_controller.ld_data_valid[i]    //= s.ld_st_unit.ld_ifc[i].o_done # ld/st -> rf
            s.rf_controller.ld_data_id[i]       //= s.ld_st_unit.ld_ifc[i].o_data_id # ld/st -> rf
            s.rf_controller.ld_req_accepted[i]  //= s.ld_req_accepted[i]
            s.rf_controller.st_req_accepted[i]  //= s.st_req_accepted[i]
        s.rf_controller.ld_st_complete //= s.ld_st_unit.ld_st_complete # ld/st -> rf
        s.rf_controller.mem_ready_mask_bank0 //= s.ld_st_unit.mem_ready_mask_bank0
        s.rf_controller.mem_ready_mask_bank1 //= s.ld_st_unit.mem_ready_mask_bank1
        s.rf_controller.mem_complete_mask_bank0 //= s.ld_st_unit.mem_complete_mask_bank0
        s.rf_controller.mem_complete_mask_bank1 //= s.ld_st_unit.mem_complete_mask_bank1
        s.rf_controller.mem_release_valid //= s.ld_st_unit.ld_release_valid
        s.rf_controller.mem_release_tid //= s.ld_st_unit.ld_release_tid
        s.rf_controller.mem_release_take //= s.ld_st_unit.release_take
        s.rf_controller.cfg_thread_min_bank0 //= s.ld_st_unit.cfg_thread_min_bank0
        s.rf_controller.cfg_thread_max_bank0 //= s.ld_st_unit.cfg_thread_max_bank0
        s.rf_controller.cfg_thread_min_bank1 //= s.ld_st_unit.cfg_thread_min_bank1
        s.rf_controller.cfg_thread_max_bank1 //= s.ld_st_unit.cfg_thread_max_bank1
        s.rf_controller.cfg_thread_mask_bank0 //= s.ld_st_unit.cfg_thread_mask_bank0
        s.rf_controller.cfg_thread_mask_bank1 //= s.ld_st_unit.cfg_thread_mask_bank1
        s.rf_controller.cfg_bank_has_load0 //= s.ld_st_unit.cfg_bank_has_load0
        s.rf_controller.cfg_bank_has_load1 //= s.ld_st_unit.cfg_bank_has_load1
        s.rf_controller.cfg_bank_has_store0 //= s.ld_st_unit.cfg_bank_has_store0
        s.rf_controller.cfg_bank_has_store1 //= s.ld_st_unit.cfg_bank_has_store1

        s.ld_st_unit.cfg_active_sel //= s.cfg_active_sel
        s.ld_st_unit.cfg_load_sel //= s.cfg_load_sel
        s.ld_st_unit.cfg_bank_commit //= s.cfg_bank_commit

        @update
        def update_ld_st_accepts():
            for i in range(num_ld_ports):
                s.ld_req_accepted[i] @= s.ld_st_unit.ld_ifc[i].i_req & s.ld_st_unit.ld_ifc[i].o_rdy & s.rf_controller.ld_enable[i]
            for i in range(num_st_ports):
                s.st_req_accepted[i] @= s.ld_st_unit.st_ifc[i].i_req & s.ld_st_unit.st_ifc[i].o_rdy & s.rf_controller.st_enable[i]

        ##### Load/Store & Fabric Connections
        s.load_addr_wire = [Wire(AxiAddrType) for _ in range(num_ld_ports)]
        s.load_pred_wire = [Wire(Bits1) for _ in range(num_ld_ports)]
        s.load_data_wire = [Wire(DataType) for _ in range(num_ld_ports)]
        s.store_addr_wire = [Wire(AxiAddrType) for _ in range(num_st_ports)]
        s.store_pred_wire = [Wire(Bits1) for _ in range(num_st_ports)]
        s.store_data_wire = [Wire(DataType) for _ in range(num_st_ports)]
        for i in range(num_tile_cols // 2):
            # TODO @darrenl make sure works for differently timed data and addr
            # Predicates
            s.ld_st_unit.ld_tile_pred[i] //= s.load_pred_wire[i] # fabric -> ld/st
            s.ld_st_unit.st_tile_pred[i] //= s.store_pred_wire[i] # fabric -> ld/st

            # Data and Control Store - SOUTH ONLY
            s.ld_st_unit.st_ifc[i].i_data //= s.store_data_wire[i] # fabric -> ld/st
            s.ld_st_unit.st_ifc[i].i_addr //= s.store_addr_wire[i] # fabric -> ld/st
            s.ld_st_unit.ld_ifc[i].i_addr //= s.load_addr_wire[i] # fabric -> ld/st
        
        # Load/Store & Fabric Update Connections
        @update
        def update_ld_st_fabric():
            # NORTH Load ONLY - Addr at Even tile columns
            # widen narrow data flits into full AXI address width
            s.load_pred_wire[0] @= s.tile_fabric.send_north_pred_port[0]
            s.load_addr_wire[0] @= zext( s.tile_fabric.send_north_data_port[0], AxiAddrType.nbits ) # ld/st -> fabric

            # SOUTH Store ONLY - Addr at Even tile columns, Data at Odd tile columns
            s.store_pred_wire[0] @= s.tile_fabric.send_south_pred_port[0]
            s.store_data_wire[0] @= s.tile_fabric.send_south_data_port[1]
            s.store_addr_wire[0] @= zext( s.tile_fabric.send_south_data_port[0], AxiAddrType.nbits ) # ld/st -> fabric

            # NORTH Load ONLY - Addr at Even tile columns
            # widen narrow data flits into full AXI address width
            s.load_pred_wire[1] @= s.tile_fabric.send_north_pred_port[3]
            s.load_addr_wire[1] @= zext( s.tile_fabric.send_north_data_port[3], AxiAddrType.nbits ) # ld/st -> fabric

            # SOUTH Store ONLY - Addr at Even tile columns, Data at Odd tile columns
            s.store_pred_wire[1] @= s.tile_fabric.send_south_pred_port[2]
            s.store_data_wire[1] @= s.tile_fabric.send_south_data_port[3]
            s.store_addr_wire[1] @= zext( s.tile_fabric.send_south_data_port[2], AxiAddrType.nbits ) # ld/st -> fabric

            # Sparse single-tile branch stores place a single value on the
            # leftmost south lane. When the remapped store port is active and
            # its native columns are idle, reuse that lone value as both
            # address-predicate source and store data so the control path can
            # observe the divergent value.
            # if num_st_ports > 1:
            #     if s.rf_controller.st_enable[1] & ~s.rf_controller.st_enable[0]:
            #         if (s.tile_fabric.send_south_data_port[2] == DataType(0)) & (s.tile_fabric.send_south_data_port[3] == DataType(0)):
            #             s.south_addr_wire[1] @= zext(s.tile_fabric.send_south_data_port[0], AxiAddrType.nbits)
            #             s.store_pred_wire[1] @= s.tile_fabric.send_south_pred_port[0]
            #             if s.tile_fabric.send_south_data_port[1] != DataType(0):
            #                 s.store_data_wire[1] @= s.tile_fabric.send_south_data_port[1]
            #             else:
            #                 s.store_data_wire[1] @= s.tile_fabric.send_south_data_port[0]
        
        ##### Load/Store External Connections
        # Load Axis
        for i in range(num_ld_ports):
            s.ld_axi[i] //= s.ld_st_unit.ld_axi[i]
        # Store Axis
        for i in range(num_st_ports):
            s.st_axi[i] //= s.ld_st_unit.st_axi[i]

        ###### Tokenizer & Core Controller
        s.core_controller.send_cfg_to_tokenizer //= s.tokenizer.recv_cfg_from_ctrl # cc -> tokenizer
        s.tokenizer.cfg_active_sel //= s.cfg_active_sel # cc -> tokenizer
        s.tokenizer.cfg_load_sel //= s.cfg_load_sel # cc -> tokenizer
        s.tokenizer.cfg_swap //= s.cfg_swap # cc -> tokenizer
        s.tokenizer.cfg_relaunch //= s.cfg_relaunch # cc -> tokenizer

        ###### Tokenizer & Rf
        for i in range(num_taker_ports):
            s.tokenizer.token_take[i] //= s.rf_controller.tile_token_take[i] # rf -> tokenizer
            s.tokenizer.token_avail[i] //= s.rf_controller.tile_token_avail[i] # tokenizer -> rf
        for i in range(num_wr_ports):
            s.tokenizer.token_return[i] //= s.rf_controller.tile_token_return[i] # rf -> tokenizer [initial slots]
            s.tokenizer.token_shifter_out[i] //= s.rf_controller.tile_token_shifter_out[i] # tokenizer -> rf

        ##### Tokenizer & Ld/St Connections
        for i in range(num_wr_ports, num_returner_ports - num_ld_ports):
            s.tokenizer.token_return[i] //= s.ld_st_unit.ld_token_return[i - num_wr_ports]
            s.tokenizer.token_return[i + num_ld_ports] //= s.ld_st_unit.st_token_return[i - num_wr_ports]

        for i in range(num_ld_ports):
            # Data and Control Load - North ONLY
            s.tokenizer.token_shifter_out[i + num_wr_ports] //= s.ld_st_unit.ld_ifc[i].i_req # tokenizer -> ld/st
            # s.ld_st_unit.ld_ifc[i].o_rdy //=  # fabric -> ld/st

            # Data and Control Store - SOUTH ONLY
            s.tokenizer.token_shifter_out[i + num_wr_ports + num_ld_ports] //= s.ld_st_unit.st_ifc[i].i_req # tokenizer -> ld/st

        #### Test Connections ###
        if debug:
            # TODO @darrenl to remove
            # Cfg Tests
            BitstreamAddrType = mk_bits(clog2(MAX_BITSTREAM_COUNT))
            s.cc_cfg_to_tiles = OutPort(TileBitstreamType)
            s.cc_cfg_to_tiles_val = OutPort(Bits1)
            s.cc_cfg_to_rf = OutPort(CfgMetadataType)
            s.cc_cfg_to_rf_val = OutPort(Bits1)
            s.cc_cfg_to_rf_rdy = OutPort(Bits1)
            s.cc_cfg_raddr = OutPort(BitstreamAddrType)
            s.cc_pc_next = OutPort(BitstreamAddrType)
            s.cc_pc = OutPort(BitstreamAddrType)
            s.cc_state = OutPort(mk_bits(2))
            s.cc_cfg_packets_injected = OutPort( TileCountType )
            s.cc_pc_started = OutPort( Bits1 )
            s.cc_pc_done = OutPort( Bits1 )
            s.cc_last_pc = OutPort( Bits1 )

            s.cc_cfg_to_tiles //= s.core_controller.send_cfg_to_tiles.msg
            s.cc_cfg_to_tiles_val //= s.core_controller.send_cfg_to_tiles.val
            s.cc_cfg_to_rf //= s.core_controller.send_cfg_to_rf.msg
            s.cc_cfg_to_rf_val //= s.core_controller.send_cfg_to_rf.val
            s.cc_cfg_to_rf_rdy //= s.rf_controller.recv_cfg_from_ctrl.rdy
            s.cc_cfg_raddr //= s.core_controller.cfg_mem_raddr
            s.cc_pc_next //= s.core_controller.pc_next
            s.cc_pc //= s.core_controller.pc
            s.cc_state //= s.core_controller.state
            s.cc_cfg_packets_injected //= s.core_controller.cfg_packets_injected_count
            s.cc_pc_started //= s.core_controller.pc_started
            s.cc_pc_done //= s.core_controller.pc_done
            s.cc_last_pc //= s.core_controller.last_pc

            # Memory predicates
            s.tile_north_preds = [OutPort(1) for _ in range(num_tile_cols)]
            s.tile_south_preds = [OutPort(1) for _ in range(num_tile_cols)]
            s.tile_north_data = [OutPort(DataType) for _ in range(num_tile_cols)]
            s.tile_south_data = [OutPort(DataType) for _ in range(num_tile_cols)]
            for i in range(num_tile_cols):
                s.tile_north_preds[i] //= s.tile_fabric.send_north_pred_port[i]
                s.tile_south_preds[i] //= s.tile_fabric.send_south_pred_port[i]
                s.tile_north_data[i] //= s.tile_fabric.send_north_data_port[i]
                s.tile_south_data[i] //= s.tile_fabric.send_south_data_port[i]
            
            # Ld St Test
            s.ld_enable = [OutPort(Bits1) for _ in range(num_ld_ports)]
            s.st_enable = [OutPort(Bits1) for _ in range(num_st_ports)]
            s.ld_st_complete = OutPort(Bits1)
            s.ld_st_complete //= s.ld_st_unit.ld_st_complete
            s.ld_complete = [OutPort(1) for _ in range(num_ld_ports)]
            s.st_complete = [OutPort(1) for _ in range(num_st_ports)]
            s.ld_pred_in = [OutPort(1) for _ in range(num_ld_ports)]
            s.ld_data_in = [OutPort(DataType) for _ in range(num_ld_ports)]
            for i in range(num_ld_ports):
                s.ld_complete[i] //= s.ld_st_unit.ld_complete[i]
                s.ld_pred_in[i] //= s.tile_fabric.send_north_pred_port[i*2]
                s.ld_data_in[i] //= s.tile_fabric.send_north_data_port[i*2]
                s.ld_enable[i] //= s.rf_controller.ld_enable[i]
            for i in range(num_st_ports):
                s.st_enable[i] //= s.rf_controller.st_enable[i]
                s.st_complete[i] //= s.ld_st_unit.st_complete[i]
            s.lds_outstanding = [ OutPort( clog2(MAX_THREAD_COUNT + 1) ) for _ in range(num_ld_ports) ]
            s.lds_in_tile     = [ OutPort( clog2(MAX_THREAD_COUNT + 1) ) for _ in range(num_ld_ports) ]
            s.lds_tile_counter     = [ OutPort( clog2(MAX_THREAD_COUNT) ) for _ in range(num_ld_ports) ]
            s.sts_tile_counter     = [ OutPort( clog2(MAX_THREAD_COUNT) ) for _ in range(num_ld_ports) ]
            s.store_queue_rdy   = [ OutPort(1) for _ in range(num_ld_ports) ]
            s.sts_outstanding= [ OutPort( clog2(MAX_THREAD_COUNT + 1) ) for _ in range(num_ld_ports) ]
            s.stores_in_tile    = [ OutPort( clog2(MAX_THREAD_COUNT + 1) ) for _ in range(num_ld_ports) ]
            s.ld_i_req = [OutPort(1) for _ in range(num_ld_ports)]
            s.ld_tile_last_seen = [OutPort(1) for _ in range(num_ld_ports)]
            s.st_tile_last_seen = [OutPort(1) for _ in range(num_st_ports)]
            for i in range(num_ld_ports):
                s.lds_outstanding[i] //= s.ld_st_unit.outstanding_reqs[i]
                s.lds_in_tile[i] //= s.ld_st_unit.loads_in_tile[i]
                s.lds_tile_counter[i] //= s.ld_st_unit.loads_tile_counter[i]
                s.store_queue_rdy[i] //= s.ld_st_unit.store_queue_rdy[i]
                s.sts_outstanding[i] //= s.ld_st_unit.outstanding_stores[i]
                s.stores_in_tile[i] //= s.ld_st_unit.stores_in_tile[i]
                s.ld_tile_last_seen[i] //= s.ld_st_unit.ld_tile_last_seen[i]
                s.ld_i_req[i] //= s.tokenizer.token_shifter_out[num_wr_ports + i] # fabric -> ld/st
            s.recv_ld_st_thread_min = OutPort( clog2(MAX_THREAD_COUNT) )
            s.recv_ld_st_thread_max = OutPort( clog2(MAX_THREAD_COUNT) )
            s.recv_ld_st_thread_min //= s.rf_controller.send_thread_min
            s.recv_ld_st_thread_max //= s.rf_controller.send_thread_max
            s.st_i_req = [OutPort(1) for _ in range(num_st_ports)]
            s.st_i_data = [OutPort(DataType) for _ in range(num_st_ports)]
            s.st_i_addr = [OutPort(AxiAddrType) for _ in range(num_st_ports)]
            for i in range(num_st_ports):
                s.st_i_req[i] //= s.tokenizer.token_shifter_out[num_wr_ports + num_ld_ports + i] # fabric -> ld/st
                s.st_i_data[i] //= s.tile_fabric.send_south_data_port[i*2+1] # fabric -> ld/st
                s.st_tile_last_seen[i] //= s.ld_st_unit.st_tile_last_seen[i]
                s.sts_tile_counter[i] //= s.ld_st_unit.store_tile_counter[i]
            @update
            def test_st_addr():
                for i in range(num_st_ports):
                    s.st_i_addr[i] @= zext( s.tile_fabric.send_south_data_port[i*2], AxiAddrType.nbits )

            # RF Controller Test
            s.rf_state_n = OutPort(1)
            s.rf_state_n //= s.rf_controller.state_n
            s.rf_cfg_done = OutPort(Bits1)
            s.rf_cfg_done //= s.rf_controller.cfg_done
            s.rf_cfg_issue_ready = OutPort(Bits1)
            s.rf_cfg_issue_ready //= s.rf_controller.cfg_issue_ready
            s.rf_cfg_writeback_complete = OutPort(Bits1)
            s.rf_cfg_writeback_complete //= s.rf_controller.cfg_writeback_complete
            s.rf_issue_fire = OutPort(Bits1)
            s.rf_issue_tid = OutPort(mk_bits(clog2(MAX_THREAD_COUNT)))
            s.rf_issue_fire //= s.rf_controller.rf_issue_fire
            s.rf_issue_tid //= s.rf_controller.rf_issue_tid
            s.rf_wr_track_en = [OutPort(Bits1) for _ in range(num_wr_ports)]
            s.rf_wr_commit_valid = [OutPort(Bits1) for _ in range(num_wr_ports)]
            s.rf_wr_commit_tid = [OutPort(mk_bits(clog2(MAX_THREAD_COUNT))) for _ in range(num_wr_ports)]
            for i in range(num_wr_ports):
                s.rf_wr_track_en[i] //= s.rf_controller.rf_wr_track_en[i]
                s.rf_wr_commit_valid[i] //= s.rf_controller.rf_wr_commit_valid[i]
                s.rf_wr_commit_tid[i] //= s.rf_controller.rf_wr_commit_tid[i]
            s.rf_rd_addr_valcfg_n  = [OutPort(Bits1)         for _ in range(num_rd_ports)]
            s.rf_rd_addr_cfg_n  = [OutPort(RegAddrType)         for _ in range(num_rd_ports)]
            s.rf_wr_addr_cfg_n  = [OutPort(RegAddrType)         for _ in range(num_wr_ports)]
            s.rf_rd_count_n = [OutPort(mk_bits(clog2(MAX_THREAD_COUNT))) for _ in range(num_rd_ports)]
            for i in range(num_rd_ports):
                s.rf_rd_addr_valcfg_n[i] //= s.rf_controller.rd_addr_valcfg_n[i]
                s.rf_rd_addr_cfg_n[i] //= s.rf_controller.rd_addr_cfg_n[i]
                s.rf_rd_count_n[i] //= s.rf_controller.rd_count_n[i]
            for i in range(num_wr_ports):
                s.rf_wr_addr_cfg_n[i] //= s.rf_controller.wr_addr_cfg_n[i]

            
            # RF & Fabric Test
            s.rf_to_fabric_msg = [ OutPort(DataType) for _ in range(num_rd_ports)]
            for i in range(num_rd_ports):
                # Expose the post-select RF output actually sent into fabric
                # (register, constant, or synthetic tid path).
                s.rf_to_fabric_msg[i] //= s.rf_controller.rd_data[i]
            s.rf_from_fabric_msg = [ OutPort(DataType) for _ in range(num_wr_ports)]
            for i in range(num_wr_ports // 2):
                s.rf_from_fabric_msg[2*i] //= s.tile_fabric.send_west_data_port[i]
                s.rf_from_fabric_msg[2*i + 1] //= s.tile_fabric.send_east_data_port[i]

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
            
            # CHECK SPECIFIC TILE
            s.fu_in = [ OutPort(DataType) for _ in range(num_fu_inports) ]
            s.fu_out = [ OutPort(DataType) for _ in range(num_fu_outports) ]
            
            s.tile_bitstream_cmd = OutPort(OperationType)
            s.tile_bitstream_cmd //= s.tile_fabric.tile_bitstream_cmd
            s.tile_bitstream_in_route = OutPort(Bits4)
            s.tile_bitstream_in_route //= s.tile_fabric.tile_bitstream_in_route
            s.tile_in_test = [ OutPort(DataType) for _ in range(num_tile_inports) ]
            s.tile_new_bitstream_val = OutPort(Bits1)
            s.tile_new_bitstream_val //= s.tile_fabric.tile_new_bitstream_val
            s.tile_new_bitstream_ingested = OutPort(Bits1)
            s.tile_new_bitstream_ingested //= s.tile_fabric.tile_new_bitstream_ingested
            TileIdType = mk_bits(clog2(num_tile_rows * num_tile_cols))
            s.tile_new_bitstream_tile_id = OutPort(TileIdType)
            s.tile_new_bitstream_tile_id //= s.tile_fabric.tile_new_bitstream_tile_id
            s.tile_id_matched = OutPort(Bits1)
            s.tile_id_matched //= s.tile_fabric.tile_id_matched
            s.tile_wrapper_id_matched = OutPort(Bits1)
            s.tile_wrapper_id_matched //= s.tile_fabric.tile_wrapper_id_matched
            s.tile_id_received = OutPort(TileIdType)
            s.tile_id_received //= s.tile_fabric.tile_id_received

            for i in range(num_fu_inports):
                s.fu_in[i] //= s.tile_fabric.fu_in[i]
            for i in range(num_fu_outports):
                s.fu_out[i] //= s.tile_fabric.fu_out[i]
            for i in range(num_tile_inports):
                s.tile_in_test[i] //= s.tile_fabric.tile_in_test[i]
            
            s.tile_data_out = [OutPort(DataType) for _ in range(num_tile_outports)]
            for i in range(num_tile_outports):
                s.tile_data_out[i] //= s.tile_fabric.tile_data_out[i]
            s.tile_pred_out = [OutPort(1) for _ in range(num_tile_outports)]
            for i in range(num_tile_outports):
                s.tile_pred_out[i] //= s.tile_fabric.tile_pred_out[i]

    def line_trace(s):
        # Minimal trace to satisfy tests; can be extended with key state.
        return ""
