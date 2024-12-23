"""
==========================================================================
RingMultiCtrlMemDynamicRTL.py
==========================================================================
Ring connecting multiple control memories.

Author : Cheng Tan
  Date : Dec 22, 2024
"""

from pymtl3 import *
from pymtl3.stdlib.primitive import RegisterFile
from .CtrlMemDynamicRTL import CtrlMemDynamicRTL
from ...lib.basic.en_rdy.ifcs import SendIfcRTL
from ...lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL
from ...lib.opt_type import *
from ...noc.PyOCN.pymtl3_net.ringnet.RingNetworkRTL import RingNetworkRTL
from ...cgra.CGRAWithCrossbarDataMemRTL import CGRAWithCrossbarDataMemRTL
from ...noc.PyOCN.pymtl3_net.ocnlib.ifcs.positions import mk_ring_pos

class RingMultiCtrlMemDynamicRTL(Component):

  def construct(s, CtrlPktType, CtrlSignalType, width, height,
                ctrl_mem_size, num_fu_inports, num_fu_outports,
                num_tile_inports, num_tile_outports,
                ctrl_count_per_iter = 4, total_ctrl_steps = 4):

    # Constant
    num_terminals = width * height
    CtrlRingPos = mk_ring_pos(num_terminals)
    s.num_terminals = width * height
    # CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
    # ControllerIdType = mk_bits(clog2(num_terminals))

    # Interface
    # # Request from/to CPU.
    # s.recv_from_cpu = RecvIfcRTL(CGRADataType)
    # s.send_to_cpu = SendIfcRTL(CGRADataType)
    # s.recv_waddr = [[RecvIfcRTL(CtrlAddrType) for _ in range(s.num_tiles)]
    #                 for _ in range(s.num_terminals)]
    # s.recv_wopt = [[RecvIfcRTL(CtrlType)  for _ in range(s.num_tiles)]
    #                for _ in range(s.num_terminals)]
    s.send_ctrl = [SendIfcRTL(CtrlSignalType) for _ in range(s.num_terminals)]
    s.recv_pkt_from_controller = ValRdyRecvIfcRTL(CtrlPktType)

    # Components
    # s.cgra = [CGRAWithCrossbarDataMemRTL(
    #     CGRADataType, PredicateType, CtrlType, NocPktType, CmdType,
    #     ControllerIdType, terminal_id, width, height, ctrl_mem_size,
    #     data_mem_size_global, data_mem_size_per_bank, num_banks_per_cgra,
    #     num_ctrl, total_steps, FunctionUnit, FuList, controller2addr_map,
    #     preload_data = None, preload_const = None)
    #   for terminal_id in range(s.num_terminals)]
    s.ctrl_memories = [
        CtrlMemDynamicRTL(CtrlPktType, CtrlSignalType, ctrl_mem_size,
                          num_fu_inports, num_fu_outports, num_tile_inports,
                          num_tile_outports, ctrl_count_per_iter,
                          total_ctrl_steps) for terminal_id in range(s.num_terminals)]
    s.ctrl_ring = RingNetworkRTL(CtrlPktType, CtrlRingPos, num_terminals, 0)

    # Connections
    for i in range(s.num_terminals):
      s.ctrl_ring.send[i] //= s.ctrl_memories[i].recv_pkt

    s.ctrl_ring.recv[0] //= s.recv_pkt_from_controller
    for i in range(1, s.num_terminals):
      s.ctrl_ring.recv[i].val //= 0
      s.ctrl_ring.recv[i].msg //= CtrlPktType()

    for i in range(s.num_terminals):
      s.ctrl_memories[i].send_ctrl //= s.send_ctrl[i]

  def line_trace(s):
    res = "||\n".join([(("[ctrl_memory["+str(i)+"]: ") + x.line_trace())
                       for (i,x) in enumerate(s.ctrl_memories)])
    res += " ## ctrl_ring: " + s.ctrl_ring.line_trace()
    return res

