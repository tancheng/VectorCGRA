from pymtl3 import *
from ..lib.basic.val_rdy.ifcs import RecvIfcRTL, SendIfcRTL
from pymtl3.stdlib.primitive import Reg
from ..mem.register_cluster.STEP_RegisterFileRTL import STEP_RegisterFileRTL
from ..mem.register_cluster.STEP_RegisterFileFullBankRTL import STEP_RegisterFileFullBankRTL
from ..lib.messages import *
from ..lib.opt_type import *
from ..lib.util.common import *

class STEP_RegisterFileControllerRTL( Component ):
    def construct(s,
                    num_tiles,
                    RegDataType,
                    RegAddrType,
                    PredAddrType,
                    CfgMetadataType,
                    num_ld_ports,
                    num_st_ports,
                    num_banks=2,
                    num_rd_ports=2,
                    num_wr_ports=2,
                    num_registers=16,
                    num_pred_registers = 16,
                    enable_double_buffering = False,
                    debug = True,
                    ):

        # -------------------------------------------------------------------------
        # Submodules
        # -------------------------------------------------------------------------
        print("total read ports", num_rd_ports)

        # s.register_file = STEP_RegisterFileRTL(
        #     RegDataType, RegAddrType,
        #     num_reg_banks=num_banks,
        #     num_rd_ports=num_rd_ports,
        #     num_wr_ports=num_wr_ports + num_ld_ports,
        #     num_registers_per_reg_bank=num_registers // num_banks
        # )
        s.register_file = STEP_RegisterFileFullBankRTL(RegDataType, RegAddrType, num_registers,
                num_rd_ports=num_rd_ports,
                num_wr_ports=num_wr_ports + num_ld_ports,
                num_registers_per_reg_bank=MAX_THREAD_COUNT)

        # External ifcs
        s.recv_cfg_from_ctrl = RecvIfcRTL( CfgMetadataType )   # from main ctrl
        s.recv_cfg_thread_mask = InPort(mk_bits(MAX_THREAD_COUNT))
        s.rd_data            = [ OutPort(RegDataType) for _ in range(num_rd_ports) ]
        s.wr_data            = [ InPort(RegDataType) for _ in range(num_wr_ports) ]
        s.cfg_done           = OutPort( 1 )                # level-true when RUN complete this cycle
        s.cfg_ready_for_next = OutPort( 1 )
        s.dep_mode_out       = OutPort( 1 )
        s.recv_pred_port = [ InPort(1) for _ in range(num_wr_ports)]
        s.send_tile_preds = [ OutPort(Bits1) for _ in range(num_tiles)]
        s.pred_any_true = [ OutPort(Bits1) for _ in range(num_pred_registers) ]
        s.pred_any_false = [ OutPort(Bits1) for _ in range(num_pred_registers) ]
        s.pred_complete = [ OutPort(Bits1) for _ in range(num_pred_registers) ]
        s.pred_true_count = [ OutPort(mk_bits(clog2(MAX_THREAD_COUNT))) for _ in range(num_pred_registers) ]
        s.pred_false_count = [ OutPort(mk_bits(clog2(MAX_THREAD_COUNT))) for _ in range(num_pred_registers) ]
        s.pred_true_mask = [ OutPort(mk_bits(MAX_THREAD_COUNT)) for _ in range(num_pred_registers) ]
        s.pred_false_mask = [ OutPort(mk_bits(MAX_THREAD_COUNT)) for _ in range(num_pred_registers) ]
        s.cfg_active_sel_w = Wire(Bits1)
        s.cfg_load_sel_w = Wire(Bits1)
        s.cfg_swap_w = Wire(Bits1)
        s.cfg_dep_start_w = Wire(Bits1)
        if enable_double_buffering:
            s.cfg_active_sel = InPort(Bits1)
            s.cfg_load_sel = InPort(Bits1)
            s.cfg_swap = InPort(Bits1)
            s.cfg_dep_start = InPort(Bits1)
            @update
            def cfg_select_wires():
                s.cfg_active_sel_w @= s.cfg_active_sel
                s.cfg_load_sel_w @= s.cfg_load_sel
                s.cfg_swap_w @= s.cfg_swap
                s.cfg_dep_start_w @= s.cfg_dep_start
        else:
            @update
            def cfg_select_wires():
                s.cfg_active_sel_w @= Bits1(0)
                s.cfg_load_sel_w @= Bits1(0)
                s.cfg_swap_w @= Bits1(0)
                s.cfg_dep_start_w @= Bits1(0)
        s.send_thread_min = OutPort( clog2(MAX_THREAD_COUNT) )
        s.send_thread_max = OutPort( clog2(MAX_THREAD_COUNT) )
        s.ld_enable = [OutPort(1) for _ in range(num_ld_ports)]
        s.st_enable = [OutPort(1) for _ in range(num_st_ports)]
        s.ld_st_complete = InPort(1)
        s.mem_ready_mask_bank0 = InPort(mk_bits(MAX_THREAD_COUNT))
        s.mem_ready_mask_bank1 = InPort(mk_bits(MAX_THREAD_COUNT))
        s.mem_complete_mask_bank0 = InPort(mk_bits(MAX_THREAD_COUNT))
        s.mem_complete_mask_bank1 = InPort(mk_bits(MAX_THREAD_COUNT))
        s.mem_release_valid = InPort(1)
        s.mem_release_tid = InPort(clog2(MAX_THREAD_COUNT))
        s.mem_release_take = OutPort(1)
        s.cfg_thread_min_bank0 = OutPort(clog2(MAX_THREAD_COUNT))
        s.cfg_thread_max_bank0 = OutPort(clog2(MAX_THREAD_COUNT))
        s.cfg_thread_min_bank1 = OutPort(clog2(MAX_THREAD_COUNT))
        s.cfg_thread_max_bank1 = OutPort(clog2(MAX_THREAD_COUNT))
        s.cfg_thread_mask_bank0 = OutPort(mk_bits(MAX_THREAD_COUNT))
        s.cfg_thread_mask_bank1 = OutPort(mk_bits(MAX_THREAD_COUNT))
        s.cfg_bank_has_load0 = OutPort(Bits1)
        s.cfg_bank_has_load1 = OutPort(Bits1)
        s.cfg_bank_has_store0 = OutPort(Bits1)
        s.cfg_bank_has_store1 = OutPort(Bits1)
        s.ld_data = [InPort(RegDataType) for _ in range(num_ld_ports)]
        s.ld_data_valid = [InPort(1) for _ in range(num_ld_ports)]
        s.ld_data_id = [InPort(clog2(MAX_THREAD_COUNT)) for _ in range(num_ld_ports)]
        s.ld_req_accepted = [InPort(1) for _ in range(num_ld_ports)]
        s.st_req_accepted = [InPort(1) for _ in range(num_st_ports)]
        s.ld_issue_tid = [OutPort(clog2(MAX_THREAD_COUNT)) for _ in range(num_ld_ports)]
        s.st_issue_tid = [OutPort(clog2(MAX_THREAD_COUNT)) for _ in range(num_st_ports)]
        s.tile_token_take = [ OutPort(1) for _ in range(num_rd_ports) ]
        s.tile_token_return = [ OutPort(1) for _ in range(num_wr_ports) ]
        s.tile_token_avail = [ InPort(1) for _ in range(num_rd_ports) ]
        s.tile_token_shifter_out = [ InPort(1) for _ in range(num_wr_ports) ]
        s.tile_token_take_req = [ Wire(Bits1) for _ in range(num_rd_ports) ]
        s.tile_token_take_pair_req = [ Wire(Bits1) for _ in range(num_rd_ports) ]
        s.tile_token_take_pair_mirror = [ Wire(Bits1) for _ in range(num_rd_ports) ]
        s.tile_token_avail_pair = [ Wire(Bits1) for _ in range(num_rd_ports) ]

        s.pred_tile_valid_active = [ Wire(Bits1) for _ in range(num_tiles) ]
        s.pred_tile_valid_bank0 = [ Wire(Bits1) for _ in range(num_tiles) ]
        s.pred_tile_valid_bank1 = [ Wire(Bits1) for _ in range(num_tiles) ]
        s.cfg_bank_valid0 = Wire(Bits1)
        s.cfg_bank_valid1 = Wire(Bits1)

        # Predicate register file
        PredCountType = mk_bits(clog2(MAX_THREAD_COUNT))
        MaskType = mk_bits(MAX_THREAD_COUNT)
        s.pred_count = [ Wire(PredCountType) for _ in range(num_pred_registers) ]
        s.pred_expected = [ Wire(PredCountType) for _ in range(num_pred_registers) ]
        s.pred_any_true_reg = [ Wire(Bits1) for _ in range(num_pred_registers) ]
        s.pred_any_false_reg = [ Wire(Bits1) for _ in range(num_pred_registers) ]
        s.pred_true_count_reg = [ Wire(PredCountType) for _ in range(num_pred_registers) ]
        s.pred_false_count_reg = [ Wire(PredCountType) for _ in range(num_pred_registers) ]
        s.pred_true_mask_reg = [ Wire(MaskType) for _ in range(num_pred_registers) ]
        s.pred_false_mask_reg = [ Wire(MaskType) for _ in range(num_pred_registers) ]
        s.pred_seen_mask_reg = [ Wire(MaskType) for _ in range(num_pred_registers) ]
        s.pred_count_next = [ Wire(PredCountType) for _ in range(num_pred_registers) ]
        s.pred_expected_next = [ Wire(PredCountType) for _ in range(num_pred_registers) ]
        s.pred_any_true_next = [ Wire(Bits1) for _ in range(num_pred_registers) ]
        s.pred_any_false_next = [ Wire(Bits1) for _ in range(num_pred_registers) ]
        s.pred_true_count_next = [ Wire(PredCountType) for _ in range(num_pred_registers) ]
        s.pred_false_count_next = [ Wire(PredCountType) for _ in range(num_pred_registers) ]
        s.pred_true_mask_next = [ Wire(MaskType) for _ in range(num_pred_registers) ]
        s.pred_false_mask_next = [ Wire(MaskType) for _ in range(num_pred_registers) ]
        s.pred_seen_mask_next = [ Wire(MaskType) for _ in range(num_pred_registers) ]
        s.active_pred_reg = Wire(PredAddrType)
        s.active_branch_en = Wire(Bits1)
        s.active_const_store = Wire(Bits1)
        num_tile_rows_local = num_wr_ports // 2
        num_tile_cols_local = num_tiles // num_tile_rows_local
        for i in range(num_rd_ports):
            s.tile_token_take_pair_mirror[i] //= s.tile_token_take_pair_req[i ^ 2]
            s.tile_token_avail_pair[i] //= s.tile_token_avail[i ^ 2]

        @update
        def select_predicates():
            for i in range(num_tiles):
                s.send_tile_preds[i] @= s.pred_tile_valid_active[i]

        @update
        def comb_cfg_bank_requirements():
            bank0_has_load = Bits1(0)
            bank1_has_load = Bits1(0)
            bank0_has_store = Bits1(0)
            bank1_has_store = Bits1(0)
            for i in range(num_ld_ports):
                bank0_has_load = bank0_has_load | s.ld_enable_bank0[i]
                bank1_has_load = bank1_has_load | s.ld_enable_bank1[i]
            for i in range(num_st_ports):
                bank0_has_store = bank0_has_store | s.st_enable_bank0[i]
                bank1_has_store = bank1_has_store | s.st_enable_bank1[i]
            s.cfg_thread_min_bank0 @= s.active_thread_min_bank0
            s.cfg_thread_max_bank0 @= s.active_thread_max_bank0
            s.cfg_thread_min_bank1 @= s.active_thread_min_bank1
            s.cfg_thread_max_bank1 @= s.active_thread_max_bank1
            s.cfg_thread_mask_bank0 @= s.active_thread_mask_bank0
            s.cfg_thread_mask_bank1 @= s.active_thread_mask_bank1
            s.cfg_bank_has_load0 @= bank0_has_load
            s.cfg_bank_has_load1 @= bank1_has_load
            s.cfg_bank_has_store0 @= bank0_has_store
            s.cfg_bank_has_store1 @= bank1_has_store

        @update
        def pred_reduce():
            for r in range(num_pred_registers):
                s.pred_any_true[r] @= s.pred_any_true_reg[r]
                s.pred_any_false[r] @= s.pred_any_false_reg[r]
                s.pred_complete[r] @= (s.pred_count[r] >= s.pred_expected[r]) & (s.pred_expected[r] > 0)
                s.pred_true_count[r] @= s.pred_true_count_reg[r]
                s.pred_false_count[r] @= s.pred_false_count_reg[r]
                s.pred_true_mask[r] @= s.pred_true_mask_reg[r]
                s.pred_false_mask[r] @= s.pred_false_mask_reg[r]

        # Helpful observability (optional)
        # Debug Flags TODO: @darrenl to delete
        MaxThreadType        = mk_bits( clog2( MAX_THREAD_COUNT ) )
        s.recv_cfg_thread_mask_resolved = Wire(MaskType)
        s.recv_cfg_thread_count_resolved = Wire(MaxThreadType)
        s.recv_cfg_thread_min_resolved = Wire(MaxThreadType)
        s.recv_cfg_thread_max_resolved = Wire(MaxThreadType)

        s.wr_addr_valcfg_o   = [ OutPort(Bits1)       for _ in range(num_wr_ports) ]
        s.ld_addr            = [ OutPort(RegAddrType) for _ in range(num_ld_ports) ]

        # Ld/St Unit Configuration
        s.ld_enable_active = [ Wire(Bits1) for _ in range(num_ld_ports) ]
        s.st_enable_active = [ Wire(Bits1) for _ in range(num_st_ports) ]
        s.ld_reg_addr_active = [ Wire(RegAddrType) for _ in range(num_ld_ports) ]
        s.ld_enable_bank0 = [ Wire(Bits1) for _ in range(num_ld_ports) ]
        s.ld_enable_bank1 = [ Wire(Bits1) for _ in range(num_ld_ports) ]
        s.st_enable_bank0 = [ Wire(Bits1) for _ in range(num_st_ports) ]
        s.st_enable_bank1 = [ Wire(Bits1) for _ in range(num_st_ports) ]
        s.ld_reg_addr_bank0 = [ Wire(RegAddrType) for _ in range(num_ld_ports) ]
        s.ld_reg_addr_bank1 = [ Wire(RegAddrType) for _ in range(num_ld_ports) ]
        for i in range(num_ld_ports):
            s.ld_enable[i] //= s.ld_enable_active[i]
            s.ld_addr[i] //= s.ld_reg_addr_active[i]
        for i in range(num_st_ports):
            s.st_enable[i] //= s.st_enable_active[i]

        # -------------------------------------------------------------------------
        # FSM + config registers
        # -------------------------------------------------------------------------

        # States
        ST_IDLE = Bits1(0)
        ST_RUN  = Bits1(1)

        # State reg
        s.state    = Wire( 1 )
        s.state_n  = OutPort( 1 )

        # Latched configuration (stable during RUN)
        s.rd_addr_cfg    = [ Wire(RegAddrType) for _ in range(num_rd_ports) ]
        s.rd_addr_valcfg = [ Wire(Bits1)       for _ in range(num_rd_ports) ]
        s.tid_enabled    = [ Wire(Bits1)       for _ in range(num_rd_ports) ]
        s.wr_addr_cfg    = [ Wire(RegAddrType) for _ in range(num_wr_ports) ]
        s.wr_addr_valcfg = [ Wire(Bits1)       for _ in range(num_wr_ports) ]
        s.pred_wr_valcfg = [ Wire(Bits1)       for _ in range(num_wr_ports) ]
        s.expected_count = Wire( MaxThreadType )
        s.active_thread_min = Wire(MaxThreadType)
        s.active_thread_max = Wire(MaxThreadType)
        s.rd_addr_cfg_bank0    = [ Wire(RegAddrType) for _ in range(num_rd_ports) ]
        s.rd_addr_cfg_bank1    = [ Wire(RegAddrType) for _ in range(num_rd_ports) ]
        s.rd_addr_valcfg_bank0 = [ Wire(Bits1)       for _ in range(num_rd_ports) ]
        s.rd_addr_valcfg_bank1 = [ Wire(Bits1)       for _ in range(num_rd_ports) ]
        s.tid_enabled_bank0    = [ Wire(Bits1)       for _ in range(num_rd_ports) ]
        s.tid_enabled_bank1    = [ Wire(Bits1)       for _ in range(num_rd_ports) ]
        s.pred_reg_bank0       = Wire(PredAddrType)
        s.pred_reg_bank1       = Wire(PredAddrType)
        s.branch_en_bank0      = Wire(Bits1)
        s.branch_en_bank1      = Wire(Bits1)
        s.const_store_bank0    = Wire(Bits1)
        s.const_store_bank1    = Wire(Bits1)
        s.wr_addr_cfg_bank0    = [ Wire(RegAddrType) for _ in range(num_wr_ports) ]
        s.wr_addr_cfg_bank1    = [ Wire(RegAddrType) for _ in range(num_wr_ports) ]
        s.wr_addr_valcfg_bank0 = [ Wire(Bits1)       for _ in range(num_wr_ports) ]
        s.wr_addr_valcfg_bank1 = [ Wire(Bits1)       for _ in range(num_wr_ports) ]
        s.pred_wr_valcfg_bank0 = [ Wire(Bits1)       for _ in range(num_wr_ports) ]
        s.pred_wr_valcfg_bank1 = [ Wire(Bits1)       for _ in range(num_wr_ports) ]
        s.expected_count_bank0 = Wire( MaxThreadType )
        s.expected_count_bank1 = Wire( MaxThreadType )
        s.active_thread_min_bank0 = Wire(MaxThreadType)
        s.active_thread_max_bank0 = Wire(MaxThreadType)
        s.active_thread_min_bank1 = Wire(MaxThreadType)
        s.active_thread_max_bank1 = Wire(MaxThreadType)
        s.active_thread_mask = Wire(MaskType)
        s.active_thread_mask_bank0 = Wire(MaskType)
        s.active_thread_mask_bank1 = Wire(MaskType)
        s.dep_thread_mask = Wire(MaskType)
        s.dep_complete_mask = Wire(MaskType)
        s.nonmem_ready_mask = Wire(MaskType)
        s.active_target_mask = Wire(MaskType)
        s.issue_count = Wire(MaxThreadType)
        s.issue_count_n = Wire(MaxThreadType)
        s.dep_mode = Wire(Bits1)
        s.dep_mode_n = Wire(Bits1)
        s.run_primed = Wire(Bits1)
        s.run_primed_n = Wire(Bits1)
        s.current_issue_tid = Wire(MaxThreadType)
        s.current_issue_tid_data = Wire(RegDataType)
        s.issue_fire = Wire(Bits1)
        s.any_wr_enabled = Wire(Bits1)
        s.ld_seq_count = [Wire(MaxThreadType) for _ in range(num_ld_ports)]
        s.st_seq_count = [Wire(MaxThreadType) for _ in range(num_st_ports)]
        s.ld_seq_count_n = [Wire(MaxThreadType) for _ in range(num_ld_ports)]
        s.st_seq_count_n = [Wire(MaxThreadType) for _ in range(num_st_ports)]
        s.wr_thread_tid = [Wire(MaxThreadType) for _ in range(num_wr_ports)]
        s.pred_wr_addr_cfg = [ Wire(PredAddrType) for _ in range(num_wr_ports) ]
        s.pred_wr_addr_cfg_bank0 = [ Wire(PredAddrType) for _ in range(num_wr_ports) ]
        s.pred_wr_addr_cfg_bank1 = [ Wire(PredAddrType) for _ in range(num_wr_ports) ]

        s.send_thread_min //= s.active_thread_min
        s.send_thread_max //= s.active_thread_max

        if RegDataType.nbits >= MaxThreadType.nbits:
            @update
            def comb_current_issue_tid_data():
                s.current_issue_tid_data @= zext(s.current_issue_tid, RegDataType.nbits)
        else:
            @update
            def comb_current_issue_tid_data():
                s.current_issue_tid_data @= trunc(s.current_issue_tid, RegDataType.nbits)

        # Counters (increment on handshakes)
        s.rd_count = [ Wire(MaxThreadType) for _ in range(num_rd_ports) ]
        s.wr_count = [ Wire(MaxThreadType) for _ in range(num_wr_ports) ]

        # Next values
        s.rd_count_n = [ OutPort(MaxThreadType) for _ in range(num_rd_ports) ]
        s.wr_count_n = [ OutPort(MaxThreadType) for _ in range(num_wr_ports) ]
        s.rd_addr_valcfg_n = [ OutPort(Bits1) for _ in range(num_rd_ports) ]
        s.wr_addr_valcfg_n = [ OutPort(Bits1) for _ in range(num_wr_ports) ]
        s.rd_addr_cfg_n    = [ OutPort(RegAddrType) for _ in range(num_rd_ports) ]
        s.wr_addr_cfg_n    = [ OutPort(RegAddrType) for _ in range(num_wr_ports) ]
        s.tid_enabled_n    = [ Wire(Bits1)       for _ in range(num_rd_ports) ]
        s.expected_count_n = Wire( MaxThreadType )

        #TODO: @darrenl delete me debug statements
        if debug:
            for i in range(num_wr_ports):
                s.wr_addr_valcfg_o[i] //= s.wr_addr_valcfg_n[i]
            
            s.rf_ld_wr_reg_addr = [OutPort(RegAddrType)   for _ in range(num_ld_ports)]
            s.rf_ld_wr_tid_addr = [OutPort(MaxThreadType) for _ in range(num_ld_ports)]
            s.rf_ld_wr_data     = [OutPort(RegDataType)   for _ in range(num_ld_ports)]
            s.rf_ld_wr_enable   = [OutPort(Bits1)         for _ in range(num_ld_ports)]
            s.rf_rd_tid_addr = [OutPort(MaxThreadType) for _ in range(num_rd_ports)]
            s.rf_rd_data = [OutPort(RegDataType) for _ in range(num_rd_ports)]
            s.rf_rd_addr = [OutPort(RegAddrType) for _ in range(num_rd_ports)]
            for i in range(num_ld_ports):
                s.rf_ld_wr_reg_addr[i] //= s.ld_reg_addr_active[i]
                s.rf_ld_wr_tid_addr[i] //= s.ld_data_id[i]
                s.rf_ld_wr_data[i] //= s.ld_data[i]
                s.rf_ld_wr_enable[i] //= s.ld_data_valid[i]
            @update
            def update_some_ports():
                for i in range(num_rd_ports):
                    s.rf_rd_tid_addr[i] @= s.current_issue_tid
                    s.rf_rd_data[i] @= s.register_file.rd_data[i]
                    s.rf_rd_addr[i] @= s.rd_addr_cfg[i]
             

        # -------------------------------------------------------------------------
        # Static connections to regfile data channels
        # (addresses/val asserted only when in RUN)
        # -------------------------------------------------------------------------

        # Thread Idx wires for r/w
        @update
        def update_thread_idx():
            for i in range(num_rd_ports):
                s.register_file.rd_thread_idx[i] @= s.current_issue_tid
            for i in range(num_wr_ports):
                wr_tid = MaxThreadType(0)
                rank = MaxThreadType(0)
                for tid in range(MAX_THREAD_COUNT):
                    if s.active_thread_mask[tid] & ~s.dep_thread_mask[tid]:
                        if s.wr_count[i] == rank:
                            wr_tid = MaxThreadType(tid)
                        rank = rank + MaxThreadType(1)
                for tid in range(MAX_THREAD_COUNT):
                    if s.dep_thread_mask[tid]:
                        if s.wr_count[i] == rank:
                            wr_tid = MaxThreadType(tid)
                        rank = rank + MaxThreadType(1)
                s.wr_thread_tid[i] @= wr_tid
                s.register_file.wr_thread_idx[i] @= s.wr_thread_tid[i]
            for i in range(num_ld_ports):
                s.register_file.wr_thread_idx[i + num_wr_ports] @= s.ld_data_id[i]

            for i in range(num_ld_ports):
                ld_tid = MaxThreadType(0)
                rank = MaxThreadType(0)
                for tid in range(MAX_THREAD_COUNT):
                    if s.active_thread_mask[tid] & ~s.dep_thread_mask[tid]:
                        if s.ld_seq_count[i] == rank:
                            ld_tid = MaxThreadType(tid)
                        rank = rank + MaxThreadType(1)
                for tid in range(MAX_THREAD_COUNT):
                    if s.dep_thread_mask[tid]:
                        if s.ld_seq_count[i] == rank:
                            ld_tid = MaxThreadType(tid)
                        rank = rank + MaxThreadType(1)
                s.ld_issue_tid[i] @= ld_tid
            for i in range(num_st_ports):
                st_tid = MaxThreadType(0)
                rank = MaxThreadType(0)
                for tid in range(MAX_THREAD_COUNT):
                    if s.active_thread_mask[tid] & ~s.dep_thread_mask[tid]:
                        if s.st_seq_count[i] == rank:
                            st_tid = MaxThreadType(tid)
                        rank = rank + MaxThreadType(1)
                for tid in range(MAX_THREAD_COUNT):
                    if s.dep_thread_mask[tid]:
                        if s.st_seq_count[i] == rank:
                            st_tid = MaxThreadType(tid)
                        rank = rank + MaxThreadType(1)
                s.st_issue_tid[i] @= st_tid

        @update
        def comb_issue_tid():
            issue_tid = MaxThreadType(0)
            rank = MaxThreadType(0)
            for tid in range(MAX_THREAD_COUNT):
                if s.active_thread_mask[tid] & ~s.dep_thread_mask[tid]:
                    if s.issue_count == rank:
                        issue_tid = MaxThreadType(tid)
                    rank = rank + MaxThreadType(1)
            for tid in range(MAX_THREAD_COUNT):
                if s.dep_thread_mask[tid]:
                    if s.issue_count == rank:
                        issue_tid = MaxThreadType(tid)
                    rank = rank + MaxThreadType(1)
            s.current_issue_tid @= issue_tid


        # Enable wires for read and write ports
        s.rd_enable = [ OutPort(Bits1) for _ in range(num_rd_ports) ]
        s.wr_enable = [ OutPort(Bits1) for _ in range(num_wr_ports) ]

        @update
        def comb_port_enables():
            rd_issue_ok = Bits1(1)
            for i in range(num_rd_ports):
                if s.rd_addr_valcfg[i]:
                    rd_issue_ok = rd_issue_ok & s.tile_token_avail[i] & s.tile_token_avail_pair[i]
            s.issue_fire @= Bits1(0)
            if (s.state == ST_RUN) & s.run_primed & (s.issue_count < s.expected_count):
                if s.dep_mode:
                    dep_tid_ready = Bits1(0)
                    for tid in range(MAX_THREAD_COUNT):
                        if s.current_issue_tid == MaxThreadType(tid):
                            dep_tid_ready = Bits1((s.dep_thread_mask[tid] == Bits1(0)) | s.dep_complete_mask[tid])
                    if dep_tid_ready & rd_issue_ok:
                        s.issue_fire @= Bits1(1)
                elif rd_issue_ok:
                    s.issue_fire @= Bits1(1)

            for i in range(num_rd_ports):
                if (s.state == ST_RUN) & ~s.run_primed:
                    s.rd_enable[i] @= s.rd_addr_valcfg[i]
                else:
                    s.rd_enable[i] @= s.rd_addr_valcfg[i] & s.issue_fire
            for i in range(num_wr_ports):
                mapped_idx = i
                if i < 4:
                    mapped_idx = ((i & 0x1) << 1) + ((i & 0x2) >> 1)
                s.wr_enable[i] @= s.tile_token_shifter_out[mapped_idx] & s.wr_addr_valcfg[i] & (s.state == ST_RUN) & s.run_primed & (s.wr_count[i] <= s.expected_count_n - 1)

        @update
        def comb_token_takes():
            for i in range(num_rd_ports):
                s.tile_token_take[i] @= s.tile_token_take_req[i] | s.tile_token_take_pair_mirror[i]

        for i in range(num_rd_ports):
            s.register_file.rd_addr[i].msg //= s.rd_addr_cfg[i]
            s.register_file.rd_addr[i].val //= s.rd_enable[i]

        for i in range(num_wr_ports):
            s.register_file.wr_addr[i].msg //= s.wr_addr_cfg[i]
            s.register_file.wr_addr[i].val //= s.wr_enable[i]
            s.register_file.wr_data[i].msg //= s.wr_data[i]
            s.register_file.wr_data[i].val //= s.wr_enable[i]
        
        # Configure ld writing into RF
        for i in range(num_ld_ports):
            s.register_file.wr_addr[i + num_wr_ports].msg //= s.ld_reg_addr_active[i]
            s.register_file.wr_addr[i + num_wr_ports].val //= s.ld_data_valid[i]
            s.register_file.wr_data[i + num_wr_ports].msg //= s.ld_data[i]
            s.register_file.wr_data[i + num_wr_ports].val //= s.ld_data_valid[i]

        # -------------------------------------------------------------------------
        # Assign output data as register or tid for counts
        # -------------------------------------------------------------------------
        @update
        def comb_output_data():
            for i in range(num_rd_ports):
                if ~s.rd_addr_valcfg[i]:
                    s.rd_data[i] @= RegDataType(0)
                elif s.active_const_store:
                    s.rd_data[i] @= RegDataType(0)
                elif s.tid_enabled[i]:
                    s.rd_data[i] @= s.current_issue_tid_data
                    if i % 4 == 0:
                        if i + 2 < num_rd_ports:
                            if s.rd_addr_valcfg[i + 2] & ~s.tid_enabled[i + 2]:
                                # Loop bodies use the west/east pair together:
                                # the west compare tile should see the
                                # incremented loop-carried value from the
                                # paired east read, while pure tid-only configs
                                # still get the synthetic thread id path.
                                s.rd_data[i] @= s.register_file.rd_data[i + 2] + RegDataType(1)
                else:
                    s.rd_data[i] @= s.register_file.rd_data[i]

        # -------------------------------------------------------------------------
        # Ready/valid for external ifcs (single-writer comb)
        # -------------------------------------------------------------------------

        @update
        def comb_ready_valid():
            s.recv_cfg_from_ctrl.rdy @= Bits1(1)

        @update
        def comb_recv_cfg_thread_mask():
            resolved_mask = s.recv_cfg_thread_mask
            resolved_count = MaxThreadType(0)
            resolved_min = MaxThreadType(0)
            resolved_max = MaxThreadType(0)
            if s.recv_cfg_thread_mask == MaskType(0):
                resolved_mask = MaskType(0)
                resolved_min = s.recv_cfg_from_ctrl.msg.thread_count_min
                resolved_max = s.recv_cfg_from_ctrl.msg.thread_count_max
                for tid in range(MAX_THREAD_COUNT):
                    tid_bits = MaxThreadType(tid)
                    if (tid_bits >= resolved_min) & (tid_bits < resolved_max):
                        resolved_mask = resolved_mask | MaskType(1 << tid)
                        resolved_count = resolved_count + MaxThreadType(1)
            else:
                found_tid = Bits1(0)
                for tid in range(MAX_THREAD_COUNT):
                    if s.recv_cfg_thread_mask[tid]:
                        resolved_count = resolved_count + MaxThreadType(1)
                        if ~found_tid:
                            resolved_min = MaxThreadType(tid)
                            found_tid = Bits1(1)
                        resolved_max = MaxThreadType(tid + 1)
            s.recv_cfg_thread_count_resolved @= resolved_count
            s.recv_cfg_thread_min_resolved @= resolved_min
            s.recv_cfg_thread_max_resolved @= resolved_max
            s.recv_cfg_thread_mask_resolved @= resolved_mask

        @update
        def comb_dep_complete_mask():
            if s.cfg_active_sel_w == Bits1(0):
                s.dep_complete_mask @= s.mem_complete_mask_bank1
            else:
                s.dep_complete_mask @= s.mem_complete_mask_bank0

        @update_ff
        def cfg_bank_ff():
            if s.reset:
                s.cfg_bank_valid0 <<= 0
                s.cfg_bank_valid1 <<= 0
                s.expected_count_bank0 <<= MaxThreadType(0)
                s.expected_count_bank1 <<= MaxThreadType(0)
                s.active_thread_min_bank0 <<= MaxThreadType(0)
                s.active_thread_max_bank0 <<= MaxThreadType(0)
                s.active_thread_min_bank1 <<= MaxThreadType(0)
                s.active_thread_max_bank1 <<= MaxThreadType(0)
                s.active_thread_mask_bank0 <<= MaskType(0)
                s.active_thread_mask_bank1 <<= MaskType(0)
                s.pred_reg_bank0 <<= PredAddrType(0)
                s.pred_reg_bank1 <<= PredAddrType(0)
                s.branch_en_bank0 <<= Bits1(0)
                s.branch_en_bank1 <<= Bits1(0)
                s.const_store_bank0 <<= Bits1(0)
                s.const_store_bank1 <<= Bits1(0)
                for i in range(num_rd_ports):
                    s.rd_addr_cfg_bank0[i] <<= RegAddrType(0)
                    s.rd_addr_cfg_bank1[i] <<= RegAddrType(0)
                    s.rd_addr_valcfg_bank0[i] <<= Bits1(0)
                    s.rd_addr_valcfg_bank1[i] <<= Bits1(0)
                    s.tid_enabled_bank0[i] <<= Bits1(0)
                    s.tid_enabled_bank1[i] <<= Bits1(0)
                for i in range(num_wr_ports):
                    s.wr_addr_cfg_bank0[i] <<= RegAddrType(0)
                    s.wr_addr_cfg_bank1[i] <<= RegAddrType(0)
                    s.wr_addr_valcfg_bank0[i] <<= Bits1(0)
                    s.wr_addr_valcfg_bank1[i] <<= Bits1(0)
                    s.pred_wr_valcfg_bank0[i] <<= Bits1(0)
                    s.pred_wr_valcfg_bank1[i] <<= Bits1(0)
                    s.pred_wr_addr_cfg_bank0[i] <<= PredAddrType(0)
                    s.pred_wr_addr_cfg_bank1[i] <<= PredAddrType(0)
                for i in range(num_tiles):
                    s.pred_tile_valid_bank0[i] <<= Bits1(0)
                    s.pred_tile_valid_bank1[i] <<= Bits1(0)
                for i in range(num_ld_ports):
                    s.ld_enable_bank0[i] <<= Bits1(0)
                    s.ld_enable_bank1[i] <<= Bits1(0)
                    s.ld_reg_addr_bank0[i] <<= RegAddrType(0)
                    s.ld_reg_addr_bank1[i] <<= RegAddrType(0)
                for i in range(num_st_ports):
                    s.st_enable_bank0[i] <<= Bits1(0)
                    s.st_enable_bank1[i] <<= Bits1(0)
            else:
                if s.cfg_swap_w:
                    if s.cfg_load_sel_w == Bits1(0):
                        s.cfg_bank_valid0 <<= 0
                    else:
                        s.cfg_bank_valid1 <<= 0
                if s.recv_cfg_from_ctrl.val & s.recv_cfg_from_ctrl.rdy:
                    cfg_is_const_store = Bits1(s.recv_cfg_from_ctrl.msg.end_cfg)
                    any_store = Bits1(0)
                    any_load = Bits1(0)
                    any_data_write = Bits1(0)
                    any_pred_write = Bits1(0)
                    any_input_read = Bits1(0)
                    for i in range(num_st_ports):
                        any_store = any_store | s.recv_cfg_from_ctrl.msg.st_enable[i]
                    for i in range(num_ld_ports):
                        any_load = any_load | s.recv_cfg_from_ctrl.msg.ld_enable[i]
                    for i in range(num_wr_ports):
                        any_data_write = any_data_write | s.recv_cfg_from_ctrl.msg.out_regs_val[i]
                        any_pred_write = any_pred_write | s.recv_cfg_from_ctrl.msg.out_pred_regs_val[i]
                    for i in range(num_rd_ports):
                        any_input_read = any_input_read | s.recv_cfg_from_ctrl.msg.in_regs_val[i]
                    cfg_is_const_store = cfg_is_const_store & any_store & ~any_load & ~any_data_write & ~any_pred_write & ~any_input_read
                    if s.cfg_load_sel_w == Bits1(0):
                        s.cfg_bank_valid0 <<= 1
                        s.expected_count_bank0 <<= s.recv_cfg_thread_count_resolved
                        s.active_thread_min_bank0 <<= s.recv_cfg_thread_min_resolved
                        s.active_thread_max_bank0 <<= s.recv_cfg_thread_max_resolved
                        s.active_thread_mask_bank0 <<= s.recv_cfg_thread_mask_resolved
                        s.pred_reg_bank0 <<= s.recv_cfg_from_ctrl.msg.pred_reg_id
                        s.branch_en_bank0 <<= s.recv_cfg_from_ctrl.msg.branch_en
                        s.const_store_bank0 <<= cfg_is_const_store
                        for i in range(num_rd_ports):
                            s.rd_addr_cfg_bank0[i] <<= s.recv_cfg_from_ctrl.msg.in_regs[i]
                            s.rd_addr_valcfg_bank0[i] <<= s.recv_cfg_from_ctrl.msg.in_regs_val[i]
                            s.tid_enabled_bank0[i] <<= s.recv_cfg_from_ctrl.msg.in_tid_enable[i]
                        for i in range(num_wr_ports):
                            s.wr_addr_cfg_bank0[i] <<= s.recv_cfg_from_ctrl.msg.out_regs[i]
                            s.wr_addr_valcfg_bank0[i] <<= s.recv_cfg_from_ctrl.msg.out_regs_val[i]
                            s.pred_wr_valcfg_bank0[i] <<= s.recv_cfg_from_ctrl.msg.out_pred_regs_val[i]
                            s.pred_wr_addr_cfg_bank0[i] <<= s.recv_cfg_from_ctrl.msg.out_pred_regs[i]
                        for i in range(num_tiles):
                            s.pred_tile_valid_bank0[i] <<= s.recv_cfg_from_ctrl.msg.pred_tile_valid[i]
                        for i in range(num_ld_ports):
                            s.ld_enable_bank0[i] <<= s.recv_cfg_from_ctrl.msg.ld_enable[i]
                            s.ld_reg_addr_bank0[i] <<= s.recv_cfg_from_ctrl.msg.ld_reg_addr[i]
                        for i in range(num_st_ports):
                            s.st_enable_bank0[i] <<= s.recv_cfg_from_ctrl.msg.st_enable[i]
                    else:
                        s.cfg_bank_valid1 <<= 1
                        s.expected_count_bank1 <<= s.recv_cfg_thread_count_resolved
                        s.active_thread_min_bank1 <<= s.recv_cfg_thread_min_resolved
                        s.active_thread_max_bank1 <<= s.recv_cfg_thread_max_resolved
                        s.active_thread_mask_bank1 <<= s.recv_cfg_thread_mask_resolved
                        s.pred_reg_bank1 <<= s.recv_cfg_from_ctrl.msg.pred_reg_id
                        s.branch_en_bank1 <<= s.recv_cfg_from_ctrl.msg.branch_en
                        s.const_store_bank1 <<= cfg_is_const_store
                        for i in range(num_rd_ports):
                            s.rd_addr_cfg_bank1[i] <<= s.recv_cfg_from_ctrl.msg.in_regs[i]
                            s.rd_addr_valcfg_bank1[i] <<= s.recv_cfg_from_ctrl.msg.in_regs_val[i]
                            s.tid_enabled_bank1[i] <<= s.recv_cfg_from_ctrl.msg.in_tid_enable[i]
                        for i in range(num_wr_ports):
                            s.wr_addr_cfg_bank1[i] <<= s.recv_cfg_from_ctrl.msg.out_regs[i]
                            s.wr_addr_valcfg_bank1[i] <<= s.recv_cfg_from_ctrl.msg.out_regs_val[i]
                            s.pred_wr_valcfg_bank1[i] <<= s.recv_cfg_from_ctrl.msg.out_pred_regs_val[i]
                            s.pred_wr_addr_cfg_bank1[i] <<= s.recv_cfg_from_ctrl.msg.out_pred_regs[i]
                        for i in range(num_tiles):
                            s.pred_tile_valid_bank1[i] <<= s.recv_cfg_from_ctrl.msg.pred_tile_valid[i]
                        for i in range(num_ld_ports):
                            s.ld_enable_bank1[i] <<= s.recv_cfg_from_ctrl.msg.ld_enable[i]
                            s.ld_reg_addr_bank1[i] <<= s.recv_cfg_from_ctrl.msg.ld_reg_addr[i]
                        for i in range(num_st_ports):
                            s.st_enable_bank1[i] <<= s.recv_cfg_from_ctrl.msg.st_enable[i]

        # -------------------------------------------------------------------------
        # Completion check (comb)
        # -------------------------------------------------------------------------

        s.cfg_writeback_complete = OutPort( 1 )
        s.cfg_issue_ready = OutPort( 1 )
        s.rd_regs_complete = OutPort( num_rd_ports )
        s.wr_regs_complete = OutPort( num_wr_ports )

        @update
        def comb_nonmem_masks():
            target_mask = s.active_thread_mask
            s.active_target_mask @= target_mask

            s.any_wr_enabled @= Bits1(0)
            wr_complete_mask = target_mask
            for port in range(num_wr_ports):
                if s.wr_addr_valcfg[port]:
                    s.any_wr_enabled @= Bits1(1)
                    port_mask = MaskType(0)
                    rank = MaxThreadType(0)
                    for tid in range(MAX_THREAD_COUNT):
                        if s.active_thread_mask[tid] & ~s.dep_thread_mask[tid]:
                            if s.wr_count[port] > rank:
                                port_mask = port_mask | MaskType(1 << tid)
                            rank = rank + MaxThreadType(1)
                    for tid in range(MAX_THREAD_COUNT):
                        if s.dep_thread_mask[tid]:
                            if s.wr_count[port] > rank:
                                port_mask = port_mask | MaskType(1 << tid)
                            rank = rank + MaxThreadType(1)
                    wr_complete_mask = wr_complete_mask & port_mask

            if s.any_wr_enabled:
                s.nonmem_ready_mask @= wr_complete_mask
            else:
                s.nonmem_ready_mask @= target_mask

        @update
        def comb_completion():
            # Default cfg
            s.cfg_writeback_complete @= Bits1(0)
            # Only check completion when in RUN state
            if s.state == ST_RUN:
                # Check read ports
                for i in range(num_rd_ports):
                    s.rd_regs_complete[i] @= Bits1(1)
                # Check write ports
                for i in range(num_wr_ports):
                    if s.wr_addr_valcfg[i]:
                        s.wr_regs_complete[i] @= Bits1(s.wr_count[i] >= s.expected_count)
                    else:
                        s.wr_regs_complete[i] @= Bits1(1)

                s.cfg_writeback_complete @= reduce_and(s.wr_regs_complete) & (s.expected_count > MaxThreadType(0))
        
        # -------------------------------------------------------------------------
        # Next-state & counters (single comb writer)
        # -------------------------------------------------------------------------

        @update
        def comb_next_state_and_counts():
            # Default hold
            s.state_n @= s.state
            s.issue_count_n @= s.issue_count
            s.dep_mode_n @= s.dep_mode
            s.run_primed_n @= s.run_primed
            s.mem_release_take @= Bits1(0)
            for i in range(num_rd_ports):
                # RF defaults
                s.rd_count_n[i] @= s.rd_count[i]
                s.rd_addr_valcfg_n[i] @= s.rd_addr_valcfg[i]
                s.rd_addr_cfg_n[i] @= s.rd_addr_cfg[i]
                s.tid_enabled_n[i] @= s.tid_enabled[i]

                # Token defaults
                s.tile_token_take_req[i] @= Bits1(0)
                s.tile_token_take_pair_req[i] @= Bits1(0)
            for i in range(num_wr_ports):
                # Token default
                s.tile_token_return[i] @= 0

                # Address
                s.wr_count_n[i] @= s.wr_count[i]
                s.wr_addr_valcfg_n[i] @= s.wr_addr_valcfg[i]
                s.wr_addr_cfg_n[i] @= s.wr_addr_cfg[i]
            s.expected_count_n @= s.expected_count
            for i in range(num_ld_ports):
                s.ld_seq_count_n[i] @= s.ld_seq_count[i]
            for i in range(num_st_ports):
                s.st_seq_count_n[i] @= s.st_seq_count[i]

            # State transitions
            if s.state == ST_IDLE:
                # Handshake to start configuration
                if s.recv_cfg_from_ctrl.val & s.recv_cfg_from_ctrl.rdy & (s.cfg_active_sel_w == s.cfg_load_sel_w):
                    s.state_n @= ST_RUN
                    s.issue_count_n @= MaxThreadType(0)
                    s.dep_mode_n @= Bits1(0)
                    s.run_primed_n @= Bits1(0)
                    for i in range(num_rd_ports):
                        s.rd_count_n[i] @= MaxThreadType(0)
                        s.rd_addr_valcfg_n[i] @= s.recv_cfg_from_ctrl.msg.in_regs_val[i]
                        s.rd_addr_cfg_n[i] @= s.recv_cfg_from_ctrl.msg.in_regs[i]
                        s.tid_enabled_n[i] @= s.recv_cfg_from_ctrl.msg.in_tid_enable[i] & s.recv_cfg_from_ctrl.msg.in_regs_val[i]
                    for i in range(num_wr_ports):
                        s.wr_count_n[i] @= MaxThreadType(0)
                        s.wr_addr_valcfg_n[i] @= s.recv_cfg_from_ctrl.msg.out_regs_val[i]
                        s.wr_addr_cfg_n[i] @= s.recv_cfg_from_ctrl.msg.out_regs[i]
                    for i in range(num_ld_ports):
                        s.ld_seq_count_n[i] @= MaxThreadType(0)
                    for i in range(num_st_ports):
                        s.st_seq_count_n[i] @= MaxThreadType(0)
                    s.expected_count_n @= s.recv_cfg_thread_count_resolved
            
            elif s.state == ST_RUN:
                if ~s.run_primed:
                    s.run_primed_n @= Bits1(1)
                else:
                    if s.dep_mode & s.mem_release_valid:
                        s.mem_release_take @= Bits1(1)
                    if s.issue_fire:
                        s.issue_count_n @= s.issue_count + MaxThreadType(1)
                        for i in range(num_rd_ports):
                            if s.rd_addr_valcfg[i]:
                                s.rd_count_n[i] @= s.rd_count[i] + MaxThreadType(1)
                                s.tile_token_take_req[i] @= Bits1(1)
                                s.tile_token_take_pair_req[i] @= Bits1(1)

                    for i in range(num_wr_ports):
                        mapped_idx = i
                        if i < 4:
                            mapped_idx = ((i & 0x1) << 1) + ((i & 0x2) >> 1)
                        if s.wr_addr_valcfg[i]:
                            if s.tile_token_shifter_out[mapped_idx] & (s.wr_count[i] < s.expected_count):
                                s.wr_count_n[i] @= s.wr_count[i] + MaxThreadType(1)
                                s.tile_token_return[mapped_idx] @= 1
                        elif s.pred_wr_valcfg[i]:
                            if s.tile_token_shifter_out[mapped_idx] & (s.pred_count[s.active_pred_reg] < s.pred_expected[s.active_pred_reg]):
                                s.wr_count_n[i] @= s.wr_count[i] + MaxThreadType(1)
                                s.tile_token_return[mapped_idx] @= 1
                    for i in range(num_ld_ports):
                        if s.ld_req_accepted[i] & (s.ld_seq_count[i] < s.expected_count):
                            s.ld_seq_count_n[i] @= s.ld_seq_count[i] + MaxThreadType(1)
                    for i in range(num_st_ports):
                        if s.st_req_accepted[i] & (s.st_seq_count[i] < s.expected_count):
                            s.st_seq_count_n[i] @= s.st_seq_count[i] + MaxThreadType(1)

                # Transition back to IDLE when complete
                if s.cfg_done:
                    s.state_n @= ST_IDLE

        # -------------------------------------------------------------------------
        # Sequential update: commit state, counters, and capture config
        # -------------------------------------------------------------------------

        @update_ff
        def seq_ff():
            if s.reset:
                s.state           <<= ST_IDLE
                s.expected_count  <<= MaxThreadType(0)
                s.active_thread_min <<= MaxThreadType(0)
                s.active_thread_max <<= MaxThreadType(0)
                s.active_thread_mask <<= MaskType(0)
                s.dep_thread_mask <<= MaskType(0)
                s.active_pred_reg <<= PredAddrType(0)
                s.active_branch_en <<= Bits1(0)
                s.active_const_store <<= Bits1(0)
                s.issue_count <<= MaxThreadType(0)
                s.dep_mode <<= Bits1(0)
                s.run_primed <<= Bits1(0)
                for i in range(num_rd_ports):
                    s.rd_addr_cfg[i]    <<= RegAddrType(0)
                    s.rd_addr_valcfg[i] <<= Bits1(0)
                    s.tid_enabled[i]    <<= Bits1(0)
                    s.rd_count[i]       <<= MaxThreadType(0)
                for i in range(num_wr_ports):
                    s.wr_addr_cfg[i]    <<= RegAddrType(0)
                    s.wr_addr_valcfg[i] <<= Bits1(0)
                    s.pred_wr_valcfg[i] <<= Bits1(0)
                    s.pred_wr_addr_cfg[i] <<= PredAddrType(0)
                    s.wr_count[i]       <<= MaxThreadType(0)
                for i in range(num_tiles):
                    s.pred_tile_valid_active[i] <<= Bits1(0)
                for i in range(num_ld_ports):
                    s.ld_enable_active[i] <<= Bits1(0)
                    s.ld_reg_addr_active[i] <<= RegAddrType(0)
                for i in range(num_st_ports):
                    s.st_enable_active[i] <<= Bits1(0)
                for i in range(num_ld_ports):
                    s.ld_seq_count[i] <<= MaxThreadType(0)
                for i in range(num_st_ports):
                    s.st_seq_count[i] <<= MaxThreadType(0)

            else:
                if s.cfg_swap_w:
                    s.state <<= ST_RUN
                    s.issue_count <<= MaxThreadType(0)
                    s.run_primed <<= Bits1(0)
                    # The controller tells us when a bank swap overlaps an
                    # incomplete prior config, so new TIDs must be released
                    # from the previous bank before issuing this config.
                    s.dep_mode <<= s.cfg_dep_start_w
                    if s.cfg_active_sel_w == Bits1(0):
                        s.expected_count <<= s.expected_count_bank0
                        s.active_thread_min <<= s.active_thread_min_bank0
                        s.active_thread_max <<= s.active_thread_max_bank0
                        s.active_thread_mask <<= s.active_thread_mask_bank0
                        dep_mask = MaskType(0)
                        if s.cfg_dep_start_w:
                            dep_mask = s.active_thread_mask_bank0 & s.active_thread_mask_bank1
                        s.dep_thread_mask <<= dep_mask
                        s.active_pred_reg <<= s.pred_reg_bank0
                        s.active_branch_en <<= s.branch_en_bank0
                        s.active_const_store <<= s.const_store_bank0
                        for i in range(num_rd_ports):
                            s.rd_addr_cfg[i] <<= s.rd_addr_cfg_bank0[i]
                            s.rd_addr_valcfg[i] <<= s.rd_addr_valcfg_bank0[i]
                            s.tid_enabled[i] <<= s.tid_enabled_bank0[i] & s.rd_addr_valcfg_bank0[i]
                            s.rd_count[i] <<= MaxThreadType(0)
                        for i in range(num_wr_ports):
                            s.wr_addr_cfg[i] <<= s.wr_addr_cfg_bank0[i]
                            s.wr_addr_valcfg[i] <<= s.wr_addr_valcfg_bank0[i]
                            s.pred_wr_valcfg[i] <<= s.pred_wr_valcfg_bank0[i]
                            s.pred_wr_addr_cfg[i] <<= s.pred_wr_addr_cfg_bank0[i]
                            s.wr_count[i] <<= MaxThreadType(0)
                        for i in range(num_tiles):
                            s.pred_tile_valid_active[i] <<= s.pred_tile_valid_bank0[i]
                        for i in range(num_ld_ports):
                            s.ld_enable_active[i] <<= s.ld_enable_bank0[i]
                            s.ld_reg_addr_active[i] <<= s.ld_reg_addr_bank0[i]
                        for i in range(num_st_ports):
                            s.st_enable_active[i] <<= s.st_enable_bank0[i]
                    else:
                        s.expected_count <<= s.expected_count_bank1
                        s.active_thread_min <<= s.active_thread_min_bank1
                        s.active_thread_max <<= s.active_thread_max_bank1
                        s.active_thread_mask <<= s.active_thread_mask_bank1
                        dep_mask = MaskType(0)
                        if s.cfg_dep_start_w:
                            dep_mask = s.active_thread_mask_bank1 & s.active_thread_mask_bank0
                        s.dep_thread_mask <<= dep_mask
                        s.active_pred_reg <<= s.pred_reg_bank1
                        s.active_branch_en <<= s.branch_en_bank1
                        s.active_const_store <<= s.const_store_bank1
                        for i in range(num_rd_ports):
                            s.rd_addr_cfg[i] <<= s.rd_addr_cfg_bank1[i]
                            s.rd_addr_valcfg[i] <<= s.rd_addr_valcfg_bank1[i]
                            s.tid_enabled[i] <<= s.tid_enabled_bank1[i] & s.rd_addr_valcfg_bank1[i]
                            s.rd_count[i] <<= MaxThreadType(0)
                        for i in range(num_wr_ports):
                            s.wr_addr_cfg[i] <<= s.wr_addr_cfg_bank1[i]
                            s.wr_addr_valcfg[i] <<= s.wr_addr_valcfg_bank1[i]
                            s.pred_wr_valcfg[i] <<= s.pred_wr_valcfg_bank1[i]
                            s.pred_wr_addr_cfg[i] <<= s.pred_wr_addr_cfg_bank1[i]
                            s.wr_count[i] <<= MaxThreadType(0)
                        for i in range(num_tiles):
                            s.pred_tile_valid_active[i] <<= s.pred_tile_valid_bank1[i]
                        for i in range(num_ld_ports):
                            s.ld_enable_active[i] <<= s.ld_enable_bank1[i]
                            s.ld_reg_addr_active[i] <<= s.ld_reg_addr_bank1[i]
                        for i in range(num_st_ports):
                            s.st_enable_active[i] <<= s.st_enable_bank1[i]
                    for i in range(num_ld_ports):
                        s.ld_seq_count[i] <<= MaxThreadType(0)
                    for i in range(num_st_ports):
                        s.st_seq_count[i] <<= MaxThreadType(0)
                else:
                    # Advance state
                    s.state <<= s.state_n
                    s.issue_count <<= s.issue_count_n
                    s.dep_mode <<= s.dep_mode_n
                    s.run_primed <<= s.run_primed_n

                    # Update counters/config
                    for i in range(num_rd_ports):
                        s.rd_count[i] <<= s.rd_count_n[i]
                        s.rd_addr_cfg[i] <<= s.rd_addr_cfg_n[i]
                        s.rd_addr_valcfg[i] <<= s.rd_addr_valcfg_n[i]
                        s.tid_enabled[i] <<= s.tid_enabled_n[i]

                    for i in range(num_wr_ports):
                        s.wr_count[i] <<= s.wr_count_n[i]
                        s.wr_addr_cfg[i] <<= s.wr_addr_cfg_n[i]
                        s.wr_addr_valcfg[i] <<= s.wr_addr_valcfg_n[i]
                        if s.recv_cfg_from_ctrl.val & s.recv_cfg_from_ctrl.rdy & (s.cfg_active_sel_w == s.cfg_load_sel_w) & (s.state == ST_IDLE):
                            s.pred_wr_valcfg[i] <<= s.recv_cfg_from_ctrl.msg.out_pred_regs_val[i]
                            s.pred_wr_addr_cfg[i] <<= s.recv_cfg_from_ctrl.msg.out_pred_regs[i]
                    for i in range(num_ld_ports):
                        s.ld_seq_count[i] <<= s.ld_seq_count_n[i]
                    for i in range(num_st_ports):
                        s.st_seq_count[i] <<= s.st_seq_count_n[i]

                    s.expected_count <<= s.expected_count_n

                    if s.recv_cfg_from_ctrl.val & s.recv_cfg_from_ctrl.rdy & (s.cfg_active_sel_w == s.cfg_load_sel_w) & (s.state == ST_IDLE):
                        s.active_thread_min <<= s.recv_cfg_thread_min_resolved
                        s.active_thread_max <<= s.recv_cfg_thread_max_resolved
                        s.active_thread_mask <<= s.recv_cfg_thread_mask_resolved
                        s.dep_thread_mask <<= MaskType(0)
                        s.active_pred_reg <<= s.recv_cfg_from_ctrl.msg.pred_reg_id
                        s.active_branch_en <<= s.recv_cfg_from_ctrl.msg.branch_en
                        cfg_is_const_store = Bits1(s.recv_cfg_from_ctrl.msg.end_cfg)
                        any_store = Bits1(0)
                        any_load = Bits1(0)
                        any_data_write = Bits1(0)
                        any_pred_write = Bits1(0)
                        any_input_read = Bits1(0)
                        for j in range(num_st_ports):
                            any_store = any_store | s.recv_cfg_from_ctrl.msg.st_enable[j]
                        for j in range(num_ld_ports):
                            any_load = any_load | s.recv_cfg_from_ctrl.msg.ld_enable[j]
                        for j in range(num_wr_ports):
                            any_data_write = any_data_write | s.recv_cfg_from_ctrl.msg.out_regs_val[j]
                            any_pred_write = any_pred_write | s.recv_cfg_from_ctrl.msg.out_pred_regs_val[j]
                        for j in range(num_rd_ports):
                            any_input_read = any_input_read | s.recv_cfg_from_ctrl.msg.in_regs_val[j]
                        s.active_const_store <<= cfg_is_const_store & any_store & ~any_load & ~any_data_write & ~any_pred_write & ~any_input_read
                        for i in range(num_tiles):
                            s.pred_tile_valid_active[i] <<= s.recv_cfg_from_ctrl.msg.pred_tile_valid[i]
                        for i in range(num_ld_ports):
                            s.ld_enable_active[i] <<= s.recv_cfg_from_ctrl.msg.ld_enable[i]
                            s.ld_reg_addr_active[i] <<= s.recv_cfg_from_ctrl.msg.ld_reg_addr[i]
                        for i in range(num_st_ports):
                            s.st_enable_active[i] <<= s.recv_cfg_from_ctrl.msg.st_enable[i]

        # -------------------------------------------------------------------------
        # Predicate register file update
        # -------------------------------------------------------------------------
        @update
        def comb_pred_rf_next():
            cfg_start = s.recv_cfg_from_ctrl.val & s.recv_cfg_from_ctrl.rdy & (s.cfg_active_sel_w == s.cfg_load_sel_w) & (s.state == ST_IDLE)
            for r in range(num_pred_registers):
                count = s.pred_count[r]
                expected = s.pred_expected[r]
                any_true = s.pred_any_true_reg[r]
                any_false = s.pred_any_false_reg[r]
                true_count = s.pred_true_count_reg[r]
                false_count = s.pred_false_count_reg[r]
                true_mask = s.pred_true_mask_reg[r]
                false_mask = s.pred_false_mask_reg[r]
                seen_mask = s.pred_seen_mask_reg[r]

                if cfg_start:
                    for i in range(num_wr_ports):
                        if s.recv_cfg_from_ctrl.msg.out_pred_regs_val[i] & (s.recv_cfg_from_ctrl.msg.out_pred_regs[i] == PredAddrType(r)):
                            count = PredCountType(0)
                            expected = PredCountType(s.recv_cfg_thread_count_resolved)
                            any_true = Bits1(0)
                            any_false = Bits1(0)
                            true_count = PredCountType(0)
                            false_count = PredCountType(0)
                            true_mask = MaskType(0)
                            false_mask = MaskType(0)
                            seen_mask = MaskType(0)
                elif s.cfg_swap_w:
                    if s.cfg_active_sel_w == Bits1(0):
                        cfg_expected = PredCountType(s.expected_count_bank0)
                        for i in range(num_wr_ports):
                            if s.pred_wr_valcfg_bank0[i] & (s.pred_wr_addr_cfg_bank0[i] == PredAddrType(r)):
                                count = PredCountType(0)
                                expected = cfg_expected
                                any_true = Bits1(0)
                                any_false = Bits1(0)
                                true_count = PredCountType(0)
                                false_count = PredCountType(0)
                                true_mask = MaskType(0)
                                false_mask = MaskType(0)
                                seen_mask = MaskType(0)
                    else:
                        cfg_expected = PredCountType(s.expected_count_bank1)
                        for i in range(num_wr_ports):
                            if s.pred_wr_valcfg_bank1[i] & (s.pred_wr_addr_cfg_bank1[i] == PredAddrType(r)):
                                count = PredCountType(0)
                                expected = cfg_expected
                                any_true = Bits1(0)
                                any_false = Bits1(0)
                                true_count = PredCountType(0)
                                false_count = PredCountType(0)
                                true_mask = MaskType(0)
                                false_mask = MaskType(0)
                                seen_mask = MaskType(0)

                if s.state == ST_RUN:
                    for i in range(num_wr_ports):
                        mapped_idx = i
                        if i < 4:
                            mapped_idx = ((i & 0x1) << 1) + ((i & 0x2) >> 1)
                        if s.pred_wr_valcfg[i] & (s.pred_wr_addr_cfg[i] == PredAddrType(r)) & s.tile_token_shifter_out[mapped_idx]:
                            tid_mask = MaskType(0)
                            for tid in range(MAX_THREAD_COUNT):
                                if s.wr_thread_tid[i] == MaxThreadType(tid):
                                    tid_mask = MaskType(1 << tid)
                            if (tid_mask != MaskType(0)) & ((seen_mask & tid_mask) == MaskType(0)):
                                seen_mask = seen_mask | tid_mask
                                if count < expected:
                                    count = count + PredCountType(1)
                                if s.recv_pred_port[i]:
                                    any_true = Bits1(1)
                                    true_mask = true_mask | tid_mask
                                    if true_count < expected:
                                        true_count = true_count + PredCountType(1)
                                else:
                                    any_false = Bits1(1)
                                    false_mask = false_mask | tid_mask
                                    if false_count < expected:
                                        false_count = false_count + PredCountType(1)

                s.pred_count_next[r] @= count
                s.pred_expected_next[r] @= expected
                s.pred_any_true_next[r] @= any_true
                s.pred_any_false_next[r] @= any_false
                s.pred_true_count_next[r] @= true_count
                s.pred_false_count_next[r] @= false_count
                s.pred_true_mask_next[r] @= true_mask
                s.pred_false_mask_next[r] @= false_mask
                s.pred_seen_mask_next[r] @= seen_mask

        @update_ff
        def pred_rf_ff():
            if s.reset:
                for r in range(num_pred_registers):
                    s.pred_count[r] <<= PredCountType(0)
                    s.pred_expected[r] <<= PredCountType(0)
                    s.pred_any_true_reg[r] <<= Bits1(0)
                    s.pred_any_false_reg[r] <<= Bits1(0)
                    s.pred_true_count_reg[r] <<= PredCountType(0)
                    s.pred_false_count_reg[r] <<= PredCountType(0)
                    s.pred_true_mask_reg[r] <<= MaskType(0)
                    s.pred_false_mask_reg[r] <<= MaskType(0)
                    s.pred_seen_mask_reg[r] <<= MaskType(0)
            else:
                for r in range(num_pred_registers):
                    s.pred_count[r] <<= s.pred_count_next[r]
                    s.pred_expected[r] <<= s.pred_expected_next[r]
                    s.pred_any_true_reg[r] <<= s.pred_any_true_next[r]
                    s.pred_any_false_reg[r] <<= s.pred_any_false_next[r]
                    s.pred_true_count_reg[r] <<= s.pred_true_count_next[r]
                    s.pred_false_count_reg[r] <<= s.pred_false_count_next[r]
                    s.pred_true_mask_reg[r] <<= s.pred_true_mask_next[r]
                    s.pred_false_mask_reg[r] <<= s.pred_false_mask_next[r]
                    s.pred_seen_mask_reg[r] <<= s.pred_seen_mask_next[r]

        # -------------------------------------------------------------------------
        # Outputs derived from registered state (single-writer comb)
        # -------------------------------------------------------------------------

        @update
        def comb_outputs():
            active_mem_ready = MaskType(0)
            active_mem_complete = MaskType(0)
            mem_issue_complete = Bits1(1)
            pred_issue_complete = Bits1(1)
            if s.cfg_active_sel_w == Bits1(0):
                active_mem_ready = s.mem_ready_mask_bank0
                active_mem_complete = s.mem_complete_mask_bank0
            else:
                active_mem_ready = s.mem_ready_mask_bank1
                active_mem_complete = s.mem_complete_mask_bank1

            for i in range(num_ld_ports):
                if s.ld_enable_active[i]:
                    mem_issue_complete = mem_issue_complete & Bits1(s.ld_seq_count[i] >= s.expected_count)
            for i in range(num_st_ports):
                if s.st_enable_active[i]:
                    mem_issue_complete = mem_issue_complete & Bits1(s.st_seq_count[i] >= s.expected_count)

            thread_ready = s.nonmem_ready_mask & active_mem_ready
            thread_complete = thread_ready & active_mem_complete
            target_mask = s.active_target_mask

            if s.active_branch_en:
                pred_issue_complete = Bits1(
                    (s.pred_expected[s.active_pred_reg] > PredCountType(0))
                    & (s.pred_count[s.active_pred_reg] >= s.pred_expected[s.active_pred_reg])
                )

            fabric_ready = Bits1(
                (s.state == ST_RUN)
                & (s.expected_count > MaxThreadType(0))
                & mem_issue_complete
                & pred_issue_complete
                & (thread_ready == target_mask)
            )
            dep_release_pending = Bits1(
                (s.state == ST_RUN)
                & s.dep_mode
                & (s.issue_count < s.expected_count)
            )
            s.cfg_issue_ready @= fabric_ready
            s.cfg_ready_for_next @= fabric_ready
            s.dep_mode_out @= dep_release_pending
            s.cfg_done @= Bits1(
                (s.state == ST_RUN)
                & (s.expected_count > MaxThreadType(0))
                & mem_issue_complete
                & pred_issue_complete
                & (thread_complete == target_mask)
            )
