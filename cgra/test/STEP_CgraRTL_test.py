"""
==========================================================================
CgraRTL_test.py
==========================================================================
Test cases for CGRA with crossbar-based data memory and ring-based control
memory of each tile.

Author : Cheng Tan
  Date : Dec 22, 2024
"""

from pymtl3.passes.backends.verilog import (VerilogVerilatorImportPass)
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)

from ..CgraRTL import CgraRTL
from ..CgraTrackedPktChunked import CgraTrackedPktChunked
from ..CgraTrackedHelper import convertPktToCPUWidth
from ...fu.double.SeqMulAdderRTL import SeqMulAdderRTL
from ...fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from ...fu.float.FpAddRTL import FpAddRTL
from ...fu.float.FpMulRTL import FpMulRTL
from ...fu.single.AdderRTL import AdderRTL
from ...fu.single.BranchRTL import BranchRTL
from ...fu.single.CompRTL import CompRTL
from ...fu.single.LogicRTL import LogicRTL
from ...fu.single.MemUnitRTL import MemUnitRTL
from ...fu.single.MulRTL import MulRTL
from ...fu.single.PhiRTL import PhiRTL
from ...fu.single.RetRTL import RetRTL
from ...fu.single.SelRTL import SelRTL
from ...fu.single.ShifterRTL import ShifterRTL
from ...fu.vector.VectorAdderComboRTL import VectorAdderComboRTL
from ...fu.vector.VectorMulComboRTL import VectorMulComboRTL
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
                src_ctrl_pkt, ctrl_steps, topology, controller2addr_map,
                idTo2d_map, complete_signal_sink_out,
                multi_cgra_rows, multi_cgra_columns, src_query_pkt):

    DataAddrType = mk_bits(clog2(data_mem_size_global))
    s.num_tiles = width * height
    s.src_ctrl_pkt = TestSrcRTL(CtrlPktType, src_ctrl_pkt)
    s.src_query_pkt = TestSrcRTL(CtrlPktType, src_query_pkt)

    s.dut = DUT(DataType, PredicateType, CtrlPktType, CgraPayloadType,
                CtrlSignalType, NocPktType, ControllerIdType,
                # CGRA terminals on x/y. Assume in total 4, though this
                # test is for single CGRA.
                multi_cgra_rows, multi_cgra_columns,
                width, height, ctrl_mem_size,
                data_mem_size_global, data_mem_size_per_bank,
                num_banks_per_cgra, num_registers_per_reg_bank,
                ctrl_steps, ctrl_steps, FunctionUnit,
                FuList, topology, controller2addr_map, idTo2d_map,
                is_multi_cgra = False)

    cmp_fn = lambda a, b : a.payload.data == b.payload.data and a.payload.cmd == b.payload.cmd
    s.complete_signal_sink_out = TestSinkRTL(CtrlPktType, complete_signal_sink_out, cmp_fn = cmp_fn)

    # Connections
    s.complete_signal_sink_out.recv //= s.dut.send_to_cpu_pkt

    # complete_count_value = \
    #         sum(1 for pkt in complete_signal_sink_out \
    #             if pkt.payload.cmd == CMD_COMPLETE)
    complete_count_value = 1

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

def init_param(topology, FuList = [MemUnitRTL, AdderRTL],
               x_tiles = 2, y_tiles = 2, data_bitwidth = 32,
               test_name = 'default'):
  tile_ports = 4
  assert(topology == "Mesh" or topology == "KingMesh")
  if topology == "Mesh":
    tile_ports = 4
  elif topology == "KingMesh":
    tile_ports = 8
  num_tile_inports  = tile_ports
  num_tile_outports = tile_ports
  num_fu_inports = 4
  num_fu_outports = 2
  num_routing_outports = num_tile_outports + num_fu_inports
  ctrl_mem_size = 6
  # data_mem_size_global = 4096
  # data_mem_size_per_bank = 32
  # num_banks_per_cgra = 24
  data_mem_size_global = 128
  data_mem_size_per_bank = 16
  num_banks_per_cgra = 2
  num_cgra_columns = 1
  num_cgra_rows = 1
  num_cgras = num_cgra_columns * num_cgra_rows
  num_ctrl_operations = 64
  num_registers_per_reg_bank = 16
  TileInType = mk_bits(clog2(num_tile_inports + 1))
  FuInType = mk_bits(clog2(num_fu_inports + 1))
  FuOutType = mk_bits(clog2(num_fu_outports + 1))
  addr_nbits = clog2(data_mem_size_global)
  num_tiles = x_tiles * y_tiles
  per_cgra_data_size = int(data_mem_size_global / num_cgras)

  DUT = CgraRTL
  FunctionUnit = FlexibleFuRTL

  DataAddrType = mk_bits(addr_nbits)
  RegIdxType = mk_bits(clog2(num_registers_per_reg_bank))
  DataType = mk_data(data_bitwidth, 1)
  print("data_bitwidth:", data_bitwidth)
  print("DataType:", DataType.nbits)
  PredicateType = mk_predicate(1, 1)
  ControllerIdType = mk_bits(max(1, clog2(num_cgras)))
  cgra_id = 0
  controller2addr_map = {}
  # 0: [0,    1023]
  # 1: [1024, 2047]
  # 2: [2048, 3071]
  # 3: [3072, 4095]
  for i in range(num_cgras):
    controller2addr_map[i] = [i * per_cgra_data_size,
                              (i + 1) * per_cgra_data_size - 1]
  idTo2d_map = {0: [0, 0]}
  #{i: [i,0] for i in range(num_cgras)}

  cgra_id_nbits = clog2(num_cgras)
  addr_nbits = clog2(data_mem_size_global)
  predicate_nbits = 1

  CtrlType = mk_ctrl(num_fu_inports,
                     num_fu_outports,
                     num_tile_inports,
                     num_tile_outports,
                     num_registers_per_reg_bank)
  
  CtrlAddrType = mk_bits(clog2(ctrl_mem_size))

  CgraPayloadType = mk_cgra_payload(DataType,
                                    DataAddrType,
                                    CtrlType,
                                    CtrlAddrType)

  InterCgraPktType = mk_inter_cgra_pkt(num_cgra_columns,
                                       num_cgra_rows,
                                       num_tiles,
                                       CgraPayloadType)

  IntraCgraPktType = mk_intra_cgra_pkt(num_cgra_columns,
                                       num_cgra_rows,
                                       num_tiles,
                                       CgraPayloadType)
  print("IntraCgraPktType:", IntraCgraPktType.nbits)

  routing_xbar_code = [TileInType(0) for _ in range(num_routing_outports)]
  fu_in_code = [FuInType(0) for _ in range(num_fu_inports)]
  fu_in_code[0] = FuInType(1)
  fu_xbar_code = [FuOutType(0) for _ in range(num_routing_outports)]
  fu_xbar_code[num_tile_outports] = FuOutType(1)
  read_reg_from_code = [b1(0) for _ in range(num_fu_inports)]
  read_reg_from_code[0] = b1(1)
  read_reg_idx_code = [RegIdxType(0) for _ in range(num_fu_inports)]
  read_reg_idx_code[0] = RegIdxType(2)

  src_ctrl_pkt = []
  complete_signal_sink_out = []
  ctrl_steps = 0
  src_query_pkt = []
  if test_name == 'default':
      '''
      Each tile performs independent INC, without waiting for data from
      neighbours, instead, consuming the data inside their own register
      cluster/file (i.e., `read_reg_from`).
      '''

      # Usage example:
      # res = convertPktToCPUWidth(something[0][0], cpu_width=32)
      # print(res)
      # res = convertPktToCPUWidth(something[0][0], cpu_width=32)
      # print(res)

      # Bit_Placeholder = mk_bits(4)
      # my_pkt = something[0][0]
      # my_pkt.payload.cmd = Bit_Placeholder(8)
      # print("Something:", my_pkt)
      # print("CMD", my_pkt.payload.cmd)
      # print("Payload Bits", my_pkt.payload.nbits)
      # for payload_var_key in vars(my_pkt.payload):
      #   payload_var = getattr(my_pkt.payload, payload_var_key)
      #   if (hasattr(payload_var, '__dict__')):
      #     print(f"\t{payload_var_key}: {payload_var}")
      #   else:
      #     print(f"\t{payload_var_key}: {payload_var} ({payload_var.nbits})")
      # print()
      # print("DATA", my_pkt.payload.data.payload[0:3])
      # print("DATA_ADDR", my_pkt.payload.data_addr)
      # print("CTRL", my_pkt.payload.ctrl)

      activation_tensor_preload_data = [
          [
              # tile 6
              IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(1, 1), data_addr = 0)),
              IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(2, 1), data_addr = 1)),

              # tile 3
              IntraCgraPktType(1, 1, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(3, 1), data_addr = 2)),
              IntraCgraPktType(1, 1, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(4, 1), data_addr = 3)),
          ]
      ]
      src_opt_per_tile = [[
          # Pre-configure per-tile total config count. As we only have single `INC` operation,
          # we set it as one, which would trigger `COMPLETE` signal be sent back to CPU.
          IntraCgraPktType(0, # src
                           i, # dst
                           cgra_id, # src_cgra_id
                           cgra_id, # dst_cgra_id
                           idTo2d_map[cgra_id][0], # src_cgra_x
                           idTo2d_map[cgra_id][1], # src_cgra_y
                           idTo2d_map[cgra_id][0], # dst_cgra_x
                           idTo2d_map[cgra_id][1], # dst_cgra_y
                           0, # opaque
                           0, # vc_id
                           # Only execute one operation (i.e., store) is enough for this tile.
                           # If this is set more than 1, no `COMPLETE` signal would be set back to CPU.
                           CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(1))),

          IntraCgraPktType(0, # src
                           i, # dst
                           cgra_id, # src_cgra_id
                           cgra_id, # dst_cgra_id
                           idTo2d_map[cgra_id][0], # src_cgra_x
                           idTo2d_map[cgra_id][1], # src_cgra_y
                           idTo2d_map[cgra_id][0], # dst_cgra_x
                           idTo2d_map[cgra_id][1], # dst_cgra_y
                           0, # opaque
                           0, # vc_id
                           CgraPayloadType(CMD_CONFIG,
                                           ctrl = CtrlType(OPT_INC,
                                                           0,
                                                           fu_in_code,
                                                           routing_xbar_code,
                                                           fu_xbar_code,
                                                           read_reg_from = read_reg_from_code,
                                                           read_reg_idx = read_reg_idx_code))),

          IntraCgraPktType(0, # src
                           i, # dst
                           cgra_id, # src_cgra_id
                           cgra_id, # dst_cgra_id
                           idTo2d_map[cgra_id][0], # src_cgra_x
                           idTo2d_map[cgra_id][1], # src_cgra_y
                           idTo2d_map[cgra_id][0], # dst_cgra_x
                           idTo2d_map[cgra_id][1], # dst_cgra_y
                           0, # opaque
                           0, # vc_id
                           CgraPayloadType(CMD_LAUNCH,
                                           ctrl = CtrlType(OPT_NAH)))] for i in range(num_tiles)]

      # src_query_pkt = \
      #     [
      #         IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = 4)),
      #         IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = 5)),

      #         IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = 6)),
      #         IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = 7)),
      #     ]

      # vc_id needs to be 1 due to the message might traverse across the date line via ring.
      complete_signal_sink_out = \
          [IntraCgraPktType(i, # src
                            num_tiles, # dst
                            cgra_id, # src_cgra_id
                            cgra_id, # dst_cgra_id
                            idTo2d_map[cgra_id][0], # src_cgra_x
                            idTo2d_map[cgra_id][1], # src_cgra_y
                            idTo2d_map[cgra_id][0], # dst_cgra_x
                            idTo2d_map[cgra_id][1], # dst_cgra_y
                            0, # opaque
                            0, # vc_id
                            CgraPayloadType(CMD_COMPLETE)) for i in range(num_tiles)]
      # expected_mem_sink_out_pkt = \
      #     [
      #         # tile 1
      #         IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_RESPONSE, data = DataType(0x0e, 1), data_addr = 4)),
      #         IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_RESPONSE, data = DataType(0x14, 1), data_addr = 5)),

      #         # tile 2
      #         IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_RESPONSE, data = DataType(0x1e, 1), data_addr = 6)),
      #         IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_RESPONSE, data = DataType(0x2c, 1), data_addr = 7)),
      #     ]

      # for opt_per_tile in src_opt_per_tile:
      #   src_ctrl_pkt.extend(opt_per_tile)
      for opt_per_tile in src_opt_per_tile:
        src_ctrl_pkt.extend(opt_per_tile)
      # complete_signal_sink_out = convertPktToCPUWidth(complete_signal_sink_out[0], cpu_width=32)
      # expected_mem_sink_out_pkt = convertPktToCPUWidth(expected_mem_sink_out_pkt, cpu_width=32)
      # complete_signal_sink_out.extend(complete_signal_sink_out)
      # print("Full Original Pkt bits", src_opt_per_tile[0][0])
      # for i in range(4):
      #   print(f"src_ctrl_pkt[{i}] bits", src_ctrl_pkt[i])

      

      # src_query_pkt = convertPktToCPUWidth(src_query_pkt, cpu_width=32)
      ctrl_steps = ctrl_mem_size

  th = TestHarness(DUT, FunctionUnit, FuList, DataType, PredicateType,
                   IntraCgraPktType, CgraPayloadType, CtrlType, InterCgraPktType,
                   ControllerIdType, cgra_id, x_tiles, y_tiles,
                   ctrl_mem_size, data_mem_size_global,
                   data_mem_size_per_bank, num_banks_per_cgra,
                   num_registers_per_reg_bank,
                   src_ctrl_pkt, ctrl_steps, topology,
                   controller2addr_map, idTo2d_map, complete_signal_sink_out,
                   num_cgra_rows, num_cgra_columns,
                   src_query_pkt)
  return th

def test_homogeneous_2x2(cmdline_opts):
  topology = "Mesh"
  FuList = [AdderRTL,
            MulRTL,
            LogicRTL,
            ShifterRTL,
            PhiRTL,
            CompRTL,
            BranchRTL,
            MemUnitRTL,
            SelRTL,
            RetRTL,
           ]
  th = init_param(topology, FuList, x_tiles=2, y_tiles=2)

  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                       ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                        'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)
