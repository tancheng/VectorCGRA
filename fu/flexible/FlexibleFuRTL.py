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
from ...fu.single.AdderRTL  import AdderRTL
from ...fu.single.NahRTL  import NahRTL
from ...lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ...lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ...lib.opt_type import *
from ...lib.util.common import *


class FlexibleFuRTL(Component):

  def construct(s,
                DataType,
                PredicateType,
                CtrlType,
                num_inports,
                num_outports,
                data_mem_size,
                num_tiles,
                FuList,
                exec_lantency = {}):

    # Constant
    num_entries = 2
    if NahRTL not in FuList:
      FuList.append(NahRTL)
    s.fu_list_size = len(FuList)
    CountType = mk_bits(clog2(num_entries + 1))
    AddrType = mk_bits(clog2(data_mem_size))
    PrologueCountType = mk_bits(clog2(PROLOGUE_MAX_COUNT + 1))

    # Interface
    s.recv_in = [RecvIfcRTL(DataType) for _ in range(num_inports)]
    s.recv_const = RecvIfcRTL(DataType)
    s.recv_opt = RecvIfcRTL(CtrlType)
    s.send_out = [SendIfcRTL(DataType) for _ in range(num_outports)]

    s.to_mem_raddr = [SendIfcRTL(AddrType) for _ in range(s.fu_list_size)]
    s.from_mem_rdata = [RecvIfcRTL(DataType) for _ in range(s.fu_list_size)]
    s.to_mem_waddr = [SendIfcRTL(AddrType) for _ in range(s.fu_list_size)]
    s.to_mem_wdata = [SendIfcRTL(DataType) for _ in range(s.fu_list_size)]

    s.prologue_count_inport = InPort(PrologueCountType)
    s.tile_id = InPort(mk_bits(clog2(num_tiles + 1)))

    # Components
    s.fu = [FuList[i](DataType, PredicateType, CtrlType, num_inports, num_outports,
                      data_mem_size) if FuList[i] not in exec_lantency.keys() else FuList[i](DataType, PredicateType, CtrlType, num_inports, num_outports,
                      data_mem_size, latency=exec_lantency[FuList[i]]) for i in range(s.fu_list_size) ]

    s.fu_recv_const_rdy_vector = Wire(s.fu_list_size)
    s.fu_recv_opt_rdy_vector = Wire(s.fu_list_size)
    s.fu_recv_in_rdy_vector = [Wire(s.fu_list_size) for i in range(num_inports)]

    # Connection
    for i in range(len(FuList)):
      s.to_mem_raddr[i] //= s.fu[i].to_mem_raddr
      s.from_mem_rdata[i] //= s.fu[i].from_mem_rdata
      s.to_mem_waddr[i] //= s.fu[i].to_mem_waddr
      s.to_mem_wdata[i] //= s.fu[i].to_mem_wdata

    @update
    def comb_logic():

      for j in range(num_outports):
        s.send_out[j].val @= b1(0)
        s.send_out[j].msg @= DataType()

      for i in range(s.fu_list_size):

        # const connection
        s.fu[i].recv_const.msg @= s.recv_const.msg
        s.fu[i].recv_const.val @= s.recv_const.val
        s.fu_recv_const_rdy_vector[i] @= s.fu[i].recv_const.rdy

        # opt connection
        s.fu[i].recv_opt.msg @= s.recv_opt.msg
        s.fu[i].recv_opt.val  @= s.recv_opt.val
        s.fu_recv_opt_rdy_vector[i] @= s.fu[i].recv_opt.rdy

        # send_out connection
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

      # recv_in connection
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

