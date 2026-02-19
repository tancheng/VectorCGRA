"""
========================================================================
SourceRTL
========================================================================
Test sources with RTL interfaces.

Author : Shunning Jiang
  Date : Feb 12, 2021
"""

from collections import deque
from copy import deepcopy

from pymtl3 import *
from .AxiInterface import RecvAxiReadLoadAddrIfcRTL, RecvAxiReadStoreAddrIfcRTL
from ...lib.util.common import *
from ...lib.basic.val_rdy.queues import NormalQueueRTL

class AxiLdSourceRTL( Component ):

    def construct( s, DataType, msgs, num_empty = 0, initial_delay=0, interval_delay=0 ):

        # Interface
        s.send = RecvAxiReadLoadAddrIfcRTL( DataType )

        # Data
        s.msgs = deepcopy(msgs)

        # TODO: use wires and ROM to make it translatable
        s.idx = 0
        s.count = 0

        @update
        def update_ext_signals():
            s.send.addr_rdy @= 1
            s.send.resp_valid @= 0
            s.send.resp @= 0
            s.send.resp_last @= 0

        @update_ff
        def up_src():
            if s.reset:
                s.idx   = 0
                s.count = initial_delay
                s.send.data_valid <<= 0

            else:
                if s.send.data_valid & s.send.data_ready:
                    s.idx += 1
                    s.count = interval_delay

                if s.count > 0:
                    s.count -= 1
                    s.send.data_valid <<= 0

                else: # s.count == 0
                    if s.idx < len(s.msgs):
                        s.send.data_valid <<= 1
                        s.send.data <<= s.msgs[s.idx]
                        s.send.resp_id <<= s.idx + num_empty
                    else:
                        s.send.data_valid <<= 0

    def done( s ):
        return s.idx >= len(s.msgs)

    # Line trace

    def line_trace( s ):
        return f"{s.send}"

class AxiLdSourceTriggeredRTL( Component ):

    def construct( s, DataType, msgs, delay = 1 ):

        # Interface
        s.send = RecvAxiReadLoadAddrIfcRTL( DataType )

        # Local storage
        s.msgs = deepcopy( msgs )

        ThreadIdxType = mk_bits( clog2( MAX_THREAD_COUNT ) )

        s.msg_idx    = 0
        s.loaded_idx = 0

        # Queues
        s.q_data = NormalQueueRTL( DataType,       delay + 1 )
        s.q_id   = NormalQueueRTL( ThreadIdxType,  delay + 1 )

        # Wire connections
        s.send.data        //= s.q_data.send.msg
        s.send.data_valid  //= s.q_data.send.val
        s.send.resp_id     //= s.q_id.send.msg

        s.send.resp_last   //= 0

        s.q_data.send.rdy  //= 1
        s.q_id.send.rdy    //= 1

        # External AXI signals
        @update
        def update_ext_signals():
            s.send.addr_rdy   @= 1
            s.send.resp_valid @= 0
            s.send.resp       @= 0

        # Canonical enqueue condition
        s.fire = OutPort(Bits1)
        @update
        def comb_fire():
            s.fire @= (
                ( s.msg_idx < len( s.msgs ) ) &
                s.send.addr_val &
                s.send.addr_rdy
            )

        # Sequential enqueue
        @update_ff
        def up_src():

            # Defaults
            s.q_data.recv.val <<= 0
            s.q_id.recv.val   <<= 0

            if s.reset:
                s.msg_idx    = 0
                s.loaded_idx = 0

            else:
                if s.fire:
                    # Enqueue data
                    s.q_data.recv.msg <<= s.msgs[ s.msg_idx ]
                    s.q_data.recv.val <<= 1

                    # Enqueue ID
                    s.q_id.recv.msg   <<= s.send.id
                    s.q_id.recv.val   <<= 1

                    s.msg_idx    += 1
            if s.q_id.send.val:
                s.loaded_idx += 1

    def done( s ):
        return s.loaded_idx >= len( s.msgs )


class AxiStSourceRTL( Component ):

    def construct( s, DataType, msgs, initial_delay=0, interval_delay=0 ):

        # Interface
        s.send = RecvAxiReadStoreAddrIfcRTL( DataType )

        # Data
        s.msgs = deepcopy(msgs)

        # TODO: use wires and ROM to make it translatable
        s.idx = 0
        s.count = 0

        @update
        def update_ext_signals():
            s.send.addr_rdy @= 1
            s.send.resp_last @= 0
            s.send.resp_id @= s.idx

        @update_ff
        def up_src():
            if s.reset:
                s.idx   = 0
                s.count = initial_delay
                s.send.resp_valid <<= 0

            else:
                if s.send.resp_valid & s.send.resp_ready:
                    s.idx += 1
                    s.count = interval_delay

                if s.count > 0:
                    s.count -= 1
                    s.send.resp_valid <<= 0

                else: # s.count == 0
                    if s.idx < len(s.msgs):
                        s.send.resp_valid <<= 1
                        s.send.resp <<= s.msgs[s.idx]
                    else:
                        s.send.resp_valid <<= 0

    def done( s ):
        return s.idx >= len(s.msgs)

    # Line trace

    def line_trace( s ):
        return f"{s.send}"

class AxiStSourceTriggeredRTL( Component ):

    def construct( s, DataType, num_total_stores, delay = 1 ):
        assert(delay >= 1)
        s.num_total_stores = num_total_stores

        # Interface
        s.send = RecvAxiReadStoreAddrIfcRTL( DataType )
        
        # Thread Id
        s.idx = 0
        ThreadIdxType = mk_bits(clog2(MAX_THREAD_COUNT))

        # Queue to Delay
        s.q_data = NormalQueueRTL( Bits2, delay + 1 )
        s.q_id = NormalQueueRTL( ThreadIdxType, delay + 1 )

        # Wire connections
        s.send.resp //= s.q_data.send.msg
        s.send.resp_id //= s.q_id.send.msg
        s.send.addr_rdy //= s.q_data.recv.rdy
        s.send.resp_last //= 0
        s.q_data.send.rdy //= 1
        s.q_id.send.rdy //= 1

        # Canonical enqueue condition
        s.fire = OutPort(Bits1)
        @update
        def comb_fire():
            s.fire @= (
                ( s.idx < num_total_stores ) &
                s.send.addr_val &
                s.send.data_valid
            )

        @update_ff
        def up_src():
            if s.reset:
                s.idx = 0
            s.q_data.recv.msg <<= 0
            s.q_id.recv.msg <<= 0
            
            if s.fire:
                # Data signals
                s.q_data.recv.msg <<= 1
                s.q_id.recv.msg <<= s.send.id

                # Valid signals
                s.q_data.recv.val <<= 1
                s.q_id.recv.val <<= 1
                
            s.send.resp_valid <<= s.q_data.send.msg[0]
            if s.send.resp_valid:
                # Increment counter
                s.idx += 1

    def done( s ):
        return s.idx >= s.num_total_stores

    # Line trace

    def line_trace( s ):
        return f"{s.send}"