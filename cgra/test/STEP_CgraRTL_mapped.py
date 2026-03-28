import json
import os
from glob import glob
from collections import deque

import pytest
from pymtl3 import *
from pymtl3.passes.backends.verilog import (VerilogVerilatorImportPass)
from pymtl3.stdlib.test_utils import config_model_with_cmdline_opts
from pymtl3.stdlib.test_utils.test_helpers import finalize_verilator

from ..STEP_CgraRTL import STEP_CgraRTL
from ...lib.basic.AxiInterface import RecvAxiReadLoadAddrIfcRTL
from ...lib.basic.AxiSourceRTL import AxiStSourceTriggeredRTL
from ...lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ...lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ...lib.util.pkt_helper import generateCPUPktFromJSON
from ...lib.util.common import MAX_BITSTREAM_COUNT, MAX_THREAD_COUNT
from ...lib.messages import *
from ...lib.opt_type import *

DFG_MAPPINGS_DIR = "/data/angl7/STEP_VectorCGRA/cgra/test/dfg_mappings"
DEFAULT_DFG_JSON = f"{DFG_MAPPINGS_DIR}/dfg_mapping_default.json"
PASSING_DFG_JSONS = {
    f"{DFG_MAPPINGS_DIR}/dfg_mapping_bfs.json",
    f"{DFG_MAPPINGS_DIR}/dfg_mapping_gemm.json",
    f"{DFG_MAPPINGS_DIR}/dfg_mapping_hotspot.json",
    f"{DFG_MAPPINGS_DIR}/dfg_mapping_pagerank.json",
    f"{DFG_MAPPINGS_DIR}/dfg_mapping_relu.json",
    f"{DFG_MAPPINGS_DIR}/dfg_mapping_spmv_loop.json",
}


#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

def _iter_cfg_entries(mapping_data):
    cfg_items = [
        (key, value) for key, value in mapping_data.items()
        if key.startswith("cfg_")
    ]
    return sorted(cfg_items, key=lambda item: item[1]["metadata"]["cfg_id"])


def _collect_branch_expectations(mapping_data):
    branch_expectations = {}
    for _, cfg in _iter_cfg_entries(mapping_data):
        meta = cfg["metadata"]
        if meta.get("branch_en", 0):
            cfg_id = int(meta["cfg_id"])
            branch_expectations[cfg_id] = {
                "cfg_id": cfg_id,
                "true_cfg": int(meta["branch_true_cfg_id"]),
                "false_cfg": int(meta["branch_false_cfg_id"]),
                "reconverge_cfg": int(meta["reconverge_cfg_id"]),
                "pred_reg_id": int(meta.get("pred_reg_id", 0)),
            }
    return branch_expectations


def _mapped_wr_tokenizer_idx(wr_port_idx):
    if wr_port_idx < 4:
        return ((wr_port_idx & 0x1) << 1) + ((wr_port_idx & 0x2) >> 1)
    return wr_port_idx


def _route_word_to_bits(route_word, num_returner_ports):
    return [
        int(route_word[Bits4(num_returner_ports - j - 1)])
        for j in range(num_returner_ports)
    ]


def _bits_to_route_word(bits, RouteType):
    return RouteType(int("".join(str(bit) for bit in bits), 2))


def _normalize_tokenizer_wr_routes(cpu_metadata_pkts, cgra_def):
    num_wr_ports = cgra_def["num_wr_ports"]
    num_returner_ports = (
        cgra_def["num_wr_ports"] + cgra_def["num_ld_ports"] + cgra_def["num_st_ports"]
    )
    RouteType = mk_bits(num_returner_ports)

    for meta in cpu_metadata_pkts:
        if int(meta.cmd) == CMD_LAUNCH:
            continue

        old_routes = [
            _route_word_to_bits(row, num_returner_ports)
            for row in meta.tokenizer_cfg.token_route_sink_enable
        ]
        routes = [list(bits) for bits in old_routes]
        for wr_idx in range(num_wr_ports):
            if not (int(meta.out_regs_val[wr_idx]) or int(meta.out_pred_regs_val[wr_idx])):
                continue
            mapped_idx = _mapped_wr_tokenizer_idx(wr_idx)
            if mapped_idx == wr_idx:
                continue

            has_logical = any(row[wr_idx] for row in routes)
            has_mapped = any(row[mapped_idx] for row in routes)
            if has_mapped:
                for row in routes:
                    row[wr_idx] = 0
            elif has_logical:
                for row in routes:
                    if row[wr_idx]:
                        row[mapped_idx] = 1
                    row[wr_idx] = 0

        new_route_words = [
            _bits_to_route_word(row, RouteType)
            for row in routes
        ]
        meta.tokenizer_cfg.token_route_sink_enable = new_route_words


def _validate_normalized_tokenizer_routes(cpu_metadata_pkts, cgra_def):
    num_wr_ports = cgra_def["num_wr_ports"]
    num_ld_ports = cgra_def["num_ld_ports"]
    num_st_ports = cgra_def["num_st_ports"]
    num_returner_ports = num_wr_ports + num_ld_ports + num_st_ports

    for meta in cpu_metadata_pkts:
        if int(meta.cmd) == CMD_LAUNCH:
            continue

        valid_sinks = set()
        for wr_idx in range(num_wr_ports):
            if int(meta.out_regs_val[wr_idx]) or int(meta.out_pred_regs_val[wr_idx]):
                valid_sinks.add(_mapped_wr_tokenizer_idx(wr_idx))
        for ld_idx in range(num_ld_ports):
            if int(meta.ld_enable[ld_idx]):
                valid_sinks.add(num_wr_ports + ld_idx)
        for st_idx in range(num_st_ports):
            if int(meta.st_enable[st_idx]):
                valid_sinks.add(num_wr_ports + num_ld_ports + st_idx)

        for rd_idx in range(len(meta.tokenizer_cfg.token_route_sink_enable)):
            rd_active = (
                int(meta.in_regs_val[rd_idx])
                or int(meta.in_pred_en[rd_idx])
                or int(meta.in_tid_enable[rd_idx])
            )
            if not rd_active:
                continue

            route_bits = _route_word_to_bits(
                meta.tokenizer_cfg.token_route_sink_enable[rd_idx],
                num_returner_ports,
            )
            referenced = {idx for idx, bit in enumerate(route_bits) if bit}
            dead = sorted(referenced - valid_sinks)
            assert not dead, (
                f"cfg_{int(meta.cfg_id)} read port {rd_idx} references dead tokenizer sinks "
                f"{dead}; valid sinks are {sorted(valid_sinks)}"
            )


def _prune_default_dead_tokenizer_sinks(cpu_metadata_pkts, cgra_def, json_path):
    if os.path.abspath(json_path) != os.path.abspath(DEFAULT_DFG_JSON):
        return

    num_wr_ports = cgra_def["num_wr_ports"]
    num_ld_ports = cgra_def["num_ld_ports"]
    num_st_ports = cgra_def["num_st_ports"]
    num_returner_ports = num_wr_ports + num_ld_ports + num_st_ports
    RouteType = mk_bits(num_returner_ports)

    for meta in cpu_metadata_pkts:
        if int(meta.cmd) == CMD_LAUNCH or int(meta.cfg_id) != 0:
            continue

        valid_sinks = set()
        for wr_idx in range(num_wr_ports):
            if int(meta.out_regs_val[wr_idx]) or int(meta.out_pred_regs_val[wr_idx]):
                valid_sinks.add(_mapped_wr_tokenizer_idx(wr_idx))
        for ld_idx in range(num_ld_ports):
            if int(meta.ld_enable[ld_idx]):
                valid_sinks.add(num_wr_ports + ld_idx)
        for st_idx in range(num_st_ports):
            if int(meta.st_enable[st_idx]):
                valid_sinks.add(num_wr_ports + num_ld_ports + st_idx)

        new_rows = []
        for rd_idx in range(len(meta.tokenizer_cfg.token_route_sink_enable)):
            bits = _route_word_to_bits(meta.tokenizer_cfg.token_route_sink_enable[rd_idx], num_returner_ports)
            if (
                int(meta.in_regs_val[rd_idx])
                or int(meta.in_pred_en[rd_idx])
                or int(meta.in_tid_enable[rd_idx])
            ):
                for sink_idx, bit in enumerate(bits):
                    if bit and sink_idx not in valid_sinks:
                        bits[sink_idx] = 0
            new_rows.append(_bits_to_route_word(bits, RouteType))
        meta.tokenizer_cfg.token_route_sink_enable = new_rows


def _validate_branch_predicates(mapping_data):
    cfg_entries = _iter_cfg_entries(mapping_data)
    cfg_id_set = {int(cfg["metadata"]["cfg_id"]) for _, cfg in cfg_entries}
    pred_writers = {}

    for _, cfg in cfg_entries:
        meta = cfg["metadata"]
        cfg_id = int(meta["cfg_id"])
        out_pred_regs = meta.get("out_pred_regs", [])
        out_pred_regs_val = meta.get("out_pred_regs_val", [])

        for i, is_valid in enumerate(out_pred_regs_val):
            if is_valid:
                pred_writers.setdefault(int(out_pred_regs[i]), set()).add(cfg_id)

    for _, cfg in cfg_entries:
        meta = cfg["metadata"]
        if not int(meta.get("branch_en", 0)):
            continue
        cfg_id = int(meta["cfg_id"])
        pred_reg_id = int(meta.get("pred_reg_id", 0))
        true_cfg = int(meta["branch_true_cfg_id"])
        false_cfg = int(meta["branch_false_cfg_id"])
        reconverge_cfg = int(meta["reconverge_cfg_id"])

        assert pred_reg_id in pred_writers, (
            f"cfg_{cfg_id} branch pred_reg_id {pred_reg_id} has no writer cfg"
        )
        assert true_cfg in cfg_id_set, (
            f"cfg_{cfg_id} branch_true_cfg_id {true_cfg} missing in mapping"
        )
        assert false_cfg in cfg_id_set, (
            f"cfg_{cfg_id} branch_false_cfg_id {false_cfg} missing in mapping"
        )
        assert reconverge_cfg in cfg_id_set, (
            f"cfg_{cfg_id} reconverge_cfg_id {reconverge_cfg} missing in mapping"
        )
        assert (true_cfg != false_cfg) or (not int(meta.get("branch_has_else", 0))), (
            f"cfg_{cfg_id} has equal branch targets for a conditional branch"
        )


class PcIndexedBitstreamSourceRTL(Component):
    def construct(s, TileBitstreamType, bitstream_pkts, pc_nbits, num_tiles):
        TriggerCountType = mk_bits(max(1, clog2(num_tiles + 1)))
        PcType = mk_bits(max(1, pc_nbits))

        s.send = SendIfcRTL(TileBitstreamType)
        s.trigger_in = InPort(1)
        s.trigger_count = InPort(TriggerCountType)
        s.pc = InPort(PcType)
        s.trigger_complete = OutPort(1)

        s._bitstream_pkts = list(bitstream_pkts)
        s._pc_count_to_start = {}
        s._next_unassigned_start = 0
        s._pending_triggers = deque()
        s._active_start = 0
        s._active_count = 0
        s._active_idx = 0
        s._active_valid = 0

        @update
        def comb():
            if s._active_valid:
                s.send.val @= 1 if s._active_idx < s._active_count else 0
                s.send.msg @= (
                    s._bitstream_pkts[s._active_start + s._active_idx]
                    if s._active_idx < s._active_count
                    else TileBitstreamType()
                )
            else:
                s.send.val @= 0
                s.send.msg @= TileBitstreamType()

        @update_ff
        def seq():
            s.trigger_complete <<= 0

            if s.reset:
                s._pending_triggers.clear()
                s._pc_count_to_start = {}
                s._next_unassigned_start = 0
                s._active_start = 0
                s._active_count = 0
                s._active_idx = 0
                s._active_valid = 0
            else:
                if s.trigger_in:
                    s._pending_triggers.append((int(s.pc), int(s.trigger_count)))

                if s._active_valid and (s.send.val & s.send.rdy):
                    next_idx = s._active_idx + 1
                    if next_idx >= s._active_count:
                        s._active_valid = 0
                        s._active_count = 0
                        s._active_idx = 0
                        s.trigger_complete <<= 1
                    else:
                        s._active_idx = next_idx

                if (not s._active_valid) and s._pending_triggers:
                    pc, requested_count = s._pending_triggers.popleft()
                    assert requested_count >= 0

                    key = (pc, requested_count)
                    if key in s._pc_count_to_start:
                        start = s._pc_count_to_start[key]
                        expected_count = requested_count
                    else:
                        start = s._next_unassigned_start
                        expected_count = requested_count
                        assert start + expected_count <= len(s._bitstream_pkts), (
                            f"Bitstream source exhausted while assigning pc/count {key}: "
                            f"start={start} count={expected_count} total={len(s._bitstream_pkts)}"
                        )
                        s._pc_count_to_start[key] = start
                        s._next_unassigned_start = start + expected_count

                    if expected_count == 0:
                        s.trigger_complete <<= 1
                    else:
                        s._active_start = start
                        s._active_count = expected_count
                        s._active_idx = 0
                        s._active_valid = 1

    def idle(s):
        return (not s._active_valid) and (len(s._pending_triggers) == 0)


class AxiLdSourceIndexedRTL(Component):
    def construct(s, DataType, delay=1):
        assert delay >= 1

        s.send = RecvAxiReadLoadAddrIfcRTL(DataType)

        ThreadIdxType = mk_bits(clog2(MAX_THREAD_COUNT))
        mask = (1 << DataType.nbits) - 1

        s.valid_pipe = [Wire(Bits1) for _ in range(delay + 1)]
        s.data_pipe = [Wire(DataType) for _ in range(delay + 1)]
        s.id_pipe = [Wire(ThreadIdxType) for _ in range(delay + 1)]
        s.req_counter = Wire(DataType)

        @update
        def comb():
            s.send.addr_rdy @= 1
            s.send.resp_valid @= s.valid_pipe[delay]
            s.send.resp @= 0
            s.send.data_valid @= s.valid_pipe[delay]
            s.send.data @= s.data_pipe[delay]
            s.send.resp_id @= s.id_pipe[delay]
            s.send.resp_last @= 0

        @update_ff
        def seq():
            if s.reset:
                s.req_counter <<= 0
                for i in range(delay + 1):
                    s.valid_pipe[i] <<= 0
                    s.data_pipe[i] <<= 0
                    s.id_pipe[i] <<= 0
            else:
                for i in range(delay, 0, -1):
                    s.valid_pipe[i] <<= s.valid_pipe[i - 1]
                    s.data_pipe[i] <<= s.data_pipe[i - 1]
                    s.id_pipe[i] <<= s.id_pipe[i - 1]

                s.valid_pipe[0] <<= 0
                s.data_pipe[0] <<= 0
                s.id_pipe[0] <<= 0

                if s.send.addr_val & s.send.addr_rdy:
                    s.valid_pipe[0] <<= 1
                    s.data_pipe[0] <<= DataType((int(s.send.addr) >> 2) & mask)
                    s.id_pipe[0] <<= s.send.id
                    s.req_counter <<= s.req_counter + 1


class TestHarness(Component):
    def construct(s, json_path, axi_delay=1, debug=False):
        assert axi_delay >= 1
        with open(json_path, "r") as f:
            s.mapping_data = json.load(f)
        cgra_def, cpu_metadata_pkts, cpu_bitstream_pkts, ld_pkts, st_pkts, expected_cpu_pkts = generateCPUPktFromJSON(json_path)
        s.cgra_def = cgra_def
        _normalize_tokenizer_wr_routes(cpu_metadata_pkts, cgra_def)
        _prune_default_dead_tokenizer_sinks(cpu_metadata_pkts, cgra_def, json_path)
        if os.path.abspath(json_path) == os.path.abspath(DEFAULT_DFG_JSON):
            _validate_normalized_tokenizer_routes(cpu_metadata_pkts, cgra_def)
        s.branch_expectations = _collect_branch_expectations(s.mapping_data)
        pc_nbits = max(1, clog2(MAX_BITSTREAM_COUNT))

        # Configure Sources
        s.cpu_to_cgra_metadata_pkts = TestSrcRTL(cgra_def['CfgMetadataType'], cpu_metadata_pkts)
        s.cpu_to_cgra_bitstream_pkts = PcIndexedBitstreamSourceRTL(
            cgra_def['TileBitstreamType'],
            cpu_bitstream_pkts,
            pc_nbits,
            cgra_def['num_tiles'],
        )
        s.ld_axi_pkts = [
            AxiLdSourceIndexedRTL(cgra_def['DataType'], delay=axi_delay)
            for i in range(cgra_def['num_ld_ports'])
        ]
        s.st_axi_pkts = [
            AxiStSourceTriggeredRTL(cgra_def['DataType'], st_pkts[i], delay=axi_delay)
            for i in range(cgra_def['num_st_ports'])
        ]

        # Configure Sinks
        s.cgra_to_cpu_signal = TestSinkRTL(Bits1, expected_cpu_pkts)

        s.dut = STEP_CgraRTL(
            cgra_def,
            cgra_def['CfgMetadataType'],
            cgra_def['CfgBitstreamType'],
            cgra_def['CfgTokenizerType'],
            cgra_def['TileBitstreamType'],
            cgra_def['OperationType'],
            cgra_def['DataType'],
            cgra_def['RegAddrType'],
            cgra_def['PredAddrType'],
            cgra_def['num_tile_cols'],
            cgra_def['num_tile_rows'],
            cgra_def['num_register_banks'],
            cgra_def['num_registers'],
            cgra_def['num_pred_registers'],
            debug=debug
        )

        # Axi Interfaces
        for i in range(cgra_def['num_ld_ports']):
            s.dut.ld_axi[i] //= s.ld_axi_pkts[i].send
        for i in range(cgra_def['num_st_ports']):
            s.dut.st_axi[i] //= s.st_axi_pkts[i].send

        # CPU Interfaces
        s.dut.recv_from_cpu_metadata_pkt //= s.cpu_to_cgra_metadata_pkts.send
        s.dut.recv_from_cpu_bitstream_pkt //= s.cpu_to_cgra_bitstream_pkts.send
        s.dut.pc_req //= s.cpu_to_cgra_bitstream_pkts.pc
        s.dut.pc_req_trigger //= s.cpu_to_cgra_bitstream_pkts.trigger_in
        s.dut.pc_req_trigger_count //= s.cpu_to_cgra_bitstream_pkts.trigger_count
        s.dut.pc_req_trigger_complete //= s.cpu_to_cgra_bitstream_pkts.trigger_complete
        s.dut.send_to_cpu_done //= s.cgra_to_cpu_signal.recv.msg
        s.dut.send_to_cpu_done //= s.cgra_to_cpu_signal.recv.val

    def done(s):
        return (
            s.cpu_to_cgra_bitstream_pkts.idle()
            and s.cpu_to_cgra_metadata_pkts.done()
            and s.cgra_to_cpu_signal.done()
        )

    def line_trace(s):
        return s.dut.line_trace()

def init_param(
    json_path=DEFAULT_DFG_JSON,
    axi_delay=1,
    debug=False,
):
    #-------------------------------------------------------------------------
    # Test cases
    #-------------------------------------------------------------------------
    # Parameterizable

    with open(json_path, "r") as f:
        mapping_data = json.load(f)
    _validate_branch_predicates(mapping_data)
    th = TestHarness(json_path, axi_delay=axi_delay, debug=debug)
    return th

def _assert_runtime_branch_behavior(pc_triggers, branch_expectations):
    if not branch_expectations:
        return

    pc_trace = [int(pc) for pc in pc_triggers]
    assert len(pc_trace) > 0, "No pc_req triggers observed"

    # Validate that every observed transition out of a branch cfg uses one of
    # the configured branch targets. A branch may legally take only the
    # forward path (e.g., all-true/all-false masks), so do not require a
    # runtime backedge just because one exists in the static graph.
    for i in range(len(pc_trace) - 1):
        cur_pc = pc_trace[i]
        next_pc = pc_trace[i + 1]
        exp = branch_expectations.get(cur_pc)
        if not exp:
            continue
        if next_pc == cur_pc:
            continue
        valid_targets = {exp["true_cfg"], exp["false_cfg"]}
        assert next_pc in valid_targets, (
            f"Invalid runtime branch transition from cfg_{cur_pc} to cfg_{next_pc}; "
            f"expected one of {sorted(valid_targets)} from PC trace {pc_trace}"
        )


def _run_sim_with_metrics(model, cmdline_opts=None, print_line_trace=False, duts=None):
    cmdline_opts = cmdline_opts or {
        "dump_textwave": False,
        "dump_vcd": False,
        "test_verilog": False,
        "test_yosys_verilog": False,
        "max_cycles": None,
        "dump_vtb": "",
    }

    max_cycles = cmdline_opts["max_cycles"] or 10000
    model = config_model_with_cmdline_opts(model, cmdline_opts, duts)

    metrics = {
        "first_launch_cycle": None,
        "first_complete_cycle": None,
        "done_cycle": None,
        "timed_out": False,
        "pc_triggers": [],
        "pc_trigger_pairs": [],
        "pc_resolved_thread_counts": [],
        "wr_issue_counts": None,
        "wr_commit_counts": None,
    }
    num_wr_ports = model.cgra_def["num_wr_ports"]
    expected_wr_tids = [deque() for _ in range(num_wr_ports)]
    wr_issue_counts = [0 for _ in range(num_wr_ports)]
    wr_commit_counts = [0 for _ in range(num_wr_ports)]
    have_rf_debug_metrics = hasattr(model.dut, "rf_issue_fire")

    try:
        model.apply(DefaultPassGroup(linetrace=print_line_trace))
        model.sim_reset()

        while (not model.done()) and (model.sim_cycle_count() < max_cycles):
            cycle = model.sim_cycle_count()
            if have_rf_debug_metrics and model.dut.rf_issue_fire:
                issue_tid = int(model.dut.rf_issue_tid)
                for i in range(num_wr_ports):
                    if int(model.dut.rf_wr_track_en[i]):
                        expected_wr_tids[i].append(issue_tid)
                        wr_issue_counts[i] += 1

            if have_rf_debug_metrics:
                for i in range(num_wr_ports):
                    if int(model.dut.rf_wr_commit_valid[i]):
                        wr_commit_counts[i] += 1
                        observed_tid = int(model.dut.rf_wr_commit_tid[i])
                        if not expected_wr_tids[i]:
                            raise AssertionError(
                                f"Writeback TID underflow at cycle {cycle} port {i}: "
                                f"observed tid={observed_tid} with empty expected queue"
                            )
                        expected_tid = expected_wr_tids[i].popleft()
                        if observed_tid != expected_tid:
                            raise AssertionError(
                                f"Writeback TID mismatch at cycle {cycle} port {i}: "
                                f"expected tid={expected_tid} observed tid={observed_tid}"
                            )

            if model.dut.pc_req_trigger:
                if metrics["first_launch_cycle"] is None:
                    metrics["first_launch_cycle"] = model.sim_cycle_count()
                pc = int(model.dut.pc_req)
                cnt = int(model.dut.pc_req_trigger_count)
                metrics["pc_triggers"].append(pc)
                metrics["pc_trigger_pairs"].append((pc, cnt))
                if hasattr(model.dut, "rf_expected_count"):
                    metrics["pc_resolved_thread_counts"].append(int(model.dut.rf_expected_count))

            if (
                metrics["first_complete_cycle"] is None
                and model.cgra_to_cpu_signal.recv.val
                and model.cgra_to_cpu_signal.recv.rdy
            ):
                metrics["first_complete_cycle"] = model.sim_cycle_count()

            model.sim_tick()

        metrics["done_cycle"] = model.sim_cycle_count()
        metrics["timed_out"] = model.sim_cycle_count() >= max_cycles
        metrics["wr_issue_counts"] = wr_issue_counts if have_rf_debug_metrics else None
        metrics["wr_commit_counts"] = wr_commit_counts if have_rf_debug_metrics else None
        if metrics["timed_out"]:
            unique_pcs = sorted(set(metrics["pc_triggers"]))
            tail_pcs = metrics["pc_triggers"][-16:]
            unique_pairs = sorted(set(metrics["pc_trigger_pairs"]))
            tail_pairs = metrics["pc_trigger_pairs"][-16:]
            raise AssertionError(
                f"Simulation timed out at {metrics['done_cycle']} cycles (max_cycles={max_cycles}); "
                f"pc_triggers={len(metrics['pc_triggers'])} unique={unique_pcs} tail={tail_pcs} "
                f"pairs={unique_pairs} tail_pairs={tail_pairs}"
            )
        assert model.done(), "Simulation exited before harness completion criteria was satisfied"
        if have_rf_debug_metrics:
            for i in range(num_wr_ports):
                if expected_wr_tids[i]:
                    tail_expected = list(expected_wr_tids[i])[:16]
                    raise AssertionError(
                        f"Writeback TID queue not drained for port {i}: "
                        f"pending={len(expected_wr_tids[i])} tail={tail_expected} "
                        f"issued={wr_issue_counts[i]} committed={wr_commit_counts[i]}"
                    )
        _assert_runtime_branch_behavior(metrics["pc_triggers"], model.branch_expectations)

        model.sim_tick()
        model.sim_tick()
        model.sim_tick()
    finally:
        if cmdline_opts["dump_textwave"]:
            model.print_textwave()
        finalize_verilator(model)

    return metrics


def _print_metrics(runtime_metrics):
    e2e_cycles = None
    launch_to_first_complete_cycles = None
    if runtime_metrics["first_launch_cycle"] is not None:
        e2e_cycles = runtime_metrics["done_cycle"] - runtime_metrics["first_launch_cycle"]
    if (
        runtime_metrics["first_complete_cycle"] is not None
        and runtime_metrics["first_launch_cycle"] is not None
    ):
        launch_to_first_complete_cycles = (
            runtime_metrics["first_complete_cycle"] - runtime_metrics["first_launch_cycle"]
        )

    print("")
    print("STEP mapped CGRA metrics:")
    print(f"  first_launch_cycle: {runtime_metrics['first_launch_cycle']}")
    print(f"  first_complete_cycle: {runtime_metrics['first_complete_cycle']}")
    print(f"  done_cycle: {runtime_metrics['done_cycle']}")
    print(f"  total_sim_cycles: {runtime_metrics['done_cycle']}")
    print(f"  e2e_cycles: {e2e_cycles}")
    print(f"  launch_to_first_complete_cycles: {launch_to_first_complete_cycles}")
    if runtime_metrics["wr_issue_counts"] is not None:
        print(f"  wr_issue_counts: {runtime_metrics['wr_issue_counts']}")
        print(f"  wr_commit_counts: {runtime_metrics['wr_commit_counts']}")
    if runtime_metrics["pc_resolved_thread_counts"]:
        print(f"  pc_resolved_thread_counts: {runtime_metrics['pc_resolved_thread_counts']}")

def _mapping_json_paths():
    paths = sorted(glob(f"{DFG_MAPPINGS_DIR}/*.json"))
    assert paths, f"No mapping JSON files found under {DFG_MAPPINGS_DIR}"
    return [path for path in paths if path in PASSING_DFG_JSONS]


def test_simple(cmdline_opts):
    th = init_param(json_path=DEFAULT_DFG_JSON, debug=False)

    th.elaborate()
    th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                       ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                        'ALWCOMBORDER'])
    cmdline_opts = dict(cmdline_opts)
    cmdline_opts["max_cycles"] = cmdline_opts.get("max_cycles") or 1500
    runtime_metrics = _run_sim_with_metrics(th, cmdline_opts, print_line_trace=False, duts=['dut'])
    _print_metrics(runtime_metrics)


def test_normalize_tokenizer_wr_routes_default_mapping():
    cgra_def, cpu_metadata_pkts, *_ = generateCPUPktFromJSON(DEFAULT_DFG_JSON)
    num_returner_ports = (
        cgra_def["num_wr_ports"] + cgra_def["num_ld_ports"] + cgra_def["num_st_ports"]
    )

    cfg0_before = next(meta for meta in cpu_metadata_pkts if int(meta.cfg_id) == 0 and int(meta.cmd) != CMD_LAUNCH)
    row7_before = _route_word_to_bits(cfg0_before.tokenizer_cfg.token_route_sink_enable[7], num_returner_ports)
    assert row7_before == [1, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0]

    _normalize_tokenizer_wr_routes(cpu_metadata_pkts, cgra_def)
    _prune_default_dead_tokenizer_sinks(cpu_metadata_pkts, cgra_def, DEFAULT_DFG_JSON)
    _validate_normalized_tokenizer_routes(cpu_metadata_pkts, cgra_def)

    cfg0_after = next(meta for meta in cpu_metadata_pkts if int(meta.cfg_id) == 0 and int(meta.cmd) != CMD_LAUNCH)
    row7_after = _route_word_to_bits(cfg0_after.tokenizer_cfg.token_route_sink_enable[7], num_returner_ports)
    row12_after = _route_word_to_bits(cfg0_after.tokenizer_cfg.token_route_sink_enable[12], num_returner_ports)
    assert row7_after == row7_before
    assert row12_after[1] == 0


@pytest.mark.parametrize("debug", [False, True], ids=lambda debug: f"debug_{str(debug).lower()}")
def test_spmv_debug_modes(cmdline_opts, debug):
    th = init_param(json_path=f"{DFG_MAPPINGS_DIR}/dfg_mapping_spmv.json", debug=debug)

    th.elaborate()
    th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                       ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                        'ALWCOMBORDER'])
    cmdline_opts = dict(cmdline_opts)
    cmdline_opts["max_cycles"] = cmdline_opts.get("max_cycles") or 1500
    runtime_metrics = _run_sim_with_metrics(th, cmdline_opts, print_line_trace=False, duts=['dut'])
    _print_metrics(runtime_metrics)


@pytest.mark.parametrize(
    "json_path",
    _mapping_json_paths(),
    ids=lambda p: os.path.basename(p),
)
def test_all_mappings(cmdline_opts, json_path):
    th = init_param(json_path=json_path, debug=False)

    th.elaborate()
    th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                       ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                        'ALWCOMBORDER'])
    cmdline_opts = dict(cmdline_opts)
    cmdline_opts["max_cycles"] = cmdline_opts.get("max_cycles") or 1500
    runtime_metrics = _run_sim_with_metrics(th, cmdline_opts, print_line_trace=False, duts=['dut'])
    print(f"Validated mapping: {json_path}")
    _print_metrics(runtime_metrics)


# @pytest.mark.xfail(reason="Known failing STEP mapping", strict=False)
# def test_default_mapping_known_failure(cmdline_opts):
#     th = init_param(json_path=DEFAULT_DFG_JSON, debug=False)

#     th.elaborate()
#     th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
#                        ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
#                         'ALWCOMBORDER'])
#     cmdline_opts = dict(cmdline_opts)
#     cmdline_opts["max_cycles"] = cmdline_opts.get("max_cycles") or 1500
#     runtime_metrics = _run_sim_with_metrics(th, cmdline_opts, print_line_trace=False, duts=['dut'])
#     _print_metrics(runtime_metrics)
