from pymtl3 import *
from .val_rdy.ifcs import RecvIfcRTL
from .val_rdy.ifcs import SendIfcRTL
from pymtl3.stdlib.primitive import Reg
from pymtl3.stdlib.primitive import RegisterFile

#-------------------------------------------------------------------------
# Simple Timed Write Source
#-------------------------------------------------------------------------

class TimedWriteSource(Component):
    
    def construct(s, DataType, msgs, start_delay = 5, repeat_delay = 0):
        if len(msgs) == 0:
            s.done_flag = True
            s.send = SendIfcRTL(DataType)
            s.send.val //= 0
            s.send.msg //= DataType()
        else:
            assert repeat_delay >= 1
            s.send = SendIfcRTL(DataType)
            s.msgs = msgs
            DelayType = mk_bits(clog2(max(4, start_delay + repeat_delay * len(msgs))))
            IdxType = mk_bits(clog2(max(4, len(msgs) + 1)))
            CounterType = IdxType
            if DelayType.nbits > IdxType.nbits:
                CounterType = DelayType

            s.idx = OutPort( CounterType )
            s.delay_counter = OutPort( CounterType )
            s.delay_limit = OutPort( CounterType )
            s.idx_limit = OutPort( CounterType )
            s.done_flag = False

            s.next_delay = OutPort( CounterType )
            s.start_delay_w = OutPort( CounterType )
            s.repeat_delay_w = OutPort( CounterType )

            @update_ff
            def up_wires():
                if s.reset:
                    s.start_delay_w <<= start_delay
                    s.repeat_delay_w <<= repeat_delay

            @update
            def up_next_delay():
                s.next_delay @= s.start_delay_w + s.repeat_delay_w * s.idx
            
            @update_ff
            def up_counter():
                if s.reset:
                    s.delay_counter <<= 0
                    s.idx <<= 0
                    s.delay_limit <<= start_delay
                    s.idx_limit <<= len(msgs)
                else:
                    s.delay_counter <<= s.delay_counter + 1

                    if (s.delay_counter == s.next_delay) & (s.idx < s.idx_limit):
                        s.idx <<= s.idx + 1

                    if (s.idx >= s.idx_limit) & (s.idx >= 1):
                        s.done_flag = True
            
            @update
            def up_send():
                # Start sending after 5 cycles, valid for 1 cycle each
                if ~s.reset & (s.delay_counter == s.next_delay) & (s.idx < s.idx_limit):
                    s.send.val @= 1
                    s.send.msg @= msgs[s.idx]
                else:
                    s.send.val @= 0
                    s.send.msg @= DataType()

    def done(s):
        return s.done_flag

    def line_trace( s ):
        return f"{s.send}"