from pymtl3 import *
from ...lib.basic.val_rdy.queues import NormalQueueRTL
from ...lib.basic.AxiInterface import SendAxiReadLoadAddrIfcRTL, RecvAxiLoadIfcRTL
from ...lib.messages import *
from ...lib.util.common import *

class STEP_LoadRTL( Component ):
    def construct( s, DataType, queue_depth=8 ):
        LdCountType = mk_bits( clog2(MAX_THREAD_COUNT + 1) )
        # Interfaces
        s.axi = SendAxiReadLoadAddrIfcRTL(DataType)
        s.load_ifc = RecvAxiLoadIfcRTL(DataType)
        
        # Add tile tracking interface
        s.thread_span = InPort( clog2(MAX_THREAD_COUNT) )
        s.enable = InPort( 1 )
        s.i_tile_pred = InPort( 1 )             # Tile data indicator  
        s.issue_tid = InPort( clog2(MAX_THREAD_COUNT) )
        s.issue_bank = InPort( Bits1 )
        s.o_tile_complete = OutPort( 1 )        # All tile loads complete
        s.o_data_bank = OutPort( Bits1 )

        # Return token for new data
        s.token_return = OutPort( 1 )

        # Internal queues for streaming
        LdReqType = mk_ld_req_pkt()
        LdRespType = mk_ld_resp_pkt(DataType)
        s.addr_queue = NormalQueueRTL( LdReqType, queue_depth )  # Store addresses
        s.data_queue = NormalQueueRTL( LdRespType, queue_depth ) # Store responses
        s.bank_queue = NormalQueueRTL( Bits1, queue_depth )
        
        # Outstanding request counter
        s.outstanding_reqs = OutPort( LdCountType )
        
        # Tile tracking
        s.tile_counter = OutPort( clog2(MAX_THREAD_COUNT) )
        s.tile_last_seen = OutPort( 1 )
        s.loads_in_tile = OutPort( LdCountType )  # Loads from current tile
        
        transfer_size_bits = clog2((DataType.nbits + 7) // 8)
        id_mask = (1 << clog2(MAX_THREAD_COUNT)) - 1
        
        # Input request handling with tile tracking
        @update_ff
        def tile_tracking():
            # Default trigger token as output addr is valid
            s.token_return <<= s.addr_queue.send.val

            if s.reset | s.o_tile_complete:
                s.tile_counter <<= 0
                s.tile_last_seen <<= 0
                s.loads_in_tile <<= 0
            else:
                if s.load_ifc.i_req & s.addr_queue.recv.rdy:
                    if s.enable & s.i_tile_pred:
                        s.loads_in_tile <<= s.loads_in_tile + 1
                    else:
                        # Disabled or predicated-off requests should release the token
                        # without entering the memory pipeline.
                        s.token_return <<= 1
                    if s.enable:
                        s.tile_counter <<= s.tile_counter + 1
                        
                        # Check if we've hit the threshold
                        if s.tile_counter + 1 >= s.thread_span:
                            s.tile_last_seen <<= 1
                
                # Decrement loads_in_tile when data comes back and is consumed
                if s.data_queue.send.val & s.data_queue.send.rdy:
                    # Check that we have not also tried to increment.
                    if s.load_ifc.i_req & s.addr_queue.recv.rdy & s.i_tile_pred:
                        s.loads_in_tile <<= s.loads_in_tile
                    else:
                        s.loads_in_tile <<= s.loads_in_tile - 1
       
        # Input request handling - queue addresses when requests come in
        @update
        def input_handling():
            # Queue the address when request is valid and queue has space
            s.addr_queue.recv.val @= s.load_ifc.i_req & s.addr_queue.recv.rdy & s.i_tile_pred & s.enable
            s.addr_queue.recv.msg.addr @= s.load_ifc.i_addr
            s.addr_queue.recv.msg.id @= s.issue_tid
            s.bank_queue.recv.val @= s.load_ifc.i_req & s.addr_queue.recv.rdy & s.i_tile_pred & s.enable
            s.bank_queue.recv.msg @= s.issue_bank
            s.load_ifc.o_rdy @= s.addr_queue.recv.rdy

        
        # Track outstanding requests
        @update_ff
        def outstanding_counter():
            if s.reset:
                s.outstanding_reqs <<= 0
            else:
                # Direct combinational logic - no state machine delays
                addr_sent = s.addr_queue.send.val & s.addr_queue.send.rdy & s.axi.addr_rdy
                data_recv = s.axi.data_valid & s.axi.data_ready & s.data_queue.recv.rdy
                
                if addr_sent & ~data_recv:
                    s.outstanding_reqs <<= s.outstanding_reqs + 1
                elif data_recv & ~addr_sent:
                    s.outstanding_reqs <<= s.outstanding_reqs - 1
                # If both happen same cycle, counter stays same
        
        # Direct address channel control - no state machine
        @update
        def addr_channel():
            # Send address directly when queue has data and AXI is ready
            s.axi.addr_val @= s.addr_queue.send.val
            s.axi.addr     @= s.addr_queue.send.msg.addr if s.addr_queue.send.val else 0
            s.axi.cache    @= 0b0011    # Cacheable, bufferable for coherency
            s.axi.len      @= 0         # Single beat
            s.axi.size     @= transfer_size_bits
            s.axi.burst    @= 1         # INCR
            # Guard the ID so we don't propagate garbage bits when queue is empty
            # Mask to AXI ID width (clog2(MAX_THREAD_COUNT) == 9)
            s.axi.id       @= (s.addr_queue.send.msg.id & id_mask) if s.addr_queue.send.val else 0
            
            # Dequeue address when both sides are ready
            s.addr_queue.send.rdy @= s.axi.addr_rdy
       
        # Direct data channel control - no state machine
        @update
        def data_channel():
            # Always ready to receive data when we have outstanding requests
            # and space in the data queue
            s.axi.data_ready @= s.data_queue.recv.rdy
            
            # Enqueue received data directly
            s.data_queue.recv.val @= s.axi.data_valid & s.axi.data_ready
            s.data_queue.recv.msg.data @= s.axi.data
            # Mask resp_id to prevent stray upper bits from violating Bits9
            s.data_queue.recv.msg.id @= s.axi.resp_id & id_mask
            
        # Output data handling
        @update
        def output_handling():
            # Stream output data when available
            has_data = s.data_queue.send.val
            s.load_ifc.o_data    @= s.data_queue.send.msg.data if has_data else 0
            s.load_ifc.o_done    @= has_data  # Data available = done
            # Guard data_id to prevent uninitialized queue contents from leaking
            s.load_ifc.o_data_id @= s.data_queue.send.msg.id if has_data else 0
            s.o_data_bank @= s.bank_queue.send.msg if has_data else Bits1(0)
            s.data_queue.send.rdy @= 1  # Always consume output data
            s.bank_queue.send.rdy @= has_data

            
            # Tile completion: tile_last_seen AND all loads from tile complete
            s.o_tile_complete @= s.tile_last_seen & (s.loads_in_tile == 0) & (s.outstanding_reqs == 0)
