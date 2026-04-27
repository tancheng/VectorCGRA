"""
==========================================================================
CgraRTL_2x2_translate.py
==========================================================================
Standalone script to translate a 2x2 MESH CgraRTL into Verilog.
Only performs translation (no verilator import needed).

Run with:
  cd VectorCGRA
  python -m cgra.translate.CgraRTL_2x2_translate

Author : Auto-generated for CGRA-SoC integration
  Date : 2026
"""

import sys
import os

# Add VectorCGRA root to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from pymtl3 import *
from pymtl3.passes.backends.verilog import VerilogTranslationPass

from cgra.CgraRTL import CgraRTL
from fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from fu.single.AdderRTL import AdderRTL
from fu.single.CompRTL import CompRTL
from fu.single.GrantRTL import GrantRTL
from fu.single.LogicRTL import LogicRTL
from fu.single.MemUnitRTL import MemUnitRTL
from fu.single.MulRTL import MulRTL
from fu.single.PhiRTL import PhiRTL
from fu.single.RetRTL import RetRTL
from fu.single.SelRTL import SelRTL
from fu.single.ShifterRTL import ShifterRTL
from lib.messages import *
from lib.opt_type import *
from lib.util.common import *


def main():
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

    ctrl_mem_size = 6
    data_mem_size_global = 128
    data_mem_size_per_bank = 16
    num_banks_per_cgra = 2
    num_cgra_columns = 4
    num_cgra_rows = 1
    num_cgras = num_cgra_columns * num_cgra_rows
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

    # Only translate, do NOT import (no verilator needed)
    dut.elaborate()
    dut.apply(VerilogTranslationPass())

    print("Translation complete!")
    print(f"Output directory: {os.getcwd()}")


if __name__ == '__main__':
    main()
