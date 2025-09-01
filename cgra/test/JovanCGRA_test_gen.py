"""
==========================================================================
generic_cgra_tester.py
==========================================================================
Generic test for CGRA RTL. It reads CGRA parameters and mapping
configurations from JSON files.

from a build dir:
python ../cgra/test/generic_cgra_tester.py --param ../cgra/test/param.json --config ../cgra/test/config_fir.json --test-verilog --dump-vtb --dump-vcd --tb=long

Author : Jovan Koledin
  Date : Jul 20, 2025
"""

import json
import argparse
from pymtl3.passes.backends.verilog import (VerilogVerilatorImportPass)
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)

# Assuming the test is run from a directory where these imports are valid.
# If not, you might need to adjust the Python path.
from ..CgraRTL import CgraRTL
from ...fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from ...fu.single.AdderRTL import AdderRTL
from ...fu.single.MulRTL import MulRTL
from ...fu.single.LogicRTL import LogicRTL
from ...fu.single.ShifterRTL import ShifterRTL
from ...fu.single.PhiRTL import PhiRTL
from ...fu.single.CompRTL import CompRTL
from ...fu.single.BranchRTL import BranchRTL
from ...fu.single.MemUnitRTL import MemUnitRTL
from ...fu.single.SelRTL import SelRTL
from ...fu.single.RetRTL import RetRTL
from ...lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ...lib.messages import *
from ...lib.opt_type import *

#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, DUT, FunctionUnit, FuList, DataType, PredicateType,
                CtrlPktType, CgraPayloadType, CtrlSignalType, NocPktType,
                ControllerIdType, cgra_id, width, height,
                ctrl_mem_size, data_mem_size_global,
                data_mem_size_per_bank, num_banks_per_cgra,
                num_registers_per_reg_bank,
                src_ctrl_pkt, ctrl_count_per_iter, total_ctrl_steps,
                controller2addr_map, idTo2d_map, complete_signal_sink_out,
                multi_cgra_rows, multi_cgra_columns, src_query_pkt):

    DataAddrType = mk_bits(clog2(data_mem_size_global))
    s.num_tiles = width * height
    s.src_ctrl_pkt = TestSrcRTL(CtrlPktType, src_ctrl_pkt)
    # Print src_ctrl_pkt info
    print("\n--- src_ctrl_pkt info ---")
    if hasattr(s.src_ctrl_pkt, 'msgs'): # TestSrcRTL often stores messages in a 'msgs' attribute
        for i, pkt in enumerate(s.src_ctrl_pkt.msgs):
            print(f"Packet {i}: {pkt}")
    else:
        print("Could not find 'msgs' attribute in src_ctrl_pkt. Inspect TestSrcRTL implementation.")
    print("-------------------------\n")
    s.src_query_pkt = TestSrcRTL(CtrlPktType, src_query_pkt)

    s.dut = DUT(DataType, PredicateType, CtrlPktType, CgraPayloadType,
                CtrlSignalType, NocPktType, ControllerIdType,
                multi_cgra_rows, multi_cgra_columns,
                width, height, ctrl_mem_size,
                data_mem_size_global, data_mem_size_per_bank,
                num_banks_per_cgra, num_registers_per_reg_bank,
                ctrl_count_per_iter, total_ctrl_steps, FunctionUnit,
                FuList, "Mesh", controller2addr_map, idTo2d_map,
                is_multi_cgra = False)

    cmp_fn = lambda a, b: a.payload.cmd == b.payload.cmd
    s.complete_signal_sink_out = TestSinkRTL(CtrlPktType, complete_signal_sink_out, cmp_fn = cmp_fn)

    # Connections
    s.dut.cgra_id //= cgra_id
    s.complete_signal_sink_out.recv //= s.dut.send_to_cpu_pkt

    complete_count_value = \
            sum(1 for pkt in complete_signal_sink_out \
                if pkt.payload.cmd == CMD_COMPLETE)

    CompleteCountType = mk_bits(clog2(complete_count_value + 1))
    s.complete_count = Wire(CompleteCountType)

    @update
    def conditional_issue_ctrl_or_query():
      s.dut.recv_from_cpu_pkt.val @= s.src_ctrl_pkt.send.val
      s.dut.recv_from_cpu_pkt.msg @= s.src_ctrl_pkt.send.msg
      s.src_ctrl_pkt.send.rdy @= 0
      s.src_query_pkt.send.rdy @= 0
      if (s.complete_count >= complete_count_value) & \
         ~s.src_ctrl_pkt.send.val:
        s.dut.recv_from_cpu_pkt.val @= s.src_query_pkt.send.val
        s.dut.recv_from_cpu_pkt.msg @= s.src_query_pkt.send.msg
        s.src_query_pkt.send.rdy @= s.dut.recv_from_cpu_pkt.rdy
      else:
        s.src_ctrl_pkt.send.rdy @= s.dut.recv_from_cpu_pkt.rdy

    @update_ff
    def update_complete_count():
      if s.reset:
        s.complete_count <<= 0
      else:
        if s.complete_signal_sink_out.recv.val & s.complete_signal_sink_out.recv.rdy & \
           (s.complete_count < complete_count_value):
          s.complete_count <<= s.complete_count + CompleteCountType(1)

  def done(s):
    return (s.src_ctrl_pkt.done() and s.src_query_pkt.done()
            and s.complete_signal_sink_out.done())

  def line_trace(s):
    return s.dut.line_trace()

#-------------------------------------------------------------------------
# run_generic_test
#-------------------------------------------------------------------------
def test_run_generic(cmdline_opts):
  
  # Load parameters from JSON files
  with open("../../BITSTREAMS_TO_TEST/param.json", 'r') as f:
    cgra_params = json.load(f)
  with open("../../BITSTREAMS_TO_TEST/counter/counter_config.json", 'r') as f:
    config_data = json.load(f)

  # FuList for a typical CGRA
  FuList = [AdderRTL, MulRTL, LogicRTL, ShifterRTL, PhiRTL, CompRTL,
            BranchRTL, MemUnitRTL, SelRTL, RetRTL]
  
  # Extract CGRA parameters
  x_tiles = cgra_params.get("column", 4)
  y_tiles = cgra_params.get("row", 4)
  ctrl_mem_size = cgra_params.get("ctrlMemConstraint", 8)
  num_registers_per_reg_bank = cgra_params.get("regConstraint", 8)
  
  # These could also be parameterized in param.json if needed
  data_bitwidth = 32
  tile_ports = 4
  num_tile_inports  = tile_ports
  num_tile_outports = tile_ports
  num_fu_inports = 4
  num_fu_outports = 2
  data_mem_size_global = 128
  data_mem_size_per_bank = 16
  num_banks_per_cgra = 2
  num_cgra_columns = 1
  num_cgra_rows = 1
  
  # PyMTL type definitions
  num_cgras = num_cgra_columns * num_cgra_rows
  addr_nbits = clog2(data_mem_size_global)
  num_tiles = x_tiles * y_tiles
  per_cgra_data_size = int(data_mem_size_global / num_cgras)

  DUT = CgraRTL
  FunctionUnit = FlexibleFuRTL

  DataAddrType = mk_bits(addr_nbits)
  RegIdxType = mk_bits(clog2(num_registers_per_reg_bank))
  DataType = mk_data(data_bitwidth, 1)
  PredicateType = mk_predicate(1, 1)
  ControllerIdType = mk_bits(max(1, clog2(num_cgras)))
  
  CtrlType = mk_ctrl(num_fu_inports, num_fu_outports, num_tile_inports,
                     num_tile_outports, num_registers_per_reg_bank)
  CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
  CgraPayloadType = mk_cgra_payload(DataType, DataAddrType, CtrlType, CtrlAddrType)
  InterCgraPktType = mk_inter_cgra_pkt(num_cgra_columns, num_cgra_rows,
                                       num_tiles, CgraPayloadType)
  IntraCgraPktType = mk_intra_cgra_pkt(num_cgra_columns, num_cgra_rows,
                                       num_tiles, CgraPayloadType)

  # Map string opcodes from JSON to OPT variables
  opcode_map = {
      "OPT_NAH"       : OPT_NAH,
      "OPT_ADD"       : OPT_ADD,
      "OPT_ADD_CONST" : OPT_ADD_CONST,
      "OPT_SUB"       : OPT_SUB,
      "OPT_MUL"       : OPT_MUL,
      "OPT_PHI"       : OPT_PHI,
      "OPT_PHI_CONST" : OPT_PHI_CONST,
      "OPT_LD"        : OPT_LD,
      "OPT_STR"       : OPT_STR,
      "OPT_STR_CONST" : OPT_STR_CONST,
      "OPT_EQ"        : OPT_EQ,
      "OPT_EQ_CONST"  : OPT_EQ_CONST,
      "OPT_BRH"       : OPT_BRH,
      # Add other opcodes as needed
  }

  # --- Dynamic Packet Generation from config.json ---
 
  src_opt_pkt_map = {i: [] for i in range(num_tiles)}
  max_cycle = 0

  for op in config_data:
    tile_x = op['x']
    tile_y = op['y']
    tile_id = tile_y * x_tiles + tile_x
    cycle = op['cycle']
    max_cycle = max(max_cycle, cycle)

    # Default values
    # The default is to connect FU input 'i' to tile input 'i+1'.
    fu_in_code = [mk_bits(clog2(num_tile_inports + 1))(x + 1) for x in range(num_fu_inports)]
    fu_xbar_outport = [mk_bits(clog2(num_tile_inports + 1))(0)] * (num_tile_outports + num_fu_inports)
    
    # Corrected Section: Read fu_in_port parameters from JSON
    # This loop checks for 'fu_in_X' keys in the config and overrides the default values.
    for i in range(num_fu_inports):
        inport_key = f"fu_in_{i}"
        # If the key exists for this operation, use its value.
        if inport_key in op:
            # The value from the JSON specifies which tile input port to use.
            fu_in_code[i] = mk_bits(clog2(num_tile_inports + 1))(op[inport_key])

    # Parse outputs for FU crossbar
    for i in range(num_tile_outports + num_fu_inports):
        out_val = op.get(f"out_{i}", "none")
        if out_val != "none":
            # Assuming out_X refers to one of the FU outputs (e.g., 1 or 2)
            fu_xbar_outport[i] = mk_bits(clog2(num_tile_inports + 1))(int(out_val))

    # Create the control packet with the potentially updated fu_in_code
    ctrl_pkt = CtrlType(
        opcode_map[op['opt']],
        op['predicate'],
        fu_in_code,
        fu_xbar_outport
        # NOTE: More complex fields like routing_xbar, write_reg_from, etc.
        # would need to be added to the JSON and parsed here if needed.
    )
    
    src_tile = 0
    config_pkt = IntraCgraPktType(
        src_tile, tile_id,
        payload = CgraPayloadType(
            cmd=CMD_CONFIG,
            ctrl_addr=cycle,
            ctrl=ctrl_pkt
        )
    )
    src_opt_pkt_map[tile_id].append(config_pkt)

  total_ctrl_steps = max_cycle + 1
  ctrl_count_per_iter = total_ctrl_steps # Assuming one iteration for this test

  # Add other necessary packets (launch, config counts, etc.) to each tile
  for tile_id, pkts in src_opt_pkt_map.items():
      
      # Insert config count packets at the beginning
      pkts.insert(0, IntraCgraPktType(src_tile, tile_id, payload=CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data=DataType(total_ctrl_steps, 1))))
      pkts.insert(0, IntraCgraPktType(src_tile, tile_id, payload=CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data=DataType(ctrl_count_per_iter, 1))))
      
      # Add launch command at the end
      pkts.append(IntraCgraPktType(src_tile, tile_id, payload=CgraPayloadType(CMD_LAUNCH)))

      pkts.append(IntraCgraPktType(src_tile, tile_id, payload=CgraPayloadType(CMD_COMPLETE)))
  # Flatten the map into a single list of packets
  src_opt_pkt = []
  for tile_id in sorted(src_opt_pkt_map.keys()):
      src_opt_pkt.extend(src_opt_pkt_map[tile_id])

  # --- Kernel-Specific Section ---
  # The following data (preload, query, expected results) is specific
  # to the FIR filter kernel. For a different kernel, this section
  # would need to be updated accordingly.

  preload_data = [
      IntraCgraPktType(0, 0, payload=CgraPayloadType(CMD_STORE_REQUEST, data=DataType(10, 1), data_addr = 0)),
      IntraCgraPktType(0, 0, payload=CgraPayloadType(CMD_STORE_REQUEST, data=DataType(11, 1), data_addr = 1)),
      IntraCgraPktType(0, 0, payload=CgraPayloadType(CMD_STORE_REQUEST, data=DataType(12, 1), data_addr = 2)),
      IntraCgraPktType(0, 0, payload=CgraPayloadType(CMD_STORE_REQUEST, data=DataType(13, 1), data_addr = 3)),
      IntraCgraPktType(0, 0, payload=CgraPayloadType(CMD_STORE_REQUEST, data=DataType(14, 1), data_addr = 4)),
      IntraCgraPktType(0, 0, payload=CgraPayloadType(CMD_STORE_REQUEST, data=DataType(15, 1), data_addr = 5)),
  ]

  src_query_pkt = [
      IntraCgraPktType(payload=CgraPayloadType(CMD_LOAD_REQUEST, data_addr=16)),
  ]

  num_active_tiles = len([tid for tid, pkts in src_opt_pkt_map.items() if pkts])
  expected_complete_sink_out_pkg = [IntraCgraPktType(payload=CgraPayloadType(CMD_COMPLETE)) for _ in range(num_active_tiles)]
  
  expected_mem_sink_out_pkt = [
      IntraCgraPktType(dst=16, payload=CgraPayloadType(CMD_LOAD_RESPONSE, data=DataType(0xab, 1), data_addr=16)),
  ]
  # --- End Kernel-Specific Section ---

  src_ctrl_pkt = []
  src_ctrl_pkt.extend(preload_data)
  src_ctrl_pkt.extend(src_opt_pkt)

  complete_signal_sink_out = []
  complete_signal_sink_out.extend(expected_complete_sink_out_pkg)
  complete_signal_sink_out.extend(expected_mem_sink_out_pkt)
  
  # CGRA addressing and ID setup
  cgra_id = 0
  controller2addr_map = {i: [i * per_cgra_data_size, (i + 1) * per_cgra_data_size - 1] for i in range(num_cgras)}
  idTo2d_map = {i: [i, 0] for i in range(num_cgras)} # Simplified for single row of CGRAs

  # Instantiate and run the test harness
  th = TestHarness(DUT, FunctionUnit, FuList, DataType, PredicateType,
                   IntraCgraPktType, CgraPayloadType, CtrlType, InterCgraPktType,
                   ControllerIdType, cgra_id, x_tiles, y_tiles,
                   ctrl_mem_size, data_mem_size_global,
                   data_mem_size_per_bank, num_banks_per_cgra,
                   num_registers_per_reg_bank,
                   src_ctrl_pkt, ctrl_count_per_iter, total_ctrl_steps,
                   controller2addr_map, idTo2d_map, complete_signal_sink_out,
                   num_cgra_rows, num_cgra_columns,
                   src_query_pkt)

  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                       ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                        'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)
