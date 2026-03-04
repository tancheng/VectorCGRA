from pymtl3 import *
from .STEP_LoadRTL import STEP_LoadRTL
from .STEP_StoreRTL import STEP_StoreRTL
from .STEP_LdStScoreboardRTL import STEP_LdStScoreboardRTL
from ...lib.util.common import *
from ...lib.basic.AxiInterface import SendAxiReadLoadAddrIfcRTL, SendAxiReadStoreAddrIfcRTL, \
                            RecvAxiLoadIfcRTL, RecvAxiStoreIfcRTL

class STEP_LoadStoreRTL( Component ):
    def construct(s, DataType, num_ports=1, queue_depth=8, debug=False):
        ###### Interface #####
        s.ld_axi = [SendAxiReadLoadAddrIfcRTL(DataType) for _ in range(num_ports)]
        s.ld_ifc = [RecvAxiLoadIfcRTL(DataType) for _ in range(num_ports)]
        s.ld_tile_pred = [InPort(1) for _ in range(num_ports)]
        s.ld_token_return = [OutPort(1) for _ in range(num_ports)]
        
        s.st_axi = [SendAxiReadStoreAddrIfcRTL(DataType) for _ in range(num_ports)]
        s.st_ifc = [RecvAxiStoreIfcRTL(DataType) for _ in range(num_ports)]
        s.st_tile_pred = [InPort(1) for _ in range(num_ports)]
        s.st_token_return = [OutPort(1) for _ in range(num_ports)]

        s.thread_count = InPort( clog2(MAX_THREAD_COUNT) )
        
        # Enable/disable individual units
        s.ld_enable = [InPort(1) for _ in range(num_ports)]  # Enable load unit i
        s.st_enable = [InPort(1) for _ in range(num_ports)]  # Enable store unit i
        
        # Mark Ld/St completion for Cfg when all ENABLED units complete
        s.ld_st_complete = OutPort(1)
        s.ld_tid_done_mask = OutPort( mk_bits(MAX_THREAD_COUNT) )
        s.ld_all_launched = OutPort(1)

        ###### Load/Store Units #########
        s.ld_units = [STEP_LoadRTL(DataType) for _ in range(num_ports)]
        s.st_units = [STEP_StoreRTL(DataType) for _ in range(num_ports)]
        s.scoreboard = STEP_LdStScoreboardRTL()

        # Track thread_count to detect new configuration (for scoreboard clear)
        CountType = mk_bits(clog2(MAX_THREAD_COUNT))
        s.prev_thread_count = Wire(CountType)

        #### DEBUG
        if debug:
            s.ld_complete = [OutPort(1) for _ in range(num_ports)]
            s.st_complete = [OutPort(1) for _ in range(num_ports)]
            s.outstanding_reqs = [OutPort( clog2(queue_depth + 1) ) for _ in range(num_ports)]
            s.loads_in_tile = [OutPort( clog2(queue_depth + 1) ) for _ in range(num_ports)]
            s.loads_tile_counter = [OutPort( clog2(MAX_THREAD_COUNT) ) for _ in range(num_ports)]
            s.store_queue_rdy = [OutPort(1) for _ in range(num_ports)]
            s.outstanding_stores = [OutPort( clog2(queue_depth + 1) ) for _ in range(num_ports)]
            s.stores_in_tile = [OutPort( clog2(queue_depth + 1) ) for _ in range(num_ports)]
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
            s.ld_token_return[i] //= s.ld_units[i].token_return
            s.thread_count //= s.ld_units[i].thread_count
            
            # Store Unit connections
            s.st_axi[i] //= s.st_units[i].axi
            s.st_ifc[i] //= s.st_units[i].store_ifc
            s.st_tile_pred[i] //= s.st_units[i].i_tile_pred
            s.st_token_return[i] //= s.st_units[i].token_return
            s.thread_count //= s.st_units[i].thread_count

        # Scoreboard static connections
        s.scoreboard.thread_count //= s.thread_count
       
        # Scoreboard wiring defaults are driven in comb blocks below

        @update
        def update_ld_st_complete():
            s.ld_tid_done_mask @= s.scoreboard.done_mask
            s.ld_all_launched @= s.scoreboard.all_launched
            # Keep original port-wise completion to avoid stalling if mask logic lags
            complete = Bits1(1)
            for i in range(num_ports):
                ld_condition = (~s.ld_enable[i]) | s.ld_units[i].o_tile_complete
                complete = complete & ld_condition
                st_condition = (~s.st_enable[i]) | s.st_units[i].o_tile_complete
                complete = complete & st_condition
            s.ld_st_complete @= complete

        TidType = mk_bits(clog2(MAX_THREAD_COUNT))

        @update
        def drive_scoreboard():
            launch_val = Bits1(0)
            launch_tid = TidType(0)
            ld_done_val = Bits1(0)
            ld_done_tid = TidType(0)
            st_done_val = Bits1(0)
            st_done_tid = TidType(0)

            clear_sb = Bits1(0)
            if s.thread_count != s.prev_thread_count:
                clear_sb = Bits1(1)

            for i in range(num_ports):
                if s.ld_ifc[i].i_req & s.ld_ifc[i].o_rdy:
                    launch_val = Bits1(1)
                    launch_tid = s.ld_units[i].tile_counter
                if s.st_ifc[i].i_req & s.st_ifc[i].o_rdy:
                    launch_val = Bits1(1)
                    launch_tid = s.st_units[i].tile_counter
                if s.ld_units[i].o_tile_complete:
                    ld_done_val = Bits1(1)
                    ld_done_tid = s.ld_units[i].tile_counter
                if s.st_units[i].o_tile_complete:
                    st_done_val = Bits1(1)
                    st_done_tid = s.st_units[i].tile_counter

            # If we are about to launch a new thread but scoreboard still shows previous cfg done mask,
            # force clear so new config starts fresh.
            if launch_val & s.scoreboard.all_done:
                clear_sb = Bits1(1)

            s.scoreboard.clear @= clear_sb
            s.scoreboard.launch_tid_val @= launch_val
            s.scoreboard.launch_tid @= launch_tid
            s.scoreboard.ld_done_val @= ld_done_val
            s.scoreboard.ld_done_tid @= ld_done_tid
            s.scoreboard.st_done_val @= st_done_val
            s.scoreboard.st_done_tid @= st_done_tid

        @update_ff
        def track_thread_count():
            if s.reset:
                s.prev_thread_count <<= CountType(0)
            else:
                s.prev_thread_count <<= s.thread_count
