from ..Parser import Parser
from ...test import MeshMultiCgraTemplateRTL_test
import os


def test_Parser(cmdline_opts):
    arch_yaml_path = os.path.join(os.path.dirname(__file__), "arch.yaml")
    MeshMultiCgraTemplateRTL_test.test_mesh_multi_cgra_universal(cmdline_opts, arch_yaml_path=arch_yaml_path)
