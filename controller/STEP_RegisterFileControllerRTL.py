"""
==========================================================================
ControllerRTL.py
==========================================================================
Controller for each CGRA. Mutiple controllers are interconnected in a
multi-cgra system.

Author : Cheng Tan
  Date : Dec 2, 2024
"""

from ..lib.basic.val_rdy.ifcs import RecvIfcRTL
from ..lib.basic.val_rdy.ifcs import SendIfcRTL
from pymtl3.stdlib.primitive import RegisterFile
from ..lib.basic.val_rdy.queues import NormalQueueRTL
from ..lib.messages import *
from ..lib.opt_type import *
from ..lib.util.common import *
from ..noc.PyOCN.pymtl3_net.channel.ChannelRTL import ChannelRTL
from ..noc.PyOCN.pymtl3_net.xbar.XbarBypassQueueRTL import XbarBypassQueueRTL

class STEP_RegisterFileControllerRTL(Component):
  def construct(s,
                RegDataType,
                num_banks = 2,
                num_rd_ports = 2,
                num_wr_ports = 2,
                num_registers = 16):

    RegAddrType = mk_bits(clog2(num_registers))

    # InterCmds
    # Cfg for full fabric including constants
    # Start Cgra
    # Cgra Done running
    s.register_file = STEP_RegisterFileRTL(RegDataType, RegAddrType,
                                            num_reg_banks = num_banks,
                                            num_rd_ports = num_rd_ports,
                                            num_wr_ports = num_wr_ports,
                                            num_registers_per_reg_bank = num_registers / num_banks)

    

    s.rd_addr = [RecvIfcRTL(RegAddrType) for _ in range(num_rd_ports)]
    s.rd_data = [SendIfcRTL(RegDataType) for _ in range(num_rd_ports)]
    s.wr_addr = [RecvIfcRTL(RegAddrType) for _ in range(num_wr_ports)]
    s.wr_data = [RecvIfcRTL(RegDataType) for _ in range(num_wr_ports)]
    s.cfg_done = OutPort(b(1))

    s.rd_count = Reg(mkbits(clog2(MAX_THREAD_COUNT)))
    s.wr_count = Reg(mkbits(clog2(MAX_THREAD_COUNT)))

    @update
    def update_rd_regs():
        for i in range(num_rd_ports):
            s.rd_data[i].msg @= s.register_file.rdata[i]
            s.rd_data[i].val @= s.register_file.rvalid[i]
    
    @update
    def update_cfg_done():

    BitstreamAddrType = mk_bits(clog2(MAX_BITSTREAM_SIZE))

    s.recv_from_cpu_pkt = RecvIfcRTL(CpuPktType)
    s.send_to_cpu_pkt = SendIfcRTL(CpuPktType)

    s.send_cfg_to_tiles = SendIfcRTL(BitstreamType)
    s.send_launch_to_tiles = SendIfcRTL(b(1))

    s.pc = Reg(BitstreamAddrType)
    s.pc_started = Reg(b(1))
    s.pc_done = Reg(b(1))

    s.cfg_mem = RegisterFile(CfgType, MAX_BITSTREAM_SIZE, rd_ports = 1,
                            wr_ports = 1)

    @update
    def update_cfg_mem():
        s.cfg_mem.raddr[0] @= BitstreamAddrType()
        s.cfg_mem.waddr[0] @= BitstreamAddrType()
        s.cfg_mem.wdata[0] @= StepBitstreamPktType()
        s.cfg_mem.wen[0] @= 0

        if (s.recv_from_cpu_pkt.msg.cmd == CMD_CONFIG):
            s.cfg_mem.waddr[0] @= s.recv_from_cpu_pkt.msg.cfg_id
            s.cfg_mem.wdata[0] @= s.recv_from_cpu_pkt.msg.bitstream
            s.cfg_mem.wen[0] @= 1
        elif (s.recv_from_cpu_pkt.msg.cmd == CMD_LAUNCH):
            s.cfg_mem.raddr[0] @= s.pc
            s.send_cfg_to_tiles.msg @= s.cfg_mem.rdata[0]
            s.send_cfg_to_tiles.val @= 1
            s.pc_started @= 1
            s.pc_done @= 0
