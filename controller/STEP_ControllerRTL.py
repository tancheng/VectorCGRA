from pymtl3 import *
from pymtl3.stdlib.primitive import Reg
from ..lib.basic.val_rdy.ifcs import RecvIfcRTL
from ..lib.basic.val_rdy.ifcs import SendIfcRTL
from pymtl3.stdlib.primitive import RegisterFile
from ..lib.basic.val_rdy.queues import NormalQueueRTL
from ..lib.messages import *
from ..lib.opt_type import *
from ..lib.util.common import *
from ..lib.cmd_type import *
from ..noc.PyOCN.pymtl3_net.channel.ChannelRTL import ChannelRTL
from ..noc.PyOCN.pymtl3_net.xbar.XbarBypassQueueRTL import XbarBypassQueueRTL
from ..mem.register_cluster.STEP_BRAMRTL import STEP_BRAMRTL

class STEP_ControllerRTL(Component):
  def construct(s,
                CfgBitstreamType,
                CfgMetadataType,
                CfgTokenizerType,
                TileBitstreamType,
                num_tiles,
                num_pred_registers,
                debug = False
                ):
    BitstreamAddrType = mk_bits(clog2(MAX_BITSTREAM_COUNT))
    PredRegType = mk_bits(clog2(num_pred_registers))
    LoopCountType = mk_bits(clog2(MAX_THREAD_COUNT))
    TileCountType = mk_bits(clog2(num_tiles + 1))
    
    # CPU ports
    s.recv_from_cpu_bitstream_pkt = RecvIfcRTL(TileBitstreamType)
    s.recv_from_cpu_metadata_pkt = RecvIfcRTL(CfgMetadataType)
    s.send_to_cpu_done = OutPort(1)
    s.pc_req_trigger = OutPort(1)
    s.pc_req_trigger_count = OutPort(TileCountType)
    s.pc_req_trigger_complete = InPort(1)
    s.pc_req = OutPort(BitstreamAddrType)
    s.cfg_active_sel = OutPort(1)
    s.cfg_load_sel = OutPort(1)
    s.cfg_swap = OutPort(1)
    s.rf_dep_start = OutPort(1)

    # Fabric Pkts Counts
    if debug:
        s.tile_bitstreams_seen = OutPort( TileCountType )
    else:
        s.tile_bitstreams_seen = Wire( TileCountType )
    
    # PE Fabric ports
    s.send_cfg_to_tiles = SendIfcRTL(TileBitstreamType)
    # s.send_fabric_bitstream_rst = OutPort(1)
    
    # RF ports
    s.send_cfg_to_rf = SendIfcRTL(CfgMetadataType)

    # Tokenizer ports
    s.send_cfg_to_tokenizer = SendIfcRTL(CfgTokenizerType)
    
    # Internal Ports
    s.rf_cfg_done = InPort(1)
    s.rf_cfg_ready = InPort(1)
    s.rf_dep_mode = InPort(1)
    s.pred_any_true = [ InPort(1) for _ in range(num_pred_registers) ]
    s.pred_any_false = [ InPort(1) for _ in range(num_pred_registers) ]
    s.pred_complete = [ InPort(1) for _ in range(num_pred_registers) ]
    s.pred_true_count = [ InPort(LoopCountType) for _ in range(num_pred_registers) ]
    s.pred_false_count = [ InPort(LoopCountType) for _ in range(num_pred_registers) ]
    s.pred_any_true_sel = Wire(1)
    s.pred_any_false_sel = Wire(1)
    s.pred_complete_sel = Wire(1)
    s.pred_true_count_sel = Wire(LoopCountType)
    s.pred_false_count_sel = Wire(LoopCountType)

    @update
    def select_predicate_reg():
        s.pred_any_true_sel @= Bits1(0)
        s.pred_any_false_sel @= Bits1(0)
        s.pred_complete_sel @= Bits1(0)
        s.pred_true_count_sel @= LoopCountType(0)
        s.pred_false_count_sel @= LoopCountType(0)
        for i in range(num_pred_registers):
            if s.active_meta.pred_reg_id == i:
                s.pred_any_true_sel @= s.pred_any_true[i]
                s.pred_any_false_sel @= s.pred_any_false[i]
                s.pred_complete_sel @= s.pred_complete[i]
                s.pred_true_count_sel @= s.pred_true_count[i]
                s.pred_false_count_sel @= s.pred_false_count[i]
    if debug:
        s.pc_started = OutPort(1)
        s.pc_done = OutPort(1)
        s.pc = OutPort(BitstreamAddrType)
        s.pc_next = OutPort(BitstreamAddrType)
        s.last_pc = OutPort(1)
    else:
        s.pc = Wire(BitstreamAddrType)
        s.pc_started = Wire(1)
        s.pc_done = Wire(1)
        s.pc_next = Wire(BitstreamAddrType)
        s.last_pc = Wire(1)
    s.pc_req //= s.pc
    
    # New register for maintaining current cfg_mem read address
    s.cfg_mem_raddr_reg = Wire(BitstreamAddrType)
    if debug:
        s.cfg_mem_raddr = OutPort(BitstreamAddrType)
        s.cfg_mem_raddr //= s.cfg_mem_raddr_reg
    s.state = OutPort(mk_bits(2))
    
    # Internal Cfg mem
    s.cfg_mem_metadata = STEP_BRAMRTL(CfgMetadataType, MAX_BITSTREAM_COUNT, rd_ports=1,
                            wr_ports=1)

    s.cfg_metadata_rd = OutPort(CfgMetadataType)
    s.cfg_metadata_rd //= s.cfg_mem_metadata.rdata

    # Shadow metadata storage for low-latency reads in control logic
    s.cfg_mem_shadow = [ Wire(CfgMetadataType) for _ in range(MAX_BITSTREAM_COUNT) ]
    s.cfg_mem_shadow_rdata = Wire(CfgMetadataType)
    s.br_id_shadow = [ Wire(BitstreamAddrType) for _ in range(MAX_BITSTREAM_COUNT) ]
    s.end_cfg_shadow = [ Wire(1) for _ in range(MAX_BITSTREAM_COUNT) ]
    s.br_id_by_load_pc = Wire(BitstreamAddrType)
    s.end_cfg_by_load_pc = Wire(1)
    s.br_id_by_next_pc = Wire(BitstreamAddrType)
    s.end_cfg_by_next_pc = Wire(1)
    s.end_cfg_by_branch_reconverge = Wire(1)
    s.tile_load_shadow = [ Wire(TileCountType) for _ in range(MAX_BITSTREAM_COUNT) ]
    s.tile_load_by_load_pc = Wire(TileCountType)
    s.tile_load_by_next_pc = Wire(TileCountType)
    s.tile_load_by_branch_true_meta = Wire(TileCountType)
    s.tile_load_by_branch_false_meta = Wire(TileCountType)
    s.tile_load_by_branch_false_reg = Wire(TileCountType)
    s.tile_load_by_branch_reconverge = Wire(TileCountType)
    s.tile_load_by_loop_start_meta = Wire(TileCountType)
    s.tile_load_by_loop_exit_meta = Wire(TileCountType)
    
    # Connect the read address register to the actual cfg_mem read address
    s.cfg_mem_metadata.raddr //= s.cfg_mem_raddr_reg
    s.active_bank = Wire(1)
    s.load_bank = Wire(1)
    s.load_bank_reg = Wire(1)
    s.load_pc = Wire(BitstreamAddrType)
    s.next_pc = Wire(BitstreamAddrType)
    s.active_meta = Wire(CfgMetadataType)
    s.next_meta = Wire(CfgMetadataType)
    s.load_meta = Wire(CfgMetadataType)
    s.active_meta_valid = Wire(1)
    s.load_meta_valid = Wire(1)
    s.next_ready = Wire(1)
    s.load_tiles_done = Wire(1)
    s.load_cfg_done = Wire(1)
    s.load_inflight = Wire(1)
    s.meta_req_pending = Wire(1)
    s.cfg_send_pending = Wire(1)
    s.prefetch_inflight = Wire(1)
    s.rf_done_pending = Wire(1)
    s.rf_wait_for_busy = Wire(1)
    s.branch_active = Wire(1)
    s.branch_need_false = Wire(1)
    s.branch_phase = Wire(1)
    s.branch_true_cfg = Wire(BitstreamAddrType)
    s.branch_false_cfg = Wire(BitstreamAddrType)
    s.branch_reconverge_cfg = Wire(BitstreamAddrType)
    s.branch_true_count = Wire(LoopCountType)
    s.branch_false_count = Wire(LoopCountType)
    s.load_thread_count_override = Wire(LoopCountType)
    s.load_thread_count_override_valid = Wire(1)
    s.loop_counter = Wire(LoopCountType)
    s.rf_active = Wire(1)
    s.last_cfg_id = Wire(BitstreamAddrType)
    s.send_to_cpu_done_reg = Wire(1)
    s.load_tile_count = Wire(TileCountType)
    s.load_tile_count_next = Wire(TileCountType)
    s.scan_drain_count = Wire(TileCountType)
    s.cfg_to_rf_msg = Wire(CfgMetadataType)
    s.cfg_to_tokenizer_msg = Wire(CfgTokenizerType)
    num_pred_tiles = len(s.cfg_to_rf_msg.pred_tile_valid)
    num_ld_cfg_ports = len(s.cfg_to_rf_msg.ld_enable)
    num_st_cfg_ports = len(s.cfg_to_rf_msg.st_enable)
    num_rd_cfg_ports = len(s.cfg_to_rf_msg.in_regs)
    num_wr_cfg_ports = len(s.cfg_to_rf_msg.out_regs)
    num_token_sinks = len(s.cfg_to_rf_msg.tokenizer_cfg.token_route_sink_enable)
    num_token_delays = len(s.cfg_to_rf_msg.tokenizer_cfg.token_route_delay_to_sink)
    last_st_port_idx = num_st_cfg_ports - 1
    RouteType = mk_bits(num_token_delays)
    route_low_mask = RouteType(0b11)
    route_store0_sel = RouteType(0b10)
    route_store1_sel = RouteType(0b01)
    s.active_meta_has_load = Wire(1)
    s.active_meta_has_store = Wire(1)

    # Debug ports removed for simplified interface

    @update
    def update_ready():
        # Always ready to accept metadata; bitstream always ready
        s.recv_from_cpu_metadata_pkt.rdy @= 1
        s.recv_from_cpu_bitstream_pkt.rdy @= 1

    @update
    def shadow_read():
        # Use shadow entry zero as the default to keep the block translatable.
        s.cfg_mem_shadow_rdata @= s.cfg_mem_shadow[0]
        s.br_id_by_load_pc @= s.br_id_shadow[0]
        s.end_cfg_by_load_pc @= s.end_cfg_shadow[0]
        s.br_id_by_next_pc @= s.br_id_shadow[0]
        s.end_cfg_by_next_pc @= s.end_cfg_shadow[0]
        s.end_cfg_by_branch_reconverge @= s.end_cfg_shadow[0]
        s.tile_load_by_load_pc @= s.tile_load_shadow[0]
        s.tile_load_by_next_pc @= s.tile_load_shadow[0]
        s.tile_load_by_branch_true_meta @= s.tile_load_shadow[0]
        s.tile_load_by_branch_false_meta @= s.tile_load_shadow[0]
        s.tile_load_by_branch_false_reg @= s.tile_load_shadow[0]
        s.tile_load_by_branch_reconverge @= s.tile_load_shadow[0]
        s.tile_load_by_loop_start_meta @= s.tile_load_shadow[0]
        s.tile_load_by_loop_exit_meta @= s.tile_load_shadow[0]
        for i in range(MAX_BITSTREAM_COUNT):
            if s.load_pc == BitstreamAddrType(i):
                s.cfg_mem_shadow_rdata @= s.cfg_mem_shadow[i]
                s.br_id_by_load_pc @= s.br_id_shadow[i]
                s.end_cfg_by_load_pc @= s.end_cfg_shadow[i]
                s.tile_load_by_load_pc @= s.tile_load_shadow[i]
            if s.pc_next == BitstreamAddrType(i):
                s.br_id_by_next_pc @= s.br_id_shadow[i]
                s.end_cfg_by_next_pc @= s.end_cfg_shadow[i]
                s.tile_load_by_next_pc @= s.tile_load_shadow[i]
            if s.active_meta.branch_true_cfg_id == BitstreamAddrType(i):
                s.tile_load_by_branch_true_meta @= s.tile_load_shadow[i]
            if s.active_meta.branch_false_cfg_id == BitstreamAddrType(i):
                s.tile_load_by_branch_false_meta @= s.tile_load_shadow[i]
            if s.branch_false_cfg == BitstreamAddrType(i):
                s.tile_load_by_branch_false_reg @= s.tile_load_shadow[i]
            if s.branch_reconverge_cfg == BitstreamAddrType(i):
                s.end_cfg_by_branch_reconverge @= s.end_cfg_shadow[i]
                s.tile_load_by_branch_reconverge @= s.tile_load_shadow[i]
            if s.active_meta.loop_start_cfg_id == BitstreamAddrType(i):
                s.tile_load_by_loop_start_meta @= s.tile_load_shadow[i]
            if s.active_meta.loop_exit_cfg_id == BitstreamAddrType(i):
                s.tile_load_by_loop_exit_meta @= s.tile_load_shadow[i]

    @update
    def update_scan_chain():
        s.send_cfg_to_tiles.msg @= s.recv_from_cpu_bitstream_pkt.msg
        s.send_cfg_to_tiles.val @= s.recv_from_cpu_bitstream_pkt.val

    @update
    def prepare_cfg_messages():
        s.cfg_to_rf_msg.cmd @= s.load_meta.cmd
        s.cfg_to_rf_msg.tile_load_count @= s.load_meta.tile_load_count
        for i in range(num_pred_tiles):
            s.cfg_to_rf_msg.pred_tile_valid[i] @= s.load_meta.pred_tile_valid[i]
        for i in range(num_ld_cfg_ports):
            s.cfg_to_rf_msg.ld_enable[i] @= s.load_meta.ld_enable[i]
            s.cfg_to_rf_msg.ld_reg_addr[i] @= s.load_meta.ld_reg_addr[i]
        for i in range(num_st_cfg_ports):
            s.cfg_to_rf_msg.st_enable[i] @= s.load_meta.st_enable[i]
        for i in range(num_rd_cfg_ports):
            s.cfg_to_rf_msg.in_regs[i] @= s.load_meta.in_regs[i]
            s.cfg_to_rf_msg.in_regs_val[i] @= s.load_meta.in_regs_val[i]
            s.cfg_to_rf_msg.in_tid_enable[i] @= s.load_meta.in_tid_enable[i]
        for i in range(num_wr_cfg_ports):
            s.cfg_to_rf_msg.out_regs[i] @= s.load_meta.out_regs[i]
            s.cfg_to_rf_msg.out_regs_val[i] @= s.load_meta.out_regs_val[i]
            s.cfg_to_rf_msg.out_pred_regs[i] @= s.load_meta.out_pred_regs[i]
            s.cfg_to_rf_msg.out_pred_regs_val[i] @= s.load_meta.out_pred_regs_val[i]
        for i in range(num_token_sinks):
            s.cfg_to_rf_msg.tokenizer_cfg.token_route_sink_enable[i] @= s.load_meta.tokenizer_cfg.token_route_sink_enable[i]
            s.cfg_to_tokenizer_msg.token_route_sink_enable[i] @= s.load_meta.tokenizer_cfg.token_route_sink_enable[i]
        for i in range(num_token_delays):
            s.cfg_to_rf_msg.tokenizer_cfg.token_route_delay_to_sink[i] @= s.load_meta.tokenizer_cfg.token_route_delay_to_sink[i]
            s.cfg_to_tokenizer_msg.token_route_delay_to_sink[i] @= s.load_meta.tokenizer_cfg.token_route_delay_to_sink[i]
        s.cfg_to_rf_msg.cfg_id @= s.load_meta.cfg_id
        s.cfg_to_rf_msg.br_id @= s.load_meta.br_id
        if s.load_thread_count_override_valid:
            s.cfg_to_rf_msg.thread_count @= s.load_thread_count_override
        else:
            s.cfg_to_rf_msg.thread_count @= s.load_meta.thread_count
        s.cfg_to_rf_msg.start_cfg @= s.load_meta.start_cfg
        s.cfg_to_rf_msg.end_cfg @= s.load_meta.end_cfg
        s.cfg_to_rf_msg.branch_en @= s.load_meta.branch_en
        s.cfg_to_rf_msg.pred_reg_id @= s.load_meta.pred_reg_id
        s.cfg_to_rf_msg.branch_true_cfg_id @= s.load_meta.branch_true_cfg_id
        s.cfg_to_rf_msg.branch_false_cfg_id @= s.load_meta.branch_false_cfg_id
        s.cfg_to_rf_msg.reconverge_cfg_id @= s.load_meta.reconverge_cfg_id
        s.cfg_to_rf_msg.loop_en @= s.load_meta.loop_en
        s.cfg_to_rf_msg.loop_start_cfg_id @= s.load_meta.loop_start_cfg_id
        s.cfg_to_rf_msg.loop_exit_cfg_id @= s.load_meta.loop_exit_cfg_id
        s.cfg_to_rf_msg.loop_max @= s.load_meta.loop_max

        sparse_store_fix = Bits1(0)
        if s.load_meta.tile_load_count == TileCountType(1):
            sparse_store_fix = s.load_meta.st_enable[0]
            for i in range(1, num_st_cfg_ports):
                sparse_store_fix = sparse_store_fix & ~s.load_meta.st_enable[i]

        if sparse_store_fix:
            s.cfg_to_rf_msg.st_enable[0] @= Bits1(0)
            s.cfg_to_rf_msg.st_enable[last_st_port_idx] @= Bits1(1)
            for i in range(num_token_sinks):
                route = s.load_meta.tokenizer_cfg.token_route_sink_enable[i]
                if (route & route_low_mask) == route_store0_sel:
                    s.cfg_to_rf_msg.tokenizer_cfg.token_route_sink_enable[i] @= (route & ~route_low_mask) | route_store1_sel
                    s.cfg_to_tokenizer_msg.token_route_sink_enable[i] @= (route & ~route_low_mask) | route_store1_sel

    @update
    def comb_active_meta_mem_flags():
        has_load = Bits1(0)
        has_store = Bits1(0)
        if s.active_meta_valid:
            for i in range(num_ld_cfg_ports):
                has_load = has_load | s.active_meta.ld_enable[i]
            for i in range(num_st_cfg_ports):
                has_store = has_store | s.active_meta.st_enable[i]
        s.active_meta_has_load @= has_load
        s.active_meta_has_store @= has_store

    s.pc_req_trigger_count //= s.load_tile_count
    
    @update_ff
    def update_controller():
        # Default values for cfg_mem write interface
        s.cfg_mem_metadata.waddr <<= s.cfg_mem_raddr_reg
        s.cfg_mem_metadata.wdata <<= s.recv_from_cpu_metadata_pkt.msg
        s.cfg_mem_metadata.wen <<= 0

        # Default interface values
        s.send_cfg_to_rf.val <<= 0
        s.send_cfg_to_tokenizer.val <<= 0
        s.send_to_cpu_done <<= s.send_to_cpu_done_reg
        s.pc_req_trigger <<= 0
        s.cfg_swap <<= 0
        s.rf_dep_start <<= 0

        s.cfg_active_sel <<= s.active_bank
        s.cfg_load_sel <<= s.load_bank_reg
        s.state <<= Bits2(1) if (s.pc_started & ~s.pc_done) else Bits2(0)

        # Handshake / readiness helpers
        load_ready = s.load_meta_valid & s.load_tiles_done
        send_rdy = s.send_cfg_to_rf.rdy & s.send_cfg_to_tokenizer.rdy
        cfg_complete_event = s.rf_done_pending | s.rf_cfg_done

        if s.reset:
            # Reset state and shadow metadata tables
            s.pc <<= BitstreamAddrType(0)
            s.pc_next <<= BitstreamAddrType(0)
            s.pc_started <<= 0
            s.pc_done <<= 0
            s.last_pc <<= 0
            s.last_cfg_id <<= BitstreamAddrType(0)
            s.active_bank <<= 0
            s.load_bank <<= 0
            s.load_bank_reg <<= 0
            s.load_pc <<= BitstreamAddrType(0)
            s.next_pc <<= BitstreamAddrType(0)
            s.active_meta <<= s.active_meta
            s.next_meta <<= s.next_meta
            s.load_meta <<= s.load_meta
            s.active_meta_valid <<= 0
            s.next_ready <<= 0
            s.load_tiles_done <<= 0
            s.load_cfg_done <<= 0
            s.load_inflight <<= 0
            s.meta_req_pending <<= 0
            s.cfg_send_pending <<= 0
            s.prefetch_inflight <<= 0
            s.rf_done_pending <<= 0
            s.rf_wait_for_busy <<= 0
            s.rf_active <<= 0
            s.branch_active <<= 0
            s.branch_need_false <<= 0
            s.branch_phase <<= 0
            s.branch_true_cfg <<= BitstreamAddrType(0)
            s.branch_false_cfg <<= BitstreamAddrType(0)
            s.branch_reconverge_cfg <<= BitstreamAddrType(0)
            s.branch_true_count <<= LoopCountType(0)
            s.branch_false_count <<= LoopCountType(0)
            s.load_thread_count_override <<= LoopCountType(0)
            s.load_thread_count_override_valid <<= Bits1(0)
            s.loop_counter <<= LoopCountType(0)
            s.cfg_mem_raddr_reg <<= BitstreamAddrType(0)
            s.tile_bitstreams_seen <<= TileCountType(0)
            s.scan_drain_count <<= TileCountType(0)
            s.send_to_cpu_done_reg <<= 0
            for i in range(MAX_BITSTREAM_COUNT):
                s.cfg_mem_shadow[i] <<= s.cfg_mem_shadow[i]
                s.br_id_shadow[i] <<= BitstreamAddrType(0)
                s.end_cfg_shadow[i] <<= Bits1(0)
                s.tile_load_shadow[i] <<= TileCountType(0)
        else:
            if s.rf_wait_for_busy & ~s.rf_cfg_done:
                s.rf_wait_for_busy <<= 0
            # Overlap non-branch memory configs once all memory requests are
            # issued. The next config then consumes per-thread completions from
            # the inactive bank in dep-mode as they arrive.
            if s.rf_cfg_ready & ~s.rf_wait_for_busy & s.pc_started & ~s.pc_done \
               & (s.active_meta_has_load | s.active_meta_has_store) \
               & ~s.branch_active \
               & ~s.active_meta.branch_en & ~s.active_meta.loop_en:
                s.rf_active <<= 0
            # Latch full completion so a demand-loaded next config can start
            # even if rf_cfg_done deasserts before the load finishes.
            if s.rf_cfg_done & s.pc_started & ~s.pc_done:
                s.rf_done_pending <<= 1
                s.rf_active <<= 0
            # Handle CPU metadata packets (config/launch)
            if s.recv_from_cpu_metadata_pkt.val & s.recv_from_cpu_metadata_pkt.rdy:
                if s.recv_from_cpu_metadata_pkt.msg.cmd == CMD_CONFIG:
                    s.cfg_mem_metadata.waddr <<= s.recv_from_cpu_metadata_pkt.msg.cfg_id
                    s.cfg_mem_metadata.wdata <<= s.recv_from_cpu_metadata_pkt.msg
                    s.cfg_mem_metadata.wen <<= 1
                    s.cfg_mem_shadow[s.recv_from_cpu_metadata_pkt.msg.cfg_id] <<= s.recv_from_cpu_metadata_pkt.msg
                    s.br_id_shadow[s.recv_from_cpu_metadata_pkt.msg.cfg_id] <<= s.recv_from_cpu_metadata_pkt.msg.br_id
                    s.end_cfg_shadow[s.recv_from_cpu_metadata_pkt.msg.cfg_id] <<= s.recv_from_cpu_metadata_pkt.msg.end_cfg
                    s.tile_load_shadow[s.recv_from_cpu_metadata_pkt.msg.cfg_id] <<= \
                        s.recv_from_cpu_metadata_pkt.msg.tile_load_count
                    if s.recv_from_cpu_metadata_pkt.msg.end_cfg:
                        s.last_cfg_id <<= s.recv_from_cpu_metadata_pkt.msg.cfg_id
                    if s.recv_from_cpu_metadata_pkt.msg.start_cfg:
                        s.pc <<= s.recv_from_cpu_metadata_pkt.msg.cfg_id
                        s.load_tile_count <<= s.recv_from_cpu_metadata_pkt.msg.tile_load_count
                elif s.recv_from_cpu_metadata_pkt.msg.cmd == CMD_LAUNCH:
                    if ~s.pc_started:
                        s.pc_started <<= 1
                        s.pc_done <<= 0
                        s.pc_req_trigger <<= 1
                        s.load_bank_reg <<= s.active_bank
                        s.load_bank <<= s.active_bank
                        s.load_pc <<= s.pc
                        s.load_inflight <<= 1
                        s.tile_bitstreams_seen <<= TileCountType(0)
                        s.scan_drain_count <<= TileCountType(0)
                        s.load_thread_count_override_valid <<= Bits1(0)
                        s.load_tiles_done <<= 0
                        s.load_cfg_done <<= 0
                        s.load_meta_valid <<= 0
                        s.cfg_send_pending <<= 0
                        s.meta_req_pending <<= 1
                        s.cfg_mem_raddr_reg <<= s.pc

            # A load is only complete after the last injected bitstream has
            # drained through the full scan chain and reached its target tile.
            if s.scan_drain_count > TileCountType(0):
                s.scan_drain_count <<= s.scan_drain_count - TileCountType(1)
                if s.scan_drain_count == TileCountType(1):
                    s.load_tiles_done <<= 1
                    s.load_inflight <<= 0

            # Tile stream tracking for the current load.
            if s.load_inflight & s.recv_from_cpu_bitstream_pkt.val:
                if s.pc_req_trigger_complete:
                    s.scan_drain_count <<= TileCountType(num_tiles)

            # Metadata read response (BRAM raddr registered + sync read => two-cycle latency)
            if s.meta_req_pending:
                s.load_meta <<= s.cfg_mem_shadow_rdata
                s.load_meta_valid <<= 1
                s.meta_req_pending <<= 0

            # Load ready handling: send cfg to RF/tokenizer and either stash or start
            if load_ready & send_rdy:
                if s.load_bank_reg != s.active_bank:
                    s.send_cfg_to_rf.msg <<= s.cfg_to_rf_msg
                    s.send_cfg_to_rf.val <<= 1
                    s.send_cfg_to_tokenizer.msg <<= s.cfg_to_tokenizer_msg
                    s.send_cfg_to_tokenizer.val <<= 1
                    # Prefetch complete: stash next config metadata
                    s.next_meta <<= s.load_meta
                    s.next_pc <<= s.load_pc
                    s.next_ready <<= 1
                    s.load_meta_valid <<= 0
                    s.load_tiles_done <<= 0
                    s.load_tile_count_next <<= s.load_meta.tile_load_count
                    s.prefetch_inflight <<= 0
                elif (~s.rf_active) | s.rf_done_pending | s.rf_cfg_done:
                    # Active-bank load complete: start config when allowed
                    s.send_cfg_to_rf.msg <<= s.cfg_to_rf_msg
                    s.send_cfg_to_rf.val <<= 1
                    s.send_cfg_to_tokenizer.msg <<= s.cfg_to_tokenizer_msg
                    s.send_cfg_to_tokenizer.val <<= 1
                    s.load_meta_valid <<= 0
                    s.load_tiles_done <<= 0
                    s.prefetch_inflight <<= 0
                    s.rf_active <<= 1
                    s.rf_wait_for_busy <<= 1
                    s.active_meta <<= s.load_meta
                    s.active_meta_valid <<= 1
                    s.pc <<= s.load_pc
                    s.last_pc <<= s.load_pc == s.last_cfg_id
                    s.pc_next <<= s.load_pc + BitstreamAddrType(1)
                    s.load_tile_count_next <<= s.load_meta.tile_load_count
                    s.rf_done_pending <<= 0

            # Issue prefetch for predicted pc (static br_id) while current cfg executes.
            # Use the shadowed tile count for the target pc so pc_req_trigger_count matches
            # the config being prefetched.
            # Keep using the demand-load fallback until speculative prefetch is
            # reconciled with the new per-thread readiness tracking.
            if s.pc_started & ~s.pc_done & s.rf_active & ~s.last_pc \
               & ~s.prefetch_inflight & ~s.next_ready & ~s.load_inflight \
               & ~s.meta_req_pending & ~s.rf_done_pending \
               & ~s.branch_active \
               & ~s.active_meta.branch_en & ~s.active_meta.loop_en \
               & ~s.cfg_swap \
               & ~s.rf_cfg_ready \
               & ~s.rf_dep_mode:
                s.pc_req_trigger <<= 1
                s.load_bank_reg <<= ~s.active_bank
                s.load_bank <<= ~s.active_bank
                s.load_pc <<= s.pc_next
                s.load_inflight <<= 1
                s.load_tile_count <<= s.tile_load_by_next_pc
                s.tile_bitstreams_seen <<= TileCountType(0)
                s.scan_drain_count <<= TileCountType(0)
                s.load_thread_count_override_valid <<= Bits1(0)
                s.load_tiles_done <<= 0
                s.load_cfg_done <<= 0
                s.load_meta_valid <<= 0
                s.cfg_send_pending <<= 0
                s.meta_req_pending <<= 1
                s.cfg_mem_raddr_reg <<= s.pc_next
                s.prefetch_inflight <<= 1

            # Completion / swap / branch / loop
            if (s.rf_done_pending | s.rf_cfg_ready) & ~s.rf_active & s.pc_started & ~s.pc_done \
               & ~s.load_inflight & ~s.meta_req_pending & ~s.load_meta_valid \
               & ~s.rf_wait_for_busy & ~(load_ready & send_rdy):
                if (s.last_pc | (s.pc == s.last_cfg_id)) & cfg_complete_event & ~s.rf_wait_for_busy:
                    s.pc_started <<= 0
                    s.pc_done <<= 1
                    s.send_to_cpu_done_reg <<= 1
                    s.rf_done_pending <<= 0
                elif ~(s.last_pc | (s.pc == s.last_cfg_id)) & s.branch_active \
                     & (s.pc == s.active_meta.cfg_id) & cfg_complete_event:
                    # Branch sequence in progress: run false branch if needed, else reconverge
                    if s.branch_need_false & ~s.branch_phase:
                        next_cfg = s.branch_false_cfg
                        s.branch_phase <<= 1
                        s.load_thread_count_override <<= s.branch_false_count
                        s.load_thread_count_override_valid <<= Bits1(1)
                        next_tile_count = s.tile_load_by_branch_false_reg
                    else:
                        next_cfg = s.branch_reconverge_cfg
                        s.branch_active <<= 0
                        s.branch_need_false <<= 0
                        s.branch_phase <<= 0
                        s.load_thread_count_override_valid <<= Bits1(0)
                        next_tile_count = s.tile_load_by_branch_reconverge
                        if s.end_cfg_by_branch_reconverge:
                            s.pc_started <<= 0
                            s.pc_done <<= 1
                            s.send_to_cpu_done_reg <<= 1
                            s.rf_done_pending <<= 0
                    if ~s.load_inflight & ~s.meta_req_pending & ~s.load_meta_valid:
                        drain_only = s.end_cfg_by_branch_reconverge & ~(s.branch_need_false & ~s.branch_phase)
                        s.pc_req_trigger <<= 1
                        s.load_bank_reg <<= s.active_bank
                        s.load_bank <<= s.active_bank
                        s.load_pc <<= next_cfg
                        s.load_tile_count <<= next_tile_count
                        if ~drain_only:
                            s.pc <<= next_cfg
                            s.meta_req_pending <<= 1
                            s.cfg_mem_raddr_reg <<= next_cfg
                        s.load_inflight <<= 1
                        s.tile_bitstreams_seen <<= TileCountType(0)
                        s.scan_drain_count <<= TileCountType(0)
                        s.load_tiles_done <<= 0
                        s.load_cfg_done <<= 0
                        s.load_meta_valid <<= 0
                        s.prefetch_inflight <<= 0
                        s.rf_done_pending <<= 0
                elif ~(s.last_pc | (s.pc == s.last_cfg_id)) & s.active_meta.branch_en \
                     & (s.pc == s.active_meta.cfg_id) & cfg_complete_event:
                    if s.pred_complete_sel:
                        any_true = Bits1(s.pred_any_true_sel)
                        any_false = Bits1(s.pred_any_false_sel)
                        s.branch_true_cfg <<= s.active_meta.branch_true_cfg_id
                        s.branch_false_cfg <<= s.active_meta.branch_false_cfg_id
                        s.branch_reconverge_cfg <<= s.active_meta.reconverge_cfg_id
                        s.branch_true_count <<= s.pred_true_count_sel
                        s.branch_false_count <<= s.pred_false_count_sel
                        s.branch_active <<= 1
                        if any_true:
                            next_cfg = s.active_meta.branch_true_cfg_id
                            next_tile_count = s.tile_load_by_branch_true_meta
                            s.load_thread_count_override <<= s.pred_true_count_sel
                            s.load_thread_count_override_valid <<= Bits1(1)
                            s.branch_need_false <<= any_false
                            if any_false:
                                s.branch_phase <<= 0
                            else:
                                s.branch_phase <<= 1
                        else:
                            next_cfg = s.active_meta.branch_false_cfg_id
                            next_tile_count = s.tile_load_by_branch_false_meta
                            s.load_thread_count_override <<= s.pred_false_count_sel
                            s.load_thread_count_override_valid <<= Bits1(1)
                            s.branch_need_false <<= Bits1(0)
                            s.branch_phase <<= Bits1(1)
                        if ~s.load_inflight & ~s.meta_req_pending & ~s.load_meta_valid:
                            s.pc_req_trigger <<= 1
                            s.load_bank_reg <<= s.active_bank
                            s.load_bank <<= s.active_bank
                            s.load_pc <<= next_cfg
                            s.load_tile_count <<= next_tile_count
                            s.pc <<= next_cfg
                            s.load_inflight <<= 1
                            s.tile_bitstreams_seen <<= TileCountType(0)
                            s.scan_drain_count <<= TileCountType(0)
                            s.load_tiles_done <<= 0
                            s.load_cfg_done <<= 0
                            s.load_meta_valid <<= 0
                            s.meta_req_pending <<= 1
                            s.cfg_mem_raddr_reg <<= next_cfg
                            s.prefetch_inflight <<= 0
                            s.rf_done_pending <<= 0
                elif ~(s.last_pc | (s.pc == s.last_cfg_id)) & s.active_meta.loop_en \
                     & cfg_complete_event:
                    if s.loop_counter + LoopCountType(1) < s.active_meta.loop_max:
                        next_cfg = s.active_meta.loop_start_cfg_id
                        next_tile_count = s.tile_load_by_loop_start_meta
                        s.loop_counter <<= s.loop_counter + LoopCountType(1)
                    else:
                        next_cfg = s.active_meta.loop_exit_cfg_id
                        next_tile_count = s.tile_load_by_loop_exit_meta
                        s.loop_counter <<= LoopCountType(0)
                    if ~s.load_inflight & ~s.meta_req_pending & ~s.load_meta_valid:
                        s.pc_req_trigger <<= 1
                        s.load_bank_reg <<= s.active_bank
                        s.load_bank <<= s.active_bank
                        s.load_pc <<= next_cfg
                        s.load_tile_count <<= next_tile_count
                        s.pc <<= next_cfg
                        s.load_inflight <<= 1
                        s.tile_bitstreams_seen <<= TileCountType(0)
                        s.scan_drain_count <<= TileCountType(0)
                        s.load_thread_count_override_valid <<= Bits1(0)
                        s.load_tiles_done <<= 0
                        s.load_cfg_done <<= 0
                        s.load_meta_valid <<= 0
                        s.meta_req_pending <<= 1
                        s.cfg_mem_raddr_reg <<= next_cfg
                        s.prefetch_inflight <<= 0
                        s.rf_done_pending <<= 0
                elif ~(s.last_pc | (s.pc == s.last_cfg_id)) & s.next_ready:
                    s.cfg_swap <<= 1
                    s.rf_dep_start <<= s.rf_cfg_ready & ~s.rf_cfg_done
                    # Present the post-swap active bank in the same cycle as cfg_swap
                    s.cfg_active_sel <<= ~s.active_bank
                    s.active_bank <<= ~s.active_bank
                    s.pc <<= s.next_pc
                    s.active_meta <<= s.next_meta
                    s.active_meta_valid <<= 1
                    s.last_pc <<= s.next_pc == s.last_cfg_id
                    s.pc_next <<= s.next_pc + BitstreamAddrType(1)
                    s.load_tile_count_next <<= s.next_meta.tile_load_count
                    s.next_ready <<= 0
                    s.rf_done_pending <<= 0
                    s.rf_active <<= 1
                    s.rf_wait_for_busy <<= 1
                elif ~(s.last_pc | (s.pc == s.last_cfg_id)) & ~s.load_inflight & ~s.meta_req_pending & ~s.load_meta_valid:
                    # Fallback: demand-load next config if prefetch not ready
                    s.pc_req_trigger <<= 1
                    s.load_bank_reg <<= s.active_bank
                    s.load_bank <<= s.active_bank
                    s.load_pc <<= s.pc_next
                    s.load_tile_count <<= s.tile_load_by_next_pc
                    s.load_inflight <<= 1
                    s.tile_bitstreams_seen <<= TileCountType(0)
                    s.scan_drain_count <<= TileCountType(0)
                    s.load_thread_count_override_valid <<= Bits1(0)
                    s.load_tiles_done <<= 0
                    s.load_cfg_done <<= 0
                    s.load_meta_valid <<= 0
                    s.meta_req_pending <<= 1
                    s.cfg_mem_raddr_reg <<= s.pc_next
                    s.prefetch_inflight <<= 0
                    s.rf_done_pending <<= 0
