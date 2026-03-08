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
from ..tile.STEP_TileCrossbarRTL import STEP_TileCrossbarRTL

class STEP_TileRTL(Component):

    def construct(s,
                    id,
                    num_tile_inports,
                    num_tile_outports,
                    num_fu_inports,
                    num_fu_outports,
                    DataType,
                    TileBitstreamType,
                    OperationType,
                    RegAddrType,
                    PredRegAddrType,
                    debug = False,
                    enable_double_buffering = False
                ):
        assert num_fu_inports == 3
        assert num_fu_outports == 1
        assert(num_tile_inports in [4,8])
        assert(num_tile_outports in [4,8])
        s.id = id

        # I/O Interfaces
        s.tile_in_data_port = [ InPort(DataType) for _ in range(num_tile_inports) ]
        s.tile_out_data_port = [ OutPort(DataType) for _ in range(num_tile_outports) ]
        s.tile_in_pred_port = [ InPort(Bits1) for _ in range(num_tile_inports) ]
        s.tile_out_pred_port = [ OutPort(Bits1) for _ in range(num_tile_outports) ]
        s.recv_tile_bitstream = RecvIfcRTL(TileBitstreamType)
        s.recv_tile_bitstream.rdy //= 1
        s.cfg_packet_applied = OutPort(Bits1)
        s.cfg_active_sel_w = Wire(1)
        s.cfg_load_sel_w = Wire(1)
        s.cfg_swap_w = Wire(1)
        s.cfg_bank_commit = InPort(1)
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
        @update
        def cfg_packet_applied_update():
            s.cfg_packet_applied @= Bits1(
                (s.recv_tile_bitstream.msg.tile_id == s.id) & s.recv_tile_bitstream.val
            )

        if debug:
            s.fu_in = [ OutPort(DataType) for _ in range(num_fu_inports) ]
            s.fu_out = [ OutPort(DataType) for _ in range(num_fu_outports) ]
        else:
            s.fu_in = [ Wire(DataType) for _ in range(num_fu_inports) ]
            s.fu_out = [ Wire(DataType) for _ in range(num_fu_outports) ]
        
        # Predicate interfaces - one for each direction (North, South, West, East)
        s.tile_in_pred_port_rf = InPort(Bits1)  # Predicate from register file

        # Internal bitstream
        if debug:
            s.tile_bitstream = OutPort(TileBitstreamType)
        else:
            s.tile_bitstream = Wire(TileBitstreamType)
        s.opt_type = Wire(OperationType)
        s.opt_type //= s.tile_bitstream.opt_type
        s.tile_bitstream_bank0 = Wire(TileBitstreamType)
        s.tile_bitstream_bank1 = Wire(TileBitstreamType)

        ##### Crossbar instantiation #####
        s.crossbar = STEP_TileCrossbarRTL(num_tile_inports,
                                            num_tile_outports,
                                            num_fu_inports,
                                            num_fu_outports,
                                            DataType,
                                            TileBitstreamType,
                                            RegAddrType
                                        )
        
        ####### Test Connections
        # TODO: @darrenl delete me
        if debug:
            DirectionType = mk_bits( clog2(num_tile_inports + 1))
            TileIdType = mk_bits(clog2(16))
        
            s.tile_in_test = [ OutPort(DataType) for _ in range(num_tile_inports) ]
            for i in range(num_tile_inports):
                s.tile_in_test[i] //= s.tile_in_data_port[i]
            s.ingest_new_bitstream = OutPort(Bits1)
            s.id_matched = OutPort(Bits1)
            s.id_received = OutPort(TileIdType)
            @update
            def new_bitstream():
                s.ingest_new_bitstream @= s.cfg_packet_applied
                s.id_matched @= s.recv_tile_bitstream.msg.tile_id == s.id
                s.id_received @= s.recv_tile_bitstream.msg.tile_id
        #######

        # Wire Connections
        s.crossbar.tile_bitstream //= s.tile_bitstream

        for i in range(num_tile_inports):
            s.crossbar.tile_in_data_port[i] //= s.tile_in_data_port[i]
            s.crossbar.tile_in_pred_port[i] //= s.tile_in_pred_port[i]
            
        for i in range(num_tile_outports):
            s.crossbar.tile_out_data_port[i] //= s.tile_out_data_port[i]
            s.crossbar.tile_out_pred_port[i] //= s.tile_out_pred_port[i]
            
        for i in range(num_fu_outports):
            s.fu_out[i] //= s.crossbar.recv_from_fu[i]
        
        for i in range(num_fu_inports):
            s.fu_in[i] //= s.crossbar.send_to_fu[i]

        # Connect register file predicate
        s.crossbar.pred_in_rf //= s.tile_in_pred_port_rf

        @update_ff
        def cfg_banks():
            if s.reset:
                s.tile_bitstream_bank0 <<= s.tile_bitstream_bank0
                s.tile_bitstream_bank1 <<= s.tile_bitstream_bank1
            if s.cfg_bank_commit:
                if s.cfg_load_sel_w == Bits1(0):
                    s.tile_bitstream_bank0 <<= s.tile_bitstream_bank0
                else:
                    s.tile_bitstream_bank1 <<= s.tile_bitstream_bank1
            elif (s.recv_tile_bitstream.msg.tile_id == s.id) & s.recv_tile_bitstream.val:
                if s.cfg_load_sel_w == Bits1(0):
                    s.tile_bitstream_bank0 <<= s.recv_tile_bitstream.msg
                else:
                    s.tile_bitstream_bank1 <<= s.recv_tile_bitstream.msg

        @update
        def select_active_cfg():
            if s.cfg_active_sel_w == Bits1(0):
                s.tile_bitstream @= s.tile_bitstream_bank0
            else:
                s.tile_bitstream @= s.tile_bitstream_bank1
        
        @update
        def perform_alu_op():
            for i in range(num_fu_outports):
                # Constant Passthrough
                if s.opt_type == OPT_PAS:
                    s.fu_out[i] @= s.tile_bitstream.const_val

                # Comparators
                elif s.opt_type == OPT_LT:
                    s.fu_out[i] @= zext(s.crossbar.send_to_fu[0] < s.crossbar.send_to_fu[1], DataType.nbits)
                elif s.opt_type == OPT_GTE:
                    s.fu_out[i] @= zext(s.crossbar.send_to_fu[0] >= s.crossbar.send_to_fu[1], DataType.nbits)
                elif s.opt_type == OPT_GT:
                    s.fu_out[i] @= zext(s.crossbar.send_to_fu[0] > s.crossbar.send_to_fu[1], DataType.nbits)
                elif s.opt_type == OPT_LTE:
                    s.fu_out[i] @= zext(s.crossbar.send_to_fu[0] <= s.crossbar.send_to_fu[1], DataType.nbits)
                elif s.opt_type == OPT_EQ:
                    s.fu_out[i] @= zext(s.crossbar.send_to_fu[0] == s.crossbar.send_to_fu[1], DataType.nbits)
                
                # Constant Ops
                elif s.opt_type == OPT_ADD_CONST:
                    s.fu_out[i] @= s.crossbar.send_to_fu[0] + s.tile_bitstream.const_val
                elif s.opt_type == OPT_SUB_CONST:
                    s.fu_out[i] @= s.crossbar.send_to_fu[0] - s.tile_bitstream.const_val
                elif s.opt_type == OPT_EQ_CONST:
                    s.fu_out[i] @= zext(s.crossbar.send_to_fu[0] == s.tile_bitstream.const_val, DataType.nbits)
                elif s.opt_type == OPT_MUL_CONST:
                    s.fu_out[i] @= s.crossbar.send_to_fu[0] * s.tile_bitstream.const_val
                elif s.opt_type == OPT_LD:
                    s.fu_out[i] @= s.crossbar.send_to_fu[0] + s.tile_bitstream.const_val # Add Base address to Mem Unit

                # 2 ops
                elif s.opt_type == OPT_ADD:
                    s.fu_out[i] @= s.crossbar.send_to_fu[0] + s.crossbar.send_to_fu[1]
                elif s.opt_type == OPT_DIV:
                    s.fu_out[i] @= s.crossbar.send_to_fu[0] / s.crossbar.send_to_fu[1]
                elif s.opt_type == OPT_SUB:
                    s.fu_out[i] @= s.crossbar.send_to_fu[0] - s.crossbar.send_to_fu[1]
                elif s.opt_type == OPT_MUL:
                    s.fu_out[i] @= s.crossbar.send_to_fu[0] * s.crossbar.send_to_fu[1]
                elif s.opt_type == OPT_INC:
                    s.fu_out[i] @= s.crossbar.send_to_fu[0] + 1
                elif s.opt_type == OPT_OR:
                    s.fu_out[i] @= s.crossbar.send_to_fu[0] | s.crossbar.send_to_fu[1]
                elif s.opt_type == OPT_XOR:
                    s.fu_out[i] @= s.crossbar.send_to_fu[0] ^ s.crossbar.send_to_fu[1]
                elif s.opt_type == OPT_AND:
                    s.fu_out[i] @= s.crossbar.send_to_fu[0] & s.crossbar.send_to_fu[1]
                elif s.opt_type == OPT_NOT:
                    s.fu_out[i] @= ~s.crossbar.send_to_fu[0]
                elif s.opt_type == OPT_LLS:
                    s.fu_out[i] @= s.crossbar.send_to_fu[0] << s.crossbar.send_to_fu[1]
                elif s.opt_type == OPT_LRS:
                    s.fu_out[i] @= s.crossbar.send_to_fu[0] >> s.crossbar.send_to_fu[1]
                
                # 3 ops
                elif s.opt_type == OPT_MUL_ADD:
                    s.fu_out[i] @= s.crossbar.send_to_fu[0] * s.crossbar.send_to_fu[1] + s.crossbar.send_to_fu[2]
                elif s.opt_type == OPT_MUL_SUB:
                    s.fu_out[i] @= s.crossbar.send_to_fu[0] * s.crossbar.send_to_fu[1] - s.crossbar.send_to_fu[2]
                else:
                    s.fu_out[i] @= DataType(0)
