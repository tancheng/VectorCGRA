from pymtl3 import *
from ..lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ..lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL

class STEP_TokenizerRTL(Component):
    def construct(s, num_tokens, max_delay):
        """
        token-based tokenizer component
        
        Parameters:
        - num_tokens: Initial number of tokens available
        - refresh_cycles: Number of cycles before a token is refreshed
        - token_bits: Bit width for token counter
        """
        
        # Interface
        s.token_take = InPort(1)      # Signal to take a token
        s.token_return = InPort(1)
        s.token_shifter_out = OutPort(1)
        s.token_avail = OutPort(1)
        s.cfg_swap = InPort(1)
        s.cfg_relaunch = InPort(1)
        
        DelayIdxType = mk_bits( clog2(max_delay) )
        s.token_shifter = OutPort( max_delay )
        s.token_shifter_n = OutPort( max_delay )
        s.token_count = OutPort( clog2(num_tokens + 1) )
        s.token_delay = InPort( DelayIdxType )

        @update
        def update_shifter_out():
            if s.cfg_swap | s.cfg_relaunch:
                s.token_shifter_out @= 0
            else:
                # Preserve the historical positive-delay timing used by the
                # load/store benchmarks, but fix the zero-delay case so it no
                # longer wraps around to the tail of the shift register.
                if s.token_delay == DelayIdxType(0):
                    s.token_shifter_out @= s.token_shifter[DelayIdxType(max_delay - 1)]
                else:
                    s.token_shifter_out @= (
                        s.token_shifter[DelayIdxType(max_delay - 1) - s.token_delay + DelayIdxType(1)]
                    )
        
        @update
        def update_shifter_n():
            s.token_shifter_n @= (1 << (max_delay - 1)) | (s.token_shifter >> 1)
        
        @update
        def update_token_avail():
            s.token_avail @= 0
            if s.token_count:
                s.token_avail @= 1
        
        @update_ff
        def update_token():
            if s.reset:
                s.token_count <<= num_tokens
                s.token_shifter <<= 0
            if s.cfg_swap | s.cfg_relaunch:
                # Tokenizer state is shared across config banks, so a bank swap
                # must restart credits for the newly active config.
                s.token_count <<= num_tokens
                s.token_shifter <<= 0
            else:
                s.token_shifter <<= s.token_shifter >> 1
                
                if s.token_take:
                    s.token_shifter <<= s.token_shifter_n
                
                if s.token_return & ~s.token_take:
                    s.token_count <<= s.token_count + 1
                elif s.token_take & ~s.token_return:
                    s.token_count <<= s.token_count - 1


    def line_trace(s):
        return (
            f"count:{int(s.token_count)} take:{int(s.token_take)} "
            f"ret:{int(s.token_return)} out:{int(s.token_shifter_out)}"
        )
