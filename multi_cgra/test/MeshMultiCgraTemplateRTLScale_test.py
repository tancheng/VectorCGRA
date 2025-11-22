from . import MeshMultiCgraTemplateRTL_test
from ..parser.MultiCgraParam import MultiCgraParam


def test_mesh_multi_cgra_scaling(cmdline_opts):
    # multi_cgra_sizes[i] = [num_cgra_rows, num_cgra_cols, per_cgra_rows, per_cgra_cols]
    multi_cgra_sizes = [[2, 2, 4, 4], [4, 4, 2, 2]]
    for size in multi_cgra_sizes:
        multi_cgra_param = MultiCgraParam.from_params(*size)
        MeshMultiCgraTemplateRTL_test.test_mesh_multi_cgra_universal(cmdline_opts, multi_cgra_param)
