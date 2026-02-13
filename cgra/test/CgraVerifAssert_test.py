"""
==========================================================================
CgraVerifAssert_test.py
==========================================================================
Test cases for CGRA with crossbar-based data memory and ring-based control
memory of each tile.

Author : Yuchen Wang
  Date : Feb 13, 2026
"""

from pymtl3.passes.backends.verilog import (VerilogVerilatorImportPass)
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)

from ..CgraRTL import CgraRTL
from ...fu.double.SeqMulAdderRTL import SeqMulAdderRTL
from ...fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from ...fu.float.FpAddRTL import FpAddRTL
from ...fu.float.FpMulRTL import FpMulRTL
from ...fu.quadra.FourIncCmpNotGrantRTL import FourIncCmpNotGrantRTL
from ...fu.single.AdderRTL import AdderRTL
from ...fu.single.GrantRTL import GrantRTL
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
from ...fu.vector.VectorAllReduceRTL import VectorAllReduceRTL
from ...lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ...lib.messages import *
from ...lib.opt_type import *


#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):

  def construct(s, DUT, FunctionUnit, FuList,
                CtrlPktType,
                cgra_id, width, height,
                ctrl_mem_size, data_mem_size_global,
                data_mem_size_per_bank, num_banks_per_cgra,
                num_registers_per_reg_bank,
                src_ctrl_pkt, kCtrlCountPerIter, kTotalCtrlSteps,
                mem_access_is_combinational,
                has_ctrl_ring,
                controller2addr_map,
                idTo2d_map, complete_signal_sink_out,
                multi_cgra_rows, multi_cgra_columns, src_query_pkt):

    CgraPayloadType = CtrlPktType.get_field_type(kAttrPayload)
    DataType = CgraPayloadType.get_field_type(kAttrData)
    DataAddrType = mk_bits(clog2(data_mem_size_global))
    s.num_tiles = width * height
    s.src_ctrl_pkt = TestSrcRTL(CtrlPktType, src_ctrl_pkt)
    s.src_query_pkt = TestSrcRTL(CtrlPktType, src_query_pkt)

    s.dut = DUT(CgraPayloadType,
                # CGRA terminals on x/y. Assume in total 4, though this
                # test is for single CGRA.
                multi_cgra_rows, multi_cgra_columns,
                width, height, ctrl_mem_size,
                data_mem_size_global, data_mem_size_per_bank,
                num_banks_per_cgra, num_registers_per_reg_bank,
                kCtrlCountPerIter, kTotalCtrlSteps,
                mem_access_is_combinational,
                FunctionUnit, FuList, "KingMesh",
                controller2addr_map, idTo2d_map,
                is_multi_cgra = False,
                has_ctrl_ring = has_ctrl_ring)

    s.has_ctrl_ring = has_ctrl_ring

    cmp_fn = lambda a, b : a.payload.data == b.payload.data and a.payload.cmd == b.payload.cmd
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

    # Connects memory address upper and lower bound for each CGRA.
    s.dut.address_lower //= DataAddrType(controller2addr_map[cgra_id][0])
    s.dut.address_upper //= DataAddrType(controller2addr_map[cgra_id][1])

    for tile_col in range(width):
      s.dut.send_data_on_boundary_north[tile_col].rdy //= 0
      s.dut.recv_data_on_boundary_north[tile_col].val //= 0
      s.dut.recv_data_on_boundary_north[tile_col].msg //= DataType()

      s.dut.send_data_on_boundary_south[tile_col].rdy //= 0
      s.dut.recv_data_on_boundary_south[tile_col].val //= 0
      s.dut.recv_data_on_boundary_south[tile_col].msg //= DataType()

    for tile_row in range(height):
      s.dut.send_data_on_boundary_west[tile_row].rdy //= 0
      s.dut.recv_data_on_boundary_west[tile_row].val //= 0
      s.dut.recv_data_on_boundary_west[tile_row].msg //= DataType()

      s.dut.send_data_on_boundary_east[tile_row].rdy //= 0
      s.dut.recv_data_on_boundary_east[tile_row].val //= 0
      s.dut.recv_data_on_boundary_east[tile_row].msg //= DataType()

  def done(s):
    if not s.has_ctrl_ring:
      return True
    return (s.src_ctrl_pkt.done() and s.src_query_pkt.done()
            and s.complete_signal_sink_out.done())

  def line_trace(s):
    return s.dut.line_trace()

# Common configurations/setups.
FuList = [AdderRTL,
          MulRTL,
          LogicRTL,
          ShifterRTL,
          PhiRTL,
          CompRTL,
          GrantRTL,
          MemUnitRTL,
          SelRTL,
          RetRTL,
          FourIncCmpNotGrantRTL,
         ]
x_tiles = 2
y_tiles = 2
data_bitwidth = 32
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
num_cgra_columns = 4
num_cgra_rows = 1
num_cgras = num_cgra_columns * num_cgra_rows
num_ctrl_operations = 64
num_registers_per_reg_bank = 16
TileInType = mk_bits(clog2(num_tile_inports + 1))
FuInType = mk_bits(clog2(num_fu_inports + 1))
FuOutType = mk_bits(clog2(num_fu_outports + 1))
addr_nbits = clog2(data_mem_size_global)
num_tiles = x_tiles * y_tiles
num_rd_tiles = x_tiles + y_tiles - 1
per_cgra_data_size = int(data_mem_size_global / num_cgras)

DUT = CgraRTL
FunctionUnit = FlexibleFuRTL

DataAddrType = mk_bits(addr_nbits)
RegIdxType = mk_bits(clog2(num_registers_per_reg_bank))
DataType = mk_data(data_bitwidth, 1)
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
idTo2d_map = {
        0: [0, 0],
        1: [1, 0],
        2: [2, 0],
        3: [3, 0],
}

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
                                      num_rd_tiles,
                                      CgraPayloadType)

IntraCgraPktType = mk_intra_cgra_pkt(num_cgra_columns,
                                      num_cgra_rows,
                                      num_tiles,
                                      CgraPayloadType)

routing_xbar_code = [TileInType(0) for _ in range(num_routing_outports)]
fu_xbar_code = [FuOutType(0) for _ in range(num_routing_outports)]
write_reg_from_code = [b2(0) for _ in range(num_fu_inports)]
# 2 indicates the FU xbar port (instead of const queue or routing xbar port).
write_reg_from_code[0] = b2(2)
read_reg_from_code = [b1(0) for _ in range(num_fu_inports)]
read_reg_from_code[0] = b1(1)
read_reg_idx_code = [RegIdxType(0) for _ in range(num_fu_inports)]

fu_in_code = [FuInType(x + 1) for x in range(num_fu_inports)]

preload_data = [
    [
        #response
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(1, 1), data_addr = 0)),
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(1, 1), data_addr = 1)),
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(1, 1), data_addr = 2)),
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(1, 1), data_addr = 3)),
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(1, 1), data_addr = 4)),
        #req
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(1, 1), data_addr = 5)),
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(0, 1), data_addr = 6)),
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(1, 1), data_addr = 7)),
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(1, 1), data_addr = 8)),
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(0, 1), data_addr = 9)),
        #ack
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(0, 1), data_addr = 10)),
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(1, 1), data_addr = 11)),
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(1, 1), data_addr = 12)),
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(0, 1), data_addr = 13)),
        IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_STORE_REQUEST, data = DataType(0, 1), data_addr = 14)),
    ]
]

# Assertation1 demo.
'''
assert property (@(posedge clk) req |-> ##2 ack); 

int req[N];
int ack[N];
int assertation = 1;

for(int i=0; i<N; i++){
    if(req[i]==1 && ack[i+2]==0)
        assertation = 0;
}

// assume ack[i+2] begin from data_mem[10]
// N = 5
// data_mem = [1,1,1,1,1,  1,0,1,1,0,  1,0,1,0,1] 
// first 5 assertation_flag, next 5 req, last 5 ack
// assertation_flag = 1 -> pass
// assertation_flag = 0 -> fail
// store_addr_base = 0
// req_addr_base = 5
// ack_addr_base = 10
// 0(phi_const)  int i = 0


// response should be data_mem[0:4] = [0,1,1,0,1]
// return value should be i (i = 4 in the end)
'''

def sim_fir_return(cmdline_opts, mem_access_is_combinational, has_ctrl_ring):
  src_ctrl_pkt = []
  complete_signal_sink_out = []
  src_query_pkt = []

  # kernel specific parameters.
  kStoreAddress = 0 
  kReqAddress = 5
  kAckAddress = 10
  kLoopLowerBound = 0
  kLoopIncrement = 1
  kLoopUpperBound = 5
  kCtrlCountPerIter = 5
  kCmpOne = 1
  kCmpZero = 0
  # Though kTotalCtrlSteps is way more than required loop iteration count,
  # the stored result should still be correct thanks to the grant predicate.
  kTotalCtrlSteps = kCtrlCountPerIter * \
                    (kLoopUpperBound - kLoopLowerBound) + \
                    1000
  kExpectedOutput = 4

  # Corresponding DFG:
  # After fusion:
  #
  #            ------0(phi_const) <-----------┐
  #           /       |     |  |   \          |
  #          /        |     |  |    \         |
  #     1(+,ld)    2(+,ld)  |  |     8(+,cmp,not,grant_pred)
  #         |         |     |  |              |
  #         |         |    /   |              |
  #     3(cmp)     4(cmp) /    |------ 9(grant_predicate)
  #          \      /    /                    |
  #           \    /    /                     |
  #           5(and)   /                   10(ret)
  #             |     /       
  #           6(not) /        
  #             |   /   
  #           7(str)  
  #                        
  # Corresponding mapping (II = 5):
  '''
       ↑ Y
       |
  (0,1)|  🔳   🔳
       |
  (0,0)|  🔳   🔳
       +-----------→ X
        (1,0) (2,0)

  =============================
  cycle 0:
  [  7(str)   ←  0(phi_const)  ]
              ↙       ↺
  [    🔳            🔳       ]
                     
  =============================
  cycle 1:
  [  1(+ ld)  ->   8(fused)    ]
       ↺      ↘      ↓ ↺
  [  2(+ ld)          🔳      ]
       ↺              
  =============================
  cycle 2:
  [    🔳          3(cmp)     ]
                    ↑ ↓
  [  4(cmp)  -> 9(grant_pred)  ]

  =============================
  cycle 3:
  [    🔳          10(ret)     ]

  [    🔳           5(and)     ]
                      ↺
  =============================
  cycle 4:
  [    🔳            🔳       ]
               ↖
  [    🔳           6(not)     ]

  =============================
  '''

  src_opt_pkt = [
      # tile 0
      [
          # Const for ADD_CONST_LD.
          IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONST, data = DataType(kAckAddress, 1))),

          # Const for CMP.
          IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONST, data = DataType(kCmpZero, 1))),

          # Pre-configure per-tile config count per iter.
          IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter, 1))),

          # Pre-configure per-tile total config count.
          IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps, 1))),

          # NAH.
          IntraCgraPktType(0, 0,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                     ctrl = CtrlType(OPT_NAH,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

          # ADD_CONST_LD.
          IntraCgraPktType(0, 0,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                     ctrl = CtrlType(OPT_ADD_CONST_LD,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(6), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                      write_reg_from = [b2(2), b2(0), b2(0), b2(0)]))),
          
          # EQ_CONST.
          IntraCgraPktType(0, 0,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                     ctrl = CtrlType(OPT_EQ_CONST,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                      read_reg_from = [b1(1), b1(0), b1(0), b1(0)]))),  
          
          # NAH.
          IntraCgraPktType(0, 0,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 3,
                                                     ctrl = CtrlType(OPT_NAH,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),
          
          # NAH.
          IntraCgraPktType(0, 0,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 4,
                                                     ctrl = CtrlType(OPT_NAH,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

          # Launch the tile.
          IntraCgraPktType(0, 0, payload = CgraPayloadType(CMD_LAUNCH))
      ],

      # tile 1
      [
          # Pre-configure per-tile config count per iter.
          IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter, 1))),

          # Pre-configure per-tile total config count.
          IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps, 1))),

          # NAH.
          IntraCgraPktType(0, 1,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                     ctrl = CtrlType(OPT_NAH,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),
          
          # NAH.
          IntraCgraPktType(0, 1,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                     ctrl = CtrlType(OPT_NAH,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

          # GRT_PRED.
          IntraCgraPktType(0, 1,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                     ctrl = CtrlType(OPT_GRT_PRED,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(5), TileInType(1), TileInType(0), TileInType(0)],
                                                                     [FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

          # AND.
          IntraCgraPktType(0, 1,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 3,
                                                     ctrl = CtrlType(OPT_AND,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(1), TileInType(3), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                     write_reg_from = [b2(2), b2(0), b2(0), b2(0)]))),   

          # NOT.
          IntraCgraPktType(0, 1,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 4,
                                                     ctrl = CtrlType(OPT_NOT,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)], 
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                     read_reg_from = [b1(1), b1(0), b1(0), b1(0)]))),                                                                                                                          

          # Launch the tile.
          IntraCgraPktType(0, 1, payload = CgraPayloadType(CMD_LAUNCH))
      ],

      # tile 2
      [
          # Const for ADD_CONST_LD.
          IntraCgraPktType(0, 2, payload = CgraPayloadType(CMD_CONST, data = DataType(kReqAddress, 1))),

          # Pre-configure per-tile config count per iter.
          IntraCgraPktType(0, 2, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter, 1))),

          # Pre-configure per-tile total config count.
          IntraCgraPktType(0, 2, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps, 1))),

          # STR.
          IntraCgraPktType(0, 2,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                     ctrl = CtrlType(OPT_STR,
                                                                     #reognized according to fu inports
                                                                     [FuInType(3), FuInType(2), FuInType(0), FuInType(0)],
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(7), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                      read_reg_from = [b1(0), b1(0), b1(1), b1(0)]))),

          # ADD_CONST_LD.
          IntraCgraPktType(0, 2,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                     ctrl = CtrlType(OPT_ADD_CONST_LD,
                                                                     fu_in_code,
                                                                     #send input to SE without fu; send input to fu; save input to reg;
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(4), TileInType(0),
                                                                      TileInType(4), TileInType(0), TileInType(4), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                      write_reg_from = [b2(0), b2(0), b2(1), b2(0)]))),
                                                                      #one indicates from routing xbar, other than const queue and fu xbar

          # NAH.
          IntraCgraPktType(0, 2,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                     ctrl = CtrlType(OPT_NAH,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

          # NAH.
          IntraCgraPktType(0, 2,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 3,
                                                     ctrl = CtrlType(OPT_NAH,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

          # NAH.
          IntraCgraPktType(0, 2,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 4,
                                                     ctrl = CtrlType(OPT_NAH,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

          IntraCgraPktType(0, 2,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU, ctrl_addr = 0,
                                                     data = DataType(1, 1))),
                                                     #DataType first 1 means skip one cycle
          IntraCgraPktType(0, 2,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR, ctrl_addr = 0,
                                                     ctrl = CtrlType(routing_xbar_outport = [
                                                        TileInType(7), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                        TileInType(0), TileInType(0), TileInType(0), TileInType(0)]),
                                                     data = DataType(1, 1))),
                                                     #ignore direction number where the data comes from
          IntraCgraPktType(0, 2,
                           payload = CgraPayloadType(CMD_CONFIG_PROLOGUE_FU_CROSSBAR, ctrl_addr = 0,
                                                     ctrl = CtrlType(fu_xbar_outport = [
                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                        FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]),
                                                     data = DataType(1, 1))),

          # Launch the tile.
          IntraCgraPktType(0, 2, payload = CgraPayloadType(CMD_LAUNCH))
      ],

      # tile 3
      [
          # Const for PHI_CONST.
          IntraCgraPktType(0, 3, payload = CgraPayloadType(CMD_CONST, data = DataType(kLoopLowerBound, 1))),

          # Const for CMP.
          IntraCgraPktType(0, 3, payload = CgraPayloadType(CMD_CONST, data = DataType(kLoopUpperBound, 1))),

          # Const for CMP.
          IntraCgraPktType(0, 3, payload = CgraPayloadType(CMD_CONST, data = DataType(kCmpOne, 1))),

          # Pre-configure per-tile config count per iter.
          IntraCgraPktType(0, 3, payload = CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER, data = DataType(kCtrlCountPerIter, 1))),

          # Pre-configure per-tile total config count.
          IntraCgraPktType(0, 3, payload = CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT, data = DataType(kTotalCtrlSteps, 1))),

          # PHI_CONST.
          IntraCgraPktType(0, 3,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 0,
                                                     ctrl = CtrlType(OPT_PHI_CONST,
                                                                     # The first 2 indicates the first operand is from the second inport,
                                                                     # which is actually from the second register cluster rather than the
                                                                     # inport channel, indicated by the `read_reg_from_code`.
                                                                     [FuInType(2), FuInType(0), FuInType(0), FuInType(0)],
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(1),
                                                                      FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0)],
                                                                     write_reg_from = [b2(2), b2(0), b2(0), b2(0)],
                                                                     read_reg_from = [b1(0), b1(1), b1(0), b1(0)]))),

          # INC_NE_CONST_NOT_GRT.
          IntraCgraPktType(0, 3,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 1,
                                                     ctrl = CtrlType(OPT_INC_NE_CONST_NOT_GRT,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     # Sends two outputs to south and self reg, respectively.
                                                                     [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(2), FuOutType(0), FuOutType(0)],
                                                                     # 2 indicates the FU xbar port (instead of const queue(3) or routing xbar port(1)).
                                                                     write_reg_from = [b2(0), b2(2), b2(0), b2(0)],
                                                                     read_reg_from = [b1(1), b1(0), b1(0), b1(0)]))),
          
          # EQ_CONST.
          IntraCgraPktType(0, 3,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 2,
                                                     ctrl = CtrlType(OPT_EQ_CONST,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(3), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),    

          # RET.
          IntraCgraPktType(0, 3,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 3,
                                                     ctrl = CtrlType(OPT_RET,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(2), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),

          # NAH.
          IntraCgraPktType(0, 3,
                           payload = CgraPayloadType(CMD_CONFIG, ctrl_addr = 4,
                                                     ctrl = CtrlType(OPT_NAH,
                                                                     fu_in_code,
                                                                     [TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0), TileInType(0),
                                                                      TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                                                                     [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                                                                      FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)]))),                                                            

          # Launch the tile.
          IntraCgraPktType(0, 3, payload = CgraPayloadType(CMD_LAUNCH))
      ],
  ]

  src_query_pkt = \
      [
          IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = kStoreAddress)),
          IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = kStoreAddress+1)),
          IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = kStoreAddress+2)),
          IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = kStoreAddress+3)),
          IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_REQUEST, data_addr = kStoreAddress+4)),
      ]

  expected_complete_sink_out_pkg = \
      [
          IntraCgraPktType(payload = CgraPayloadType(CMD_COMPLETE, DataType(kExpectedOutput, 1, 0, 0))) for _ in range(1)
      ]
  expected_mem_sink_out_pkt = \
      [
          IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_RESPONSE, data = DataType(0, 1), data_addr = 0)),
          IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_RESPONSE, data = DataType(1, 1), data_addr = 1)),
          IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_RESPONSE, data = DataType(1, 1), data_addr = 2)),
          IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_RESPONSE, data = DataType(0, 1), data_addr = 3)),
          IntraCgraPktType(payload = CgraPayloadType(CMD_LOAD_RESPONSE, data = DataType(1, 1), data_addr = 4)),
      ]

  for activation in preload_data:
      src_ctrl_pkt.extend(activation)
  for src_opt in src_opt_pkt:
      src_ctrl_pkt.extend(src_opt)

  complete_signal_sink_out.extend(expected_complete_sink_out_pkg)
  complete_signal_sink_out.extend(expected_mem_sink_out_pkt)

  th = TestHarness(DUT, FunctionUnit, FuList,
                   IntraCgraPktType,
                   cgra_id, x_tiles, y_tiles,
                   ctrl_mem_size, data_mem_size_global,
                   data_mem_size_per_bank, num_banks_per_cgra,
                   num_registers_per_reg_bank,
                   src_ctrl_pkt, kCtrlCountPerIter, kTotalCtrlSteps,
                   mem_access_is_combinational,
                   has_ctrl_ring,
                   controller2addr_map, idTo2d_map, complete_signal_sink_out,
                   num_cgra_rows, num_cgra_columns,
                   src_query_pkt)

  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                       ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                        'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)

def test_homogeneous_2x2_fir_combinational_mem_access_return(cmdline_opts):
  sim_fir_return(cmdline_opts, mem_access_is_combinational = True, has_ctrl_ring = True)

# def test_homogeneous_2x2_fir_non_combinational_mem_access_return(cmdline_opts):
#   sim_fir_return(cmdline_opts, mem_access_is_combinational = False, has_ctrl_ring = True)

# def test_homogeneous_2x2_fir_non_combinational_mem_access_no_ctrl_ring(cmdline_opts):
#   sim_fir_return(cmdline_opts, mem_access_is_combinational = False, has_ctrl_ring = False)
