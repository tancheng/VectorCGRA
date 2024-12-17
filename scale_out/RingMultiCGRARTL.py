"""
==========================================================================
RingMultiCGRARTL.py
==========================================================================
Ring connecting multiple CGRAs, each CGRA contains one controller.

Author : Cheng Tan
  Date : Dec 4, 2024
"""


from pymtl3 import *
from pymtl3.stdlib.primitive import RegisterFile
from ..lib.basic.en_rdy.ifcs import SendIfcRTL, RecvIfcRTL
from ..lib.opt_type import *
from ..noc.PyOCN.pymtl3_net.ringnet.RingNetworkRTL import RingNetworkRTL
from ..cgra.CGRAWithCrossbarDataMemRTL import CGRAWithCrossbarDataMemRTL
from ..noc.PyOCN.pymtl3_net.ocnlib.ifcs.positions import mk_ring_pos


class RingMultiCGRARTL(Component):

  def construct(s, CGRADataType, PredicateType, CtrlType, NocPktType,
                CmdType, num_terminals, width, height, ctrl_mem_size,
                data_mem_size_global, data_mem_size_per_bank,
                num_banks_per_cgra, num_ctrl, total_steps,
                FunctionUnit, FuList, controller2addr_map,
                preload_data = None, preload_const = None):

    # Constant
    RingPos = mk_ring_pos(num_terminals)
    s.num_terminals = num_terminals
    s.num_tiles = width * height
    CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
    ControllerIdType = mk_bits(clog2(num_terminals))

    # Interface
    # # Request from/to CPU.
    # s.recv_from_cpu = RecvIfcRTL(CGRADataType)
    # s.send_to_cpu = SendIfcRTL(CGRADataType)
    s.recv_waddr = [[RecvIfcRTL(CtrlAddrType) for _ in range(s.num_tiles)]
                    for _ in range(s.num_terminals)]
    s.recv_wopt = [[RecvIfcRTL(CtrlType)  for _ in range(s.num_tiles)]
                   for _ in range(s.num_terminals)]

    # Components
    s.cgra = [CGRAWithCrossbarDataMemRTL(
        CGRADataType, PredicateType, CtrlType, NocPktType, CmdType,
        ControllerIdType, terminal_id, width, height, ctrl_mem_size,
        data_mem_size_global, data_mem_size_per_bank, num_banks_per_cgra,
        num_ctrl, total_steps, FunctionUnit, FuList, controller2addr_map,
        preload_data = None, preload_const = None)
      for terminal_id in range(s.num_terminals)]
    s.ring = RingNetworkRTL(NocPktType, RingPos, num_terminals, 0)

    # Connections
    for i in range(s.num_terminals):
      s.ring.send[i] //= s.cgra[i].recv_from_noc
      s.ring.recv[i] //= s.cgra[i].send_to_noc

      for j in range(s.num_tiles):
        s.recv_waddr[i][j] //= s.cgra[i].recv_waddr[j]
        s.recv_wopt[i][j] //= s.cgra[i].recv_wopt[j]


  def line_trace(s):
    res = "||\n".join([(("[cgra["+str(i)+"]: ") + x.line_trace())
                       for (i,x) in enumerate(s.cgra)])
    res += " ## ring: " + s.ring.line_trace()
    return res

