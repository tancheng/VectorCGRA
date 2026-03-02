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

    def construct( s, DataType, msgs, chunk_size = 1, delay = 1 ):

        # Interface
        s.send = SendIfcRTL( DataType )
        s.trigger_in = InPort(Bits1)
        s.complete = OutPort(Bits1)

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

