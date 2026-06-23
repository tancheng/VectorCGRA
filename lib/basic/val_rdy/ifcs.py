"""
========================================================================
ValRdyIfc
========================================================================
RTL val/rdy interface.

Author : Shunning Jiang
  Date : Apr 5, 2019
"""
from pymtl3 import *


def valrdy_to_str( msg, val, rdy, trace_len=15 ):
  if     val and not rdy: return "#".ljust( trace_len )
  if not val and     rdy: return " ".ljust( trace_len )
  if not val and not rdy: return ".".ljust( trace_len )
  return f"{msg}".ljust( trace_len ) # val and rdy

class RecvIfcRTL( Interface ):

  def construct( s, Type ):

    s.msg = InPort( Type )
    s.val = InPort()
    s.rdy = OutPort()

    s.trace_len = len(str(Type()))

  def __str__( s ):
    return valrdy_to_str( s.msg, s.val, s.rdy, s.trace_len )

class ValRdyRecvIfcRTL( Interface ):

  def construct( s, Type ):

    s.msg = InPort( Type )
    s.val = InPort()
    s.rdy = OutPort()

    s.trace_len = len(str(Type()))

  def __str__( s ):
    return valrdy_to_str( s.msg, s.val, s.rdy, s.trace_len )

class SendIfcRTL( Interface ):

  def construct( s, Type ):

    s.msg = OutPort( Type )
    s.val = OutPort()
    s.rdy = InPort()

    s.trace_len = len(str(Type()))

  def __str__( s ):
    return valrdy_to_str( s.msg, s.val, s.rdy, s.trace_len )

class ValRdySendIfcRTL( Interface ):

  def construct( s, Type ):

    s.msg = OutPort( Type )
    s.val = OutPort()
    s.rdy = InPort()

    s.trace_len = len(str(Type()))

  def __str__( s ):
    return valrdy_to_str( s.msg, s.val, s.rdy, s.trace_len )

class MasterIfcRTL( Interface ):
  def construct( s, ReqType, RespType ):
    s.ReqType  = ReqType
    s.RespType = RespType
    s.req  = SendIfcRTL( Type=ReqType )
    s.resp = RecvIfcRTL( Type=RespType )
  def __str__( s ):
    return f"{s.req}|{s.resp}"

class MinionIfcRTL( Interface ):
  def construct( s, ReqType, RespType ):
    s.ReqType  = ReqType
    s.RespType = RespType
    s.req  = RecvIfcRTL( Type=ReqType )
    s.resp = SendIfcRTL( Type=RespType )
  def __str__( s ):
    return f"{s.req}|{s.resp}"

class DmaSpmMasterIfcRTL( Interface ):
  """
    DMA-to-SPM Master Interface.
    
    This interface is instantiated on the DMA side. 
    It initiates all transfer requests (both write and read) to the SPM 
    and receives the corresponding read data back.
    
    Direction:
    - write   : Output (Send). DMA sends write requests to SPM.
    - read    : Output (Send). DMA sends read requests to SPM.
    - read_resp: Input  (Recv). DMA receives read data from SPM.
  """

  def construct( s, WriteReqType, ReadReqType, ReadRespType ):
    s.WriteReqType  = WriteReqType
    s.ReadReqType   = ReadReqType
    s.ReadRespType  = ReadRespType
    s.write     = SendIfcRTL( WriteReqType )
    s.read      = SendIfcRTL( ReadReqType )
    s.read_resp = RecvIfcRTL( ReadRespType )
  def __str__( s ):
    return f"wr:{s.write}|rd:{s.read}|resp:{s.read_resp}"

class DmaSpmMinionIfcRTL( Interface ):
  """
    DMA-to-SPM Minion Interface.
    
    This interface is instantiated on the SPM side.
    It passively accepts incoming transfer requests from the DMA master, 
    performs the requested memory operations, and returns read data if needed.
    
    Direction:
    - write   : Input  (Recv). SPM receives write requests from DMA.
    - read    : Input  (Recv). SPM receives read requests from DMA.
    - read_resp: Output (Send). SPM sends read data back to DMA.
  """
  def construct( s, WriteReqType, ReadReqType, ReadRespType ):
    s.WriteReqType  = WriteReqType
    s.ReadReqType   = ReadReqType
    s.ReadRespType  = ReadRespType
    s.write     = RecvIfcRTL( WriteReqType )
    s.read      = RecvIfcRTL( ReadReqType )
    s.read_resp = SendIfcRTL( ReadRespType )
  def __str__( s ):
    return f"wr:{s.write}|rd:{s.read}|resp:{s.read_resp}"

class DmaDramWrReqIfcRTL( Interface ):
  """
    DMA-to-DRAM Write Request Interface.
    
    This interface is instantiated on the DMA side. 
    It initiates a write request to the DRAM.
    
    Direction:
    - req: Output (Send). DMA sends write requests to DRAM.
  """
  def construct( s, DramAddrType, DmaMemDataType, DmaMemMaskType ):
    s.val = OutPort()
    s.rdy = InPort()
    s.addr = OutPort(DramAddrType)
    s.data = OutPort(DmaMemDataType)
    s.mask = OutPort(DmaMemMaskType)
  def __str__( s ):
    return f"val:{s.val}|rdy:{s.rdy}|addr:{s.addr}|data:{s.data}|mask:{s.mask}"