import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from STEP_VectorCGRA.lib.util.pkt_helper import generateCPUPktFromJSON


def test_generate_cpu_pkt_from_json_generates_thread_span_ld_st_counts(tmp_path):
    json_path = tmp_path / "mapped.json"
    json_path.write_text(json.dumps({
        "cgra_def": {
            "num_tiles": 2,
            "num_tile_rows": 1,
            "num_tile_cols": 2,
            "num_tile_inports": 8,
            "num_tile_outports": 8,
            "num_rd_ports": 1,
            "num_wr_ports": 1,
            "num_ld_ports": 1,
            "num_st_ports": 1,
            "num_registers": 4
        },
        "cfg_0": {
            "metadata": {
                "cmd": 3,
                "tile_load_count": 1,
                "pred_tile_valid": [1, 1],
                "ld_enable": [1],
                "ld_reg_addr": [0],
                "st_enable": [1],
                "in_regs": ["tid"],
                "in_regs_val": [1],
                "in_tid_enable": [1],
                "out_regs": [1],
                "out_regs_val": [1],
                "out_pred_regs": [0],
                "out_pred_regs_val": [0],
                "tokenizer": {
                    "token_route_sink_enable": [[0, 0, 0]],
                    "token_route_delay_to_sink": [0, 0, 0]
                },
                "cfg_id": 0,
                "br_id": 0,
                "thread_count_min": 0,
                "thread_count_max": 4,
                "start_cfg": 1,
                "end_cfg": 1,
                "branch_en": 0,
                "branch_has_else": 0,
                "branch_backedge_sel": 0,
                "pred_reg_id": 0,
                "branch_true_cfg_id": 0,
                "branch_false_cfg_id": 0,
                "reconverge_cfg_id": 0
            },
            "bitstream": {
                "tile_0": {
                    "id": 0,
                    "tile_in_route": ["N", "", ""],
                    "tile_out_route": ["S"],
                    "tile_pred_route": ["S"],
                    "tile_out_shift_amounts": [0, 0, 0, 0, 0, 0, 0, 0],
                    "tile_fwd_route": [
                        [0, 0, 0, 0, 0, 0, 0, 0],
                        [0, 0, 0, 0, 0, 0, 0, 0],
                        [0, 0, 0, 0, 0, 0, 0, 0],
                        [0, 0, 0, 0, 0, 0, 0, 0],
                        [0, 0, 0, 0, 0, 0, 0, 0],
                        [0, 0, 0, 0, 0, 0, 0, 0],
                        [0, 0, 0, 0, 0, 0, 0, 0],
                        [0, 0, 0, 0, 0, 0, 0, 0]
                    ],
                    "const_val": 0,
                    "pred_fwd_route": "",
                    "pred_gen": 0,
                    "opt_type": "OPT_ADD"
                },
                "tile_1": {
                    "id": 1,
                    "opt_type": "OPT_NAH"
                }
            }
        }
    }))

    cgra_def, cpu_metadata_pkts, cpu_bitstream_pkts, ld_pkts, st_pkts, expected_cpu_pkts = generateCPUPktFromJSON(str(json_path))

    assert cgra_def["data_width"] == 8
    assert len(cpu_metadata_pkts) == 2
    assert len(cpu_bitstream_pkts) == 1
    assert int(cpu_metadata_pkts[0].thread_count_min) == 0
    assert int(cpu_metadata_pkts[0].thread_count_max) == 4
    assert int(cpu_metadata_pkts[0].in_tid_enable[0]) == 1
    assert int(cpu_metadata_pkts[0].tokenizer_cfg.token_route_sink_enable[0]) == 0b100
    assert ld_pkts[0] == [5, 5, 5, 5]
    assert st_pkts[0] == 4
    assert expected_cpu_pkts == [1]
