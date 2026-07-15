
from pathlib import Path

from pymtl3 import *
from pymtl3.passes.backends.verilog import VerilogTranslationPass
from pymtl3.passes.backends.verilog.errors import VerilogImportError
from pymtl3.stdlib.test_utils import config_model_with_cmdline_opts
from ..DivRTL import DivRTL
from ....lib.messages import *
from ....lib.opt_type import *

DataType = mk_data(32, 1)
num_inports = 4
num_outports = 2
CtrlType = mk_ctrl(num_inports, num_outports)
DataAddrType = mk_bits(3)
CtrlAddrType = mk_bits(3)
CgraPayloadType = mk_cgra_payload(DataType, DataAddrType, CtrlType, CtrlAddrType)
IntraCgraPktType = mk_intra_cgra_pkt(1, 1, 1, CgraPayloadType)

def test_translate_rem_operator(cmdline_opts):
  dut = DivRTL(IntraCgraPktType, num_inports, num_outports)
  dut.set_metadata(VerilogTranslationPass.explicit_module_name, 'DivRTL')
  dut.set_metadata(VerilogTranslationPass.explicit_file_name, 'DivRTL__pickled.v')

  translate_opts = dict(cmdline_opts)
  translate_opts["test_verilog"] = "zeros"

  try:
    config_model_with_cmdline_opts(dut, translate_opts, duts=[])
  except VerilogImportError as e:
    # Translation already emitted Verilog before the optional Verilator import.
    # On machines without Verilator, still inspect the generated RTL.
    assert 'verilator: not found' in str(e)

  verilog = Path('DivRTL__pickled.v').read_text()
  assert 'div_remainder' in verilog
  assert "if ( divisor != 32'd0 )" in verilog
  payload_assigns = [line for line in verilog.splitlines()
                     if 'payload =' in line]
  assert any('div_remainder' in line for line in payload_assigns)
  assert all('/' not in line and '%' not in line for line in payload_assigns)
