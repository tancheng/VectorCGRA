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
                debug = False
                ):
    BitstreamAddrType = mk_bits(clog2(MAX_BITSTREAM_COUNT))
    
    # CPU ports
    s.recv_from_cpu_bitstream_pkt = RecvIfcRTL(TileBitstreamType)
    s.recv_from_cpu_metadata_pkt = RecvIfcRTL(CfgMetadataType)
    s.send_to_cpu_done = OutPort(Bits1)
    s.pc_req_trigger = OutPort(Bits1)
    s.pc_req = OutPort(BitstreamAddrType)
    s.cfg_active_sel = OutPort(Bits1)
    s.cfg_load_sel = OutPort(Bits1)
    s.cfg_swap = OutPort(Bits1)

    # Fabric Pkts Counts
    TileCountType = mk_bits(clog2(num_tiles))
    if debug:
        s.tile_bitstreams_seen = OutPort( TileCountType )
    else:
        s.tile_bitstreams_seen = Wire( TileCountType )
    
    # PE Fabric ports
    s.send_cfg_to_tiles = SendIfcRTL(TileBitstreamType)
    
    # RF ports
    s.send_cfg_to_rf = SendIfcRTL(CfgMetadataType)

    # Tokenizer ports
    s.send_cfg_to_tokenizer = SendIfcRTL(CfgTokenizerType)
    
    # Internal Ports
    s.rf_cfg_done = InPort(Bits1)
    if debug:
        s.pc_started = OutPort(Bits1)
        s.pc_done = OutPort(Bits1)
        s.pc = OutPort(BitstreamAddrType)
        s.pc_next = OutPort(BitstreamAddrType)
        s.last_pc = OutPort(Bits1)
    else:
        s.pc = Wire(BitstreamAddrType)
        s.pc_started = Wire(Bits1)
        s.pc_done = Wire(Bits1)
        s.pc_next = Wire(BitstreamAddrType)
        s.last_pc = Wire(Bits1)
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
    s.end_cfg_shadow = [ Wire(Bits1) for _ in range(MAX_BITSTREAM_COUNT) ]
    s.br_id_by_load_pc = Wire(BitstreamAddrType)
    s.end_cfg_by_load_pc = Wire(Bits1)
    s.br_id_by_next_pc = Wire(BitstreamAddrType)
    s.end_cfg_by_next_pc = Wire(Bits1)
    
    # Connect the read address register to the actual cfg_mem read address
    s.cfg_mem_metadata.raddr //= s.cfg_mem_raddr_reg
    s.active_bank = Wire(Bits1)
    s.load_bank = Wire(Bits1)
    s.load_bank_reg = Wire(Bits1)
    s.load_pc = Wire(BitstreamAddrType)
    s.next_pc = Wire(BitstreamAddrType)
    s.active_meta = Wire(CfgMetadataType)
    s.next_meta = Wire(CfgMetadataType)
    s.load_meta = Wire(CfgMetadataType)
    s.active_meta_valid = Wire(Bits1)
    s.load_meta_valid = Wire(Bits1)
    s.next_ready = Wire(Bits1)
    s.load_tiles_done = Wire(Bits1)
    s.load_cfg_done = Wire(Bits1)
    s.load_inflight = Wire(Bits1)
    s.meta_req_pending = Wire(Bits1)
    s.cfg_send_pending = Wire(Bits1)
    s.prefetch_inflight = Wire(Bits1)
    s.rf_done_pending = Wire(Bits1)
    s.rf_active = Wire(Bits1)
    s.last_cfg_id = Wire(BitstreamAddrType)
    s.send_to_cpu_done_reg = Wire(Bits1)

    # Debug ports removed for simplified interface

    @update
    def update_ready():
        # Always ready to accept metadata; bitstream always ready
        s.recv_from_cpu_metadata_pkt.rdy @= 1
        s.recv_from_cpu_bitstream_pkt.rdy @= 1

    @update
    def shadow_read():
        s.cfg_mem_shadow_rdata @= 0
        s.br_id_by_load_pc @= BitstreamAddrType(0)
        s.end_cfg_by_load_pc @= Bits1(0)
        s.br_id_by_next_pc @= BitstreamAddrType(0)
        s.end_cfg_by_next_pc @= Bits1(0)
        for i in range(MAX_BITSTREAM_COUNT):
            if s.load_pc == BitstreamAddrType(i):
                s.cfg_mem_shadow_rdata @= s.cfg_mem_shadow[i]
                s.br_id_by_load_pc @= s.br_id_shadow[i]
                s.end_cfg_by_load_pc @= s.end_cfg_shadow[i]
            if s.next_pc == BitstreamAddrType(i):
                s.br_id_by_next_pc @= s.br_id_shadow[i]
                s.end_cfg_by_next_pc @= s.end_cfg_shadow[i]

    @update
    def update_scan_chain():
        s.send_cfg_to_tiles.msg @= 0
        s.send_cfg_to_tiles.val @= 0
        if s.recv_from_cpu_bitstream_pkt.val:
            s.send_cfg_to_tiles.msg @= s.recv_from_cpu_bitstream_pkt.msg
            s.send_cfg_to_tiles.val @= 1

    @update_ff
    def update_controller():
        # Default values for cfg_mem write interface
        s.cfg_mem_metadata.waddr <<= BitstreamAddrType()
        s.cfg_mem_metadata.wdata <<= 0
        s.cfg_mem_metadata.wen <<= 0

        # Default interface values
        s.send_cfg_to_rf.val <<= 0
        s.send_cfg_to_tokenizer.val <<= 0
        s.send_to_cpu_done <<= s.send_to_cpu_done_reg
        s.pc_req_trigger <<= 0
        s.cfg_swap <<= 0

        s.cfg_active_sel <<= s.active_bank
        s.cfg_load_sel <<= s.load_bank_reg
        s.state <<= Bits2(1) if (s.pc_started & ~s.pc_done) else Bits2(0)

        load_ready = s.load_meta_valid & s.load_tiles_done
        send_rdy = s.send_cfg_to_rf.rdy & s.send_cfg_to_tokenizer.rdy

        if s.reset:
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
            s.active_meta <<= 0
            s.next_meta <<= 0
            s.load_meta <<= 0
            s.active_meta_valid <<= 0
            s.next_ready <<= 0
            s.load_tiles_done <<= 0
            s.load_cfg_done <<= 0
            s.load_inflight <<= 0
            s.meta_req_pending <<= 0
            s.cfg_send_pending <<= 0
            s.prefetch_inflight <<= 0
            s.rf_done_pending <<= 0
            s.rf_active <<= 0
            s.cfg_mem_raddr_reg <<= BitstreamAddrType(0)
            s.tile_bitstreams_seen <<= TileCountType(0)
            s.send_to_cpu_done_reg <<= 0
            for i in range(MAX_BITSTREAM_COUNT):
                s.cfg_mem_shadow[i] <<= 0
                s.br_id_shadow[i] <<= BitstreamAddrType(0)
                s.end_cfg_shadow[i] <<= Bits1(0)
        else:
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
                    if s.recv_from_cpu_metadata_pkt.msg.end_cfg:
                        s.last_cfg_id <<= s.recv_from_cpu_metadata_pkt.msg.cfg_id
                    if s.recv_from_cpu_metadata_pkt.msg.start_cfg:
                        s.pc <<= s.recv_from_cpu_metadata_pkt.msg.cfg_id
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
                        s.load_tiles_done <<= 0
                        s.load_cfg_done <<= 0
                        s.load_meta_valid <<= 0
                        s.cfg_send_pending <<= 0
                        s.meta_req_pending <<= 1
                        s.cfg_mem_raddr_reg <<= s.pc

            # Tile stream count for current load
            if s.load_inflight & s.recv_from_cpu_bitstream_pkt.val:
                if s.tile_bitstreams_seen >= num_tiles - 1:
                    s.tile_bitstreams_seen <<= TileCountType(0)
                    s.load_tiles_done <<= 1
                    s.load_inflight <<= 0
                else:
                    s.tile_bitstreams_seen <<= s.tile_bitstreams_seen + TileCountType(1)

            # Metadata read response (BRAM raddr registered + sync read => two-cycle latency)
            if s.meta_req_pending:
                s.load_meta <<= s.cfg_mem_shadow_rdata
                s.load_meta_valid <<= 1
                s.meta_req_pending <<= 0

            # Load ready handling: send cfg to RF/tokenizer and either stash or start
            if load_ready & send_rdy:
                if s.load_bank_reg != s.active_bank:
                    s.send_cfg_to_rf.msg <<= s.load_meta
                    s.send_cfg_to_rf.val <<= 1
                    s.send_cfg_to_tokenizer.msg <<= s.load_meta.tokenizer_cfg
                    s.send_cfg_to_tokenizer.val <<= 1
                    # Prefetch complete: stash next config metadata
                    s.next_meta <<= s.load_meta
                    s.next_pc <<= s.load_pc
                    s.next_ready <<= 1
                    s.load_meta_valid <<= 0
                    s.load_tiles_done <<= 0
                    s.prefetch_inflight <<= 0
                elif ((~s.active_meta_valid) | s.rf_done_pending) & ~s.rf_active:
                    # Active-bank load complete: start config when allowed
                    s.send_cfg_to_rf.msg <<= s.load_meta
                    s.send_cfg_to_rf.val <<= 1
                    s.send_cfg_to_tokenizer.msg <<= s.load_meta.tokenizer_cfg
                    s.send_cfg_to_tokenizer.val <<= 1
                    s.load_meta_valid <<= 0
                    s.load_tiles_done <<= 0
                    s.prefetch_inflight <<= 0
                    s.rf_active <<= 1
                    s.active_meta <<= s.load_meta
                    s.active_meta_valid <<= 1
                    s.pc <<= s.load_pc
                    s.last_pc <<= Bits1(s.load_pc == s.last_cfg_id)
                    s.pc_next <<= s.load_pc + BitstreamAddrType(1)
                    s.rf_done_pending <<= 0

            # Issue prefetch for predicted pc (static br_id) while current cfg executes
            if s.pc_started & ~s.pc_done & s.rf_active & ~s.last_pc \
               & ~s.prefetch_inflight & ~s.next_ready & ~s.load_inflight \
               & ~s.meta_req_pending & ~s.rf_done_pending:
                s.pc_req_trigger <<= 1
                s.load_bank_reg <<= ~s.active_bank
                s.load_bank <<= ~s.active_bank
                s.load_pc <<= s.pc_next
                s.load_inflight <<= 1
                s.tile_bitstreams_seen <<= TileCountType(0)
                s.load_tiles_done <<= 0
                s.load_cfg_done <<= 0
                s.load_meta_valid <<= 0
                s.cfg_send_pending <<= 0
                s.meta_req_pending <<= 1
                s.cfg_mem_raddr_reg <<= s.pc_next
                s.prefetch_inflight <<= 1

            # Completion / swap
            if s.rf_done_pending & s.pc_started & ~s.pc_done:
                if s.last_pc | Bits1(s.pc == s.last_cfg_id):
                    s.pc_started <<= 0
                    s.pc_done <<= 1
                    s.send_to_cpu_done_reg <<= 1
                    s.rf_done_pending <<= 0
                elif s.next_ready:
                    if s.send_cfg_to_rf.rdy & s.send_cfg_to_tokenizer.rdy & ~s.rf_active:
                        s.send_cfg_to_rf.msg <<= s.next_meta
                        s.send_cfg_to_rf.val <<= 1
                        s.send_cfg_to_tokenizer.msg <<= s.next_meta.tokenizer_cfg
                        s.send_cfg_to_tokenizer.val <<= 1
                    s.cfg_swap <<= 1
                    # Present the post-swap active bank in the same cycle as cfg_swap
                    s.cfg_active_sel <<= ~s.active_bank
                    s.active_bank <<= ~s.active_bank
                    s.pc <<= s.next_pc
                    s.active_meta <<= s.next_meta
                    s.active_meta_valid <<= 1
                    s.last_pc <<= Bits1(s.next_pc == s.last_cfg_id)
                    s.pc_next <<= s.next_pc + BitstreamAddrType(1)
                    s.next_ready <<= 0
                    s.rf_done_pending <<= 0
                    s.rf_active <<= 1
                elif ~s.load_inflight & ~s.meta_req_pending & ~s.load_meta_valid & ~s.load_tiles_done:
                    # Fallback: demand-load next config if prefetch not ready
                    s.pc_req_trigger <<= 1
                    s.load_bank_reg <<= s.active_bank
                    s.load_bank <<= s.active_bank
                    s.load_pc <<= s.pc_next
                    s.load_inflight <<= 1
                    s.tile_bitstreams_seen <<= TileCountType(0)
                    s.load_tiles_done <<= 0
                    s.load_cfg_done <<= 0
                    s.load_meta_valid <<= 0
                    s.meta_req_pending <<= 1
                    s.cfg_mem_raddr_reg <<= s.pc_next
                    s.prefetch_inflight <<= 0
