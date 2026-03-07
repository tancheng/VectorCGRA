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
            max_delay,
            enable_double_buffering = False
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
        s.cfg_active_sel_w = Wire(Bits1)
        s.cfg_load_sel_w = Wire(Bits1)
        s.cfg_swap_w = Wire(Bits1)
        if enable_double_buffering:
            s.cfg_active_sel = InPort(Bits1)
            s.cfg_load_sel = InPort(Bits1)
            s.cfg_swap = InPort(Bits1)
            @update
            def cfg_select_wires():
                s.cfg_active_sel_w @= s.cfg_active_sel
                s.cfg_load_sel_w @= s.cfg_load_sel
                s.cfg_swap_w @= s.cfg_swap
        else:
            @update
            def cfg_select_wires():
                s.cfg_active_sel_w @= Bits1(0)
                s.cfg_load_sel_w @= Bits1(0)
                s.cfg_swap_w @= Bits1(0)
        s.tokenizer_cfg = Wire(TokenizerCfgType)
        s.tokenizer_cfg_bank0 = Wire(TokenizerCfgType)
        s.tokenizer_cfg_bank1 = Wire(TokenizerCfgType)
        s.cfg_bank_valid0 = Wire(Bits1)
        s.cfg_bank_valid1 = Wire(Bits1)

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
            s.tokenizers[i].cfg_swap //= s.cfg_swap_w

        # Save Cfg States
        @update
        def cfg_ready():
            s.recv_cfg_from_ctrl.rdy @= Bits1(1)

        @update_ff
        def update_tokenizer_cfg():
            if s.reset:
                s.tokenizer_cfg_bank0 <<= TokenizerCfgType(0, 0)
                s.tokenizer_cfg_bank1 <<= TokenizerCfgType(0, 0)
                s.cfg_bank_valid0 <<= 0
                s.cfg_bank_valid1 <<= 0
            else:
                if s.cfg_swap_w:
                    if s.cfg_load_sel_w == Bits1(0):
                        s.cfg_bank_valid0 <<= 0
                    else:
                        s.cfg_bank_valid1 <<= 0
                if s.recv_cfg_from_ctrl.val & s.recv_cfg_from_ctrl.rdy:
                    if s.cfg_load_sel_w == Bits1(0):
                        s.tokenizer_cfg_bank0 <<= s.recv_cfg_from_ctrl.msg
                        s.cfg_bank_valid0 <<= 1
                    else:
                        s.tokenizer_cfg_bank1 <<= s.recv_cfg_from_ctrl.msg
                        s.cfg_bank_valid1 <<= 1

        @update
        def select_active_cfg():
            if s.cfg_active_sel_w == Bits1(0):
                s.tokenizer_cfg @= s.tokenizer_cfg_bank0
            else:
                s.tokenizer_cfg @= s.tokenizer_cfg_bank1
        
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

    def line_trace(s):
        active_tokens = ",".join(str(int(tok.token_count)) for tok in s.tokenizers[:4])
        return f"cfgswap:{int(s.cfg_swap_w)} toks:[{active_tokens}]"
