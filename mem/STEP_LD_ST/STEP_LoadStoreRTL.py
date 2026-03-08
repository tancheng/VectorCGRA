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

        ###### Interface #####
        s.ld_axi = [SendAxiReadLoadAddrIfcRTL(DataType) for _ in range(num_ports)]
        s.ld_ifc = [RecvAxiLoadIfcRTL(DataType) for _ in range(num_ports)]
        s.ld_tile_pred = [InPort(1) for _ in range(num_ports)]
        s.ld_issue_tid = [InPort(TidType) for _ in range(num_ports)]
        s.ld_token_return = [OutPort(1) for _ in range(num_ports)]
        
        s.st_axi = [SendAxiReadStoreAddrIfcRTL(DataType) for _ in range(num_ports)]
        s.st_ifc = [RecvAxiStoreIfcRTL(DataType) for _ in range(num_ports)]
        s.st_tile_pred = [InPort(1) for _ in range(num_ports)]
        s.st_issue_tid = [InPort(TidType) for _ in range(num_ports)]
        s.st_token_return = [OutPort(1) for _ in range(num_ports)]

        s.thread_count = InPort( clog2(MAX_THREAD_COUNT) )
        s.cfg_active_sel = InPort(Bits1)
        s.cfg_load_sel = InPort(Bits1)
        s.cfg_bank_commit = InPort(Bits1)
        s.release_take = InPort(1)
        s.cfg_thread_count_bank0 = InPort(clog2(MAX_THREAD_COUNT))
        s.cfg_thread_count_bank1 = InPort(clog2(MAX_THREAD_COUNT))
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

        #### DEBUG
        if debug:
            s.ld_complete = [OutPort(1) for _ in range(num_ports)]
            s.st_complete = [OutPort(1) for _ in range(num_ports)]
            s.outstanding_reqs = [OutPort( CountType ) for _ in range(num_ports)]
            s.loads_in_tile = [OutPort( CountType ) for _ in range(num_ports)]
            s.loads_tile_counter = [OutPort( clog2(MAX_THREAD_COUNT) ) for _ in range(num_ports)]
            s.store_queue_rdy = [OutPort(1) for _ in range(num_ports)]
            s.outstanding_stores = [OutPort( CountType ) for _ in range(num_ports)]
            s.stores_in_tile = [OutPort( CountType ) for _ in range(num_ports)]
            s.store_tile_counter = [OutPort( clog2(MAX_THREAD_COUNT) ) for _ in range(num_ports)]
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
            s.thread_count //= s.ld_units[i].thread_count
            
            # Store Unit connections
            s.st_axi[i] //= s.st_units[i].axi
            s.st_ifc[i] //= s.st_units[i].store_ifc
            s.st_tile_pred[i] //= s.st_units[i].i_tile_pred
            s.st_issue_tid[i] //= s.st_units[i].issue_tid
            s.cfg_active_sel //= s.st_units[i].issue_bank
            s.st_enable[i] //= s.st_units[i].enable
            s.st_token_return[i] //= s.st_units[i].token_return
            s.thread_count //= s.st_units[i].thread_count

        s.cfg_thread_count_bank0 //= s.scoreboards[0].thread_count
        s.cfg_thread_count_bank1 //= s.scoreboards[1].thread_count

        @update
        def drive_scoreboards():
            clear_bank0 = Bits1(0)
            clear_bank1 = Bits1(0)
            if s.cfg_bank_commit:
                if s.cfg_load_sel == Bits1(0):
                    clear_bank0 = Bits1(1)
                else:
                    clear_bank1 = Bits1(1)

            mem_dispatch_val0 = Bits1(0)
            mem_dispatch_val1 = Bits1(0)
            mem_dispatch_tid0 = TidType(0)
            mem_dispatch_tid1 = TidType(0)
            ld_done_val0 = Bits1(0)
            ld_done_val1 = Bits1(0)
            ld_done_tid0 = TidType(0)
            ld_done_tid1 = TidType(0)
            st_done_val0 = Bits1(0)
            st_done_val1 = Bits1(0)
            st_done_tid0 = TidType(0)
            st_done_tid1 = TidType(0)

            for i in range(num_ports):
                if s.ld_ifc[i].i_req & s.ld_ifc[i].o_rdy:
                    if s.ld_units[i].issue_bank == Bits1(0):
                        if ~mem_dispatch_val0:
                            mem_dispatch_val0 = Bits1(1)
                            mem_dispatch_tid0 = s.ld_issue_tid[i]
                    else:
                        if ~mem_dispatch_val1:
                            mem_dispatch_val1 = Bits1(1)
                            mem_dispatch_tid1 = s.ld_issue_tid[i]
                    if ~(s.ld_enable[i] & s.ld_tile_pred[i]):
                        if s.ld_units[i].issue_bank == Bits1(0):
                            if ~ld_done_val0:
                                ld_done_val0 = Bits1(1)
                                ld_done_tid0 = s.ld_issue_tid[i]
                        else:
                            if ~ld_done_val1:
                                ld_done_val1 = Bits1(1)
                                ld_done_tid1 = s.ld_issue_tid[i]
                if s.st_ifc[i].i_req & s.st_ifc[i].o_rdy:
                    if s.st_units[i].issue_bank == Bits1(0):
                        if ~mem_dispatch_val0:
                            mem_dispatch_val0 = Bits1(1)
                            mem_dispatch_tid0 = s.st_issue_tid[i]
                    else:
                        if ~mem_dispatch_val1:
                            mem_dispatch_val1 = Bits1(1)
                            mem_dispatch_tid1 = s.st_issue_tid[i]
                    if ~(s.st_enable[i] & s.st_tile_pred[i]):
                        if s.st_units[i].issue_bank == Bits1(0):
                            if ~st_done_val0:
                                st_done_val0 = Bits1(1)
                                st_done_tid0 = s.st_issue_tid[i]
                        else:
                            if ~st_done_val1:
                                st_done_val1 = Bits1(1)
                                st_done_tid1 = s.st_issue_tid[i]
                if s.ld_ifc[i].o_done:
                    if s.ld_units[i].o_data_bank == Bits1(0):
                        if ~ld_done_val0:
                            ld_done_val0 = Bits1(1)
                            ld_done_tid0 = s.ld_ifc[i].o_data_id
                    else:
                        if ~ld_done_val1:
                            ld_done_val1 = Bits1(1)
                            ld_done_tid1 = s.ld_ifc[i].o_data_id
                if s.st_ifc[i].o_done:
                    if s.st_units[i].o_done_bank == Bits1(0):
                        if ~st_done_val0:
                            st_done_val0 = Bits1(1)
                            st_done_tid0 = s.st_units[i].o_done_tid
                    else:
                        if ~st_done_val1:
                            st_done_val1 = Bits1(1)
                            st_done_tid1 = s.st_units[i].o_done_tid

            s.scoreboards[0].clear @= clear_bank0
            s.scoreboards[1].clear @= clear_bank1
            s.scoreboards[0].mem_dispatch_tid_val @= mem_dispatch_val0
            s.scoreboards[0].mem_dispatch_tid @= mem_dispatch_tid0
            s.scoreboards[0].ld_done_tid_val @= ld_done_val0
            s.scoreboards[0].ld_done_tid @= ld_done_tid0
            s.scoreboards[0].st_done_tid_val @= st_done_val0
            s.scoreboards[0].st_done_tid @= st_done_tid0
            s.scoreboards[0].release_take @= Bits1(0)

            s.scoreboards[1].mem_dispatch_tid_val @= mem_dispatch_val1
            s.scoreboards[1].mem_dispatch_tid @= mem_dispatch_tid1
            s.scoreboards[1].ld_done_tid_val @= ld_done_val1
            s.scoreboards[1].ld_done_tid @= ld_done_tid1
            s.scoreboards[1].st_done_tid_val @= st_done_val1
            s.scoreboards[1].st_done_tid @= st_done_tid1
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
