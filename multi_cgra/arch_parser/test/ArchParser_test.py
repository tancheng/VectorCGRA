from ...test import MeshMultiCgraTemplateRTL_test
import os


def test_arch_parser(cmdline_opts, pytestconfig):
    arch_yaml_path = os.path.abspath(pytestconfig.getoption("arch_file"))
    if not os.path.exists(arch_yaml_path):
        raise FileNotFoundError(f"Architecture file not found at: {arch_yaml_path}\n \
                    Check if the path is relative to your current terminal location.")

    MeshMultiCgraTemplateRTL_test.test_mesh_multi_cgra_universal(cmdline_opts, arch_yaml_path=arch_yaml_path)
