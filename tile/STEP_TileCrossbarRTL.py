"""
=========================================================================
STEP_TileCrossbarRTL.py
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

from ..fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from ..fu.single.AdderRTL import AdderRTL
from ..fu.single.BranchRTL import BranchRTL
from ..fu.single.CompRTL import CompRTL
from ..fu.single.MemUnitRTL import MemUnitRTL
from ..fu.single.MulRTL import MulRTL
from ..fu.single.PhiRTL import PhiRTL
from ..lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ..lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ..lib.cmd_type import *
from ..lib.opt_type import *
from ..lib.util.common import *
from ..mem.const.ConstQueueDynamicRTL import ConstQueueDynamicRTL
from ..mem.ctrl.STEP_CtrlMemDynamicRTL import STEP_CtrlMemDynamicRTL
from ..mem.register_cluster.RegisterClusterRTL import RegisterClusterRTL
from ..noc.CrossbarRTL import CrossbarRTL
from ..noc.LinkOrRTL import LinkOrRTL
from ..noc.PyOCN.pymtl3_net.channel.ChannelRTL import ChannelRTL
from ..rf.RegisterRTL import RegisterRTL



class STEP_TileCrossbarRTL(Component):

    def construct(s,
                    num_tile_inports,
                    num_tile_outports,
                    num_fu_inports,
                    num_fu_outports,
                    DataType,
                    TileBitstreamType,
                    RegAddrType,
                ):
        # TODO: @darrenl only 4 supported
        assert num_tile_inports == 4
        assert num_tile_outports == 4
        AbsoluteTileInPortType = mk_bits( clog2(num_tile_inports) )
        AbsoluteTileOutPortType = mk_bits( clog2(num_tile_outports) )

        # I/O Interfaces
        s.tile_in_data_port = [ InPort(DataType) for _ in range(num_tile_inports) ]
        s.tile_out_data_port = [ OutPort(DataType) for _ in range(num_tile_outports) ]
        s.send_to_fu = [ OutPort(DataType) for _ in range(num_fu_inports) ]
        s.recv_from_fu = [ InPort(DataType) for _ in range(num_fu_outports) ]
        s.tile_bitstream = InPort(TileBitstreamType)

        # Predicate interfaces
        s.tile_in_pred_port = [ InPort(Bits1) for _ in range(num_tile_inports) ]  # North, South, West, East
        s.tile_out_pred_port = [ OutPort(Bits1) for _ in range(num_tile_outports) ]
        s.pred_in_rf = InPort(Bits1)  # Predicate from register file

        s.pred_in_val = OutPort(Bits1)
        s.pred_in_rf_buffer = OutPort(Bits1)
        s.pred_out_value = OutPort(Bits1)

        s.init_cfg = [ OutPort(Bits1) for _ in range(num_tile_inports) ]
        for i in range(num_tile_inports):
            s.init_cfg[i] //= 0
        
        # Internal predicate evaluation wires
        DirectionType = mk_bits( clog2(num_tile_inports + 1))
        s.pred_eval = Wire(Bits1)
        s.should_forward = OutPort(DirectionType)

        s.output_used = Wire(Bits1)

        @update
        def update_pred_in_rf():
            if s.reset:
                s.pred_in_rf_buffer @= 0
            else:
                s.pred_in_rf_buffer @= s.pred_in_rf

        ##### Predicate evaluation logic #####
        @update
        def evaluate_predicates():
            # Get the configured input predicate port for this operation
            s.pred_in_val @= 1
            for i in range(num_fu_inports):
                if s.tile_bitstream.tile_in_route[i] > 0:
                    input_idx = Bits2(s.tile_bitstream.tile_in_route[i] - 1)
                    if ~s.tile_in_pred_port[input_idx]:
                        s.pred_in_val @= 0
            
            s.should_forward @= DirectionType(0)
            s.pred_out_value @= 1
            if ~s.pred_in_val | ~s.pred_in_rf_buffer:
                if s.tile_bitstream.pred_fwd_route > 0:
                    s.should_forward @= DirectionType(s.tile_bitstream.pred_fwd_route - 1)
            elif s.tile_bitstream.pred_gen:
                # TODO @darrenl double check is lower bit
                s.pred_out_value @= Bits1(s.recv_from_fu[0])
            elif ~(s.pred_in_val & s.pred_in_rf_buffer):
                s.pred_out_value @= 0
            
            for i in range(num_tile_outports):
                if s.tile_bitstream.tile_pred_route[i]:
                    s.tile_out_pred_port[AbsoluteTileOutPortType(num_tile_outports - i - 1)] @= s.pred_out_value
                else:
                    s.tile_out_pred_port[AbsoluteTileOutPortType(num_tile_outports - i - 1)] @= 0

        @update
        def update_port_valids():
            # Default Ports:
            for i in range(num_fu_inports):
                s.send_to_fu[i] @= DataType()
            for i in range(num_tile_outports):
                s.tile_out_data_port[i] @= DataType()

            # Handle forwarding logic when predicates are false
            if (s.should_forward > 0) & (s.tile_bitstream.opt_type != OPT_NAH):
                # Forward input data that matches write address, or any data if different addr type
                for i in range(num_tile_outports):
                    if s.tile_bitstream.tile_out_route[i]:
                        s.tile_out_data_port[AbsoluteTileOutPortType(num_tile_outports - i - 1)] @= s.tile_in_data_port[AbsoluteTileOutPortType(s.should_forward - 1)]
            else:
                # Normal operation - send to FU based on configuration
                for i in range(num_fu_inports):
                    tile_port_idx = AbsoluteTileInPortType(s.tile_bitstream.tile_in_route[i] - 1)
                    if s.tile_bitstream.tile_in_route[i] != 0:
                        s.send_to_fu[i] @= s.tile_in_data_port[tile_port_idx]
                    else:
                        s.send_to_fu[i] @= DataType()

                # Route FU output to tile outputs
                # TODO: @darrenl currently assuming only 1 fu outport
                if (s.tile_bitstream.opt_type != OPT_NAH):
                    for i in range(num_tile_outports):
                        if s.tile_bitstream.tile_out_route[i]:
                            s.tile_out_data_port[AbsoluteTileOutPortType(num_tile_outports - i - 1)] @= s.recv_from_fu[0]