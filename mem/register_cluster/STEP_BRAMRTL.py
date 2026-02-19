"""
==========================================================================
BRAM_RegisterFile.py
==========================================================================
Register file implementation using Xilinx BRAM inference.
Optimized for ZCU102 synthesis.

Author : Cheng Tan
Date : Feb 6, 2025
"""
from pymtl3 import *
from ...lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ...lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL

class STEP_BRAMRTL(Component):
    """
    Register file that infers to BRAM in Xilinx synthesis.
    Supports multiple read and write ports.
    """
    def construct(s, DataType, nregs=32, rd_ports=2, wr_ports=2):
        AddrType = mk_bits( clog2(nregs) )

        s.raddr = InPort ( AddrType )
        s.rdata = OutPort( DataType )

        s.wen   = InPort ()
        s.waddr = InPort ( AddrType )
        s.wdata = InPort ( DataType )

        # Internal memory array (this is the key)
        s.mem = [ Wire( DataType ) for _ in range( nregs ) ]

        @update_ff
        def seq_logic():
            if ~s.reset & s.wen:
                s.mem[ s.waddr ] <<= s.wdata
            # synchronous read -> BRAM
            s.rdata <<= s.mem[ s.raddr ]

    def line_trace(s):
        return "BRAMRTL"
    # def line_trace(s):
    #     content_str = "content: " + "|".join([str(data) for data in s.mem])
    #     return f'Register BRAM Bank|| [{content_str}] [BRAM]'

