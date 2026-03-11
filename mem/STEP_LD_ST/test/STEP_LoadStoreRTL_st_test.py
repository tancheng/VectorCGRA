'''
=========================================================================
ControllerRTL_test.py
=========================================================================
Simple test for ControllerRTL.

Author : Cheng Tan
  Date : Dec 15, 2024
'''
from pymtl3.passes.backends.verilog import (VerilogVerilatorImportPass)
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)

from ..STEP_LoadStoreRTL import STEP_LoadStoreRTL
from ....lib.basic.AxiSourceRTL import AxiLdSourceRTL, AxiStSourceRTL
from ....lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ....lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ....lib.messages import *
from ....lib.opt_type import *
from ....lib.basic.TimedWriteSource import TimedWriteSource


#-------------------------------------------------------------------------
# TestHarness
#-------------------------------------------------------------------------

class TestHarness(Component):
    def construct(s):
        DataType = mk_bits(8)
        num_ports = 1
        # num_requests must be >= 2
        num_req = 10
        num_empty = 2
        assert(num_req >= 2)
        initial_delay = 8
        st_data_msgs = [i + 1 for i in range(num_req)]
        # Source Pkts
        s.recv_from_ld_axi = AxiLdSourceRTL(DataType, [])

        s.recv_from_st_axi = AxiStSourceRTL(DataType, [1]*(num_req-num_empty), initial_delay)
        s.recv_from_tile_data = TestSrcRTL(DataType, st_data_msgs)
        s.recv_from_tile_pred = TestSrcRTL(Bits1, [0] * (num_empty)  + [1] * (num_req - num_empty) + [0])

        # Sink Pkts
        cmp_fn = lambda a, b : a == b
        # s.send_to_rf_pkt = TestSinkRTL(DataType, ld_data_msgs, cmp_fn=cmp_fn)
        s.ld_complete = TestSinkRTL(Bits1, [1], cmp_fn=cmp_fn)

        s.dut = STEP_LoadStoreRTL(DataType, num_ports)

        # Load Connections
        s.dut.ld_ifc[0].i_addr //= 0
        s.dut.ld_ifc[0].i_req //= 0
        s.dut.ld_tile_pred[0] //= 0
        s.dut.ld_axi[0] //= s.recv_from_ld_axi.send

        # Store Connections
        s.dut.st_axi[0] //= s.recv_from_st_axi.send
        s.dut.st_ifc[0].i_addr //= 0
        s.dut.st_ifc[0].i_data //= s.recv_from_tile_data.send.msg
        s.dut.st_ifc[0].i_req //= s.recv_from_tile_data.send.val
        s.recv_from_tile_data.send.rdy //= 1
        s.recv_from_tile_pred.send.rdy //= 1
        s.dut.st_tile_pred[0] //= s.recv_from_tile_pred.send.msg

        # Enablement Connections
        s.dut.ld_st_complete //= s.ld_complete.recv.msg
        s.dut.ld_st_complete //= s.ld_complete.recv.val
        s.dut.ld_enable[0] //= 0
        s.dut.st_enable[0] //= 1
    
        @update
        def update_cfg():
            s.dut.cfg_active_sel @= 0
            s.dut.cfg_load_sel @= 0
            s.dut.cfg_bank_commit @= 0
            s.dut.release_take @= 0
            s.dut.cfg_thread_min_bank0 @= 0
            s.dut.cfg_thread_max_bank0 @= num_req
            s.dut.cfg_thread_min_bank1 @= 0
            s.dut.cfg_thread_max_bank1 @= 0
            s.dut.cfg_thread_mask_bank0 @= 0
            s.dut.cfg_thread_mask_bank1 @= 0
            s.dut.cfg_bank_has_load0 @= 0
            s.dut.cfg_bank_has_load1 @= 0
            s.dut.cfg_bank_has_store0 @= 1
            s.dut.cfg_bank_has_store1 @= 0

    def done(s):
        return s.recv_from_st_axi.done() and s.ld_complete.done()

def init_param():
    #-------------------------------------------------------------------------
    # Test cases
    #-------------------------------------------------------------------------

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
