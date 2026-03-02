
from ..lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ..lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ..lib.opt_type import *
from ..lib.util.common import *
from ..tile.STEP_TileRTL import STEP_TileRTL

class STEP_ScanChainRTL(Component):
    
    def construct(s,
                    DataType,
                    scan_cnt = 15):
        
        s.scan_in = RecvIfcRTL(DataType)
        s.scan_pts_val = [OutPort(Bits1) for _ in range(scan_cnt)]
        s.scan_pts = [OutPort(DataType) for _ in range(scan_cnt)]

        s.scan_in.rdy //= 1

        @update_ff
        def shift_scan():
            if s.reset:
                for i in range(scan_cnt):
                    s.scan_pts_val[i] <<= 0
                    s.scan_pts[i] <<= 0
            else:
                for i in range(scan_cnt - 1):
                    s.scan_pts_val[i+1] <<= s.scan_pts_val[i]
                    s.scan_pts[i+1] <<= s.scan_pts[i]
                s.scan_pts_val[0] <<= s.scan_in.val
                s.scan_pts[0] <<= s.scan_in.msg