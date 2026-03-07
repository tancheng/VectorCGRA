from pathlib import Path
import re

from pymtl3.passes.backends.verilog.import_.VerilogVerilatorImportPass import (
    VerilogVerilatorImportPass,
)


def _patched_gen_ref_read(self, lhs, rhs, nbits, equal="="):
    if nbits <= 64:
        mask = hex((1 << nbits) - 1) if nbits else "0x0"
        return ["", f"{lhs} {equal} ({rhs}[0] & {mask})"]
    ret = ["", f"x = {rhs}"]
    item_bitwidth = 32
    num_assigns = (nbits - 1) // item_bitwidth + 1
    for idx in range(num_assigns):
        lo = item_bitwidth * idx
        hi = lo + item_bitwidth if lo + item_bitwidth <= nbits else nbits
        ret.append(f"{lhs}[{lo}:{hi}] @= x[{idx}]")
    return ret


VerilogVerilatorImportPass._gen_ref_read = _patched_gen_ref_read

_orig_create_py_wrapper = VerilogVerilatorImportPass.create_py_wrapper


def _patch_generated_wrapper(path):
    if not path.exists():
        return

    text = path.read_text()
    wire_bits = {}
    wire_decl = re.compile(r"^\s*s\.(\S+)\s*=\s*Wire\(\s*Bits(\d+)\s*\)\s*$")
    scalar_assign = re.compile(r"^(\s*s\.(\S+)\s+@=\s+)(_ffi_m\.\S+\[0\])\s*$")

    for line in text.splitlines():
        match = wire_decl.match(line)
        if match:
            wire_bits[match.group(1)] = int(match.group(2))

    patched_lines = []
    for line in text.splitlines():
        match = scalar_assign.match(line)
        if match:
            wire_name = match.group(2)
            nbits = wire_bits.get(wire_name)
            if nbits and nbits <= 64:
                mask = hex((1 << nbits) - 1) if nbits else "0x0"
                line = f"{match.group(1)}({match.group(3)} & {mask})"
        patched_lines.append(line)

    path.write_text("\n".join(patched_lines) + "\n")


def _patched_create_py_wrapper(self, m, ph_cfg, ip_cfg, rtype, ports, port_cdefs, cached):
    symbols = _orig_create_py_wrapper(self, m, ph_cfg, ip_cfg, rtype, ports, port_cdefs, cached)
    _patch_generated_wrapper(Path(ip_cfg.get_py_wrapper_path()))
    return symbols


VerilogVerilatorImportPass.create_py_wrapper = _patched_create_py_wrapper


def pytest_sessionstart(session):
    test_dir = Path(__file__).resolve().parent
    artifact_dirs = {test_dir, Path.cwd(), test_dir.parents[2]}
    for base_dir in artifact_dirs:
        for path in base_dir.glob("STEP_CgraRTL__*_v.py"):
            _patch_generated_wrapper(path)
        for path in base_dir.glob("__pycache__"):
            for child in path.rglob("*"):
                if child.is_file() or child.is_symlink():
                    child.unlink(missing_ok=True)
            for child in sorted(path.rglob("*"), reverse=True):
                if child.is_dir():
                    child.rmdir()
            path.rmdir()
