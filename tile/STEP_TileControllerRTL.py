"""
=========================================================================
TileSeparateCrossbarRTL.py
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
from ..lib.util.common import *
from ..mem.const.ConstQueueDynamicRTL import ConstQueueDynamicRTL
from ..mem.ctrl.STEP_CtrlMemDynamicRTL import STEP_CtrlMemDynamicRTL
from ..mem.register_cluster.RegisterClusterRTL import RegisterClusterRTL
from ..noc.CrossbarRTL import CrossbarRTL
from ..noc.LinkOrRTL import LinkOrRTL
from ..noc.PyOCN.pymtl3_net.channel.ChannelRTL import ChannelRTL
from ..rf.RegisterRTL import RegisterRTL


class STEP_TileControllerRTL(Component):
    def construct(s, CfgType):
        s.recv_cfg_from_cfg_ctrl = RecvIfcRTL(CfgType)
        # s.send_cfg_done = SendIfcRTL(b(1))
        s.recv_cfg_start = RecvIfcRTL(b(1))
        s.send_cfg = SendIfcRTL(CfgType)

        s.cfg_mem = RegisterFile()
