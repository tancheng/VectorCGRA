from pymtl3 import *
from ...lib.util.common import *


class STEP_LdStScoreboardRTL(Component):
    def construct(s):
        TidType = mk_bits(clog2(MAX_THREAD_COUNT))
        CountType = mk_bits(clog2(MAX_THREAD_COUNT))
        QueueIdxType = mk_bits(clog2(MAX_THREAD_COUNT))
        QueueCountType = mk_bits(clog2(MAX_THREAD_COUNT + 1))
        MaskType = mk_bits(MAX_THREAD_COUNT)

        s.mem_dispatch_tid_val = InPort(1)
        s.mem_dispatch_tid = InPort(TidType)
        s.ld_done_tid_val = InPort(1)
        s.ld_done_tid = InPort(TidType)
        s.st_done_tid_val = InPort(1)
        s.st_done_tid = InPort(TidType)
        s.thread_count = InPort(CountType)
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

        s.release_q = [Wire(TidType) for _ in range(MAX_THREAD_COUNT)]
        s.release_head = Wire(QueueIdxType)
        s.release_tail = Wire(QueueIdxType)
        s.release_count = Wire(QueueCountType)

        zero_mask = MaskType(0)

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
                mem_dispatch_next = s.mem_dispatch_mask
                ld_done_next = s.ld_done_mask
                st_done_next = s.st_done_mask
                release_seen_next = s.release_seen_mask
                release_head_next = s.release_head
                release_tail_next = s.release_tail
                release_count_next = s.release_count

                ready_after_events = zero_mask
                complete_after_events = zero_mask
                if s.thread_mask != zero_mask:
                    target_mask = s.thread_mask
                else:
                    target_mask = zero_mask

                for i in range(MAX_THREAD_COUNT):
                    one_hot_i = MaskType(1 << i)
                    if (s.thread_mask == zero_mask) & (s.thread_count > CountType(i)):
                        target_mask = target_mask | one_hot_i
                    if s.mem_dispatch_tid_val & (s.mem_dispatch_tid == TidType(i)):
                        mem_dispatch_next = mem_dispatch_next | one_hot_i
                    if s.ld_done_tid_val & (s.ld_done_tid == TidType(i)):
                        ld_done_next = ld_done_next | one_hot_i
                    if s.st_done_tid_val & (s.st_done_tid == TidType(i)):
                        st_done_next = st_done_next | one_hot_i

                if s.require_load | s.require_store:
                    ready_after_events = mem_dispatch_next
                else:
                    ready_after_events = target_mask

                complete_after_events = ready_after_events
                if s.require_load:
                    complete_after_events = complete_after_events & ld_done_next
                if s.require_store:
                    complete_after_events = complete_after_events & st_done_next

                if s.release_take & (s.release_count > QueueCountType(0)):
                    if s.release_head == QueueIdxType(MAX_THREAD_COUNT - 1):
                        release_head_next = QueueIdxType(0)
                    else:
                        release_head_next = s.release_head + QueueIdxType(1)
                    release_count_next = s.release_count - QueueCountType(1)

                for i in range(MAX_THREAD_COUNT):
                    one_hot_i = MaskType(1 << i)
                    if (complete_after_events & one_hot_i) & ~(release_seen_next & one_hot_i):
                        s.release_q[release_tail_next] <<= TidType(i)
                        release_seen_next = release_seen_next | one_hot_i
                        if release_tail_next == QueueIdxType(MAX_THREAD_COUNT - 1):
                            release_tail_next = QueueIdxType(0)
                        else:
                            release_tail_next = release_tail_next + QueueIdxType(1)
                        release_count_next = release_count_next + QueueCountType(1)

                s.mem_dispatch_mask <<= mem_dispatch_next
                s.ld_done_mask <<= ld_done_next
                s.st_done_mask <<= st_done_next
                s.release_seen_mask <<= release_seen_next
                s.release_head <<= release_head_next
                s.release_tail <<= release_tail_next
                s.release_count <<= release_count_next

        @update
        def comb_outs():
            if s.thread_mask != zero_mask:
                target_mask = s.thread_mask
            else:
                target_mask = zero_mask
            for i in range(MAX_THREAD_COUNT):
                if (s.thread_mask == zero_mask) & (s.thread_count > CountType(i)):
                    target_mask = target_mask | MaskType(1 << i)

            if s.require_load | s.require_store:
                s.ready_mask @= s.mem_dispatch_mask & target_mask
            else:
                s.ready_mask @= target_mask

            complete_mask = s.ready_mask
            if s.require_load:
                complete_mask = complete_mask & s.ld_done_mask
            if s.require_store:
                complete_mask = complete_mask & s.st_done_mask

            s.complete_mask @= complete_mask
            s.all_ready @= Bits1(s.ready_mask == target_mask)
            s.all_complete @= Bits1(s.complete_mask == target_mask)
            s.release_valid @= Bits1(s.release_count > QueueCountType(0))
            if s.release_count > QueueCountType(0):
                s.release_tid @= s.release_q[s.release_head]
            else:
                s.release_tid @= TidType(0)
