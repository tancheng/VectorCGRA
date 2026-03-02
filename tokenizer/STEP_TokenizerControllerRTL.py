from pymtl3 import *
from .STEP_TokenizerRTL import STEP_TokenizerRTL
from ..lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ..lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL

class STEP_TokenizerControllerRTL(Component):
    def construct(s,
            TokenizerCfgType,
            num_rd_ports,
            num_wr_ports,
            num_ld_ports,
            num_st_ports,
            num_tokens,
            max_delay
        ):
        """
        token-based tokenizer component
        
        Parameters:
        - num_tokens: Initial number of tokens available
        - refresh_cycles: Number of cycles before a token is refreshed
        - token_bits: Bit width for token counter
        """
        # Cfg variables
        num_taker_ports = num_rd_ports
        num_returner_ports = num_wr_ports + num_ld_ports + num_st_ports
        
        # Interface
        s.token_take = [ InPort(1) for _ in range(num_taker_ports) ]
        s.token_shifter_out = [ OutPort(1) for _ in range(num_returner_ports) ]
        s.token_avail = [ OutPort(1) for _ in range(num_taker_ports) ]
        s.token_return = [ InPort(1) for _ in range(num_returner_ports) ]

        # Cfg Specific
        s.recv_cfg_from_ctrl = RecvIfcRTL(TokenizerCfgType)
        s.recv_cfg_from_ctrl.rdy //= 1
        s.tokenizer_cfg = Wire(TokenizerCfgType)

        # Instantiate Tokenizers
        s.tokenizers = [ STEP_TokenizerRTL(num_tokens, max_delay) for _ in range(num_returner_ports) ]

        ### Debug Ports
        # s.tokenizer_take = [ OutPort(1) for _ in range(num_returner_ports) ]
        s.token_shifter = [ OutPort(max_delay) for _ in range(num_returner_ports) ]
        s.tokenizer_avail = [ OutPort(1) for _ in range(num_returner_ports) ]
        s.tokenizer_count = [ OutPort(mk_bits(clog2(num_tokens + 1))) for _ in range(num_returner_ports) ]
        for i in range(num_returner_ports):
            s.token_shifter[i] //= s.tokenizers[i].token_shifter
            s.tokenizer_avail[i] //= s.tokenizers[i].token_avail
            s.tokenizer_count[i] //= s.tokenizers[i].token_count

        # Wire Connections
        for i in range(num_returner_ports):
            s.tokenizer_cfg.token_route_delay_to_sink[i] //= s.tokenizers[i].token_delay
            s.token_return[i] //= s.tokenizers[i].token_return
            s.token_shifter_out[i] //= s.tokenizers[i].token_shifter_out

        # Save Cfg States
        @update
        def update_tokenizer_cfg():
            if s.reset:
                s.tokenizer_cfg @= TokenizerCfgType(0, 0)
            elif s.recv_cfg_from_ctrl.val:
                s.tokenizer_cfg @= s.recv_cfg_from_ctrl.msg
        
        # And all requested token returns together
        @update
        def token_crossbar():
            # Token avail logic
            for i in range(num_taker_ports):
                s.token_avail[i] @= 1
                for j in range(num_returner_ports):
                    if s.tokenizer_cfg.token_route_sink_enable[i][Bits4(num_returner_ports - j - 1)]:
                        s.token_avail[i] @= s.token_avail[i] & s.tokenizers[j].token_avail
            
            # Token take default
            for j in range(num_returner_ports):
                s.tokenizers[j].token_take @= 0
            
            # Token ake logic
            for i in range(num_taker_ports):
                for j in range(num_returner_ports):
                    if s.tokenizer_cfg.token_route_sink_enable[i][Bits4(num_returner_ports - j - 1)]:
                        s.tokenizers[j].token_take @= s.token_take[i]