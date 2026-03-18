from pymtl3 import *
from pymtl3.passes.backends.verilog import (VerilogVerilatorImportPass)
from pymtl3.stdlib.test_utils import config_model_with_cmdline_opts
from pymtl3.stdlib.test_utils.test_helpers import finalize_verilator

from ..STEP_CgraRTL import STEP_CgraRTL
from ...lib.basic.AxiSourceRTL import AxiLdSourceTriggeredRTL, AxiStSourceTriggeredRTL
from ...lib.basic.SourceTriggeredRTL import SourceTriggeredRTL
from ...lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ...lib.util.pkt_helper import generateCPUPktFromJSON
from ...lib.messages import *
from ...lib.opt_type import *


#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):
    def construct(s, json_path, axi_delay=1):
        assert axi_delay >= 1
        cgra_def, cpu_metadata_pkts, cpu_bitstream_pkts, ld_pkts, st_pkts, expected_cpu_pkts = generateCPUPktFromJSON(json_path)
        s.cgra_def = cgra_def

        # Configure Sources
        s.cpu_to_cgra_metadata_pkts = TestSrcRTL(cgra_def['CfgMetadataType'], cpu_metadata_pkts)
        s.cpu_to_cgra_bitstream_pkts = SourceTriggeredRTL(cgra_def['TileBitstreamType'], cpu_bitstream_pkts, chunk_size=cgra_def['num_tiles'], delay=1)
        s.ld_axi_pkts = [
            AxiLdSourceTriggeredRTL(cgra_def['DataType'], ld_pkts[i], delay=axi_delay)
            for i in range(cgra_def['num_ld_ports'])
        ]
        s.st_axi_pkts = [
            AxiStSourceTriggeredRTL(cgra_def['DataType'], st_pkts[i], delay=axi_delay)
            for i in range(cgra_def['num_st_ports'])
        ]

        # Configure Sinks
        s.cgra_to_cpu_signal = TestSinkRTL(Bits1, expected_cpu_pkts)

        s.dut = STEP_CgraRTL(
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
        s.dut.pc_req_trigger //= s.cpu_to_cgra_bitstream_pkts.trigger_in
        s.dut.pc_req_trigger_count //= s.cpu_to_cgra_bitstream_pkts.trigger_count
        s.dut.pc_req_trigger_complete //= s.cpu_to_cgra_bitstream_pkts.trigger_complete
        s.dut.send_to_cpu_done //= s.cgra_to_cpu_signal.recv.msg
        s.dut.send_to_cpu_done //= s.cgra_to_cpu_signal.recv.val

    def done(s):
        for i in range(s.cgra_def['num_st_ports']):
            if not s.st_axi_pkts[i].done():
                return False
        return s.cpu_to_cgra_bitstream_pkts.done() and s.cpu_to_cgra_metadata_pkts.done() and s.cgra_to_cpu_signal.done()

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

    th = TestHarness(json_path, axi_delay=axi_delay)
    return th

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
    }

    try:
        model.apply(DefaultPassGroup(linetrace=print_line_trace))
        model.sim_reset()

        while (not model.done()) and (model.sim_cycle_count() < max_cycles):
            if (metrics["first_launch_cycle"] is None) and model.dut.pc_req_trigger:
                metrics["first_launch_cycle"] = model.sim_cycle_count()

            if (
                metrics["first_complete_cycle"] is None
                and model.cgra_to_cpu_signal.recv.val
                and model.cgra_to_cpu_signal.recv.rdy
            ):
                metrics["first_complete_cycle"] = model.sim_cycle_count()

            model.sim_tick()

        metrics["done_cycle"] = model.sim_cycle_count()
        metrics["timed_out"] = model.sim_cycle_count() >= max_cycles
        assert not metrics["timed_out"], f"Simulation timed out at {metrics['done_cycle']} cycles (max_cycles={max_cycles})"
        assert model.done(), "Simulation exited before harness completion criteria was satisfied"

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
