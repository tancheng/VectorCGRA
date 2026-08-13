from types import SimpleNamespace

from ..script_generator import TileSignals


def make_signal(ctrl_addr, reads=(), writes=()):
    signal = SimpleNamespace(
        ctrl_addr=ctrl_addr,
        read_towards_reg_idx=[-1] * 4,
        read_reg_towards_fu=[-1] * 4,
        read_reg_towards_xbar=[-1] * 4,
        read_reg_retain=[0] * 4,
        write_to_reg=[-1] * 4,
        write_to_reg_idx=[-1] * 4,
    )
    for bank, register in reads:
        signal.read_towards_reg_idx[bank] = register
        signal.read_reg_towards_fu[bank] = 1
    for bank, register in writes:
        signal.write_to_reg[bank] = 1
        signal.write_to_reg_idx[bank] = register
    return signal


def test_marks_only_reads_before_the_final_user():
    write = make_signal(0, writes=((0, 3),))
    first_read = make_signal(1, reads=((0, 3),))
    final_read = make_signal(2, reads=((0, 3),))

    TileSignals.mark_nonfinal_register_reads(
        None, [final_read, write, first_read])

    assert first_read.read_reg_retain[0] == 1
    assert final_read.read_reg_retain[0] == 0


def test_same_step_conditional_write_keeps_a_version_for_later_read():
    read_modify_write = make_signal(
        0, reads=((0, 3),), writes=((0, 3),))
    later_read = make_signal(1, reads=((0, 3),))

    TileSignals.mark_nonfinal_register_reads(
        None, [read_modify_write, later_read])

    assert read_modify_write.read_reg_retain[0] == 1


def test_loop_carried_read_modify_write_keeps_a_live_version():
    read_modify_write = make_signal(
        0, reads=((0, 3),), writes=((0, 3),))

    TileSignals.mark_nonfinal_register_reads(None, [read_modify_write])

    assert read_modify_write.read_reg_retain[0] == 1
