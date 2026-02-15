"""
==========================================================================
FlexibleFuRTL.py
==========================================================================
A flexible functional unit whose functionality can be parameterized.

Author : Cheng Tan
  Date : Dec 24, 2019

"""

from pymtl3 import *
from ...fu.single.MemUnitRTL import MemUnitRTL
from ...fu.single.StreamingMemUnitRTL import StreamingMemUnitRTL
from ...fu.single.AdderRTL  import AdderRTL
from ...fu.single.RetRTL  import RetRTL
from ...fu.single.NahRTL  import NahRTL
from ...lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ...lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ...lib.messages import *
from ...lib.opt_type import *
from ...lib.util.common import *

class FlexibleFuRTL(Component):
  def construct(s,
                CtrlPktType,
                num_inports,
                num_outports,
                num_tiles,
                FuList,
                exec_lantency = {}):

    # Constants.
    num_entries = 2
    if NahRTL not in FuList:
      FuList.append(NahRTL)
    s.fu_list_size = len(FuList)
    s.DataType = CtrlPktType.get_field_type(kAttrPayload).get_field_type(kAttrData)
    s.AddrType = CtrlPktType.get_field_type(kAttrPayload).get_field_type(kAttrDataAddr)
    s.CtrlType = CtrlPktType.get_field_type(kAttrPayload).get_field_type(kAttrCtrl)
    s.CtrlAddrType = CtrlPktType.get_field_type(kAttrPayload).get_field_type(kAttrCtrlAddr)
    s.CgraPayloadType = CtrlPktType.get_field_type(kAttrPayload)
    CountType = mk_bits(clog2(num_entries + 1))
    s.ctrl_addr_inport = InPort(s.CtrlAddrType)
    PrologueCountType = mk_bits(clog2(PROLOGUE_MAX_COUNT + 1))

    # Interfaces.
    s.recv_in = [RecvIfcRTL(s.DataType) for _ in range(num_inports)]
    s.recv_const = RecvIfcRTL(s.DataType)
    s.recv_opt = RecvIfcRTL(s.CtrlType)
    s.send_out = [SendIfcRTL(s.DataType) for _ in range(num_outports)]
    # Serves as the bridge between the RetRTL and the ctrl memory controller.
    s.send_to_ctrl_mem = SendIfcRTL(CgraPayloadType)
    s.recv_from_ctrl_mem = RecvIfcRTL(CgraPayloadType)
    # Interfaces for streaming LD.
    s.recv_pkt_from_controller = RecvIfcRTL(CtrlPktType)

    s.to_mem_raddr = [SendIfcRTL(s.AddrType) for _ in range(s.fu_list_size)]
    s.from_mem_rdata = [RecvIfcRTL(s.DataType) for _ in range(s.fu_list_size)]
    s.to_mem_waddr = [SendIfcRTL(s.AddrType) for _ in range(s.fu_list_size)]
    s.to_mem_wdata = [SendIfcRTL(s.DataType) for _ in range(s.fu_list_size)]
    s.clear = [InPort(b1) for _ in range(s.fu_list_size)]

    s.prologue_count_inport = InPort(PrologueCountType)
    s.tile_id = InPort(mk_bits(clog2(num_tiles + 1)))

    # Components.
    s.fu = [FuList[i](CtrlPktType, num_inports, num_outports) 
            if FuList[i] not in exec_lantency.keys() else FuList[i](CtrlPktType, num_inports, 
                num_outports, latency=exec_lantency[FuList[i]]) for i in range(s.fu_list_size)]

    s.fu_recv_const_rdy_vector = Wire(s.fu_list_size)
    s.fu_recv_opt_rdy_vector = Wire(s.fu_list_size)
    s.recv_from_controller_rdy_vector = Wire(s.fu_list_size)
    s.fu_recv_in_rdy_vector = [Wire(s.fu_list_size) for i in range(num_inports)]

    # Connection.
    for i in range(len(FuList)):
      s.to_mem_raddr[i] //= s.fu[i].to_mem_raddr
      s.from_mem_rdata[i] //= s.fu[i].from_mem_rdata
      s.to_mem_waddr[i] //= s.fu[i].to_mem_waddr
      s.to_mem_wdata[i] //= s.fu[i].to_mem_wdata
      s.clear[i] //= s.fu[i].clear
      if FuList[i] == StreamingMemUnitRTL:
        s.recv_pkt_from_controller //= s.fu[i].recv_from_controller_pkt
    
    @update
    def connect_to_controller():
      for i in range(s.fu_list_size):
        # const connection.
        s.fu[i].recv_from_ctrl_mem.msg @= s.recv_from_ctrl_mem.msg
        s.fu[i].recv_from_ctrl_mem.val @= s.recv_from_ctrl_mem.val
        s.recv_from_controller_rdy_vector[i] @= s.fu[i].recv_from_ctrl_mem.rdy
      s.recv_from_ctrl_mem.rdy @= reduce_or(s.recv_from_controller_rdy_vector)

      s.send_to_ctrl_mem.msg @= s.CgraPayloadType(0, 0, 0, 0, 0)
      s.send_to_ctrl_mem.val @= 0
      for i in range(s.fu_list_size):
        if s.fu[i].send_to_ctrl_mem.val:
          s.send_to_ctrl_mem.msg @= s.fu[i].send_to_ctrl_mem.msg
          s.send_to_ctrl_mem.val @= s.fu[i].send_to_ctrl_mem.val
        s.fu[i].send_to_ctrl_mem.rdy @= s.send_to_ctrl_mem.rdy
        s.fu[i].ctrl_addr_inport @= s.ctrl_addr_inport

    @update
    def comb_logic():
      for j in range(num_outports):
        s.send_out[j].val @= b1(0)
        s.send_out[j].msg @= s.DataType()

      for i in range(s.fu_list_size):
        # const connection.
        s.fu[i].recv_const.msg @= s.recv_const.msg
        s.fu[i].recv_const.val @= s.recv_const.val
        s.fu_recv_const_rdy_vector[i] @= s.fu[i].recv_const.rdy

        # opt connection.
        s.fu[i].recv_opt.msg @= s.recv_opt.msg
        # Sets each FU's op code as NAH when prologue execution is not completed.
        # As they are supposed to do nothing during that prologue cycles.
        if s.prologue_count_inport != 0:
          s.fu[i].recv_opt.msg.operation @= OPT_NAH
        s.fu[i].recv_opt.val @= s.recv_opt.val
        s.fu_recv_opt_rdy_vector[i] @= s.fu[i].recv_opt.rdy

        # send_out connection.
        for j in range(num_outports):
          # FIXME: need reduce_or here: https://github.com/tancheng/VectorCGRA/issues/51.
          if s.fu[i].send_out[j].val:
            s.send_out[j].msg @= s.fu[i].send_out[j].msg
            s.send_out[j].val @= s.fu[i].send_out[j].val
          s.fu[i].send_out[j].rdy @= s.send_out[j].rdy

      s.recv_const.rdy @= reduce_or(s.fu_recv_const_rdy_vector)
      # Operation (especially mem access) won't perform more than once, because once the
      # operation is performance (i.e., the recv_opt.rdy would be set), the `element_done`
      # register would be set and be respected.
      s.recv_opt.rdy @= reduce_or(s.fu_recv_opt_rdy_vector) | (s.prologue_count_inport != 0)

      for j in range(num_inports):
        s.recv_in[j].rdy @= b1(0)

      # recv_in connection.
      for port in range(num_inports):
        for i in range(s.fu_list_size):
          s.fu[i].recv_in[port].msg @= s.recv_in[port].msg
          s.fu[i].recv_in[port].val @= s.recv_in[port].val
          # s.recv_in[j].rdy       @= s.fu[i].recv_in[j].rdy | s.recv_in[j].rdy
          s.fu_recv_in_rdy_vector[port][i] @= s.fu[i].recv_in[port].rdy
        s.recv_in[port].rdy @= reduce_or(s.fu_recv_in_rdy_vector[port])

  def line_trace(s):
    opt_str = " #"
    if s.recv_opt.val:
      opt_str = OPT_SYMBOL_DICT[s.recv_opt.msg.operation]
    out_str = " | ".join([(str(x.msg) + ", val: " + str(x.val) + ", rdy: " + str(x.rdy)) for x in s.send_out])
    recv_str = " | ".join([str(x.msg) for x in s.recv_in])
    return f'[recv: {recv_str}] {opt_str} (const: {s.recv_const.msg}, val: {s.recv_const.val}, rdy: {s.recv_const.rdy}) ] = [out: {out_str}] (recv_opt.rdy: {s.recv_opt.rdy}, recv_in[0].rdy: {s.recv_in[0].rdy}, recv_in[1].rdy: {s.recv_in[1].rdy}, {OPT_SYMBOL_DICT[s.recv_opt.msg.operation]}, recv_opt.val: {s.recv_opt.val}, send[0].val: {s.send_out[0].val}) '

