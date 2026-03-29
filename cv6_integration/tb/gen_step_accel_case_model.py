#!/usr/bin/env python3

import argparse
import re
from pathlib import Path


def parse_task_args(tb_text: str):
    match = re.search(r"task\s+t\((.*?)integer\s+lineno", tb_text, re.S)
    if not match:
        raise RuntimeError("failed to locate task signature in tb")
    names = []
    for raw_line in match.group(1).splitlines():
        line = raw_line.strip().rstrip(",")
        if line.startswith("input "):
            names.append(line.split()[-1])
    return names


def parse_hex_token(token: str) -> int:
    token = token.strip()
    if token.startswith("'h"):
        token = token[2:]
    elif token.startswith("32'h") or token.startswith("64'h"):
        token = token[4:]
    return int(token, 16) if token else 0


def parse_case_line(line: str):
    payload = line[line.find("(") + 1:line.rfind(")")]
    return [p.strip() for p in payload.split(",")]


def emit_port(out_lines, port, entries):
    count = len(entries)
    arr_len = max(1, count)
    out_lines.append(f"localparam int STEP_CASE_LD_COUNT_{port} = {count};")
    out_lines.append(f"logic [31:0] step_case_ld_data_{port} [0:{arr_len - 1}];")
    out_lines.append("initial begin")
    if count == 0:
        out_lines.append(f"  step_case_ld_data_{port}[0] = 32'h00000000;")
    else:
        for idx, (_, data) in enumerate(entries):
            out_lines.append(f"  step_case_ld_data_{port}[{idx}] = 32'h{data:08x};")
    out_lines.append("end")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tb", required=True)
    ap.add_argument("--cases", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    tb_text = Path(args.tb).read_text()
    arg_names = parse_task_args(tb_text)
    lines = Path(args.cases).read_text().splitlines()

    loads = {0: [], 1: []}

    for raw_line in lines:
        line = raw_line.strip()
        if not line.startswith("`T("):
            continue
        values = parse_case_line(line)
        for port in (0, 1):
            addr_val_idx = arg_names.index(f"ref_ld_axi__addr_val__{port}")
            data_val_idx = arg_names.index(f"inp_ld_axi__data_valid__{port}")
            addr_idx = arg_names.index(f"ref_ld_axi__addr__{port}")
            data_idx = arg_names.index(f"inp_ld_axi__data__{port}")
            if parse_hex_token(values[addr_val_idx]) and parse_hex_token(values[data_val_idx]):
                loads[port].append(
                    (
                        parse_hex_token(values[addr_idx]),
                        parse_hex_token(values[data_idx]),
                    )
                )

    out = []
    out.append("// Auto-generated from STEP Verilog .cases")
    emit_port(out, 0, loads[0])
    emit_port(out, 1, loads[1])
    Path(args.out).write_text("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
