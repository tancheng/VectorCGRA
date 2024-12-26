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

from ...tile.TileRTL_constant import tile_port_direction_dict_short_desc
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

  # verbose trace
  def verbose_trace( s, verbosity = 1 ):
    num_fu_in = len(s.reg_file.regs[0].fu_in)
    # num_inports = len(s.reg_file.regs[0].predicate_in)
    num_outports = len(s.reg_file.regs[0].outport if hasattr(s.reg_file.regs[0], 'outport') else [])
    num_direction_ports = num_outports - num_fu_in

    # recv_ctrl
    recv_ctrl_msg_dict = dict(s.recv_ctrl.msg.__dict__)
    recv_ctrl_sub_header = {}
    for key in recv_ctrl_msg_dict.keys():
      recv_ctrl_sub_header[key] = ''
    recv_ctrl_msg_list = []
    recv_ctrl_msg_dict['ctrl'] = OPT_SYMBOL_DICT[recv_ctrl_msg_dict['ctrl']]
    recv_ctrl_msg_dict['fu_in'] = [ int(fi) for fi in recv_ctrl_msg_dict['fu_in'] ]
    fu_in_header = []
    for idx, val in enumerate(recv_ctrl_msg_dict['fu_in']):
      fu_in_header.append(idx)
    fu_in_header_str = "|".join([f"{hd : ^3}" for hd in fu_in_header])
    recv_ctrl_msg_dict['fu_in'] = "|".join([f"{v : ^3}" for v in recv_ctrl_msg_dict['fu_in']])
    recv_ctrl_sub_header['fu_in'] = fu_in_header_str

    if 'outport' in recv_ctrl_msg_dict:
      recv_ctrl_msg_dict['outport'] = [ int(op) for op in recv_ctrl_msg_dict['outport'] ]
      fu_reg_num = 1
      outport_sub_header = []
      for idx, val in enumerate(recv_ctrl_msg_dict['outport']):
        # to directions
        if idx <= num_direction_ports - 1:
          hd = tile_port_direction_dict_short_desc[idx]
          outport_sub_header.append(f"{hd : ^{len(hd) + 2}}")
          recv_ctrl_msg_dict['outport'][
            idx] = f"{tile_port_direction_dict_short_desc[val - 1] if val != 0 else '-' : ^{len(hd) + 2}}"
        # to fu regs
        else:
          hd = f"fu_reg_{fu_reg_num}"
          outport_sub_header.append(f"{hd : ^{len(hd)}}")
          recv_ctrl_msg_dict['outport'][
            idx] = f"{tile_port_direction_dict_short_desc[val - 1] if val != 0 else '-' : ^{len(hd)}}"
          fu_reg_num += 1
      outport_sub_header_str = "|".join([hd for hd in outport_sub_header])
      recv_ctrl_msg_dict['outport'] = "|".join([v for v in recv_ctrl_msg_dict['outport']])
      recv_ctrl_sub_header['outport'] = outport_sub_header_str
    if 'predicate_in' in recv_ctrl_msg_dict:
      recv_ctrl_msg_dict['predicate_in'] = [int(pi) for pi in recv_ctrl_msg_dict['predicate_in']]
      fu_out_num = 1
      predicate_in_sub_header = []
      for idx, val in enumerate(recv_ctrl_msg_dict['predicate_in']):
        # from directions
        if idx <= num_direction_ports - 1:
          hd = tile_port_direction_dict_short_desc[idx]
          predicate_in_sub_header.append(f"{hd : ^{len(hd) + 2}}")
          recv_ctrl_msg_dict['predicate_in'][idx] = f"{val : ^{len(hd) + 2}}"
        # from fu
        else:
          hd = f"fu_out_{fu_out_num}"
          predicate_in_sub_header.append(f"{hd : ^{len(hd)}}")
          recv_ctrl_msg_dict['predicate_in'][idx] = f"{val : ^{len(hd)}}"
          fu_out_num += 1
      predicate_in_sub_header_str = "|".join([hd for hd in predicate_in_sub_header])
      recv_ctrl_msg_dict['predicate_in'] = "|".join([v for v in recv_ctrl_msg_dict['predicate_in']])
      recv_ctrl_sub_header['predicate_in'] = predicate_in_sub_header_str
    recv_ctrl_msg_list.append(recv_ctrl_sub_header)
    recv_ctrl_msg_list.append(recv_ctrl_msg_dict)
    send_ctrl_md = markdown_table(recv_ctrl_msg_list).set_params(quote=False).get_markdown()
    # recv_ctrl_msg = "\n".join([(key + ": " + str(value)) for key, value in recv_ctrl_msg_dict.items()])

    # send_ctrl
    send_ctrl_msg_dict = dict(s.send_ctrl.msg.__dict__)
    send_ctrl_sub_header = {}
    for key in send_ctrl_msg_dict.keys():
      send_ctrl_sub_header[key] = ''
    send_ctrl_msg_list = []
    send_ctrl_msg_dict['ctrl'] = OPT_SYMBOL_DICT[send_ctrl_msg_dict['ctrl']]
    if 'predicate' in send_ctrl_msg_dict:
      send_ctrl_msg_dict['predicate'] = int(send_ctrl_msg_dict['predicate'])
    send_ctrl_msg_dict['fu_in'] = [int(fi) for fi in send_ctrl_msg_dict['fu_in']]
    fu_in_header = []
    for idx, val in enumerate(send_ctrl_msg_dict['fu_in']):
      fu_in_header.append(idx)
    fu_in_header_str = "|".join([f"{hd : ^3}" for hd in fu_in_header])
    send_ctrl_msg_dict['fu_in'] = "|".join([f"{v : ^3}" for v in send_ctrl_msg_dict['fu_in']])
    send_ctrl_sub_header['fu_in'] = fu_in_header_str

    if 'outport' in send_ctrl_msg_dict:
      send_ctrl_msg_dict['outport'] = [int(op) for op in send_ctrl_msg_dict['outport']]
      fu_reg_num = 1
      outport_sub_header = []
      for idx, val in enumerate(send_ctrl_msg_dict['outport']):
        # to directions
        if idx <= num_direction_ports - 1:
          hd = tile_port_direction_dict_short_desc[idx]
          outport_sub_header.append(f"{hd : ^{len(hd) + 2}}")
          send_ctrl_msg_dict['outport'][
            idx] = f"{tile_port_direction_dict_short_desc[val - 1] if val != 0 else '-' : ^{len(hd) + 2}}"
        # to fu regs
        else:
          hd = f"fu_reg_{fu_reg_num}"
          outport_sub_header.append(f"{hd : ^{len(hd)}}")
          send_ctrl_msg_dict['outport'][
            idx] = f"{tile_port_direction_dict_short_desc[val - 1] if val != 0 else '-' : ^{len(hd)}}"
          fu_reg_num += 1
      outport_sub_header_str = "|".join([hd for hd in outport_sub_header])
      send_ctrl_msg_dict['outport'] = "|".join([v for v in send_ctrl_msg_dict['outport']])
      send_ctrl_sub_header['outport'] = outport_sub_header_str
    if 'predicate_in' in send_ctrl_msg_dict:
      send_ctrl_msg_dict['predicate_in'] = [int(pi) for pi in send_ctrl_msg_dict['predicate_in']]
      fu_out_num = 1
      predicate_in_sub_header = []
      for idx, val in enumerate(send_ctrl_msg_dict['predicate_in']):
        # from directions
        if idx <= num_direction_ports - 1:
          hd = tile_port_direction_dict_short_desc[idx]
          predicate_in_sub_header.append(f"{hd : ^{len(hd) + 2}}")
          send_ctrl_msg_dict['predicate_in'][idx] = f"{val : ^{len(hd) + 2}}"
        # from fu
        else:
          hd = f"fu_out_{fu_out_num}"
          predicate_in_sub_header.append(f"{hd : ^{len(hd)}}")
          send_ctrl_msg_dict['predicate_in'][idx] = f"{val : ^{len(hd)}}"
          fu_out_num += 1
      predicate_in_sub_header_str = "|".join([hd for hd in predicate_in_sub_header])
      send_ctrl_msg_dict['predicate_in'] = "|".join([v for v in send_ctrl_msg_dict['predicate_in']])
      send_ctrl_sub_header['predicate_in'] = predicate_in_sub_header_str
    if 'routing_xbar_outport' in send_ctrl_msg_dict:
      send_ctrl_msg_dict['routing_xbar_outport'] = [int(rxop) for rxop in send_ctrl_msg_dict['routing_xbar_outport']]
    if 'fu_xbar_outport' in send_ctrl_msg_dict:
      send_ctrl_msg_dict['fu_xbar_outport'] = [int(fxop) for fxop in send_ctrl_msg_dict['fu_xbar_outport']]
    if 'routing_predicate_in' in send_ctrl_msg_dict:
      send_ctrl_msg_dict['routing_predicate_in'] = [int(rpi) for rpi in send_ctrl_msg_dict['routing_predicate_in']]

    send_ctrl_msg_list.append(send_ctrl_sub_header)
    send_ctrl_msg_list.append(send_ctrl_msg_dict)
    send_ctrl_md = markdown_table(send_ctrl_msg_list).set_params(quote=False).get_markdown()
    # send_ctrl_msg = "\n".join([(key + ": " + str(value)) for key, value in send_ctrl_msg_dict.items()])

    if verbosity == 1:
      return (f'\n## class: {s.__class__.__name__}\n'
              f'- recv_ctrl_msg:\n'
              f'{send_ctrl_md}\n\n'
              f'- send_ctrl_msg:'
              f'{send_ctrl_md}\n\n')
    else:
      # reg
      reg_dicts = [dict(data.__dict__) for data in s.reg_file.regs]
      reg_sub_header = {}
      for reg_dict in reg_dicts:
        for key in reg_dict.keys():
          reg_sub_header[key] = ''
        reg_dict['ctrl'] = OPT_SYMBOL_DICT[reg_dict['ctrl']]
        reg_dict['fu_in'] = [int(fi) for fi in reg_dict['fu_in']]
        fu_in_header = []
        for idx, val in enumerate(reg_dict['fu_in']):
          fu_in_header.append(idx)
        fu_in_header_str = "|".join([f"{hd : ^3}" for hd in fu_in_header])
        reg_dict['fu_in'] = "|".join([f"{v : ^3}" for v in reg_dict['fu_in']])
        reg_sub_header['fu_in'] = fu_in_header_str
        if 'outport' in reg_dict:
          reg_dict['outport'] = [int(op) for op in reg_dict['outport']]
          fu_reg_num = 1
          outport_sub_header = []
          for idx, val in enumerate(reg_dict['outport']):
            # to directions
            if idx <= num_direction_ports - 1:
              hd = tile_port_direction_dict_short_desc[idx]
              outport_sub_header.append(f"{hd : ^{len(hd) + 2}}")
              reg_dict['outport'][
                idx] = f"{tile_port_direction_dict_short_desc[val - 1] if val != 0 else '-' : ^{len(hd) + 2}}"
            # to fu regs
            else:
              hd = f"fu_reg_{fu_reg_num}"
              outport_sub_header.append(f"{hd : ^{len(hd)}}")
              reg_dict['outport'][
                idx] = f"{tile_port_direction_dict_short_desc[val - 1] if val != 0 else '-' : ^{len(hd)}}"
              fu_reg_num += 1
          outport_sub_header_str = "|".join([hd for hd in outport_sub_header])
          reg_dict['outport'] = "|".join([v for v in reg_dict['outport']])
          reg_sub_header['outport'] = outport_sub_header_str
        if 'predicate_in' in reg_dict:
          reg_dict['predicate_in'] = [int(pi) for pi in reg_dict['predicate_in']]
          fu_out_num = 1
          predicate_in_sub_header = []
          for idx, val in enumerate(reg_dict['predicate_in']):
            # from directions
            if idx <= num_direction_ports - 1:
              hd = tile_port_direction_dict_short_desc[idx]
              predicate_in_sub_header.append(f"{hd : ^{len(hd) + 2}}")
              reg_dict['predicate_in'][idx] = f"{val : ^{len(hd) + 2}}"
            # from fu
            else:
              hd = f"fu_out_{fu_out_num}"
              predicate_in_sub_header.append(f"{hd : ^{len(hd)}}")
              reg_dict['predicate_in'][idx] = f"{val : ^{len(hd)}}"
              fu_out_num += 1
          predicate_in_sub_header_str = "|".join([hd for hd in predicate_in_sub_header])
          reg_dict['predicate_in'] = "|".join([v for v in reg_dict['predicate_in']])
          reg_sub_header['predicate_in'] = predicate_in_sub_header_str
        if 'routing_xbar_outport' in reg_dict:
          reg_dict['routing_xbar_outport'] = [int(rxop) for rxop in reg_dict['routing_xbar_outport']]
        if 'fu_xbar_outport' in reg_dict:
          reg_dict['fu_xbar_outport'] = [int(fxop) for fxop in reg_dict['fu_xbar_outport']]
        if 'routing_predicate_in' in reg_dict:
          reg_dict['routing_predicate_in'] = [int(rpi) for rpi in reg_dict['routing_predicate_in']]
      reg_dicts.insert(0, reg_sub_header)
      reg_md = markdown_table(reg_dicts).set_params(quote=False).get_markdown()
      return (f'\n## class: {s.__class__.__name__}\n'
              f'- recv_ctrl_msg:\n'
              f'{send_ctrl_md}\n\n'
              f'- send_ctrl_msg:'
              f'{send_ctrl_md}\n\n'
              f'- ctrl_memory: {reg_md}\n')


  def line_trace( s ):
    out_str = "||".join([str(data) for data in s.reg_file.regs])
    return f'{s.recv_ctrl.msg} : [{out_str}] : {s.send_ctrl.msg}'


