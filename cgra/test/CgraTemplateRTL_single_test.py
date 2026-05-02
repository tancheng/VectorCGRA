"""
==========================================================================
CgraTemplateRTL_single_test.py
==========================================================================
Single-CGRA RTL translation entry derived from CgraTemplateRTL_test.py.

This file intentionally does not run simulation. It reads the architecture
YAML and a small SoC/interface YAML, elaborates CgraTemplateRTL with
is_multi_cgra=False, and emits a PyMTL3-translated SystemVerilog file.
"""

from __future__ import annotations

import argparse
import glob
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[3]
VECTOR_ROOT = REPO_ROOT / "VectorCGRA"
if str(REPO_ROOT) not in sys.path:
  sys.path.insert(0, str(REPO_ROOT))
python_tag = f"python{sys.version_info.major}.{sys.version_info.minor}"
for site_packages in glob.glob(str(REPO_ROOT / ".venv" / "lib" / "python*" / "site-packages")):
  if site_packages not in sys.path:
    sys.path.insert(0, site_packages)
for site_packages in (
    str(Path(sys.prefix) / "lib" / python_tag / "site-packages"),
    str(Path(sys.base_prefix) / "lib" / python_tag / "site-packages"),
):
  if site_packages not in sys.path:
    sys.path.append(site_packages)

import yaml
from pymtl3 import *
from pymtl3.passes.backends.verilog import VerilogPlaceholderPass, VerilogTranslationPass

from VectorCGRA.cgra.CgraTemplateRTL import CgraTemplateRTL
from VectorCGRA.fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from VectorCGRA.lib.messages import mk_cgra_payload, mk_ctrl, mk_data
from VectorCGRA.multi_cgra.arch_parser.ArchParser import ArchParser


TOP_MODULE = "CgraTemplateRTL_single"
RTL_FILENAME = f"{TOP_MODULE}__pickled.v"


@dataclass(frozen=True)
class SocConfig:
  num_tile_inports: int
  num_tile_outports: int
  num_fu_inports: int
  num_fu_outports: int
  data_nbits: int
  predicate_nbits: int
  data_mem_size_global: int
  data_mem_size_per_bank: int
  num_banks_per_cgra: int
  num_registers_per_reg_bank: int
  mem_access_is_combinational: bool
  ctrl_count_per_iter: int | None
  total_ctrl_steps: int | None


def resolve_input_path(path: str) -> Path:
  candidate = Path(path)
  if candidate.is_absolute():
    return candidate
  for base in (Path.cwd(), REPO_ROOT, VECTOR_ROOT, Path(__file__).resolve().parent):
    resolved = base / candidate
    if resolved.exists():
      return resolved
  return Path.cwd() / candidate


def require_section(data: Mapping[str, Any], name: str) -> Mapping[str, Any]:
  section = data.get(name)
  if not isinstance(section, Mapping):
    raise ValueError(f"soc yaml is missing mapping section '{name}'")
  return section


def require_int(section: Mapping[str, Any], name: str, section_name: str) -> int:
  value = section.get(name)
  if not isinstance(value, int) or isinstance(value, bool):
    raise ValueError(f"soc yaml field '{section_name}.{name}' must be an integer")
  return value


def require_bool(section: Mapping[str, Any], name: str, section_name: str) -> bool:
  value = section.get(name)
  if not isinstance(value, bool):
    raise ValueError(f"soc yaml field '{section_name}.{name}' must be a boolean")
  return value


def optional_int(section: Mapping[str, Any], *names: str, section_name: str) -> int | None:
  present = [name for name in names if name in section]
  if not present:
    return None
  if len(present) > 1:
    raise ValueError(f"soc yaml section '{section_name}' should only set one of: {', '.join(names)}")
  return require_int(section, present[0], section_name)


def load_soc_config(path: Path) -> SocConfig:
  with path.open("r", encoding="utf-8") as stream:
    data = yaml.safe_load(stream)
  if not isinstance(data, Mapping):
    raise ValueError("soc yaml must contain a top-level mapping")

  interface = require_section(data, "interface")
  memory = require_section(data, "memory")
  execution = data.get("execution", {})
  if execution is None:
    execution = {}
  if not isinstance(execution, Mapping):
    raise ValueError("soc yaml section 'execution' must be a mapping when present")

  cfg = SocConfig(
    num_tile_inports=require_int(interface, "num_tile_inports", "interface"),
    num_tile_outports=require_int(interface, "num_tile_outports", "interface"),
    num_fu_inports=require_int(interface, "num_fu_inports", "interface"),
    num_fu_outports=require_int(interface, "num_fu_outports", "interface"),
    data_nbits=require_int(interface, "data_nbits", "interface"),
    predicate_nbits=require_int(interface, "predicate_nbits", "interface"),
    data_mem_size_global=require_int(memory, "data_mem_size_global", "memory"),
    data_mem_size_per_bank=require_int(memory, "data_mem_size_per_bank", "memory"),
    num_banks_per_cgra=require_int(memory, "num_banks_per_cgra", "memory"),
    num_registers_per_reg_bank=require_int(memory, "num_registers_per_reg_bank", "memory"),
    mem_access_is_combinational=require_bool(memory, "mem_access_is_combinational", "memory"),
    ctrl_count_per_iter=optional_int(execution, "ctrl_count_per_iter", "num_ctrl", section_name="execution"),
    total_ctrl_steps=optional_int(execution, "total_ctrl_steps", "total_steps", section_name="execution"),
  )

  if cfg.data_mem_size_per_bank * cfg.num_banks_per_cgra > cfg.data_mem_size_global:
    raise ValueError("data_mem_size_per_bank * num_banks_per_cgra exceeds data_mem_size_global")
  return cfg


def build_single_cgra(arch_yaml: Path, soc_cfg: SocConfig) -> Component:
  arch_parser = ArchParser(str(arch_yaml))
  if arch_parser.cgra_rows != 1 or arch_parser.cgra_columns != 1:
    raise ValueError("single-CGRA translation expects arch yaml multi_cgra_defaults to be 1 x 1")

  param_cgra = arch_parser.get_simplest_cgra_param()
  ctrl_mem_size = param_cgra.configMemSize
  ctrl_count_per_iter = soc_cfg.ctrl_count_per_iter if soc_cfg.ctrl_count_per_iter is not None else ctrl_mem_size
  total_ctrl_steps = soc_cfg.total_ctrl_steps if soc_cfg.total_ctrl_steps is not None else ctrl_mem_size
  num_tiles = len(param_cgra.getValidTiles())

  DataType = mk_data(soc_cfg.data_nbits, soc_cfg.predicate_nbits)
  DataAddrType = mk_bits(clog2(soc_cfg.data_mem_size_global))
  CtrlType = mk_ctrl(
    soc_cfg.num_fu_inports,
    soc_cfg.num_fu_outports,
    soc_cfg.num_tile_inports,
    soc_cfg.num_tile_outports,
    soc_cfg.num_registers_per_reg_bank,
  )
  CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
  CgraPayloadType = mk_cgra_payload(DataType, DataAddrType, CtrlType, CtrlAddrType)

  controller2addr_map = {0: (0, soc_cfg.data_mem_size_global - 1)}
  idTo2d_map = {0: (0, 0)}

  print(f"arch_yaml={arch_yaml}")
  print(f"single_cgra_tiles={num_tiles} rows={param_cgra.rows} columns={param_cgra.columns}")
  print(
    f"ctrl_mem_size={ctrl_mem_size} ctrl_count_per_iter={ctrl_count_per_iter} "
    f"total_ctrl_steps={total_ctrl_steps} data_mem_size_global={soc_cfg.data_mem_size_global}"
  )

  return CgraTemplateRTL(
    CgraPayloadType,
    1,
    1,
    param_cgra.rows,
    param_cgra.columns,
    ctrl_mem_size,
    soc_cfg.data_mem_size_global,
    soc_cfg.data_mem_size_per_bank,
    soc_cfg.num_banks_per_cgra,
    soc_cfg.num_registers_per_reg_bank,
    ctrl_count_per_iter,
    total_ctrl_steps,
    soc_cfg.mem_access_is_combinational,
    FlexibleFuRTL,
    [],
    param_cgra.getValidTiles(),
    param_cgra.getValidLinks(),
    param_cgra.dataSPM,
    controller2addr_map,
    idTo2d_map,
    is_multi_cgra=False,
    cgra_id=0,
  )


def translate_single_cgra(arch_yaml: Path, soc_yaml: Path) -> Path:
  soc_cfg = load_soc_config(soc_yaml)
  dut = build_single_cgra(arch_yaml, soc_cfg)
  dut.set_metadata(VerilogTranslationPass.enable, True)
  dut.set_metadata(VerilogTranslationPass.explicit_module_name, TOP_MODULE)
  dut.set_metadata(VerilogTranslationPass.explicit_file_name, RTL_FILENAME)

  old_cwd = Path.cwd()
  try:
    os.chdir(VECTOR_ROOT)
    dut.elaborate()
    dut.apply(VerilogPlaceholderPass())
    dut.apply(VerilogTranslationPass())
  finally:
    os.chdir(old_cwd)

  rtl_path = VECTOR_ROOT / RTL_FILENAME
  print(f"rtl_out={rtl_path}")
  return rtl_path


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description="Translate a YAML-configured single CgraTemplateRTL.")
  parser.add_argument("--arch-yaml", required=True, help="CGRA architecture YAML")
  parser.add_argument("--soc-yaml", required=True, help="SoC/interface YAML")
  return parser.parse_args()


def main() -> int:
  args = parse_args()
  arch_yaml = resolve_input_path(args.arch_yaml)
  soc_yaml = resolve_input_path(args.soc_yaml)
  if not arch_yaml.exists():
    raise FileNotFoundError(f"arch yaml not found: {arch_yaml}")
  if not soc_yaml.exists():
    raise FileNotFoundError(f"soc yaml not found: {soc_yaml}")

  translate_single_cgra(arch_yaml, soc_yaml)
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
