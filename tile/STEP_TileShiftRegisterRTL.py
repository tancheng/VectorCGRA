"""
=========================================================================
STEP_TileRTL.py
=========================================================================
The tile contains a list of functional units, a configuration memory, a
set of registers (e.g., channels), and two crossbars. One crossbar is for
routing the data to registers (i.e., the channels before FU and the
channels after the crossbar), and the other one is for passing the to the
next crossbar.

Detailed in: https://github.com/tancheng/VectorCGRA/issues/13 (Option 2).

Author : Cheng Tan
  Date : Nov 26, 2024
"""

from ..lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ..lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ..lib.cmd_type import *
from ..lib.opt_type import *
from ..lib.util.common import *

from pymtl3 import *
from pymtl3.stdlib.primitive import Reg

class STEP_TileShiftRegisterRTL( Component ):

    def construct( s, DataType ):

        ShiftAmountType = mk_bits( clog2( SHIFT_REGISTER_SIZE ) )

        # I/O
        s.data_in         = InPort( DataType )
        s.data_out        = OutPort( DataType )
        s.shift_amount_in = InPort( ShiftAmountType )

        # Shift register storage
        s.shift_reg_n = [ Wire( DataType ) for _ in range( SHIFT_REGISTER_SIZE ) ]
        s.shift_reg = [ Wire( DataType ) for _ in range( SHIFT_REGISTER_SIZE ) ]

        # Output oldest entry
        s.data_out //= s.shift_reg[0]

        @update
        def shift_reg_comb():
            # Shift toward output
            for i in range( SHIFT_REGISTER_SIZE-1 ):
                s.shift_reg_n[i] @= s.shift_reg[i+1]

            # Insert new data at programmable position
            insert_idx = s.shift_amount_in
            s.shift_reg_n[ insert_idx ] @= s.data_in

        @update_ff
        def shift_reg_ff():
            if s.reset:
                for i in range( SHIFT_REGISTER_SIZE ):
                    s.shift_reg[i] <<= DataType(0)
            else:
                # Shift toward output
                for i in range( SHIFT_REGISTER_SIZE ):
                    s.shift_reg[i] <<= s.shift_reg_n[i]