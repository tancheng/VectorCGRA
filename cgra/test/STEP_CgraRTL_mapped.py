from pymtl3.passes.backends.verilog import (VerilogVerilatorImportPass)
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)

from ..STEP_CgraRTL import STEP_CgraRTL
from ...lib.basic.AxiSourceRTL import AxiLdSourceRTL, AxiLdSourceTriggeredRTL, AxiStSourceRTL, AxiStSourceTriggeredRTL
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
    def construct(s):
        cgra_def, cpu_metadata_pkts, cpu_bitstream_pkts, ld_pkts, st_pkts, expected_cpu_pkts = generateCPUPktFromJSON('/data/angl7/STEP_VectorCGRA/cgra/test/dfg_mapping.json')
        s.cgra_def = cgra_def

        # Configure Sources
        s.cpu_to_cgra_metadata_pkts = TestSrcRTL(cgra_def['CfgMetadataType'], cpu_metadata_pkts)
        s.cpu_to_cgra_bitstream_pkts = SourceTriggeredRTL(cgra_def['TileBitstreamType'], cpu_bitstream_pkts, chunk_size=cgra_def['num_tiles'], delay=1)
        s.ld_axi_pkts = [AxiLdSourceTriggeredRTL(cgra_def['DataType'], ld_pkts[i]) for i in range(cgra_def['num_ld_ports'])]
        s.st_axi_pkts = [AxiStSourceTriggeredRTL(cgra_def['DataType'], st_pkts[i]) for i in range(cgra_def['num_st_ports'])]

        # Configure Sinks
        cmp_fn = lambda a, b : a == b
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
        s.dut.send_to_cpu_done //= s.cgra_to_cpu_signal.recv.msg
        s.dut.send_to_cpu_done //= s.cgra_to_cpu_signal.recv.val

    def done(s):
        for i in range(s.cgra_def['num_ld_ports']):
            if not s.ld_axi_pkts[i].done():
                return False
        for i in range(s.cgra_def['num_st_ports']):
            if not s.st_axi_pkts[i].done():
                return False
        return s.cpu_to_cgra_bitstream_pkts.done() and s.cpu_to_cgra_metadata_pkts.done() and s.cgra_to_cpu_signal.done()

    def line_trace(s):
        return s.dut.line_trace()

def init_param():
    #-------------------------------------------------------------------------
    # Test cases
    #-------------------------------------------------------------------------
    # Parameterizable

    th = TestHarness()
    return th

def test_simple(cmdline_opts):
    th = init_param()
    
    th.elaborate()
    th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                       ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                        'ALWCOMBORDER'])
    th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
    run_sim(th)  # Added max_cycles to prevent infinite simulation