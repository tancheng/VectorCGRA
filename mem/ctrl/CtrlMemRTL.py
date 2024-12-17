"""
==========================================================================
CtrlMemRTL.py
==========================================================================
Control memory for CGRA.

Author : Cheng Tan
  Date : Dec 21, 2019
"""
from py_markdown_table.markdown_table import markdown_table
from pymtl3 import *
from pymtl3.stdlib.primitive import RegisterFile
from ...lib.basic.en_rdy.ifcs import SendIfcRTL, RecvIfcRTL
from ...lib.opt_type import *


class CtrlMemRTL( Component ):

  def construct( s, CtrlType, ctrl_mem_size, ctrl_count_per_iter = 4,
                 total_ctrl_steps = 4 ):

    # The total_ctrl_steps indicates the number of steps the ctrl
    # signals should proceed. For example, if the number of ctrl
    # signals is 4 and they need to repeat 5 times, then the total
    # number of steps should be 4 * 5 = 20.
    # assert( ctrl_mem_size <= total_ctrl_steps )

    # Constant
    AddrType = mk_bits( clog2( ctrl_mem_size ) )
    PCType   = mk_bits( clog2( ctrl_count_per_iter + 1 ) )
    TimeType = mk_bits( clog2( total_ctrl_steps + 1 ) )
    last_item = AddrType( ctrl_mem_size - 1 )

    # Interface
    s.send_ctrl  = SendIfcRTL( CtrlType )
    s.recv_waddr = RecvIfcRTL( AddrType )
    s.recv_ctrl  = RecvIfcRTL( CtrlType )

    # Component
    s.reg_file   = RegisterFile( CtrlType, ctrl_mem_size, 1, 1 )
    s.times = Wire( TimeType )

    # Connections
    s.send_ctrl.msg //= s.reg_file.rdata[0]
    s.reg_file.waddr[0] //= s.recv_waddr.msg
    s.reg_file.wdata[0] //= s.recv_ctrl.msg
    s.reg_file.wen[0]   //= lambda: s.recv_ctrl.en & s.recv_waddr.en

    @update
    def update_signal():
      if ( ( total_ctrl_steps > 0 ) & \
           ( s.times == TimeType( total_ctrl_steps ) ) ) | \
         (s.reg_file.rdata[0].ctrl == OPT_START):
        s.send_ctrl.en @= b1( 0 )
      else:
        s.send_ctrl.en @= s.send_ctrl.rdy # s.recv_raddr[i].rdy
      s.recv_waddr.rdy @= b1( 1 )
      s.recv_ctrl.rdy @= b1( 1 )

    @update_ff
    def update_raddr():
      if s.reg_file.rdata[0].ctrl != OPT_START:
        if ( total_ctrl_steps == 0 ) | \
           ( s.times < TimeType( total_ctrl_steps ) ):
          s.times <<= s.times + TimeType( 1 )
        # Reads the next ctrl signal only when the current one is done.
        if s.send_ctrl.rdy:
          if zext(s.reg_file.raddr[0] + 1, PCType) == \
             PCType( ctrl_count_per_iter ):
            s.reg_file.raddr[0] <<= AddrType( 0 )
          else:
            s.reg_file.raddr[0] <<= s.reg_file.raddr[0] + AddrType( 1 )

  def line_trace( s ):
    out_dicts = [ dict(data.__dict__) for data in s.reg_file.regs ]
    for out_dict in out_dicts:
      out_dict['ctrl'] = OPT_SYMBOL_DICT[out_dict['ctrl']]
      out_dict['fu_in'] = [ int(fi) for fi in  out_dict['fu_in']]
      if out_dict['outport']:
        out_dict['outport'] = [ int(op) for op in  out_dict['outport']]
      out_dict['predicate_in'] = [ int(pi) for pi in  out_dict['predicate_in']]
    out_md  = markdown_table(out_dicts).set_params(quote=False).get_markdown()
    # recv_opt_msg = "\n".join([(key + ": " + str(value)) for key, value in recv_opt_msg_dict.items()])
    recv_ctrl_msg_dict = dict(s.recv_ctrl.msg.__dict__)
    recv_ctrl_msg_dict['ctrl'] = OPT_SYMBOL_DICT[recv_ctrl_msg_dict['ctrl']]
    recv_ctrl_msg_dict['fu_in'] = [ int(fi) for fi in  out_dict['fu_in']]
    recv_ctrl_msg_dict['outport'] = [ int(op) for op in  out_dict['outport']]
    recv_ctrl_msg_dict['predicate_in'] = [ int(pi) for pi in  out_dict['predicate_in']]
    recv_ctrl_msg = "\n".join([(key + ": " + str(value)) for key, value in recv_ctrl_msg_dict.items()])
    send_ctrl_msg_dict = dict(s.send_ctrl.msg.__dict__)
    send_ctrl_msg_dict['ctrl'] = OPT_SYMBOL_DICT[send_ctrl_msg_dict['ctrl']]
    send_ctrl_msg_dict['fu_in'] = [ int(fi) for fi in  send_ctrl_msg_dict['fu_in']]
    send_ctrl_msg_dict['outport'] = [int(op) for op in send_ctrl_msg_dict['outport']]
    send_ctrl_msg_dict['predicate_in'] = [int(pi) for pi in send_ctrl_msg_dict['predicate_in']]
    send_ctrl_msg = "\n".join([(key + ": " + str(value)) for key, value in send_ctrl_msg_dict.items()])
    print(f"send_ctrl_msg_dict: {send_ctrl_msg_dict}")
    return (f'\n## class: {s.__class__.__name__}\n'
            f'- recv_ctrl_msg:\n'
            f'{recv_ctrl_msg}\n'
            f'- out: {out_md}\n'
            f'- send_ctrl_msg:\n'
            f'{send_ctrl_msg}\n')

