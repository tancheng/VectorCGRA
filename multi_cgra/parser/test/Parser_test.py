from ..Parser import Parser
from ...test import MeshMultiCgraTemplateRTL_test
import os


def test_Parser(cmdline_opts):
    yaml_file = os.path.join(os.path.dirname(__file__), "architecture.yaml")
    parser = Parser(yaml_file)
    multiCgraParam = parser.parse_multi_cgra_param()
    MeshMultiCgraTemplateRTL_test.test_mesh_multi_cgra_universal(
        cmdline_opts, multiCgraParam=multiCgraParam)
