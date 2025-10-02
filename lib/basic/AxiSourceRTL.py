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

class AxiLdSourceRTL( Component ):

    def construct( s, DataType, msgs, num_empty, initial_delay=0, interval_delay=0 ):

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

