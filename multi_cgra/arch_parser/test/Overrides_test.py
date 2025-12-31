"""
    Collects some test cases of tiles/links overrides.
"""
import os
from ....cgra.test import CgraTemplateRTL_test
from ...test import MeshMultiCgraTemplateRTL_test

def test_single_cgra_overrides(cmdline_opts):
    arch_file_path = os.path.join(os.path.dirname(__file__), "arch_single_cgra_overrides.yaml")
    CgraTemplateRTL_test.test_cgra_universal(cmdline_opts, arch_file_path)

def test_multi_cgra_overrides(cmdline_opts):
    arch_file_path = os.path.join(os.path.dirname(__file__), "arch_multi_cgra_overrides.yaml")
    MeshMultiCgraTemplateRTL_test.test_mesh_multi_cgra_universal(cmdline_opts, arch_file_path)