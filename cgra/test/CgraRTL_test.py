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
    CpuCtrlPktType = mk_bits(32)
    s.src_ctrl_pkt = TestSrcRTL(CpuCtrlPktType, src_ctrl_pkt)
    s.src_query_pkt = TestSrcRTL(CpuCtrlPktType, src_query_pkt)

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
    s.complete_signal_sink_out = TestSinkRTL(CpuCtrlPktType, complete_signal_sink_out, cmp_fn = cmp_fn)

    # Connections
    s.dut.cgra_id //= cgra_id
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

    # Connects memory address upper and lower bound for each CGRA.
    s.dut.address_lower //= DataAddrType(controller2addr_map[cgra_id][0])
    s.dut.address_upper //= DataAddrType(controller2addr_map[cgra_id][1])

    # for tile_col in range(width):
    #   s.dut.send_data_on_boundary_north[tile_col].rdy //= 0
    #   s.dut.recv_data_on_boundary_north[tile_col].val //= 0
    #   s.dut.recv_data_on_boundary_north[tile_col].msg //= DataType()

    #   s.dut.send_data_on_boundary_south[tile_col].rdy //= 0
    #   s.dut.recv_data_on_boundary_south[tile_col].val //= 0
    #   s.dut.recv_data_on_boundary_south[tile_col].msg //= DataType()

    # for tile_row in range(height):
    #   s.dut.send_data_on_boundary_west[tile_row].rdy //= 0
    #   s.dut.recv_data_on_boundary_west[tile_row].val //= 0
    #   s.dut.recv_data_on_boundary_west[tile_row].msg //= DataType()

    #   s.dut.send_data_on_boundary_east[tile_row].rdy //= 0
    #   s.dut.recv_data_on_boundary_east[tile_row].val //= 0
    #   s.dut.recv_data_on_boundary_east[tile_row].msg //= DataType()

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

      src_query_pkt = \
          [
              IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = 4)),
              IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = 5)),

              IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = 6)),
              IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = 7)),
          ]

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
      expected_mem_sink_out_pkt = \
          [
              # tile 1
              IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_RESPONSE, data = DataType(0x0e, 1), data_addr = 4)),
              IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_RESPONSE, data = DataType(0x14, 1), data_addr = 5)),

              # tile 2
              IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_RESPONSE, data = DataType(0x1e, 1), data_addr = 6)),
              IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_RESPONSE, data = DataType(0x2c, 1), data_addr = 7)),
          ]

      # for opt_per_tile in src_opt_per_tile:
      #   src_ctrl_pkt.extend(opt_per_tile)
      for opt_per_tile in src_opt_per_tile:
        for opt_pkt in opt_per_tile:
          res = convertPktToCPUWidth(opt_pkt, cpu_width=32)
          src_ctrl_pkt.extend(res)
      complete_signal_sink_out = convertPktToCPUWidth(complete_signal_sink_out[0], cpu_width=32)
      expected_mem_sink_out_pkt = convertPktToCPUWidth(expected_mem_sink_out_pkt, cpu_width=32)
      complete_signal_sink_out.extend(expected_mem_sink_out_pkt)
      # print("Full Original Pkt bits", src_opt_per_tile[0][0])
      # for i in range(4):
      #   print(f"src_ctrl_pkt[{i}] bits", src_ctrl_pkt[i])

      def printBinary(bit_obj):
        int_val = int(bit_obj.hex(), 16)
        binary_str = bin(int_val)[2:]  # Remove '0b' prefix
        
        # Pad with leading zeros to match the bit width
        num_bits = bit_obj.nbits
        binary_str = binary_str.zfill(num_bits)
        
        return binary_str

      def printHex(binary_str, pad_to_nbits=32):
        int_val = int(binary_str, 2)
    
        # Calculate how many hex digits we need
        num_bits = len(binary_str)
        hex_digits_needed = (num_bits + 3) // 4
        hex_digits_needed = (hex_digits_needed + 7) // 8
        
        # Format with proper padding
        print("hex func", hex(int_val))
        print(f"{int_val:x}")
        hex_str = f"{int_val:0{hex_digits_needed}x}"
        print(hex_str)
        return hex_str
      
      binary_str = ""
      binary_bit_length = 0
      
      def bitObjToString(pkt_item):
        nonlocal binary_str
        nonlocal binary_bit_length
        if not hasattr(pkt_item, '__dict__'):
            if hasattr(pkt_item, 'nbits'):
                binary_str += printBinary(pkt_item)
                binary_bit_length += pkt_item.nbits
            return
        
        # Process each attribute in the packet
        for attr_name in vars(pkt_item):
            attr_value = getattr(pkt_item, attr_name)
            
            # Recursively process nested packet structures
            if hasattr(attr_value, '__dict__'):
                bitObjToString(attr_value)
            
            # Handle lists of packet items
            elif isinstance(attr_value, list):
                for item in attr_value:
                    bitObjToString(item)
            
            # Handle actual data fields
            else:
                if hasattr(attr_value, 'nbits'):
                    binary_str += printBinary(attr_value)
                    binary_bit_length += attr_value.nbits

      bitObjToString(src_opt_per_tile[0][0])
      
      print("Full Original Pkt bits:", binary_str)
      print("Full Original Pkt bits from str:", binary_bit_length)
      print("Full Original Pkt bits w/ printHex:", printHex(binary_str))
      print("src_ctrl_pkt bits:", [printHex(printBinary(src_ctrl_pkt[0]))])
      print("src_ctrl_pkt bits:", [src_ctrl_pkt[0]])

      src_query_pkt = convertPktToCPUWidth(src_query_pkt, cpu_width=32)
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
  th = init_param(topology, FuList)

  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                       ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                        'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)
