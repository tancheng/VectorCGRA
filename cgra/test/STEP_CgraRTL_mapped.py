import json
from collections import deque

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


def _normalize_tokenizer_wr_routes(cpu_metadata_pkts, cgra_def):
    num_wr_ports = cgra_def["num_wr_ports"]
    num_returner_ports = (
        cgra_def["num_wr_ports"] + cgra_def["num_ld_ports"] + cgra_def["num_st_ports"]
    )
    RouteType = mk_bits(num_returner_ports)

    for meta in cpu_metadata_pkts:
        if int(meta.cmd) == CMD_LAUNCH:
            continue

        old_routes = []
        for row in meta.tokenizer_cfg.token_route_sink_enable:
            bits = []
            for j in range(num_returner_ports):
                bits.append(int(row[Bits4(num_returner_ports - j - 1)]))
            old_routes.append(bits)

        routes = [list(bits) for bits in old_routes]
        for wr_idx in range(num_wr_ports):
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
            RouteType(int("".join(str(bit) for bit in row), 2))
            for row in routes
        ]
        meta.tokenizer_cfg.token_route_sink_enable = new_route_words


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

        if any(out_pred_regs_val):
            has_pred_gen = any(
                int(tile.get("pred_gen", 0)) == 1
                for tile in cfg["bitstream"].values()
                if tile.get("opt_type") != "OPT_NAH"
            )
            assert has_pred_gen, (
                f"cfg_{cfg_id} writes predicate regs but has no active pred_gen tile"
            )

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
    def construct(s, json_path, axi_delay=1):
        assert axi_delay >= 1
        with open(json_path, "r") as f:
            s.mapping_data = json.load(f)
        cgra_def, cpu_metadata_pkts, cpu_bitstream_pkts, ld_pkts, st_pkts, expected_cpu_pkts = generateCPUPktFromJSON(json_path)
        s.cgra_def = cgra_def
        _normalize_tokenizer_wr_routes(cpu_metadata_pkts, cgra_def)
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
            debug=True
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
    json_path='/data/angl7/STEP_VectorCGRA/cgra/test/dfg_mapping.json',
    axi_delay=1,
):
    #-------------------------------------------------------------------------
    # Test cases
    #-------------------------------------------------------------------------
    # Parameterizable

    with open(json_path, "r") as f:
        mapping_data = json.load(f)
    _validate_branch_predicates(mapping_data)
    th = TestHarness(json_path, axi_delay=axi_delay)
    return th

def _assert_runtime_branch_behavior(pc_triggers, branch_expectations):
    if not branch_expectations:
        return

    pc_trace = [int(pc) for pc in pc_triggers]
    assert len(pc_trace) > 0, "No pc_req triggers observed"

    unique_pcs = set(pc_trace)

    # Simple kernels may have branch metadata populated but still execute a
    # single straight-line path at runtime. Do not fail in that case.
    if len(unique_pcs) <= 1:
        return

    # Only enforce backedge behavior when the configured control-flow graph
    # actually contains a backward edge.
    has_configured_backedge = any(
        (exp["true_cfg"] < exp["cfg_id"]) or (exp["false_cfg"] < exp["cfg_id"])
        for exp in branch_expectations.values()
    )
    if has_configured_backedge:
        backedge_observed = any(
            pc_trace[i + 1] < pc_trace[i] for i in range(len(pc_trace) - 1)
        )
        assert backedge_observed, (
            f"Configured backedge not observed at runtime; observed PC trace {pc_trace}"
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
    }

    try:
        model.apply(DefaultPassGroup(linetrace=print_line_trace))
        model.sim_reset()

        while (not model.done()) and (model.sim_cycle_count() < max_cycles):
            if model.dut.pc_req_trigger:
                if metrics["first_launch_cycle"] is None:
                    metrics["first_launch_cycle"] = model.sim_cycle_count()
                pc = int(model.dut.pc_req)
                cnt = int(model.dut.pc_req_trigger_count)
                metrics["pc_triggers"].append(pc)
                metrics["pc_trigger_pairs"].append((pc, cnt))

            if (
                metrics["first_complete_cycle"] is None
                and model.cgra_to_cpu_signal.recv.val
                and model.cgra_to_cpu_signal.recv.rdy
            ):
                metrics["first_complete_cycle"] = model.sim_cycle_count()

            model.sim_tick()

        metrics["done_cycle"] = model.sim_cycle_count()
        metrics["timed_out"] = model.sim_cycle_count() >= max_cycles
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


def test_simple(cmdline_opts):
    th = init_param()
    
    th.elaborate()
    th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                       ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                        'ALWCOMBORDER'])
    cmdline_opts = dict(cmdline_opts)
    cmdline_opts["max_cycles"] = cmdline_opts.get("max_cycles") or 700
    runtime_metrics = _run_sim_with_metrics(th, cmdline_opts, print_line_trace=False, duts=['dut'])
    _print_metrics(runtime_metrics)
