"""
==========================================================================
CgraRTL_2x2_translate_test.py
==========================================================================
Translates a 2x2 MESH CgraRTL into Verilog for Chipyard integration.

Run with:
  cd VectorCGRA
  pytest cgra/translate/CgraRTL_2x2_translate_test.py -xvs --test-verilog --dump-vtb

Author : Auto-generated for CGRA-SoC integration
  Date : 2026
"""

from pymtl3 import *
from pymtl3.passes.backends.verilog import VerilogTranslationPass
from pymtl3.stdlib.test_utils import config_model_with_cmdline_opts

from ..CgraRTL import CgraRTL
from ...fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from ...fu.single.AdderRTL import AdderRTL
from ...fu.single.CompRTL import CompRTL
from ...fu.single.GrantRTL import GrantRTL
from ...fu.single.LogicRTL import LogicRTL
from ...fu.single.MemUnitRTL import MemUnitRTL
from ...fu.single.MulRTL import MulRTL
from ...fu.single.PhiRTL import PhiRTL
from ...fu.single.RetRTL import RetRTL
from ...fu.single.SelRTL import SelRTL
from ...fu.single.ShifterRTL import ShifterRTL
from ...lib.messages import *
from ...lib.opt_type import *
from ...lib.util.common import *


def test_translate_cgra_2x2(cmdline_opts):
    """Translate a 2x2 MESH CGRA to Verilog."""

    # ---- Parameters (matching CgraRTL_test.py init_param) ----
    topology = MESH
    x_tiles = 2
    y_tiles = 2
    data_bitwidth = 32

    tile_ports = 4  # MESH
    num_tile_inports = tile_ports
    num_tile_outports = tile_ports
    num_fu_inports = 4
    num_fu_outports = 2
    num_routing_outports = num_tile_outports + num_fu_inports

    ctrl_mem_size = 6
    data_mem_size_global = 128
    data_mem_size_per_bank = 16
    num_banks_per_cgra = 2
    num_cgra_columns = 4
    num_cgra_rows = 1
    num_cgras = num_cgra_columns * num_cgra_rows
    num_ctrl_operations = 64
    num_registers_per_reg_bank = 16

    num_tiles = x_tiles * y_tiles
    num_rd_tiles = x_tiles + y_tiles - 1
    per_cgra_data_size = int(data_mem_size_global / num_cgras)
    addr_nbits = clog2(data_mem_size_global)

    FunctionUnit = FlexibleFuRTL
    FuList = [AdderRTL, MulRTL, LogicRTL, ShifterRTL, PhiRTL,
              CompRTL, GrantRTL, MemUnitRTL, SelRTL, RetRTL]

    # ---- Type construction ----
    DataType = mk_data(data_bitwidth, 1)
    DataAddrType = mk_bits(addr_nbits)

    CtrlType = mk_ctrl(num_fu_inports, num_fu_outports,
                       num_tile_inports, num_tile_outports,
                       num_registers_per_reg_bank)
    CtrlAddrType = mk_bits(clog2(ctrl_mem_size))

    CgraPayloadType = mk_cgra_payload(DataType, DataAddrType,
                                       CtrlType, CtrlAddrType)

    # ---- Address map ----
    controller2addr_map = {}
    for i in range(num_cgras):
        controller2addr_map[i] = [i * per_cgra_data_size,
                                  (i + 1) * per_cgra_data_size - 1]
    idTo2d_map = {0: [0, 0], 1: [1, 0], 2: [2, 0], 3: [3, 0]}

    ctrl_steps = ctrl_mem_size

    # ---- Instantiate CGRA ----
    dut = CgraRTL(CgraPayloadType,
                  num_cgra_rows, num_cgra_columns,
                  x_tiles, y_tiles,
                  ctrl_mem_size, data_mem_size_global,
                  data_mem_size_per_bank, num_banks_per_cgra,
                  num_registers_per_reg_bank,
                  ctrl_steps, ctrl_steps,
                  False,  # mem_access_is_combinational
                  FunctionUnit, FuList, topology,
                  controller2addr_map, idTo2d_map,
                  is_multi_cgra=False)

    dut.set_metadata(VerilogTranslationPass.explicit_module_name,
                     'CgraRTL_2x2')

    # Only translate to Verilog, do NOT attempt verilator import
    dut.elaborate()
    dut.apply(VerilogTranslationPass())
