from pymtl3 import *
from ...lib.util.common import *


class STEP_LdStScoreboardRTL(Component):
    def construct(s):
        TidType = mk_bits(clog2(MAX_THREAD_COUNT))
        CountType = mk_bits(clog2(MAX_THREAD_COUNT + 1))
        QueueIdxType = mk_bits(clog2(MAX_THREAD_COUNT))
        QueueCountType = mk_bits(clog2(MAX_THREAD_COUNT + 1))
        MaskType = mk_bits(MAX_THREAD_COUNT)

        s.mem_dispatch_event_mask = InPort(MaskType)
        s.ld_done_event_mask = InPort(MaskType)
        s.st_done_event_mask = InPort(MaskType)
        s.thread_count_min = InPort(CountType)
        s.thread_count_max = InPort(CountType)
        s.thread_mask = InPort(MaskType)
        s.require_load = InPort(1)
        s.require_store = InPort(1)
        s.clear = InPort(1)
        s.release_take = InPort(1)

        s.ready_mask = OutPort(MaskType)
        s.complete_mask = OutPort(MaskType)
        s.all_ready = OutPort(1)
        s.all_complete = OutPort(1)
        s.release_valid = OutPort(1)
        s.release_tid = OutPort(TidType)

        s.mem_dispatch_mask = Wire(MaskType)
        s.ld_done_mask = Wire(MaskType)
        s.st_done_mask = Wire(MaskType)
        s.release_seen_mask = Wire(MaskType)
        s.mem_dispatch_mask_next = Wire(MaskType)
        s.ld_done_mask_next = Wire(MaskType)
        s.st_done_mask_next = Wire(MaskType)
        s.ready_mask_next = Wire(MaskType)
        s.complete_mask_next = Wire(MaskType)
        s.new_complete_events = Wire(MaskType)

        s.release_q = [Wire(TidType) for _ in range(MAX_THREAD_COUNT)]
        s.release_head = Wire(QueueIdxType)
        s.release_tail = Wire(QueueIdxType)
        s.release_count = Wire(QueueCountType)
        s.target_mask = Wire(MaskType)

        zero_mask = MaskType(0)

        @update
        def comb_target_mask():
            target_mask = s.thread_mask
            if s.thread_mask == zero_mask:
                target_mask = zero_mask
                for i in range(MAX_THREAD_COUNT):
                    tid_bits = CountType(i)
                    if (tid_bits >= s.thread_count_min) & (tid_bits < s.thread_count_max):
                        target_mask = target_mask | MaskType(1 << i)
            s.target_mask @= target_mask

        @update
        def comb_event_masks():
            s.mem_dispatch_mask_next @= s.mem_dispatch_mask | s.mem_dispatch_event_mask
            s.ld_done_mask_next @= s.ld_done_mask | s.ld_done_event_mask
            s.st_done_mask_next @= s.st_done_mask | s.st_done_event_mask

        @update
        def comb_progress_masks():
            ready_mask_next = s.target_mask
            if s.require_load | s.require_store:
                ready_mask_next = s.mem_dispatch_mask_next & s.target_mask

            complete_mask_next = ready_mask_next
            if s.require_load:
                complete_mask_next = complete_mask_next & s.ld_done_mask_next
            if s.require_store:
                complete_mask_next = complete_mask_next & s.st_done_mask_next

            s.ready_mask_next @= ready_mask_next
            s.complete_mask_next @= complete_mask_next
            s.new_complete_events @= complete_mask_next & ~s.release_seen_mask

        @update_ff
        def ff_masks_and_queue():
            if s.reset | s.clear:
                s.mem_dispatch_mask <<= zero_mask
                s.ld_done_mask <<= zero_mask
                s.st_done_mask <<= zero_mask
                s.release_seen_mask <<= zero_mask
                s.release_head <<= QueueIdxType(0)
                s.release_tail <<= QueueIdxType(0)
                s.release_count <<= QueueCountType(0)
                for i in range(MAX_THREAD_COUNT):
                    s.release_q[i] <<= TidType(0)
            else:
                release_seen_next = s.release_seen_mask
                release_head_next = s.release_head
                release_tail_next = s.release_tail
                release_count_next = s.release_count

                if s.release_take & (s.release_count > QueueCountType(0)):
                    if s.release_head == QueueIdxType(MAX_THREAD_COUNT - 1):
                        release_head_next = QueueIdxType(0)
                    else:
                        release_head_next = s.release_head + QueueIdxType(1)
                    release_count_next = s.release_count - QueueCountType(1)

                for i in range(MAX_THREAD_COUNT):
                    one_hot_i = MaskType(1 << i)
                    if s.new_complete_events & one_hot_i:
                        s.release_q[release_tail_next] <<= TidType(i)
                        release_seen_next = release_seen_next | one_hot_i
                        if release_tail_next == QueueIdxType(MAX_THREAD_COUNT - 1):
                            release_tail_next = QueueIdxType(0)
                        else:
                            release_tail_next = release_tail_next + QueueIdxType(1)
                        release_count_next = release_count_next + QueueCountType(1)

                s.mem_dispatch_mask <<= s.mem_dispatch_mask_next
                s.ld_done_mask <<= s.ld_done_mask_next
                s.st_done_mask <<= s.st_done_mask_next
                s.release_seen_mask <<= release_seen_next
                s.release_head <<= release_head_next
                s.release_tail <<= release_tail_next
                s.release_count <<= release_count_next

        @update
        def comb_outs():
            ready_mask = s.target_mask
            if s.require_load | s.require_store:
                ready_mask = s.mem_dispatch_mask & s.target_mask

            complete_mask = ready_mask
            if s.require_load:
                complete_mask = complete_mask & s.ld_done_mask
            if s.require_store:
                complete_mask = complete_mask & s.st_done_mask

            s.ready_mask @= ready_mask
            s.complete_mask @= complete_mask
            s.all_ready @= Bits1(ready_mask == s.target_mask)
            s.all_complete @= Bits1(complete_mask == s.target_mask)
            s.release_valid @= Bits1(s.release_count > QueueCountType(0))
            if s.release_count > QueueCountType(0):
                s.release_tid @= s.release_q[s.release_head]
            else:
                s.release_tid @= TidType(0)
