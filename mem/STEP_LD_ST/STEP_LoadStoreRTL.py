from pymtl3 import *
from .STEP_LoadRTL import STEP_LoadRTL
from .STEP_StoreRTL import STEP_StoreRTL
from ...lib.util.common import *
from ...lib.basic.AxiInterface import SendAxiReadLoadAddrIfcRTL, SendAxiReadStoreAddrIfcRTL, \
                            RecvAxiLoadIfcRTL, RecvAxiStoreIfcRTL

class STEP_LoadStoreRTL( Component ):
    def construct(s, DataType, num_ports=1, queue_depth=8):
        ###### Interface #####
        s.ld_axi = [SendAxiReadLoadAddrIfcRTL(DataType) for _ in range(num_ports)]
        s.ld_ifc = [RecvAxiLoadIfcRTL(DataType) for _ in range(num_ports)]
        s.ld_tile_pred = [InPort(1) for _ in range(num_ports)]
        
        s.st_axi = [SendAxiReadStoreAddrIfcRTL(DataType) for _ in range(num_ports)]
        s.st_ifc = [RecvAxiStoreIfcRTL(DataType) for _ in range(num_ports)]
        s.st_tile_pred = [InPort(1) for _ in range(num_ports)]

        s.thread_count = InPort( clog2(MAX_THREAD_COUNT) )
        
        # Enable/disable individual units
        s.ld_enable = [InPort(1) for _ in range(num_ports)]  # Enable load unit i
        s.st_enable = [InPort(1) for _ in range(num_ports)]  # Enable store unit i
        
        # Mark Ld/St completion for Cfg when all ENABLED units complete
        s.ld_st_complete = OutPort(1)

        ###### Load/Store Units #########
        s.ld_units = [STEP_LoadRTL(DataType) for _ in range(num_ports)]
        s.st_units = [STEP_StoreRTL(DataType) for _ in range(num_ports)]

        #### DEBUG
        s.ld_complete = [OutPort(1) for _ in range(num_ports)]
        s.st_complete = [OutPort(1) for _ in range(num_ports)]
        for i in range(num_ports):
            s.ld_complete[i] //= s.ld_units[i].o_tile_complete
            s.st_complete[i] //= s.st_units[i].o_tile_complete
        s.outstanding_reqs = OutPort( clog2(queue_depth + 1) )
        s.outstanding_reqs //= s.ld_units[1].outstanding_reqs
        s.loads_in_tile = OutPort( clog2(queue_depth + 1) )
        s.loads_in_tile //= s.ld_units[1].loads_in_tile
        s.store_queue_rdy = OutPort(1)
        s.store_queue_rdy //= s.st_units[1].store_queue_rdy
        s.outstanding_stores = OutPort( clog2(queue_depth + 1) )
        s.outstanding_stores //= s.st_units[1].outstanding_stores
        s.stores_in_tile = OutPort( clog2(queue_depth + 1) )
        s.stores_in_tile //= s.st_units[1].stores_in_tile
        s.ld_tile_last_seen = [OutPort(1) for _ in range(num_ports)]
        for i in range(num_ports):
            s.ld_tile_last_seen[i] //= s.ld_units[i].tile_last_seen
        ####
        
        ###### Wire Connections #########
        for i in range(num_ports):
            # Load Unit connections
            s.ld_axi[i] //= s.ld_units[i].axi
            s.ld_ifc[i] //= s.ld_units[i].load_ifc
            s.ld_tile_pred[i] //= s.ld_units[i].i_tile_pred
            s.thread_count //= s.ld_units[i].thread_count
            
            # Store Unit connections
            s.st_axi[i] //= s.st_units[i].axi
            s.st_ifc[i] //= s.st_units[i].store_ifc
            s.st_tile_pred[i] //= s.st_units[i].i_tile_pred
            s.thread_count //= s.st_units[i].thread_count
       
        @update
        def update_ld_st_complete():
            # Start with complete = True, then AND with each enabled unit
            complete = Bits1(1)
            
            for i in range(num_ports):
                # For load units: if enabled, must be complete; if disabled, ignore
                ld_condition = (~s.ld_enable[i]) | s.ld_units[i].o_tile_complete
                complete = complete & ld_condition
                
                # For store units: if enabled, must be complete; if disabled, ignore
                st_condition = (~s.st_enable[i]) | s.st_units[i].o_tile_complete
                complete = complete & st_condition
            
            s.ld_st_complete @= complete