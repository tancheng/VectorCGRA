from pymtl3 import *
from pymtl3.stdlib.primitive import Reg
from ...lib.basic.val_rdy.queues import NormalQueueRTL
from ...lib.basic.AxiInterface import SendAxiReadStoreAddrIfcRTL, RecvAxiStoreIfcRTL
from ...lib.messages import *
from ...lib.util.common import *

class STEP_StoreRTL( Component ):
   
    def construct( s, DataType, queue_depth=8):
        StCountType = mk_bits( clog2(MAX_THREAD_COUNT + 1) )
        # Use the given interfaces
        s.axi = SendAxiReadStoreAddrIfcRTL(DataType)  # Note: This interface handles both read/write
        s.store_ifc = RecvAxiStoreIfcRTL(DataType)
        
        # Add tile tracking interface
        s.thread_span = InPort( clog2(MAX_THREAD_COUNT + 1) )
        s.enable = InPort( 1 )
        s.i_tile_pred = InPort( 1 )             # Tile data indicator  
        s.issue_tid = InPort( clog2(MAX_THREAD_COUNT) )
        s.issue_bank = InPort( Bits1 )
        s.o_tile_complete = OutPort( 1 )        # All tile stores complete
        s.o_done_tid = OutPort( clog2(MAX_THREAD_COUNT) )
        s.o_done_bank = OutPort( Bits1 )
        
        # Return token for new data
        s.token_return = OutPort( 1 )

        # Internal queues and state
        StoreReqType = mk_st_req_pkt(DataType)
        
        s.store_queue = NormalQueueRTL( StoreReqType, queue_depth )
        s.bank_queue = NormalQueueRTL( Bits1, queue_depth )
        s.outstanding_stores = OutPort( StCountType )
        s.resp_counter = Wire( clog2(MAX_THREAD_COUNT + 1) )
        ## DEBUG
        s.store_queue_rdy = OutPort( 1 )
        s.store_queue_rdy //= s.store_queue.recv.rdy
        
        # Tile tracking
        s.tile_counter = OutPort( clog2(MAX_THREAD_COUNT + 1) )
        s.tile_last_seen = OutPort( 1 )
        s.stores_in_tile = OutPort( StCountType )  # Stores from current tile
        
        transfer_size_bits = clog2((DataType.nbits + 7) // 8)
        strobe_width = (DataType.nbits + 7) // 8
        
        # Input request handling with tile tracking
        @update_ff
        def tile_tracking():
            # Default trigger token as output addr is valid
            s.token_return <<= s.store_queue.send.val

            if s.reset | s.o_tile_complete:
                s.tile_counter <<= 0
                s.tile_last_seen <<= 0
                s.stores_in_tile <<= 0
                s.resp_counter <<= 0
            else:
                if s.store_ifc.i_req & s.store_queue.recv.rdy:
                    if s.enable & s.i_tile_pred:
                        s.stores_in_tile <<= s.stores_in_tile + 1
                    else:
                        # Disabled or predicated-off requests should release the token
                        # without entering the memory pipeline.
                        s.token_return <<= 1
                    if s.enable:
                        s.tile_counter <<= s.tile_counter + 1
                        
                        # Check if we've hit the threshold
                        if s.tile_counter + 1 >= s.thread_span:
                            s.tile_last_seen <<= 1
                
                # Decrement stores_in_tile when responses come back
                if s.axi.resp_valid & s.axi.resp_ready:
                    s.resp_counter <<= s.resp_counter + 1
                    # Check that we have not also tried to increment.
                    if s.store_ifc.i_req & s.store_queue.recv.rdy & s.i_tile_pred:
                        s.stores_in_tile <<= s.stores_in_tile
                    else:
                        s.stores_in_tile <<= s.stores_in_tile - 1
        
        # Input request handling - queue store requests when they come in
        @update
        def input_handling():
            handshake = s.store_ifc.i_req & s.store_queue.recv.rdy & s.i_tile_pred & s.enable
            # Queue the request when valid and queue has space
            s.store_queue.recv.val @= handshake
            s.store_queue.recv.msg.addr @= s.store_ifc.i_addr
            s.store_queue.recv.msg.data @= s.store_ifc.i_data
            s.store_queue.recv.msg.id @= s.issue_tid
            s.bank_queue.recv.val @= handshake
            s.bank_queue.recv.msg @= s.issue_bank

            s.store_ifc.o_rdy @= s.store_queue.recv.rdy

            
        # Track outstanding transactions
        @update_ff
        def outstanding_counter():
            if s.reset:
                s.outstanding_stores <<= 0
            else:
                # Direct combinational logic - no state machine delays
                addr_sent = s.store_queue.send.val & s.store_queue.send.rdy & s.axi.addr_rdy
                resp_recv = s.axi.resp_valid & s.axi.resp_ready
                
                if addr_sent & ~resp_recv:
                    s.outstanding_stores <<= s.outstanding_stores + 1
                elif resp_recv & ~addr_sent:
                    s.outstanding_stores <<= s.outstanding_stores - 1
                # If both happen same cycle, counter stays same

        # Direct address channel control - no state machine
        @update
        def addr_channel():
            # Send address directly when queue has data and AXI is ready
            s.axi.addr_val @= s.store_queue.send.val
            s.axi.addr     @= s.store_queue.send.msg.addr
            s.axi.cache    @= 0b0011    # Cacheable, bufferable for coherency
            s.axi.len      @= 0         # Single beat transfer
            s.axi.size     @= transfer_size_bits
            s.axi.burst    @= 1         # INCR burst type
            s.axi.id       @= s.store_queue.send.msg.id
            
            # Dequeue address when both sides are ready
            s.store_queue.send.rdy @= s.axi.addr_rdy
       
        # Direct data channel control - no state machine
        @update
        def data_channel():
            # Drive write data directly when we have outstanding stores
            s.axi.data @= s.store_queue.send.msg.data if s.store_queue.send.val else 0
            s.axi.data_valid @= s.store_queue.send.val
            s.axi.data_ready @= s.store_queue.recv.rdy  # Ready to send data
            
            # Write strobes - all bytes valid for the data width
            s.axi.str_bytes @= ((1 << strobe_width) - 1) if s.store_queue.send.val else 0
       
        # Direct response channel control - no state machine
        @update
        def resp_channel():
            # Always ready to receive responses when we have outstanding stores
            s.axi.resp_ready @= s.outstanding_stores > 0
            s.store_ifc.o_done @= s.axi.resp_valid & s.axi.resp_ready
            s.o_done_tid @= s.axi.resp_id if s.store_ifc.o_done else 0
            s.o_done_bank @= s.bank_queue.send.msg if s.store_ifc.o_done else Bits1(0)
            s.bank_queue.send.rdy @= s.store_ifc.o_done
            
            # Tile completion: tile_last_seen AND all stores from tile complete
            s.o_tile_complete @= s.tile_last_seen & (s.stores_in_tile == 0) & (s.outstanding_stores == 0)
