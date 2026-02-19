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
                bitstream_cnt = 1,
                debug = False
                ):
    BitstreamAddrType = mk_bits(clog2(MAX_BITSTREAM_COUNT))
    bitstream_break_interval = num_tiles // bitstream_cnt
    
    # CPU ports
    s.recv_from_cpu_bitstream_pkt = [RecvIfcRTL(CfgBitstreamType) for _ in range(bitstream_cnt)]
    s.recv_from_cpu_metadata_pkt = RecvIfcRTL(CfgMetadataType)
    s.send_to_cpu_done = OutPort(Bits1)
    
    # PE Fabric ports
    s.send_cfg_to_tiles = [OutPort(TileBitstreamType) for _ in range(num_tiles)]
    s.send_cfg_to_tiles_val = OutPort(Bits1)
    
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
    
    # New register for maintaining current cfg_mem read address
    s.cfg_mem_raddr_reg = Wire(BitstreamAddrType)
    s.cfg_mem_raddr_reg //= s.pc_next
    if debug:
        s.cfg_mem_raddr = OutPort(BitstreamAddrType)
        s.cfg_mem_raddr //= s.cfg_mem_raddr_reg
    
    # State machine for handling memory read delays
    s.STATE_IDLE = 0
    s.STATE_SENDING_NEXT_CFG = 1
    s.state = OutPort(mk_bits(2))
    
    # Internal Cfg mem
    s.cfg_mem_metadata = STEP_BRAMRTL(CfgMetadataType, MAX_BITSTREAM_COUNT, rd_ports=1,
                            wr_ports=1)
    s.cfg_mem_tile_bitstreams = [STEP_BRAMRTL(TileBitstreamType, MAX_BITSTREAM_COUNT, rd_ports=1,
                            wr_ports=1) for _ in range(num_tiles)]

    #THE ISSUE IS HERE WHERE WE USED TO USE REGISTER FILE AND NOW WE INCUR AN ADDITIONAL CYCLE DELAY?

    s.cfg_if = OutPort(b1)
    s.cfg_metadata_rd = OutPort(CfgMetadataType)
    s.cfg_metadata_rd //= s.cfg_mem_metadata.rdata
    
    # Connect the read address register to the actual cfg_mem read address
    s.cfg_mem_metadata.raddr //= s.cfg_mem_raddr_reg
    for i in range(num_tiles):
        s.cfg_mem_tile_bitstreams[i].raddr //= s.cfg_mem_raddr_reg
    
    @update
    def tester():
        s.cfg_if @= s.rf_cfg_done & s.pc_started & ~s.pc_done

    @update
    def update_ready():
        # Ready signal should be combinational
        for i in range(bitstream_cnt):
            s.recv_from_cpu_bitstream_pkt[i].rdy @= s.state == s.STATE_IDLE  # Always ready to accept commands
        s.recv_from_cpu_metadata_pkt.rdy @= s.state == s.STATE_IDLE  # Always ready to accept commands

    @update_ff
    def update_controller():
        # Default values for cfg_mem write interface
        for i in range(num_tiles):
            s.cfg_mem_tile_bitstreams[i].waddr <<= BitstreamAddrType()
            s.cfg_mem_tile_bitstreams[i].wdata <<= TileBitstreamType(0,0,0,0,0,0,0,0,0)
            s.cfg_mem_tile_bitstreams[i].wen <<= 0
        s.cfg_mem_metadata.waddr <<= BitstreamAddrType()
        s.cfg_mem_metadata.wdata <<= CfgMetadataType(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0)
        s.cfg_mem_metadata.wen <<= 0
        
        # Default interface values
        s.send_cfg_to_tiles_val <<= 0
        s.send_cfg_to_rf.val <<= 0
        s.send_cfg_to_tokenizer.val <<= 0
        s.send_to_cpu_done <<= 0
        # Return to idle state
        s.state <<= s.STATE_IDLE
        
        # State machine logic
        if s.state == s.STATE_IDLE:
            # Handle CPU commands
            if s.recv_from_cpu_bitstream_pkt[0].val & s.recv_from_cpu_bitstream_pkt[0].rdy \
                    & s.recv_from_cpu_metadata_pkt.val & s.recv_from_cpu_metadata_pkt.rdy:
                if s.recv_from_cpu_metadata_pkt.msg.cmd == CMD_CONFIG:
                    
                    for i in range(bitstream_cnt):
                        for j in range(bitstream_break_interval):
                            idx = i*bitstream_break_interval + j
                            s.cfg_mem_tile_bitstreams[idx].waddr <<= s.recv_from_cpu_metadata_pkt.msg.cfg_id
                            s.cfg_mem_tile_bitstreams[idx].wdata <<= s.recv_from_cpu_bitstream_pkt[i].msg.bitstream[j]
                            s.cfg_mem_tile_bitstreams[idx].wen <<= 1
                    s.cfg_mem_metadata.waddr <<= s.recv_from_cpu_metadata_pkt.msg.cfg_id
                    s.cfg_mem_metadata.wdata <<= s.recv_from_cpu_metadata_pkt.msg
                    s.cfg_mem_metadata.wen <<= 1
                    # Initialize initial cfg_id
                    if s.recv_from_cpu_metadata_pkt.msg.start_cfg:
                        s.pc <<= s.recv_from_cpu_metadata_pkt.msg.cfg_id
                elif s.recv_from_cpu_metadata_pkt.msg.cmd == CMD_LAUNCH:
                    # Update the read address register
                    s.pc_started <<= 1
                    s.pc_done <<= 0
                    s.state <<= s.STATE_SENDING_NEXT_CFG
            
            # Handle RF configuration completion
            elif s.rf_cfg_done & s.pc_started & ~s.pc_done:
                if s.last_pc:
                    s.pc_started <<= 0
                    s.pc_done <<= 1
                    s.send_to_cpu_done <<= 1
                else:
                    # Update the read address register for next configuration
                    s.state <<= s.STATE_SENDING_NEXT_CFG
                    s.pc <<= s.pc_next
        
        elif s.state == s.STATE_SENDING_NEXT_CFG:
            # Now the memory data is available, send the configuration
            for i in range(num_tiles):
                s.send_cfg_to_tiles[i] <<= s.cfg_mem_tile_bitstreams[i].rdata
            s.send_cfg_to_tiles_val <<= 1
            s.send_cfg_to_rf.msg <<= s.cfg_mem_metadata.rdata
            s.send_cfg_to_rf.val <<= 1
            s.send_cfg_to_tokenizer.msg <<= s.cfg_mem_metadata.rdata.tokenizer_cfg
            s.send_cfg_to_tokenizer.val <<= 1
            
            # Update PC and control signals
            s.pc_next <<= s.cfg_mem_metadata.rdata.br_id
            s.last_pc <<= s.cfg_mem_metadata.rdata.end_cfg
