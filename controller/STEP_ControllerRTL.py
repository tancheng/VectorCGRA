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
                CfgMetadataType):
    BitstreamAddrType = mk_bits(clog2(MAX_BITSTREAM_SIZE))
    
    # CPU ports
    s.recv_from_cpu_pkt = RecvIfcRTL(CpuPktType)
    s.send_to_cpu_pkt = SendIfcRTL(CpuPktType)
    
    # PE Fabric ports
    s.send_cfg_to_tiles = SendIfcRTL(CfgBitstreamType)
    
    # RF ports
    s.send_cfg_to_rf = SendIfcRTL(CfgMetadataType)
    
    # Internal Ports
    s.pc = Wire(BitstreamAddrType)
    s.pc_started = Wire(Bits1)
    s.pc_done = Wire(Bits1)
    s.pc_next = Wire(BitstreamAddrType)
    s.last_pc = Wire(Bits1)
    s.rf_cfg_done = InPort(Bits1)
    
    # Internal registers
    s.pc_reg = Reg(BitstreamAddrType)
    s.pc_started_reg = Reg(Bits1)
    s.pc_done_reg = Reg(Bits1)
    s.pc_next_reg = Reg(BitstreamAddrType)
    s.last_pc_reg = Reg(Bits1)
    
    # Wire connections
    s.pc //= s.pc_reg.out
    s.pc_started //= s.pc_started_reg.out
    s.pc_done //= s.pc_done_reg.out
    s.pc_next //= s.pc_next_reg.out
    s.last_pc //= s.last_pc_reg.out
    
    # Internal Cfg mem
    s.cfg_mem = RegisterFile(CfgType, MAX_BITSTREAM_SIZE, rd_ports=1,
                            wr_ports=1)

    @update
    def update_ready():
        # Ready signal should be combinational
        s.recv_from_cpu_pkt.rdy @= Bits1(1)  # Always ready to accept commands
    
    @update_ff
    def update_controller():
        # Default values for cfg_mem
        s.cfg_mem.raddr[0] <<= BitstreamAddrType()
        s.cfg_mem.waddr[0] <<= BitstreamAddrType()
        s.cfg_mem.wdata[0] <<= CfgType(0,0)
        s.cfg_mem.wen[0] <<= Bits1(0)
        
        # Default interface values
        s.send_cfg_to_tiles.val <<= Bits1(0)
        s.send_cfg_to_rf.val <<= Bits1(0)
        s.send_to_cpu_pkt.val <<= Bits1(0)
        
        # Handle CPU commands
        if s.recv_from_cpu_pkt.val & s.recv_from_cpu_pkt.rdy:
            if s.recv_from_cpu_pkt.msg.cmd == CMD_CONFIG:
                s.cfg_mem.waddr[0] <<= s.recv_from_cpu_pkt.msg.cfg.metadata.cfg_id
                s.cfg_mem.wdata[0] <<= s.recv_from_cpu_pkt.msg.cfg
                s.cfg_mem.wen[0] <<= Bits1(1)
                # Initialize initial cfg_id
                if s.recv_from_cpu_pkt.msg.cfg.metadata.start_cfg:
                    s.pc_reg.in_ <<= s.recv_from_cpu_pkt.msg.cfg.metadata.cfg_id
            elif s.recv_from_cpu_pkt.msg.cmd == CMD_LAUNCH:
                s.cfg_mem.raddr[0] <<= s.pc
                s.send_cfg_to_tiles.msg <<= s.cfg_mem.rdata[0].bitstream
                s.send_cfg_to_tiles.val <<= Bits1(1)
                s.send_cfg_to_rf.msg <<= s.cfg_mem.rdata[0].metadata
                s.send_cfg_to_rf.val <<= Bits1(1)
                s.pc_started_reg.in_ <<= Bits1(1)
                s.pc_done_reg.in_ <<= Bits1(0)
                s.pc_next_reg.in_ <<= s.cfg_mem.rdata[0].metadata.br_id
                s.last_pc_reg.in_ <<= s.cfg_mem.rdata[0].metadata.end_cfg
        
        # Handle RF configuration completion
        elif s.rf_cfg_done:
            if s.last_pc:
                s.pc_started_reg.in_ <<= Bits1(0)
                s.pc_done_reg.in_ <<= Bits1(1)
                s.send_to_cpu_pkt.msg <<= CpuPktType(CMD_COMPLETE, 0)
                s.send_to_cpu_pkt.val <<= Bits1(1)
            else:
                s.cfg_mem.raddr[0] <<= s.pc_next
                s.send_cfg_to_tiles.msg <<= s.cfg_mem.rdata[0].bitstream
                s.send_cfg_to_tiles.val <<= Bits1(1)
                s.send_cfg_to_rf.msg <<= s.cfg_mem.rdata[0].metadata
                s.send_cfg_to_rf.val <<= Bits1(1)
                s.pc_reg.in_ <<= s.pc_next
                s.pc_next_reg.in_ <<= s.cfg_mem.rdata[0].metadata.br_id
                s.last_pc_reg.in_ <<= s.cfg_mem.rdata[0].metadata.end_cfg