from pymtl3 import Bits1, DefaultPassGroup

from ..STEP_LdStScoreboardRTL import STEP_LdStScoreboardRTL


def test_scoreboard_accepts_multiple_same_cycle_events():
    dut = STEP_LdStScoreboardRTL()
    dut.apply(DefaultPassGroup())
    dut.sim_reset()

    dut.thread_count_min @= 0
    dut.thread_count_max @= 4
    dut.thread_mask @= 0
    dut.require_load @= Bits1(1)
    dut.require_store @= Bits1(0)
    dut.clear @= Bits1(0)
    dut.release_take @= Bits1(0)

    dut.mem_dispatch_event_mask @= (1 << 0) | (1 << 1)
    dut.ld_done_event_mask @= (1 << 0) | (1 << 1)
    dut.st_done_event_mask @= 0
    dut.sim_tick()

    assert int(dut.ready_mask) & 0xF == 0b0011
    assert int(dut.complete_mask) & 0xF == 0b0011
    assert int(dut.all_complete) == 0

    dut.mem_dispatch_event_mask @= (1 << 2) | (1 << 3)
    dut.ld_done_event_mask @= (1 << 2) | (1 << 3)
    dut.st_done_event_mask @= 0
    dut.sim_tick()

    assert int(dut.ready_mask) & 0xF == 0b1111
    assert int(dut.complete_mask) & 0xF == 0b1111
    assert int(dut.all_ready) == 1
    assert int(dut.all_complete) == 1

