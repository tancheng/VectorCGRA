from pymtl3 import *
from ...lib.util.common import *


class STEP_LdStScoreboardRTL(Component):
    def construct(s):
        TidType = mk_bits(clog2(MAX_THREAD_COUNT))
        CountType = mk_bits(clog2(MAX_THREAD_COUNT))

        # Pulses per tid
        s.launch_tid_val = InPort(1)
        s.launch_tid = InPort(TidType)
        s.ld_done_val = InPort(1)
        s.ld_done_tid = InPort(TidType)
        s.st_done_val = InPort(1)
        s.st_done_tid = InPort(TidType)
        s.thread_count = InPort(CountType)
        s.clear = InPort(1)

        # Outputs
        s.inflight_mask = OutPort(mk_bits(MAX_THREAD_COUNT))
        s.done_mask = OutPort(mk_bits(MAX_THREAD_COUNT))
        s.all_launched = OutPort(1)
        s.all_done = OutPort(1)

        s.inflight = Wire(mk_bits(MAX_THREAD_COUNT))
        s.done = Wire(mk_bits(MAX_THREAD_COUNT))
        one_mask = mk_bits(MAX_THREAD_COUNT)(1)
        zero_mask = mk_bits(MAX_THREAD_COUNT)(0)

        @update_ff
        def ff_masks():
            if s.reset | s.clear:
                s.inflight <<= 0
                s.done <<= 0
            else:
                launch_one_hot = zero_mask
                ld_done_one_hot = zero_mask
                st_done_one_hot = zero_mask
                if s.launch_tid_val:
                    launch_one_hot = one_mask << s.launch_tid
                if s.ld_done_val:
                    ld_done_one_hot = one_mask << s.ld_done_tid
                if s.st_done_val:
                    st_done_one_hot = one_mask << s.st_done_tid

                inflight_next = (s.inflight | launch_one_hot) & ~(ld_done_one_hot | st_done_one_hot)
                done_next = s.done | ld_done_one_hot | st_done_one_hot

                s.inflight <<= inflight_next
                s.done <<= done_next

        @update
        def comb_outs():
            target_mask = zero_mask
            if s.thread_count > 0:
                target_mask = (one_mask << s.thread_count) - one_mask
            s.inflight_mask @= s.inflight
            s.done_mask @= s.done
            s.all_launched @= Bits1((s.inflight | s.done) == target_mask)
            s.all_done @= Bits1(s.done == target_mask)
