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
from .val_rdy.ifcs import RecvIfcRTL
from .val_rdy.ifcs import SendIfcRTL
from ...lib.util.common import *
from ...lib.basic.val_rdy.queues import NormalQueueRTL

class SourceTriggeredRTL( Component ):

    def construct( s, DataType, msgs, max_trigger_count, delay = 1 ):

        # Interface
        TriggerCountType = mk_bits(clog2(max_trigger_count + 1))
        MsgCountType = mk_bits(len(msgs))
        s.send = SendIfcRTL( DataType )
        s.trigger_in = InPort(1)
        s.trigger_count = InPort( TriggerCountType )
        s.trigger_complete = OutPort(1)
        s.complete = OutPort(1)

        # Local storage
        s.msgs = deepcopy( msgs )

        s.msg_idx    = OutPort(MsgCountType)
        s.msg_idx_n    = OutPort(MsgCountType)
        s.loaded_idx = OutPort(MsgCountType)
        s.loaded_idx_n = OutPort(MsgCountType)
        s.trigger_start_idx = OutPort(MsgCountType)
        s.trigger_complete_idx = OutPort(MsgCountType)

        # Queues
        s.q_data = NormalQueueRTL( DataType,       delay + 1 )

        # Wire connections
        s.send.msg        //= s.q_data.send.msg
        s.send.val  //= s.q_data.send.val
        s.q_data.send.rdy  //= 1

        IDLE_STATE = 0
        RUN_STATE = 1
        s.state = OutPort(mk_bits(1))

        @update
        def update_next_cnt_state():
            s.trigger_complete_idx @= s.trigger_start_idx + zext(s.trigger_count, MsgCountType.nbits)
            s.msg_idx_n @= s.msg_idx + 1
            s.loaded_idx_n @= s.loaded_idx + 1

        # Sequential enqueue
        @update_ff
        def up_src():
            # Defaults
            s.q_data.recv.val <<= 0
            s.trigger_complete <<= 0

            if s.reset:
                s.msg_idx    <<= 0
                s.loaded_idx <<= 0
                s.trigger_start_idx <<= 0
                s.state <<= IDLE_STATE
            else:
                if s.trigger_in:
                    s.state <<= RUN_STATE
                
                if s.state == RUN_STATE:
                    if (s.msg_idx < s.trigger_complete_idx) \
                        and s.msg_idx < len(s.msgs):
                        # Enqueue data
                        s.q_data.recv.msg <<= s.msgs[ s.msg_idx ]
                        s.q_data.recv.val <<= 1
                        s.msg_idx    <<= s.msg_idx_n
                        if s.msg_idx_n == s.trigger_complete_idx:
                            s.trigger_complete <<= 1
                            s.state <<= IDLE_STATE
                            s.trigger_start_idx <<= s.msg_idx_n
            if s.q_data.send.val:
                s.loaded_idx <<= s.loaded_idx_n
        
        # Debug states
        @update
        def done_state():
            s.complete @= s.loaded_idx >= len(s.msgs)

    def done( s ):
        return s.loaded_idx >= len( s.msgs )

class SourceChunkTriggeredRTL( Component ):

    def construct( s, DataType, msgs, chunk_size = 1, delay = 1 ):

        # Interface
        s.send = SendIfcRTL( DataType )
        s.trigger_in = InPort(1)
        s.trigger_complete = OutPort(1)
        s.complete = OutPort(1)

        # Local storage
        s.msgs = deepcopy( msgs )

        s.msg_idx    = 0
        s.loaded_idx = 0

        # Queues
        s.q_data = NormalQueueRTL( DataType,       delay + 1 )

        # Wire connections
        s.send.msg        //= s.q_data.send.msg
        s.send.val  //= s.q_data.send.val
        s.q_data.send.rdy  //= 1

        # Sequential enqueue
        @update_ff
        def up_src():
            # Defaults
            s.q_data.recv.val <<= 0

            if s.reset:
                s.msg_idx    = 0
                s.loaded_idx = 0

            else:
                if (s.trigger_in or s.msg_idx % chunk_size != 0) \
                        and s.msg_idx < len(s.msgs):
                    # Enqueue data
                    s.q_data.recv.msg <<= s.msgs[ s.msg_idx ]
                    s.q_data.recv.val <<= 1
                    s.msg_idx    += 1
            if s.q_data.send.val:
                s.loaded_idx += 1
        
        # Debug states
        @update
        def done_state():
            s.complete @= s.loaded_idx >= len(s.msgs)

    def done( s ):
        return s.loaded_idx >= len( s.msgs )

