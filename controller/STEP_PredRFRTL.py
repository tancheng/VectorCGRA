from pymtl3 import *
from ..lib.basic.val_rdy.ifcs import RecvIfcRTL, SendIfcRTL
from pymtl3.stdlib.primitive import Reg
from ..mem.register_cluster.STEP_RegisterFileRTL import STEP_RegisterFileRTL
from ..lib.messages import *
from ..lib.opt_type import *

class STEP_PredRFRTL( Component ):
    def construct(s,
                    num_tiles
                    RegDataType,
                    RegAddrType,
                    CfgMetadataType,
                    num_banks=2,
                    num_rd_ports=2,
                    num_wr_ports=2,
                    num_registers=16,
                    ):

        # -------------------------------------------------------------------------
        # Submodules
        # -------------------------------------------------------------------------

        s.register_file = STEP_RegisterFileRTL(
            RegDataType, RegAddrType,
            num_reg_banks=num_banks,
            num_rd_ports=num_rd_ports,
            num_wr_ports=num_wr_ports,
            num_registers_per_reg_bank=num_registers // num_banks
        )



        @update
        def perform_pred_math():
            if s.recv_cfg_from_ctrl.val:
                for i in range(MAX_PRED_MATH):
                    if s.recv_cfg_from_ctrl.msg.pred_math[i] > 0 & s.recv_cfg_from_ctrl.msg.pred_math[i].opt_type != OPT_NAH:
                        s.wr_addr 



        # External ifcs
        s.recv_cfg_from_ctrl = RecvIfcRTL( CfgMetadataType )   # from main ctrl
        s.rd_data            = [ SendIfcRTL(RegDataType) for _ in range(num_rd_ports) ]
        s.wr_data            = [ RecvIfcRTL(RegDataType) for _ in range(num_wr_ports) ]
        s.cfg_done           = OutPort( Bits1 )                # level-true when RUN complete this cycle
        s.cfg_state          = OutPort( Bits2 )                # 0:IDLE, 1:CONFIGURE, 2:RUN
        s.recv_pred_port = [ OutPort(Bits1) for _ in range(num_wr_ports)]
        s.send_tile_preds = [ OutPort(Bits1) for _ in range(num_tiles)]

        # Helpful observability (optional)
        MaxThreadType        = mk_bits( clog2( MAX_THREAD_COUNT ) )
        s.expected_count_o   = OutPort( MaxThreadType )
        s.rd_counts_o        = [ OutPort(MaxThreadType) for _ in range(num_rd_ports) ]
        s.wr_counts_o        = [ OutPort(MaxThreadType) for _ in range(num_wr_ports) ]

        # -------------------------------------------------------------------------
        # FSM + config registers
        # -------------------------------------------------------------------------

        # States
        ST_IDLE      = Bits2(0)
        ST_CONFIGURE = Bits2(1)
        ST_RUN       = Bits2(2)

        # State reg
        s.state    = Wire( Bits2 )
        s.state_n  = OutPort( Bits2 )

        # Latched configuration (stable during RUN)
        s.rd_addr_cfg    = [ Wire(RegAddrType) for _ in range(num_rd_ports) ]
        s.rd_addr_valcfg = [ Wire(Bits1)       for _ in range(num_rd_ports) ]
        s.wr_addr_cfg    = [ Wire(RegAddrType) for _ in range(num_wr_ports) ]
        s.wr_addr_valcfg = [ Wire(Bits1)       for _ in range(num_wr_ports) ]
        s.expected_count = Wire( MaxThreadType )

        s.rd_addr_o = [ OutPort(RegAddrType) for _ in range(num_rd_ports)]
        for i in range(num_rd_ports):
            s.rd_addr_o[i] //= s.rd_addr_cfg[i]

        # Counters (increment on handshakes)
        s.rd_count = [ Wire(MaxThreadType) for _ in range(num_rd_ports) ]
        s.wr_count = [ Wire(MaxThreadType) for _ in range(num_wr_ports) ]

        # Next values
        s.rd_count_n = [ Wire(MaxThreadType) for _ in range(num_rd_ports) ]
        s.wr_count_n = [ Wire(MaxThreadType) for _ in range(num_wr_ports) ]
        s.rd_addr_valcfg_n = [ OutPort(Bits1) for _ in range(num_rd_ports) ]
        s.wr_addr_valcfg_n = [ OutPort(Bits1) for _ in range(num_wr_ports) ]
        s.rd_addr_cfg_n    = [ Wire(RegAddrType) for _ in range(num_rd_ports) ]
        s.wr_addr_cfg_n    = [ Wire(RegAddrType) for _ in range(num_wr_ports) ]
        s.expected_count_n = Wire( MaxThreadType )

        # -------------------------------------------------------------------------
        # Static connections to regfile data channels
        # (addresses/val asserted only when in RUN)
        # -------------------------------------------------------------------------

        # Enable wires for read and write ports
        s.rd_enable = [ Wire(Bits1) for _ in range(num_rd_ports) ]
        s.wr_enable = [ Wire(Bits1) for _ in range(num_wr_ports) ]

        @update
        def comb_port_enables():
        for i in range(num_rd_ports):
            s.rd_enable[i] @= s.rd_addr_valcfg[i] & (s.state == ST_RUN) & (s.rd_count[i] <= s.expected_count_n - 1)
        for i in range(num_wr_ports):
            s.wr_enable[i] @= s.wr_addr_valcfg[i] & (s.state == ST_RUN) & (s.wr_count[i] <= s.expected_count_n - 1)

        for i in range(num_rd_ports):
        s.register_file.rd_addr[i].msg //= s.rd_addr_cfg[i]
        s.register_file.rd_addr[i].val //= s.rd_enable[i]
        s.rd_data[i].msg               //= s.register_file.rd_data[i].msg
        s.rd_data[i].val               //= s.register_file.rd_data[i].val

        for i in range(num_wr_ports):
        s.register_file.wr_addr[i].msg //= s.wr_addr_cfg[i]
        s.register_file.wr_addr[i].val //= s.wr_enable[i]
        s.register_file.wr_data[i].msg //= s.wr_data[i].msg
        s.register_file.wr_data[i].val //= s.wr_data[i].val

        # -------------------------------------------------------------------------
        # Ready/valid for external ifcs (single-writer comb)
        # -------------------------------------------------------------------------

        @update
        def comb_ready_valid():
            # Accept new config only when IDLE
            s.recv_cfg_from_ctrl.rdy @= Bits1( s.state == ST_IDLE )
            # WR data is ready in RUN only if regfile input is ready
            for i in range(num_wr_ports):
                s.wr_data[i].rdy @= (s.state == ST_RUN) & s.register_file.wr_data[i].rdy

        # -------------------------------------------------------------------------
        # Completion check (comb)
        # -------------------------------------------------------------------------

        s.cfg_complete = OutPort( Bits1 )
        s.rd_regs_complete = OutPort( num_rd_ports )
        s.wr_regs_complete = OutPort( num_wr_ports )

        @update
        def comb_completion():
            # Default cfg
            s.cfg_complete @= Bits1(0)
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

                s.cfg_complete @= (reduce_and(s.rd_regs_complete) & reduce_and(s.wr_regs_complete)) \
                        & (s.expected_count > MaxThreadType(0))

        # -------------------------------------------------------------------------
        # Next-state & counters (single comb writer)
        # -------------------------------------------------------------------------

        @update
        def comb_next_state_and_counts():
            # Default hold
            s.state_n @= s.state
            for i in range(num_rd_ports):
                s.rd_count_n[i] @= s.rd_count[i]
                s.rd_addr_valcfg_n[i] @= s.rd_addr_valcfg[i]
                s.rd_addr_cfg_n[i] @= s.rd_addr_cfg[i]
            for i in range(num_wr_ports):
                s.wr_count_n[i] @= s.wr_count[i]
                s.wr_addr_valcfg_n[i] @= s.wr_addr_valcfg[i]
                s.wr_addr_cfg_n[i] @= s.wr_addr_cfg[i]
            s.expected_count_n @= s.expected_count

            # State transitions
            if s.state == ST_IDLE:
                # Handshake to start configuration
                if s.recv_cfg_from_ctrl.val & s.recv_cfg_from_ctrl.rdy:
                    s.state_n @= ST_CONFIGURE
                    for i in range(num_rd_ports):
                        s.rd_count_n[i] @= MaxThreadType(0)
                        s.rd_addr_valcfg_n[i] @= s.recv_cfg_from_ctrl.msg.in_regs_val[i]
                        s.rd_addr_cfg_n[i] @= s.recv_cfg_from_ctrl.msg.in_regs[i]
                    for i in range(num_wr_ports):
                        s.wr_count_n[i] @= MaxThreadType(0)
                        s.wr_addr_valcfg_n[i] @= s.recv_cfg_from_ctrl.msg.out_regs_val[i]
                        s.wr_addr_cfg_n[i] @= s.recv_cfg_from_ctrl.msg.out_regs[i]
                    s.expected_count_n @= s.recv_cfg_from_ctrl.msg.thread_count
            
            elif s.state == ST_CONFIGURE:
                # Always transition to RUN after configuration settles
                s.state_n @= ST_RUN
            
            elif s.state == ST_RUN:
                # Count transactions only for enabled ports
                for i in range(num_rd_ports):
                    if s.rd_addr_valcfg[i]:
                        handshake = s.register_file.rd_data[i].val & s.rd_data[i].rdy
                        s.rd_count_n[i] @= s.rd_count[i] + MaxThreadType(handshake)

                for i in range(num_wr_ports):
                    if s.wr_addr_valcfg[i]:
                        handshake = s.wr_data[i].val & s.register_file.wr_data[i].rdy
                        s.wr_count_n[i] @= s.wr_count[i] + MaxThreadType(handshake)

                # Transition back to IDLE when complete
                if s.cfg_complete:
                    s.state_n @= ST_IDLE

        # -------------------------------------------------------------------------
        # Sequential update: commit state, counters, and capture config
        # -------------------------------------------------------------------------

        @update_ff
        def seq_ff():
            if s.reset:
                s.state           <<= ST_IDLE
                s.expected_count  <<= MaxThreadType(0)
                for i in range(num_rd_ports):
                    s.rd_addr_cfg[i]    <<= RegAddrType(0)
                    s.rd_addr_valcfg[i] <<= Bits1(0)
                    s.rd_count[i]       <<= MaxThreadType(0)
                for i in range(num_wr_ports):
                    s.wr_addr_cfg[i]    <<= RegAddrType(0)
                    s.wr_addr_valcfg[i] <<= Bits1(0)
                    s.wr_count[i]       <<= MaxThreadType(0)

            else:
                # Advance state
                s.state <<= s.state_n

                # Update counters
                for i in range(num_rd_ports):
                    s.rd_count[i] <<= s.rd_count_n[i]
                    s.rd_addr_cfg[i] <<= s.rd_addr_cfg_n[i]
                    s.rd_addr_valcfg[i] <<= s.rd_addr_valcfg_n[i]

                for i in range(num_wr_ports):
                    s.wr_count[i] <<= s.wr_count_n[i]
                    s.wr_addr_cfg[i] <<= s.wr_addr_cfg_n[i]
                    s.wr_addr_valcfg[i] <<= s.wr_addr_valcfg_n[i]

                s.expected_count <<= s.expected_count_n

        # -------------------------------------------------------------------------
        # Outputs derived from registered state (single-writer comb)
        # -------------------------------------------------------------------------

        @update
        def comb_outputs():
        # State code for visibility
        s.cfg_state   @= s.state
        # cfg_done is level-true only in RUN when complete
        s.cfg_done    @= Bits1( (s.state == ST_RUN) & s.cfg_complete )
        # mirrors
        s.expected_count_o @= s.expected_count
        for i in range(num_rd_ports):
            s.rd_counts_o[i] @= s.rd_count[i]
        for i in range(num_wr_ports):
            s.wr_counts_o[i] @= s.wr_count[i]