from pymtl3 import *
from ..lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ..lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL

class STEP_TokenizerRTL(Component):
    def construct(s, num_credits, max_delay):
        """
        Credit-based tokenizer component
        
        Parameters:
        - num_credits: Initial number of credits available
        - refresh_cycles: Number of cycles before a credit is refreshed
        - credit_bits: Bit width for credit counter
        """
        
        # Interface
        s.take_credit = InPort(Bits1)      # Signal to take a credit
        s.out_credit = OutPort(1)
        s.credit_avail = OutPort(1)
        
        s.credit_shifter = OutPort(max_delay)
        s.credit_shifter_n = OutPort(max_delay)
        s.credit_count = OutPort( clog2(num_credits + 1) )

        s.out_credit //= s.credit_shifter[0]
        
        @update
        def update_shifter_n():
            s.credit_shifter_n @= (1 << (max_delay - 1)) | (s.credit_shifter >> 1)
        
        @update
        def update_credit_avail():
            s.credit_avail @= 0
            if s.credit_count:
                s.credit_avail @= 1
        
        @update_ff
        def update_credit():
            if s.reset:
                s.credit_count <<= num_credits
                s.credit_shifter <<= 0
            else:
                s.credit_shifter <<= s.credit_shifter >> 1
                
                if s.take_credit & s.out_credit:
                    s.credit_shifter <<= s.credit_shifter_n
                elif s.take_credit:
                    s.credit_shifter <<= s.credit_shifter_n
                    s.credit_count <<= s.credit_count - 1
                elif s.out_credit:
                    s.credit_count <<= s.credit_count + 1


        def line_trace(s):
            return f"credits:{s.credits_avail} pending:{s.pending_refreshes} counter:{s.refresh_counter} take:{s.take_credit} valid:{s.credit_valid}"