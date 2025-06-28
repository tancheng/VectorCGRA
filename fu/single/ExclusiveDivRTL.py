"""
==========================================================================
ExclusiveDivRTL.py
==========================================================================
Exclusive integer divisor for CGRA tile.

Author : Jiajun Qin
  Date : May 2, 2025
"""

from pymtl3 import *
from ..basic.Fu import Fu
from ...lib.opt_type import *
from pymtl3.passes.backends.verilog import *

class ExclusiveDivRTL(Fu):

  def construct(s, DataType, PredicateType, CtrlType,
                num_inports, num_outports, data_mem_size,
                latency = 4, vector_factor_power = 0):

    super(ExclusiveDivRTL, s).construct(DataType, PredicateType, CtrlType,
                               num_inports, num_outports, data_mem_size,
                               latency, vector_factor_power)

    num_entries = 2
    num_cycles = latency

    FuInType = mk_bits(clog2(num_inports + 1))
    CountType = mk_bits(clog2(num_entries + 1))

    s.in0 = Wire(FuInType)
    s.in1 = Wire(FuInType)

    # TODO: how to parameterize the bit widths
    s.div = Div(WIDTH=32, CYCLE=num_cycles)

    idx_nbits = clog2(num_inports)
    s.in0_idx = Wire(idx_nbits)
    s.in1_idx = Wire(idx_nbits)
    LatencyType = mk_bits(clog2(latency) + 1)
    s.cur_cycle = Wire(LatencyType)

    s.in0_idx //= s.in0[0:idx_nbits]
    s.in1_idx //= s.in1[0:idx_nbits]

    s.recv_all_val = Wire(1)
    s.do_div       = Wire(1)

    @update_ff
    def comb_ff():
      if (s.cur_cycle == latency - 1) & s.send_out[0].rdy:
          s.cur_cycle <<= 0
      elif s.cur_cycle == latency - 1:
        s.cur_cycle <<= s.cur_cycle
      elif s.do_div:
        s.cur_cycle <<= s.cur_cycle + 1
      elif (s.recv_all_val & (s.recv_opt.msg.operation == OPT_DIV)):
        s.cur_cycle <<= 1
      else:
        s.cur_cycle <<= 0

    @update
    def comb_logic():

      s.recv_all_val @= 0
      # For pick input register
      s.in0 @= 0
      s.in1 @= 0
      for i in range(num_inports):
        s.recv_in[i].rdy @= b1(0)
      for i in range(num_outports):
        s.send_out[i].val @= 0
        s.send_out[i].msg @= DataType()

      s.recv_const.rdy @= 0
      s.recv_predicate.rdy @= b1(0)
      s.recv_opt.rdy @= 0

      if s.recv_opt.val:
        if s.recv_opt.msg.fu_in[0] != 0:
          s.in0 @= zext(s.recv_opt.msg.fu_in[0] - 1, FuInType)
        if s.recv_opt.msg.fu_in[1] != 0:
          s.in1 @= zext(s.recv_opt.msg.fu_in[1] - 1, FuInType)

      if s.recv_opt.val:
        if (s.recv_opt.msg.operation == OPT_DIV) | (s.recv_opt.msg.operation == OPT_REM):
          s.div.dividend @= s.recv_in[s.in0_idx].msg.payload
          s.div.divisor @= s.recv_in[s.in1_idx].msg.payload
          if s.recv_opt.msg.operation == OPT_DIV:
            s.send_out[0].msg.payload @= s.div.quotient
          else:
            s.send_out[0].msg.payload @= s.div.remainder
          s.send_out[0].msg.predicate @= s.recv_in[s.in0_idx].msg.predicate & \
                                         s.recv_in[s.in1_idx].msg.predicate & \
                                         (~s.recv_opt.msg.predicate | \
                                          s.recv_predicate.msg.predicate) & \
                                         s.reached_vector_factor
          s.recv_all_val @= s.recv_in[s.in0_idx].val & s.recv_in[s.in1_idx].val & ((s.recv_opt.msg.predicate == b1(0)) | s.recv_predicate.val)
          s.send_out[0].val @= (latency - 1 == s.cur_cycle)
          s.recv_in[s.in0_idx].rdy @= s.send_out[0].val & s.send_out[0].rdy
          s.recv_in[s.in1_idx].rdy @= s.send_out[0].val & s.send_out[0].rdy
          s.do_div @= 1
          s.recv_opt.rdy @= s.send_out[0].val & s.send_out[0].rdy
          # TODO: if single-cycle?
          if s.send_out[0].rdy & (s.recv_opt.msg.predicate == b1(1)):
            s.recv_predicate.rdy @= s.send_out[0].val & s.send_out[0].rdy
        else:
          for j in range(num_outports):
            s.send_out[j].val @= b1(0)
          s.recv_opt.rdy @= 0
          s.recv_in[s.in0_idx].rdy @= 0
          s.recv_in[s.in1_idx].rdy @= 0
          s.do_div @= 0
          if s.send_out[0].rdy & (s.recv_opt.msg.predicate == b1(1)):
            s.recv_predicate.rdy @= s.recv_all_val & s.send_out[0].rdy
      else:
        s.do_div @= 0

class Div( VerilogPlaceholder, Component ):

  # Constructor
  def construct( s, WIDTH = 32, CYCLE = 8 ):

    # Interface
    s.dividend              = InPort ( WIDTH )
    s.divisor              = InPort ( WIDTH )

    s.quotient            = OutPort ( WIDTH )
    s.remainder            = OutPort ( WIDTH )

    # Configurations
    from os import path
    srcdir = path.dirname(__file__) + path.sep

    s.set_metadata( VerilogPlaceholderPass.src_file, srcdir + 'division.v' )
    s.set_metadata( VerilogPlaceholderPass.top_module, 'pipeline_division' )
    s.set_metadata( VerilogPlaceholderPass.v_include, [ srcdir ] )
    # s.set_metadata( VerilogPlaceholderPass.v_libs, [
    #   srcdir + 'division.v',
    # ])
    s.set_metadata( VerilogPlaceholderPass.has_clk, True )
    s.set_metadata( VerilogPlaceholderPass.has_reset, True )

    s.set_metadata( VerilogVerilatorImportPass.vl_Wno_list, ['WIDTH'] )
