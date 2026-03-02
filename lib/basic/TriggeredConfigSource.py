from pymtl3 import *
from .val_rdy.ifcs import RecvIfcRTL
from .val_rdy.ifcs import SendIfcRTL
from pymtl3.stdlib.primitive import Reg
from pymtl3.stdlib.primitive import RegisterFile

#-------------------------------------------------------------------------
# Config Source with cfg_done trigger
#-------------------------------------------------------------------------
class TriggeredConfigSource(Component):
   
    def construct(s, CfgMetadataType, msgs, reset_each_time = True):
        s.send = SendIfcRTL(CfgMetadataType)
        s.msgs = msgs
        s.idx = Wire( mk_bits(clog2(max(4, len(msgs) + 1))))
        s.cfg_done_received = InPort(Bits1)
        s.first_msg_sent = Wire(Bits1)
        s.idx_limit = OutPort( mk_bits(clog2(max(4, len(msgs) + 1))) )
        s.done_flag = False
        
        @update_ff
        def up_first_msg_sent():
            s.send.val <<= 0
            if reset_each_time:
                s.send.msg <<= CfgMetadataType()
            if s.reset:
                s.first_msg_sent <<= 0
                s.idx_limit <<= len(msgs)
                s.idx <<= 0
            else:
                if (~s.first_msg_sent):
                    s.first_msg_sent <<= 1
                    s.idx <<= s.idx + 1
                    s.send.val <<= 1
                    s.send.msg <<= msgs[s.idx]

                elif (s.cfg_done_received) & (s.idx < s.idx_limit):
                    s.idx <<= s.idx + 1
                    s.send.val <<= 1
                    s.send.msg <<= msgs[s.idx]
            
            if s.idx >= s.idx_limit:
                s.done_flag = True

    
    def done(s):
        return s.done_flag
    