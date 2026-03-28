from pymtl3 import *
from .STEP_LoadRTL import STEP_LoadRTL
from .STEP_StoreRTL import STEP_StoreRTL
from .STEP_LdStScoreboardRTL import STEP_LdStScoreboardRTL
from ...lib.util.common import *
from ...lib.basic.AxiInterface import SendAxiReadLoadAddrIfcRTL, SendAxiReadStoreAddrIfcRTL, \
                            RecvAxiLoadIfcRTL, RecvAxiStoreIfcRTL

class STEP_LoadStoreRTL( Component ):
    def construct(s, DataType, num_ports=1, queue_depth=8, debug=False):
        TidType = mk_bits(clog2(MAX_THREAD_COUNT))
        MaskType = mk_bits(MAX_THREAD_COUNT)
        CountType = mk_bits(clog2(MAX_THREAD_COUNT + 1))
        InternalAddrNbits = min(DataType.nbits, AXI_ADDR_BITWIDTH)

        ###### Interface #####
        s.ld_axi = [SendAxiReadLoadAddrIfcRTL(DataType) for _ in range(num_ports)]
        s.ld_ifc = [RecvAxiLoadIfcRTL(DataType, addr_nbits=InternalAddrNbits) for _ in range(num_ports)]
        s.ld_tile_pred = [InPort(1) for _ in range(num_ports)]
        s.ld_issue_tid = [InPort(TidType) for _ in range(num_ports)]
        s.ld_token_return = [OutPort(1) for _ in range(num_ports)]
        
        s.st_axi = [SendAxiReadStoreAddrIfcRTL(DataType) for _ in range(num_ports)]
        s.st_ifc = [RecvAxiStoreIfcRTL(DataType, addr_nbits=InternalAddrNbits) for _ in range(num_ports)]
        s.st_tile_pred = [InPort(1) for _ in range(num_ports)]
        s.st_issue_tid = [InPort(TidType) for _ in range(num_ports)]
        s.st_token_return = [OutPort(1) for _ in range(num_ports)]

        s.cfg_active_sel = InPort(Bits1)
        s.cfg_load_sel = InPort(Bits1)
        s.cfg_bank_commit = InPort(Bits1)
        s.release_take = InPort(1)
        s.cfg_thread_min_bank0 = InPort(CountType)
        s.cfg_thread_max_bank0 = InPort(CountType)
        s.cfg_thread_min_bank1 = InPort(CountType)
        s.cfg_thread_max_bank1 = InPort(CountType)
        s.cfg_thread_mask_bank0 = InPort(MaskType)
        s.cfg_thread_mask_bank1 = InPort(MaskType)
        s.cfg_bank_has_load0 = InPort(Bits1)
        s.cfg_bank_has_load1 = InPort(Bits1)
        s.cfg_bank_has_store0 = InPort(Bits1)
        s.cfg_bank_has_store1 = InPort(Bits1)
        
        # Enable/disable individual units
        s.ld_enable = [InPort(1) for _ in range(num_ports)]  # Enable load unit i
        s.st_enable = [InPort(1) for _ in range(num_ports)]  # Enable store unit i
        
        # Mark Ld/St completion for Cfg when all ENABLED units complete
        s.ld_st_complete = OutPort(1)
        s.cfg_ready_for_next = OutPort(1)
        s.mem_ready_mask_bank0 = OutPort(MaskType)
        s.mem_ready_mask_bank1 = OutPort(MaskType)
        s.mem_complete_mask_bank0 = OutPort(MaskType)
        s.mem_complete_mask_bank1 = OutPort(MaskType)
        s.ld_release_valid = OutPort(1)
        s.ld_release_tid = OutPort(TidType)

        ###### Load/Store Units #########
        s.ld_units = [STEP_LoadRTL(DataType) for _ in range(num_ports)]
        s.st_units = [STEP_StoreRTL(DataType) for _ in range(num_ports)]
        s.scoreboards = [STEP_LdStScoreboardRTL() for _ in range(2)]
        s.active_thread_span = Wire(CountType)
        s.sb_mem_dispatch_mask0 = Wire(MaskType)
        s.sb_mem_dispatch_mask1 = Wire(MaskType)
        s.sb_ld_done_mask0 = Wire(MaskType)
        s.sb_ld_done_mask1 = Wire(MaskType)
        s.sb_st_done_mask0 = Wire(MaskType)
        s.sb_st_done_mask1 = Wire(MaskType)

        #### DEBUG
        if debug:
            s.ld_complete = [OutPort(1) for _ in range(num_ports)]
            s.st_complete = [OutPort(1) for _ in range(num_ports)]
            s.outstanding_reqs = [OutPort( CountType ) for _ in range(num_ports)]
            s.loads_in_tile = [OutPort( CountType ) for _ in range(num_ports)]
            s.loads_tile_counter = [OutPort( clog2(MAX_THREAD_COUNT + 1) ) for _ in range(num_ports)]
            s.store_queue_rdy = [OutPort(1) for _ in range(num_ports)]
            s.outstanding_stores = [OutPort( CountType ) for _ in range(num_ports)]
            s.stores_in_tile = [OutPort( CountType ) for _ in range(num_ports)]
            s.store_tile_counter = [OutPort( clog2(MAX_THREAD_COUNT + 1) ) for _ in range(num_ports)]
            s.ld_tile_last_seen = [OutPort(1) for _ in range(num_ports)]
            s.st_tile_last_seen = [OutPort(1) for _ in range(num_ports)]
            for i in range(num_ports):
                s.ld_complete[i] //= s.ld_units[i].o_tile_complete
                s.st_complete[i] //= s.st_units[i].o_tile_complete
                s.outstanding_reqs[i] //= s.ld_units[i].outstanding_reqs
                s.loads_in_tile[i] //= s.ld_units[i].loads_in_tile
                s.loads_tile_counter[i] //= s.ld_units[i].tile_counter
                s.store_queue_rdy[i] //= s.st_units[i].store_queue_rdy
                s.outstanding_stores[i] //= s.st_units[i].outstanding_stores
                s.stores_in_tile[i] //= s.st_units[i].stores_in_tile
                s.store_tile_counter[i] //= s.st_units[i].tile_counter
                s.ld_tile_last_seen[i] //= s.ld_units[i].tile_last_seen
                s.st_tile_last_seen[i] //= s.st_units[i].tile_last_seen
        ####
        
        ###### Wire Connections #########
        for i in range(num_ports):
            # Load Unit connections
            s.ld_axi[i] //= s.ld_units[i].axi
            s.ld_ifc[i] //= s.ld_units[i].load_ifc
            s.ld_tile_pred[i] //= s.ld_units[i].i_tile_pred
            s.ld_issue_tid[i] //= s.ld_units[i].issue_tid
            s.cfg_active_sel //= s.ld_units[i].issue_bank
            s.ld_enable[i] //= s.ld_units[i].enable
            s.ld_token_return[i] //= s.ld_units[i].token_return
            s.active_thread_span //= s.ld_units[i].thread_span
            
            # Store Unit connections
            s.st_axi[i] //= s.st_units[i].axi
            s.st_ifc[i] //= s.st_units[i].store_ifc
            s.st_tile_pred[i] //= s.st_units[i].i_tile_pred
            s.st_issue_tid[i] //= s.st_units[i].issue_tid
            s.cfg_active_sel //= s.st_units[i].issue_bank
            s.st_enable[i] //= s.st_units[i].enable
            s.st_token_return[i] //= s.st_units[i].token_return
            s.active_thread_span //= s.st_units[i].thread_span

        s.cfg_thread_min_bank0 //= s.scoreboards[0].thread_count_min
        s.cfg_thread_max_bank0 //= s.scoreboards[0].thread_count_max
        s.cfg_thread_min_bank1 //= s.scoreboards[1].thread_count_min
        s.cfg_thread_max_bank1 //= s.scoreboards[1].thread_count_max
        s.cfg_thread_mask_bank0 //= s.scoreboards[0].thread_mask
        s.cfg_thread_mask_bank1 //= s.scoreboards[1].thread_mask

        @update
        def drive_active_thread_span():
            active_mask = s.cfg_thread_mask_bank0
            active_min = s.cfg_thread_min_bank0
            active_max = s.cfg_thread_max_bank0
            if s.cfg_active_sel == Bits1(1):
                active_mask = s.cfg_thread_mask_bank1
                active_min = s.cfg_thread_min_bank1
                active_max = s.cfg_thread_max_bank1

            active_span = CountType(0)
            if active_mask != MaskType(0):
                for tid in range(MAX_THREAD_COUNT):
                    if active_mask[tid]:
                        active_span = active_span + CountType(1)
            else:
                for tid in range(MAX_THREAD_COUNT):
                    tid_bits = CountType(tid)
                    if (tid_bits >= active_min) & (tid_bits < active_max):
                        active_span = active_span + CountType(1)
            s.active_thread_span @= active_span

        @update
        def collect_scoreboard_events():
            mem_dispatch_mask0 = MaskType(0)
            mem_dispatch_mask1 = MaskType(0)
            ld_done_mask0 = MaskType(0)
            ld_done_mask1 = MaskType(0)
            st_done_mask0 = MaskType(0)
            st_done_mask1 = MaskType(0)
            for i in range(num_ports):
                ld_issue_onehot = MaskType(0)
                st_issue_onehot = MaskType(0)
                ld_done_onehot = MaskType(0)
                st_done_onehot = MaskType(0)
                for tid in range(MAX_THREAD_COUNT):
                    one_hot_tid = MaskType(1 << tid)
                    if s.ld_issue_tid[i] == TidType(tid):
                        ld_issue_onehot = one_hot_tid
                    if s.st_issue_tid[i] == TidType(tid):
                        st_issue_onehot = one_hot_tid
                    if s.ld_ifc[i].o_data_id == TidType(tid):
                        ld_done_onehot = one_hot_tid
                    if s.st_units[i].o_done_tid == TidType(tid):
                        st_done_onehot = one_hot_tid

                if s.ld_ifc[i].i_req & s.ld_ifc[i].o_rdy:
                    if s.ld_units[i].issue_bank == Bits1(0):
                        mem_dispatch_mask0 = mem_dispatch_mask0 | ld_issue_onehot
                    else:
                        mem_dispatch_mask1 = mem_dispatch_mask1 | ld_issue_onehot
                    if ~(s.ld_enable[i] & s.ld_tile_pred[i]):
                        if s.ld_units[i].issue_bank == Bits1(0):
                            ld_done_mask0 = ld_done_mask0 | ld_issue_onehot
                        else:
                            ld_done_mask1 = ld_done_mask1 | ld_issue_onehot
                if s.st_ifc[i].i_req & s.st_ifc[i].o_rdy:
                    if s.st_units[i].issue_bank == Bits1(0):
                        mem_dispatch_mask0 = mem_dispatch_mask0 | st_issue_onehot
                    else:
                        mem_dispatch_mask1 = mem_dispatch_mask1 | st_issue_onehot
                    if ~(s.st_enable[i] & s.st_tile_pred[i]):
                        if s.st_units[i].issue_bank == Bits1(0):
                            st_done_mask0 = st_done_mask0 | st_issue_onehot
                        else:
                            st_done_mask1 = st_done_mask1 | st_issue_onehot
                if s.ld_ifc[i].o_done:
                    if s.ld_units[i].o_data_bank == Bits1(0):
                        ld_done_mask0 = ld_done_mask0 | ld_done_onehot
                    else:
                        ld_done_mask1 = ld_done_mask1 | ld_done_onehot
                if s.st_ifc[i].o_done:
                    if s.st_units[i].o_done_bank == Bits1(0):
                        st_done_mask0 = st_done_mask0 | st_done_onehot
                    else:
                        st_done_mask1 = st_done_mask1 | st_done_onehot

            s.sb_mem_dispatch_mask0 @= mem_dispatch_mask0
            s.sb_mem_dispatch_mask1 @= mem_dispatch_mask1
            s.sb_ld_done_mask0 @= ld_done_mask0
            s.sb_ld_done_mask1 @= ld_done_mask1
            s.sb_st_done_mask0 @= st_done_mask0
            s.sb_st_done_mask1 @= st_done_mask1

        @update
        def drive_scoreboards():
            clear_bank0 = Bits1(0)
            clear_bank1 = Bits1(0)
            if s.cfg_bank_commit:
                if s.cfg_load_sel == Bits1(0):
                    clear_bank0 = Bits1(1)
                else:
                    clear_bank1 = Bits1(1)

            s.scoreboards[0].clear @= clear_bank0
            s.scoreboards[1].clear @= clear_bank1
            s.scoreboards[0].mem_dispatch_event_mask @= s.sb_mem_dispatch_mask0
            s.scoreboards[0].ld_done_event_mask @= s.sb_ld_done_mask0
            s.scoreboards[0].st_done_event_mask @= s.sb_st_done_mask0
            s.scoreboards[0].release_take @= Bits1(0)

            s.scoreboards[1].mem_dispatch_event_mask @= s.sb_mem_dispatch_mask1
            s.scoreboards[1].ld_done_event_mask @= s.sb_ld_done_mask1
            s.scoreboards[1].st_done_event_mask @= s.sb_st_done_mask1
            s.scoreboards[1].release_take @= Bits1(0)

            s.scoreboards[0].require_load @= s.cfg_bank_has_load0
            s.scoreboards[1].require_load @= s.cfg_bank_has_load1
            s.scoreboards[0].require_store @= s.cfg_bank_has_store0
            s.scoreboards[1].require_store @= s.cfg_bank_has_store1

            if s.cfg_active_sel == Bits1(0):
                s.scoreboards[1].release_take @= s.release_take
            else:
                s.scoreboards[0].release_take @= s.release_take

        @update
        def update_outputs():
            s.mem_ready_mask_bank0 @= s.scoreboards[0].ready_mask
            s.mem_ready_mask_bank1 @= s.scoreboards[1].ready_mask
            s.mem_complete_mask_bank0 @= s.scoreboards[0].complete_mask
            s.mem_complete_mask_bank1 @= s.scoreboards[1].complete_mask

            if s.cfg_active_sel == Bits1(0):
                s.cfg_ready_for_next @= s.scoreboards[0].all_ready
                s.ld_st_complete @= s.scoreboards[0].all_complete
                s.ld_release_valid @= s.scoreboards[1].release_valid
                s.ld_release_tid @= s.scoreboards[1].release_tid
            else:
                s.cfg_ready_for_next @= s.scoreboards[1].all_ready
                s.ld_st_complete @= s.scoreboards[1].all_complete
                s.ld_release_valid @= s.scoreboards[0].release_valid
                s.ld_release_tid @= s.scoreboards[0].release_tid
