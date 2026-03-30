#!/usr/bin/env python3

import argparse
import csv
import json
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CGRA_TEST_DIR = REPO_ROOT / "cgra" / "test"
DEFAULT_BENCHMARK_DIR = CGRA_TEST_DIR / "benchmarks"
DEFAULT_RESULTS_DIR = REPO_ROOT / "cv6_integration" / "generated" / "benchmark_batch"
DEFAULT_PYTEST_ENV = Path("/data/angl7/bin/miniconda3/envs/vector_cgra_base")
DEFAULT_CV6_ENV = Path("/data/angl7/bin/miniconda3/envs/step_cv6_test")


def run_command(cmd, cwd, env, log_path):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w") as log_file:
        process = subprocess.run(
            cmd,
            cwd=str(cwd),
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    return process.returncode


def load_json(path):
    with path.open() as fp:
        return json.load(fp)


def rel_or_abs(path):
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark-dir", default=str(DEFAULT_BENCHMARK_DIR))
    parser.add_argument("--results-dir", default=str(DEFAULT_RESULTS_DIR))
    parser.add_argument("--pytest-env-prefix", default=str(DEFAULT_PYTEST_ENV))
    parser.add_argument("--cv6-env-prefix", default=str(DEFAULT_CV6_ENV))
    parser.add_argument("--standalone-max-cycles", type=int, default=200000)
    parser.add_argument("--limit", type=int, default=0)
    return parser.parse_args()


def benchmark_selector(benchmark_json_name):
    return f"cgra/test/STEP_CgraRTL_mapped.py::test_benchmark_mappings[{benchmark_json_name}]"


def find_single(pattern):
    matches = sorted(REPO_ROOT.glob(pattern))
    if len(matches) != 1:
        raise RuntimeError(f"expected one match for {pattern}, found {len(matches)}: {matches}")
    return matches[0]


def cv6_step_name(tb_path):
    raw_name = tb_path.stem
    if raw_name.endswith("_tb"):
        raw_name = raw_name[:-3]
    return raw_name.replace(".", "_")


def delta(start, end):
    if start in (None, 0) or end in (None, 0) or end < start:
        return None
    return end - start


def main():
    args = parse_args()
    benchmark_dir = Path(args.benchmark_dir).resolve()
    results_dir = Path(args.results_dir).resolve()
    results_dir.mkdir(parents=True, exist_ok=True)

    benchmark_jsons = sorted(benchmark_dir.glob("*.json"))
    if args.limit:
      benchmark_jsons = benchmark_jsons[: args.limit]
    if not benchmark_jsons:
        raise SystemExit(f"no benchmark json files found under {benchmark_dir}")

    pytest_env_prefix = Path(args.pytest_env_prefix)
    cv6_env_prefix = Path(args.cv6_env_prefix)
    rows = []
    manifest = []

    for benchmark_json in benchmark_jsons:
        benchmark_name = benchmark_json.stem
        benchmark_result_dir = results_dir / benchmark_name
        benchmark_result_dir.mkdir(parents=True, exist_ok=True)

        standalone_log = benchmark_result_dir / "standalone.log"
        standalone_metrics_path = benchmark_result_dir / "standalone_metrics.json"
        cv6_log = benchmark_result_dir / "cv6.log"

        test_case_name = benchmark_selector(benchmark_json.name)
        standalone_cmd = [
            "conda",
            "run",
            "-p",
            str(pytest_env_prefix),
            "pytest",
            test_case_name,
            "--tb=short",
            "-v",
            "--test-verilog",
            "--dump-vtb",
            "--dump-vcd",
            "--full-trace",
            "-s",
            "--max-cycles",
            str(args.standalone_max_cycles),
        ]

        standalone_env = os.environ.copy()
        standalone_env["STEP_STANDALONE_METRICS_FILE"] = str(standalone_metrics_path)
        standalone_rc = run_command(standalone_cmd, REPO_ROOT, standalone_env, standalone_log)

        tb_pattern = f"STEP_CgraRTL__*_test_benchmark_mappings_{benchmark_json.name}_tb.v"
        vtb_path = None
        cases_path = None
        standalone_metrics = None
        standalone_error = ""
        if standalone_rc == 0:
            try:
                vtb_path = find_single(tb_pattern)
                cases_path = Path(str(vtb_path) + ".cases")
                standalone_metrics = load_json(standalone_metrics_path)
            except Exception as exc:
                standalone_error = str(exc)
                standalone_rc = 1
        else:
            standalone_error = f"pytest exited with rc={standalone_rc}"

        cv6_rc = None
        cv6_stats_path = None
        cv6_stats = None
        cv6_error = ""
        if standalone_rc == 0 and vtb_path is not None:
            step_name = cv6_step_name(vtb_path)
            cv6_stats_path = REPO_ROOT / "cv6_integration" / "generated" / f"{step_name}_stats.json"
            cv6_cmd = [
                "conda",
                "run",
                "-p",
                str(cv6_env_prefix),
                "make",
                "-C",
                str(REPO_ROOT / "cv6_integration"),
                "sim_cv6_step",
                f"STEP_TB={vtb_path}",
            ]
            cv6_env = os.environ.copy()
            cv6_rc = run_command(cv6_cmd, REPO_ROOT, cv6_env, cv6_log)
            if cv6_rc == 0:
                try:
                    cv6_stats = load_json(cv6_stats_path)
                except Exception as exc:
                    cv6_error = str(exc)
                    cv6_rc = 1
            else:
                cv6_error = f"make sim_cv6_step exited with rc={cv6_rc}"

        standalone_bench = standalone_metrics or {}
        cv6_bench = (cv6_stats or {}).get("benchmark", {})
        cv6_kernel = (cv6_stats or {}).get("kernel", {})

        standalone_e2e = standalone_bench.get("e2e_cycles")
        cv6_e2e = delta(cv6_bench.get("first_dma_issue_cycle"), cv6_bench.get("cgra_done_cycle"))
        cv6_exec_proxy = delta(cv6_bench.get("first_cgra_activity_cycle"), cv6_bench.get("cgra_done_cycle"))
        cv6_dma_to_bitstream = delta(cv6_bench.get("first_dma_issue_cycle"), cv6_bench.get("first_cgra_bitstream_cycle"))
        cv6_overhead_vs_standalone = None
        if standalone_e2e is not None and cv6_e2e is not None:
            cv6_overhead_vs_standalone = cv6_e2e - standalone_e2e

        row = {
            "benchmark": benchmark_name,
            "benchmark_json": rel_or_abs(benchmark_json),
            "generated_tb": rel_or_abs(vtb_path) if vtb_path else "",
            "generated_cases": rel_or_abs(cases_path) if cases_path else "",
            "standalone_log": rel_or_abs(standalone_log),
            "cv6_log": rel_or_abs(cv6_log) if cv6_log.exists() else "",
            "standalone_pass": standalone_rc == 0,
            "cv6_pass": cv6_rc == 0 if cv6_rc is not None else False,
            "standalone_first_launch_cycle": standalone_bench.get("first_launch_cycle"),
            "standalone_first_complete_cycle": standalone_bench.get("first_complete_cycle"),
            "standalone_done_cycle": standalone_bench.get("done_cycle"),
            "standalone_e2e_cycles": standalone_e2e,
            "standalone_launch_to_first_complete_cycles": standalone_bench.get("launch_to_first_complete_cycles"),
            "cv6_first_dma_issue_cycle": cv6_bench.get("first_dma_issue_cycle"),
            "cv6_first_dma_stream_cycle": cv6_bench.get("first_dma_stream_cycle"),
            "cv6_last_dma_stream_cycle": cv6_bench.get("last_dma_stream_cycle"),
            "cv6_first_cgra_metadata_cycle": cv6_bench.get("first_cgra_metadata_cycle"),
            "cv6_first_cgra_bitstream_cycle": cv6_bench.get("first_cgra_bitstream_cycle"),
            "cv6_first_cgra_activity_cycle": cv6_bench.get("first_cgra_activity_cycle"),
            "cv6_cgra_done_cycle": cv6_bench.get("cgra_done_cycle"),
            "cv6_cpu_exit_cycle": cv6_bench.get("cpu_exit_cycle"),
            "cv6_meta_packet_count": cv6_kernel.get("meta_packet_count"),
            "cv6_bit_packet_count": cv6_kernel.get("bit_packet_count"),
            "cv6_command_count": cv6_kernel.get("command_count"),
            "cv6_e2e_offload_cycles": cv6_e2e,
            "cv6_execution_proxy_cycles": cv6_exec_proxy,
            "cv6_dma_preload_to_first_bitstream_cycles": cv6_dma_to_bitstream,
            "cv6_overhead_vs_standalone_cycles": cv6_overhead_vs_standalone,
            "standalone_error": standalone_error,
            "cv6_error": cv6_error,
        }
        rows.append(row)
        manifest.append(
            {
                "benchmark": benchmark_name,
                "benchmark_json": str(benchmark_json),
                "standalone": {
                    "returncode": standalone_rc,
                    "log": str(standalone_log),
                    "metrics": str(standalone_metrics_path),
                    "tb": str(vtb_path) if vtb_path else "",
                    "cases": str(cases_path) if cases_path else "",
                    "error": standalone_error,
                },
                "cv6": {
                    "returncode": cv6_rc,
                    "log": str(cv6_log),
                    "stats": str(cv6_stats_path) if cv6_stats_path else "",
                    "error": cv6_error,
                },
            }
        )

    manifest_path = results_dir / "benchmark_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    csv_path = results_dir / "benchmark_summary.csv"
    fieldnames = list(rows[0].keys()) if rows else []
    with csv_path.open("w", newline="") as csv_fp:
        writer = csv.DictWriter(csv_fp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    failures = [row for row in rows if not row["standalone_pass"] or not row["cv6_pass"]]
    print(f"Wrote {csv_path}")
    print(f"Wrote {manifest_path}")
    if failures:
        print(f"{len(failures)} benchmark(s) failed")
        for row in failures:
            print(
                f"  {row['benchmark']}: standalone_pass={row['standalone_pass']} "
                f"cv6_pass={row['cv6_pass']} standalone_error={row['standalone_error']} "
                f"cv6_error={row['cv6_error']}"
            )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
