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
from ..tile.STEP_TileShiftRegisterRTL import STEP_TileShiftRegisterRTL

class STEP_TileShiftRegisterBankRTL(Component):

    def construct(s,
                num_tile_outports,
                DataType,
            ):

        # Types
        ShiftAmountType = mk_bits( clog2(SHIFT_REGISTER_SIZE) )

        # I/O Interfaces
        s.data_in            = [ InPort(DataType) for _ in range(num_tile_outports) ]
        s.data_out           = [ OutPort(DataType) for _ in range(num_tile_outports) ]
        s.shift_amount_in    = [ InPort(ShiftAmountType) for _ in range(num_tile_outports) ]

        ##### Shift Register instantiation #####
        s.shift_registers = [ STEP_TileShiftRegisterRTL(DataType) for _ in range(num_tile_outports) ]

        # Wire connections
        for i in range(num_tile_outports):
            s.shift_registers[i].data_in //= s.data_in[i]
            s.shift_registers[i].shift_amount_in //= s.shift_amount_in[i]
            s.data_out[i] //= s.shift_registers[i].data_out
