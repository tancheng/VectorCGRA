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
                    enable_double_buffering = False
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
        s.rd_data            = [ OutPort(RegDataType) for _ in range(num_rd_ports) ]
        s.wr_data            = [ InPort(RegDataType) for _ in range(num_wr_ports) ]
        s.cfg_done           = OutPort( 1 )                # level-true when RUN complete this cycle
        s.recv_pred_port = [ InPort(1) for _ in range(num_wr_ports)]
        s.send_tile_preds = [ OutPort(Bits1) for _ in range(num_tiles)]
        s.pred_any_true = [ OutPort(Bits1) for _ in range(num_pred_registers) ]
        s.pred_any_false = [ OutPort(Bits1) for _ in range(num_pred_registers) ]
        s.pred_complete = [ OutPort(Bits1) for _ in range(num_pred_registers) ]
        s.cfg_active_sel_w = Wire(Bits1)
        s.cfg_load_sel_w = Wire(Bits1)
        s.cfg_swap_w = Wire(Bits1)
        if enable_double_buffering:
            s.cfg_active_sel = InPort(Bits1)
            s.cfg_load_sel = InPort(Bits1)
            s.cfg_swap = InPort(Bits1)
            @update
            def cfg_select_wires():
                s.cfg_active_sel_w @= s.cfg_active_sel
                s.cfg_load_sel_w @= s.cfg_load_sel
                s.cfg_swap_w @= s.cfg_swap
        else:
            @update
            def cfg_select_wires():
                s.cfg_active_sel_w @= Bits1(0)
                s.cfg_load_sel_w @= Bits1(0)
                s.cfg_swap_w @= Bits1(0)
        s.send_thread_count = OutPort( clog2(MAX_THREAD_COUNT) )
        s.ld_enable = [OutPort(1) for _ in range(num_ld_ports)]
        s.st_enable = [OutPort(1) for _ in range(num_st_ports)]
        s.ld_st_complete = InPort(1)
        s.ld_data = [InPort(RegDataType) for _ in range(num_ld_ports)]
        s.ld_data_valid = [InPort(1) for _ in range(num_ld_ports)]
        s.ld_data_id = [InPort(clog2(MAX_THREAD_COUNT)) for _ in range(num_ld_ports)]
        s.tile_token_take = [ OutPort(1) for _ in range(num_rd_ports) ]
        s.tile_token_return = [ OutPort(1) for _ in range(num_wr_ports) ]
        s.tile_token_avail = [ InPort(1) for _ in range(num_rd_ports) ]
        s.tile_token_shifter_out = [ InPort(1) for _ in range(num_wr_ports) ]

        s.pred_tile_valid_active = [ Wire(Bits1) for _ in range(num_tiles) ]
        s.pred_tile_valid_bank0 = [ Wire(Bits1) for _ in range(num_tiles) ]
        s.pred_tile_valid_bank1 = [ Wire(Bits1) for _ in range(num_tiles) ]
        s.cfg_bank_valid0 = Wire(Bits1)
        s.cfg_bank_valid1 = Wire(Bits1)

        # Predicate register file (summary only)
        PredCountType = mk_bits(clog2(MAX_THREAD_COUNT))
        s.pred_count = [ Wire(PredCountType) for _ in range(num_pred_registers) ]
        s.pred_expected = [ Wire(PredCountType) for _ in range(num_pred_registers) ]
        s.pred_any_true_reg = [ Wire(Bits1) for _ in range(num_pred_registers) ]
        s.pred_any_false_reg = [ Wire(Bits1) for _ in range(num_pred_registers) ]
        s.active_pred_reg = Wire(PredAddrType)
        s.active_branch_en = Wire(Bits1)
        num_tile_rows_local = num_wr_ports // 2
        num_tile_cols_local = num_tiles // num_tile_rows_local

        @update
        def select_predicates():
            for i in range(num_tiles):
                s.send_tile_preds[i] @= s.pred_tile_valid_active[i]

        @update
        def pred_reduce():
            for r in range(num_pred_registers):
                s.pred_any_true[r] @= s.pred_any_true_reg[r]
                s.pred_any_false[r] @= s.pred_any_false_reg[r]
                s.pred_complete[r] @= (s.pred_count[r] >= s.pred_expected[r]) & (s.pred_expected[r] > 0)

        # Helpful observability (optional)
        # Debug Flags TODO: @darrenl to delete
        MaxThreadType        = mk_bits( clog2( MAX_THREAD_COUNT ) )
        s.expected_count_o   = OutPort( MaxThreadType )
        s.rd_counts_o        = [ OutPort(MaxThreadType) for _ in range(num_rd_ports) ]
        s.wr_counts_o        = [ OutPort(MaxThreadType) for _ in range(num_wr_ports) ]
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
        s.expected_count = Wire( MaxThreadType )
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
        s.wr_addr_cfg_bank0    = [ Wire(RegAddrType) for _ in range(num_wr_ports) ]
        s.wr_addr_cfg_bank1    = [ Wire(RegAddrType) for _ in range(num_wr_ports) ]
        s.wr_addr_valcfg_bank0 = [ Wire(Bits1)       for _ in range(num_wr_ports) ]
        s.wr_addr_valcfg_bank1 = [ Wire(Bits1)       for _ in range(num_wr_ports) ]
        s.expected_count_bank0 = Wire( MaxThreadType )
        s.expected_count_bank1 = Wire( MaxThreadType )

        s.rd_addr_o = [ OutPort(RegAddrType) for _ in range(num_rd_ports)]
        for i in range(num_rd_ports):
            s.rd_addr_o[i] //= s.rd_addr_cfg[i]
        s.send_thread_count //= s.expected_count

        # Counters (increment on handshakes)
        s.rd_count = [ Wire(MaxThreadType) for _ in range(num_rd_ports) ]
        s.wr_count = [ Wire(MaxThreadType) for _ in range(num_wr_ports) ]

        # Next values
        s.rd_count_n = [ OutPort(MaxThreadType) for _ in range(num_rd_ports) ]
        s.wr_count_n = [ OutPort(MaxThreadType) for _ in range(num_wr_ports) ]
        s.rd_addr_valcfg_n = [ OutPort(Bits1) for _ in range(num_rd_ports) ]
        s.wr_addr_valcfg_n = [ OutPort(Bits1) for _ in range(num_wr_ports) ]
        s.rd_addr_cfg_n    = [ Wire(RegAddrType) for _ in range(num_rd_ports) ]
        s.wr_addr_cfg_n    = [ Wire(RegAddrType) for _ in range(num_wr_ports) ]
        s.tid_enabled_n    = [ Wire(Bits1)       for _ in range(num_rd_ports) ]
        s.expected_count_n = Wire( MaxThreadType )

        #TODO: @darrenl delete me debug statements
        for i in range(num_wr_ports):
            s.wr_addr_valcfg_o[i] //= s.wr_addr_valcfg_n[i]

        # -------------------------------------------------------------------------
        # Static connections to regfile data channels
        # (addresses/val asserted only when in RUN)
        # -------------------------------------------------------------------------

        # Thread Idx wires for r/w
        for i in range(num_rd_ports):
            s.register_file.rd_thread_idx[i] //= s.rd_count[i]
        for i in range(num_wr_ports):
            s.register_file.wr_thread_idx[i] //= s.wr_count[i]

        # Enable wires for read and write ports
        s.rd_enable = [ OutPort(Bits1) for _ in range(num_rd_ports) ]
        s.wr_enable = [ OutPort(Bits1) for _ in range(num_wr_ports) ]

        @update
        def comb_port_enables():
            for i in range(num_rd_ports):
                s.rd_enable[i] @= s.rd_addr_valcfg[i] & (s.state == ST_RUN) & (s.rd_count[i] <= s.expected_count_n - 1)
            for i in range(num_wr_ports):
                s.wr_enable[i] @= s.tile_token_shifter_out[i] & s.wr_addr_valcfg[i] & (s.state == ST_RUN) & (s.wr_count[i] <= s.expected_count_n - 1)

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
            s.register_file.wr_addr[i + num_wr_ports].msg //= s.recv_cfg_from_ctrl.msg.ld_reg_addr[i]
            s.register_file.wr_addr[i + num_wr_ports].val //= 1
            s.register_file.wr_data[i + num_wr_ports].msg //= s.ld_data[i]
            s.register_file.wr_data[i + num_wr_ports].val //= s.ld_data_valid[i]
            s.register_file.wr_thread_idx[i + num_wr_ports] //= s.ld_data_id[i]

        # -------------------------------------------------------------------------
        # Assign output data as register or tid for counts
        # -------------------------------------------------------------------------
        @update
        def comb_output_data():
            for i in range(num_rd_ports):
                if s.tid_enabled[i]:
                    s.rd_data[i] @= s.rd_count[i][0:RegDataType.nbits]
                else:
                    s.rd_data[i] @= s.register_file.rd_data[i]

        # -------------------------------------------------------------------------
        # Ready/valid for external ifcs (single-writer comb)
        # -------------------------------------------------------------------------

        @update
        def comb_ready_valid():
            s.recv_cfg_from_ctrl.rdy @= Bits1(1)

        @update_ff
        def cfg_bank_ff():
            if s.reset:
                s.cfg_bank_valid0 <<= 0
                s.cfg_bank_valid1 <<= 0
                s.expected_count_bank0 <<= MaxThreadType(0)
                s.expected_count_bank1 <<= MaxThreadType(0)
                s.pred_reg_bank0 <<= PredAddrType(0)
                s.pred_reg_bank1 <<= PredAddrType(0)
                s.branch_en_bank0 <<= Bits1(0)
                s.branch_en_bank1 <<= Bits1(0)
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
                    if s.cfg_load_sel_w == Bits1(0):
                        s.cfg_bank_valid0 <<= 1
                        s.expected_count_bank0 <<= s.recv_cfg_from_ctrl.msg.thread_count
                        s.pred_reg_bank0 <<= s.recv_cfg_from_ctrl.msg.pred_reg_id
                        s.branch_en_bank0 <<= s.recv_cfg_from_ctrl.msg.branch_en
                        for i in range(num_rd_ports):
                            s.rd_addr_cfg_bank0[i] <<= s.recv_cfg_from_ctrl.msg.in_regs[i]
                            s.rd_addr_valcfg_bank0[i] <<= s.recv_cfg_from_ctrl.msg.in_regs_val[i]
                            s.tid_enabled_bank0[i] <<= s.recv_cfg_from_ctrl.msg.in_tid_enable[i]
                        for i in range(num_wr_ports):
                            s.wr_addr_cfg_bank0[i] <<= s.recv_cfg_from_ctrl.msg.out_regs[i]
                            s.wr_addr_valcfg_bank0[i] <<= s.recv_cfg_from_ctrl.msg.out_regs_val[i]
                        for i in range(num_tiles):
                            s.pred_tile_valid_bank0[i] <<= s.recv_cfg_from_ctrl.msg.pred_tile_valid[i]
                        for i in range(num_ld_ports):
                            s.ld_enable_bank0[i] <<= s.recv_cfg_from_ctrl.msg.ld_enable[i]
                            s.ld_reg_addr_bank0[i] <<= s.recv_cfg_from_ctrl.msg.ld_reg_addr[i]
                        for i in range(num_st_ports):
                            s.st_enable_bank0[i] <<= s.recv_cfg_from_ctrl.msg.st_enable[i]
                    else:
                        s.cfg_bank_valid1 <<= 1
                        s.expected_count_bank1 <<= s.recv_cfg_from_ctrl.msg.thread_count
                        s.pred_reg_bank1 <<= s.recv_cfg_from_ctrl.msg.pred_reg_id
                        s.branch_en_bank1 <<= s.recv_cfg_from_ctrl.msg.branch_en
                        for i in range(num_rd_ports):
                            s.rd_addr_cfg_bank1[i] <<= s.recv_cfg_from_ctrl.msg.in_regs[i]
                            s.rd_addr_valcfg_bank1[i] <<= s.recv_cfg_from_ctrl.msg.in_regs_val[i]
                            s.tid_enabled_bank1[i] <<= s.recv_cfg_from_ctrl.msg.in_tid_enable[i]
                        for i in range(num_wr_ports):
                            s.wr_addr_cfg_bank1[i] <<= s.recv_cfg_from_ctrl.msg.out_regs[i]
                            s.wr_addr_valcfg_bank1[i] <<= s.recv_cfg_from_ctrl.msg.out_regs_val[i]
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

        s.fabric_complete = OutPort( 1 )
        s.fabric_done = OutPort( 1 )
        s.rd_regs_complete = OutPort( num_rd_ports )
        s.wr_regs_complete = OutPort( num_wr_ports )

        @update
        def comb_completion():
            # Default cfg
            s.fabric_complete @= Bits1(0)
            # Only check completion when in RUN state
            if s.state == ST_RUN:
                all_ports_done = Bits1(1)
                any_port_enabled = Bits1(0)

                # Check read ports
                for i in range(num_rd_ports):
                    if s.rd_addr_valcfg[i]:
                        s.rd_regs_complete[i] @= Bits1(s.rd_count[i] >= s.expected_count)
                    else:
                        s.rd_regs_complete[i] @= Bits1(1)
                # Check write ports
                for i in range(num_wr_ports):
                    if s.wr_addr_valcfg[i]:
                        s.wr_regs_complete[i] @= Bits1(s.wr_count[i] >= s.expected_count)
                    else:
                        s.wr_regs_complete[i] @= Bits1(1)

                s.fabric_complete @= (reduce_and(s.rd_regs_complete) & reduce_and(s.wr_regs_complete)) \
                        & (s.expected_count > MaxThreadType(0))
        
        @update
        def update_fabric_done():
            if s.reset | (s.recv_cfg_from_ctrl.val & s.recv_cfg_from_ctrl.rdy):
                s.fabric_done @= 0
            else:
                if s.fabric_complete:
                    s.fabric_done @= 1

        # -------------------------------------------------------------------------
        # Next-state & counters (single comb writer)
        # -------------------------------------------------------------------------

        @update
        def comb_next_state_and_counts():
            # Default hold
            s.state_n @= s.state
            for i in range(num_rd_ports):
                # RF defaults
                s.rd_count_n[i] @= s.rd_count[i]
                s.rd_addr_valcfg_n[i] @= s.rd_addr_valcfg[i]
                s.rd_addr_cfg_n[i] @= s.rd_addr_cfg[i]
                s.tid_enabled_n[i] @= s.tid_enabled[i]

                # Token defaults
                s.tile_token_take[i] @= 0
            for i in range(num_wr_ports):
                # Token default
                s.tile_token_return[i] @= 0

                # Address
                s.wr_count_n[i] @= s.wr_count[i]
                s.wr_addr_valcfg_n[i] @= s.wr_addr_valcfg[i]
                s.wr_addr_cfg_n[i] @= s.wr_addr_cfg[i]
            s.expected_count_n @= s.expected_count

            # State transitions
            if s.state == ST_IDLE:
                # Handshake to start configuration
                if s.recv_cfg_from_ctrl.val & s.recv_cfg_from_ctrl.rdy & (s.cfg_active_sel_w == s.cfg_load_sel_w):
                    s.state_n @= ST_RUN
                    for i in range(num_rd_ports):
                        s.rd_count_n[i] @= MaxThreadType(0)
                        s.rd_addr_valcfg_n[i] @= s.recv_cfg_from_ctrl.msg.in_regs_val[i]
                        s.rd_addr_cfg_n[i] @= s.recv_cfg_from_ctrl.msg.in_regs[i]
                        s.tid_enabled_n[i] @= s.recv_cfg_from_ctrl.msg.in_tid_enable[i]
                    for i in range(num_wr_ports):
                        s.wr_count_n[i] @= MaxThreadType(0)
                        s.wr_addr_valcfg_n[i] @= s.recv_cfg_from_ctrl.msg.out_regs_val[i]
                        s.wr_addr_cfg_n[i] @= s.recv_cfg_from_ctrl.msg.out_regs[i]
                    s.expected_count_n @= s.recv_cfg_from_ctrl.msg.thread_count
            
            elif s.state == ST_RUN:
                # Count transactions only for enabled ports
                for i in range(num_rd_ports):
                    if s.rd_addr_valcfg[i]:
                        if s.tile_token_avail[i] & (s.rd_count[i] < s.expected_count):
                            s.rd_count_n[i] @= s.rd_count[i] + 1
                            s.tile_token_take[i] @= 1

                for i in range(num_wr_ports):
                    if s.wr_addr_valcfg[i]:
                        if s.tile_token_shifter_out[i] & (s.wr_count[i] < s.expected_count):
                            s.wr_count_n[i] @= s.wr_count[i] + 1
                            s.tile_token_return[i] @= 1

                # Transition back to IDLE when complete
                if s.fabric_done & s.ld_st_complete:
                    s.state_n @= ST_IDLE

        # -------------------------------------------------------------------------
        # Sequential update: commit state, counters, and capture config
        # -------------------------------------------------------------------------

        @update_ff
        def seq_ff():
            if s.reset:
                s.state           <<= ST_IDLE
                s.expected_count  <<= MaxThreadType(0)
                s.active_pred_reg <<= PredAddrType(0)
                s.active_branch_en <<= Bits1(0)
                for i in range(num_rd_ports):
                    s.rd_addr_cfg[i]    <<= RegAddrType(0)
                    s.rd_addr_valcfg[i] <<= Bits1(0)
                    s.tid_enabled[i]    <<= Bits1(0)
                    s.rd_count[i]       <<= MaxThreadType(0)
                for i in range(num_wr_ports):
                    s.wr_addr_cfg[i]    <<= RegAddrType(0)
                    s.wr_addr_valcfg[i] <<= Bits1(0)
                    s.wr_count[i]       <<= MaxThreadType(0)
                for i in range(num_tiles):
                    s.pred_tile_valid_active[i] <<= Bits1(0)
                for i in range(num_ld_ports):
                    s.ld_enable_active[i] <<= Bits1(0)
                    s.ld_reg_addr_active[i] <<= RegAddrType(0)
                for i in range(num_st_ports):
                    s.st_enable_active[i] <<= Bits1(0)

            else:
                if s.cfg_swap_w:
                    s.state <<= ST_RUN
                    if s.cfg_active_sel_w == Bits1(0):
                        s.expected_count <<= s.expected_count_bank0
                        s.active_pred_reg <<= s.pred_reg_bank0
                        s.active_branch_en <<= s.branch_en_bank0
                        for i in range(num_rd_ports):
                            s.rd_addr_cfg[i] <<= s.rd_addr_cfg_bank0[i]
                            s.rd_addr_valcfg[i] <<= s.rd_addr_valcfg_bank0[i]
                            s.tid_enabled[i] <<= s.tid_enabled_bank0[i]
                            s.rd_count[i] <<= MaxThreadType(0)
                        for i in range(num_wr_ports):
                            s.wr_addr_cfg[i] <<= s.wr_addr_cfg_bank0[i]
                            s.wr_addr_valcfg[i] <<= s.wr_addr_valcfg_bank0[i]
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
                        s.active_pred_reg <<= s.pred_reg_bank1
                        s.active_branch_en <<= s.branch_en_bank1
                        for i in range(num_rd_ports):
                            s.rd_addr_cfg[i] <<= s.rd_addr_cfg_bank1[i]
                            s.rd_addr_valcfg[i] <<= s.rd_addr_valcfg_bank1[i]
                            s.tid_enabled[i] <<= s.tid_enabled_bank1[i]
                            s.rd_count[i] <<= MaxThreadType(0)
                        for i in range(num_wr_ports):
                            s.wr_addr_cfg[i] <<= s.wr_addr_cfg_bank1[i]
                            s.wr_addr_valcfg[i] <<= s.wr_addr_valcfg_bank1[i]
                            s.wr_count[i] <<= MaxThreadType(0)
                        for i in range(num_tiles):
                            s.pred_tile_valid_active[i] <<= s.pred_tile_valid_bank1[i]
                        for i in range(num_ld_ports):
                            s.ld_enable_active[i] <<= s.ld_enable_bank1[i]
                            s.ld_reg_addr_active[i] <<= s.ld_reg_addr_bank1[i]
                        for i in range(num_st_ports):
                            s.st_enable_active[i] <<= s.st_enable_bank1[i]
                else:
                    # Advance state
                    s.state <<= s.state_n

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

                    s.expected_count <<= s.expected_count_n

                    if s.recv_cfg_from_ctrl.val & s.recv_cfg_from_ctrl.rdy & (s.cfg_active_sel_w == s.cfg_load_sel_w) & (s.state == ST_IDLE):
                        s.active_pred_reg <<= s.recv_cfg_from_ctrl.msg.pred_reg_id
                        s.active_branch_en <<= s.recv_cfg_from_ctrl.msg.branch_en
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
        @update_ff
        def pred_rf_ff():
            if s.reset:
                for r in range(num_pred_registers):
                    s.pred_count[r] <<= PredCountType(0)
                    s.pred_expected[r] <<= PredCountType(0)
                    s.pred_any_true_reg[r] <<= Bits1(0)
                    s.pred_any_false_reg[r] <<= Bits1(0)
                # No per-tid storage; only summary bits
            else:
                cfg_start = s.recv_cfg_from_ctrl.val & s.recv_cfg_from_ctrl.rdy & (s.cfg_active_sel_w == s.cfg_load_sel_w) & (s.state == ST_IDLE)
                # Clear predicate register on config start
                if cfg_start & s.recv_cfg_from_ctrl.msg.branch_en:
                    reg = s.recv_cfg_from_ctrl.msg.pred_reg_id
                    s.pred_count[reg] <<= PredCountType(0)
                    s.pred_expected[reg] <<= PredCountType(s.recv_cfg_from_ctrl.msg.thread_count)
                    s.pred_any_true_reg[reg] <<= Bits1(0)
                    s.pred_any_false_reg[reg] <<= Bits1(0)
                elif cfg_start:
                    # Not a branch config; clear expected so controller doesn't wait
                    reg = s.recv_cfg_from_ctrl.msg.pred_reg_id
                    s.pred_expected[reg] <<= PredCountType(0)
                # Capture predicate bits while active branch config is running
                if s.state == ST_RUN:
                    reg = s.active_pred_reg
                    for i in range(num_wr_ports):
                        row = i >> 1
                        col = 0 if (i & 1) == 0 else (num_tile_cols_local - 1)
                        tile_idx = row * num_tile_cols_local + col
                        if (s.pred_expected[reg] > 0):
                            if s.pred_count[reg] < s.pred_expected[reg]:
                                s.pred_count[reg] <<= s.pred_count[reg] + PredCountType(1)
                            pred_val = Bits1(s.wr_data[i])
                            s.pred_any_true_reg[reg] <<= s.pred_any_true_reg[reg] | pred_val
                            s.pred_any_false_reg[reg] <<= s.pred_any_false_reg[reg] | ~pred_val

        # -------------------------------------------------------------------------
        # Outputs derived from registered state (single-writer comb)
        # -------------------------------------------------------------------------

        @update
        def comb_outputs():
            # cfg_done is level-true only in RUN when complete
            s.cfg_done    @= s.fabric_done & s.ld_st_complete
            # mirrors
            s.expected_count_o @= s.expected_count
            for i in range(num_rd_ports):
                s.rd_counts_o[i] @= s.rd_count[i]
            for i in range(num_wr_ports):
                s.wr_counts_o[i] @= s.wr_count[i]
