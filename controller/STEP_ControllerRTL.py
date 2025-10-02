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

class STEP_ControllerRTL(Component):
  def construct(s,
                CpuPktType,
                CfgBitstreamType,
                CfgType,
                CfgMetadataType,
                CfgTokenizerType
                ):
    BitstreamAddrType = mk_bits(clog2(MAX_BITSTREAM_SIZE))
    
    # CPU ports
    s.recv_from_cpu_pkt = RecvIfcRTL(CpuPktType)
    s.send_to_cpu_pkt = SendIfcRTL(CpuPktType)
    
    # PE Fabric ports
    s.send_cfg_to_tiles = SendIfcRTL(CfgBitstreamType)
    
    # RF ports
    s.send_cfg_to_rf = SendIfcRTL(CfgMetadataType)

    # Tokenizer ports
    s.send_cfg_to_tokenizer = SendIfcRTL(CfgTokenizerType)
    
    # Internal Ports
    s.pc = Wire(BitstreamAddrType)
    s.pc_started = OutPort(Bits1)
    s.pc_done = OutPort(Bits1)
    s.pc_next = OutPort(BitstreamAddrType)
    s.last_pc = OutPort(Bits1)
    s.rf_cfg_done = InPort(Bits1)
    
    # New register for maintaining current cfg_mem read address
    s.cfg_mem_raddr_reg = Wire(BitstreamAddrType)
    s.cfg_mem_raddr = OutPort(BitstreamAddrType)
    
    # State machine for handling memory read delays
    s.STATE_IDLE = 0
    s.STATE_SENDING_NEXT_CFG = 1
    
    s.state = OutPort(mk_bits(2))
    
    # Wire connections
    s.cfg_mem_raddr //= s.cfg_mem_raddr_reg
    
    # Internal Cfg mem
    s.cfg_mem = RegisterFile(CfgType, MAX_BITSTREAM_SIZE, rd_ports=1,
                            wr_ports=1)

    s.cfg_if = OutPort(b1)
    s.cfg_metadata_rd = OutPort(CfgMetadataType)
    s.cfg_metadata_rd //= s.cfg_mem.rdata[0].metadata
    
    # Connect the read address register to the actual cfg_mem read address
    s.cfg_mem.raddr[0] //= s.cfg_mem_raddr_reg
    
    @update
    def tester():
        s.cfg_if @= s.rf_cfg_done & s.pc_started & ~s.pc_done

    @update
    def update_ready():
        # Ready signal should be combinational
        s.recv_from_cpu_pkt.rdy @= s.state == s.STATE_IDLE  # Always ready to accept commands

    @update_ff
    def update_controller():
        # Default values for cfg_mem write interface
        s.cfg_mem.waddr[0] <<= BitstreamAddrType()
        s.cfg_mem.wdata[0] <<= CfgType(0,0)
        s.cfg_mem.wen[0] <<= Bits1(0)
        
        # Default interface values
        s.send_cfg_to_tiles.val <<= Bits1(0)
        s.send_cfg_to_rf.val <<= Bits1(0)
        s.send_cfg_to_tokenizer.val <<= Bits1(0)
        s.send_to_cpu_pkt.val <<= Bits1(0)
        # Return to idle state
        s.state <<= s.STATE_IDLE
        
        # State machine logic
        if s.state == s.STATE_IDLE:
            # Handle CPU commands
            if s.recv_from_cpu_pkt.val & s.recv_from_cpu_pkt.rdy:
                if s.recv_from_cpu_pkt.msg.cmd == CMD_CONFIG:
                    s.cfg_mem.waddr[0] <<= s.recv_from_cpu_pkt.msg.cfg.metadata.cfg_id
                    s.cfg_mem.wdata[0] <<= s.recv_from_cpu_pkt.msg.cfg
                    s.cfg_mem.wen[0] <<= Bits1(1)
                    # Initialize initial cfg_id
                    if s.recv_from_cpu_pkt.msg.cfg.metadata.start_cfg:
                        s.pc <<= s.recv_from_cpu_pkt.msg.cfg.metadata.cfg_id
                elif s.recv_from_cpu_pkt.msg.cmd == CMD_LAUNCH:
                    # Update the read address register
                    s.cfg_mem_raddr_reg <<= s.pc
                    s.pc_started <<= Bits1(1)
                    s.pc_done <<= Bits1(0)
                    s.state <<= s.STATE_SENDING_NEXT_CFG
            
            # Handle RF configuration completion
            elif s.rf_cfg_done & s.pc_started & ~s.pc_done:
                if s.last_pc:
                    s.pc_started <<= Bits1(0)
                    s.pc_done <<= Bits1(1)
                    s.send_to_cpu_pkt.msg <<= CpuPktType(CMD_COMPLETE, 0)
                    s.send_to_cpu_pkt.val <<= Bits1(1)
                else:
                    # Update the read address register for next configuration
                    s.cfg_mem_raddr_reg <<= s.pc_next
                    s.state <<= s.STATE_SENDING_NEXT_CFG
                    s.pc <<= s.pc_next
        
        elif s.state == s.STATE_SENDING_NEXT_CFG:
            # Now the memory data is available, send the configuration
            s.send_cfg_to_tiles.msg <<= s.cfg_mem.rdata[0].bitstream
            s.send_cfg_to_tiles.val <<= Bits1(1)
            s.send_cfg_to_rf.msg <<= s.cfg_mem.rdata[0].metadata
            s.send_cfg_to_rf.val <<= Bits1(1)
            s.send_cfg_to_tokenizer.msg <<= s.cfg_mem.rdata[0].metadata.tokenizer_cfg
            s.send_cfg_to_tokenizer.val <<= Bits1(1)
            
            # Update PC and control signals
            s.pc_next <<= s.cfg_mem.rdata[0].metadata.br_id
            s.last_pc <<= s.cfg_mem.rdata[0].metadata.end_cfg