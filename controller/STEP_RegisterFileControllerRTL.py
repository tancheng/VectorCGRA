from pymtl3 import *
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
                CfgMetadataType,
                num_banks=2,
                num_rd_ports=2,
                num_wr_ports=2,
                num_registers=16):
    
    RegAddrType = mk_bits(clog2(num_registers))
    
    s.register_file = STEP_RegisterFileRTL(RegDataType, RegAddrType,
                                            num_reg_banks=num_banks,
                                            num_rd_ports=num_rd_ports,
                                            num_wr_ports=num_wr_ports,
                                            num_registers_per_reg_bank=num_registers // num_banks)
    
    # Rd Reg
    s.rd_addr_data = [Reg(RegAddrType) for _ in range(num_rd_ports)]
    s.rd_addr_val = [Reg(Bits1) for _ in range(num_rd_ports)]
    s.rd_data = [OutPort(RegDataType) for _ in range(num_rd_ports)]
    
    # Wr Reg
    s.wr_addr_data = [Reg(RegAddrType) for _ in range(num_wr_ports)]
    s.wr_addr_val = [Reg(Bits1) for _ in range(num_wr_ports)]
    s.wr_data = [InPort(RegDataType) for _ in range(num_wr_ports)]
    
    # Recv from Controller (main STEP_ControllerRTL)
    s.recv_cfg_from_ctrl = RecvIfcRTL(CfgMetadataType)
    
    # Send to Controller
    s.cfg_done = OutPort(Bits1)
    
    # Internal
    MaxThreadType = mk_bits(clog2(MAX_THREAD_COUNT))
    s.rd_count = Reg(MaxThreadType)
    s.wr_count = Reg(MaxThreadType)
    s.expected_count = Reg(MaxThreadType)
    s.cfg_active = Reg(Bits1)
    
    # Wire connections to register file
    for i in range(num_rd_ports):
        s.register_file.rd_addr[i] //= s.rd_addr_data[i].out
        s.register_file.rd_en[i] //= s.rd_addr_val[i].out
        s.rd_data[i] //= s.register_file.rd_data[i]
    
    for i in range(num_wr_ports):
        s.register_file.wr_addr[i] //= s.wr_addr_data[i].out
        s.register_file.wr_en[i] //= s.wr_addr_val[i].out
        s.register_file.wr_data[i] //= s.wr_data[i]
    
    # Ready signal for receiving config from main controller
    s.recv_cfg_from_ctrl.rdy //= ~s.cfg_active.out
    
    # TODO: @darrenl handle const types
    @update
    def update_new_cfg():
        # Default assignments to avoid latches
        s.cfg_done @= s.cfg_active.out & (s.rd_count.out >= s.expected_count.out) & (s.wr_count.out >= s.expected_count.out)
        
        # Handle new configuration from main controller
        if s.recv_cfg_from_ctrl.val and s.recv_cfg_from_ctrl.rdy:
            for i in range(num_rd_ports):
                s.rd_addr_data[i].in_ @= s.recv_cfg_from_ctrl.msg.in_regs[i]
                s.rd_addr_val[i].in_ @= s.recv_cfg_from_ctrl.msg.in_regs_val[i]
           
            for i in range(num_wr_ports):
                s.wr_addr_data[i].in_ @= s.recv_cfg_from_ctrl.msg.out_regs[i]
                s.wr_addr_val[i].in_ @= s.recv_cfg_from_ctrl.msg.out_regs_val[i]
                
            s.rd_count.in_ @= MaxThreadType(0)
            s.wr_count.in_ @= MaxThreadType(0)
            s.expected_count.in_ @= s.recv_cfg_from_ctrl.msg.thread_count
            s.cfg_active.in_ @= Bits1(1)
        else:
            # Keep current values
            for i in range(num_rd_ports):
                s.rd_addr_data[i].in_ @= s.rd_addr_data[i].out
                s.rd_addr_val[i].in_ @= s.rd_addr_val[i].out
           
            for i in range(num_wr_ports):
                s.wr_addr_data[i].in_ @= s.wr_addr_data[i].out
                s.wr_addr_val[i].in_ @= s.wr_addr_val[i].out
                
            s.rd_count.in_ @= s.rd_count.out
            s.wr_count.in_ @= s.wr_count.out
            s.expected_count.in_ @= s.expected_count.out
            s.cfg_active.in_ @= s.cfg_active.out
   
    @update_ff
    def update_cfg_run():
        if s.cfg_active.out and ~s.cfg_done:
            rd_active = Bits1(0)
            wr_active = Bits1(0)
            
            # Check if we have active read operations and count completed ones
            if s.rd_count.out < s.expected_count.out:
                for i in range(num_rd_ports):
                    if s.rd_addr_val[i].out:
                        rd_active = Bits1(1)
                        # Simulate read completion (in real implementation, this would be
                        # based on actual register file ready signals)
                        if s.register_file.rd_data_val[i]:
                            s.rd_count.in_ <<= s.rd_count.out + MaxThreadType(1)
                            break
                if not rd_active:
                    s.rd_count.in_ <<= s.rd_count.out
            else:
                s.rd_count.in_ <<= s.rd_count.out
                
            # Check if we have active write operations and count completed ones  
            if s.wr_count.out < s.expected_count.out:
                for i in range(num_wr_ports):
                    if s.wr_addr_val[i].out:
                        wr_active = Bits1(1)
                        # Simulate write completion (in real implementation, this would be
                        # based on actual register file ready signals)
                        if s.register_file.wr_data_rdy[i]:
                            s.wr_count.in_ <<= s.wr_count.out + MaxThreadType(1)
                            break
                if not wr_active:
                    s.wr_count.in_ <<= s.wr_count.out
            else:
                s.wr_count.in_ <<= s.wr_count.out
            
            # Check completion and cleanup
            if (s.rd_count.out >= s.expected_count.out and 
                s.wr_count.out >= s.expected_count.out):
                s.cfg_active.in_ <<= Bits1(0)
                # Stop sending and writing data - disable all ports
                for i in range(num_rd_ports):
                    s.rd_addr_val[i].in_ <<= Bits1(0)
                for i in range(num_wr_ports):
                    s.wr_addr_val[i].in_ <<= Bits1(0)
            else:
                s.cfg_active.in_ <<= s.cfg_active.out
                # Keep current address/enable values
                for i in range(num_rd_ports):
                    s.rd_addr_data[i].in_ <<= s.rd_addr_data[i].out
                    s.rd_addr_val[i].in_ <<= s.rd_addr_val[i].out
                for i in range(num_wr_ports):
                    s.wr_addr_data[i].in_ <<= s.wr_addr_data[i].out
                    s.wr_addr_val[i].in_ <<= s.wr_addr_val[i].out
        else:
            # When not active or done, maintain current state
            s.cfg_active.in_ <<= s.cfg_active.out
            s.rd_count.in_ <<= s.rd_count.out
            s.wr_count.in_ <<= s.wr_count.out
            s.expected_count.in_ <<= s.expected_count.out
            
            # Keep address registers but disable operations when done
            for i in range(num_rd_ports):
                s.rd_addr_data[i].in_ <<= s.rd_addr_data[i].out
                s.rd_addr_val[i].in_ <<= Bits1(0) if s.cfg_done else s.rd_addr_val[i].out
            for i in range(num_wr_ports):
                s.wr_addr_data[i].in_ <<= s.wr_addr_data[i].out
                s.wr_addr_val[i].in_ <<= Bits1(0) if s.cfg_done else s.wr_addr_val[i].out