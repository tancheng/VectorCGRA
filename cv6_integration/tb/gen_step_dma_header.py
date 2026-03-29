#!/usr/bin/env python3

import argparse
import re
from pathlib import Path

META_BITS = 779
BIT_BITS = 155
META_WORDS = (META_BITS + 31) // 32
BIT_WORDS = (BIT_BITS + 31) // 32


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


def words_from_payload(payload: int, count: int):
    return [(payload >> (32 * i)) & 0xFFFFFFFF for i in range(count)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tb", required=True)
    ap.add_argument("--cases", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    tb_text = Path(args.tb).read_text()
    arg_names = parse_task_args(tb_text)
    lines = Path(args.cases).read_text().splitlines()

    meta_idx = arg_names.index("inp_recv_from_cpu_metadata_pkt__msg")
    meta_val_idx = arg_names.index("inp_recv_from_cpu_metadata_pkt__val")
    meta_rdy_idx = arg_names.index("ref_recv_from_cpu_metadata_pkt__rdy")
    bit_idx = arg_names.index("inp_recv_from_cpu_bitstream_pkt__msg")
    bit_val_idx = arg_names.index("inp_recv_from_cpu_bitstream_pkt__val")
    bit_rdy_idx = arg_names.index("ref_recv_from_cpu_bitstream_pkt__rdy")

    meta_packets = []
    bit_packets = []
    cmds = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line.startswith("`T("):
            continue
        values = parse_case_line(line)
        meta_val = parse_hex_token(values[meta_val_idx])
        meta_rdy = parse_hex_token(values[meta_rdy_idx])
        bit_val = parse_hex_token(values[bit_val_idx])
        bit_rdy = parse_hex_token(values[bit_rdy_idx])
        if meta_val and meta_rdy:
            meta_packets.append(words_from_payload(parse_hex_token(values[meta_idx]), META_WORDS))
            cmds.append(("META", len(meta_packets) - 1))
        if bit_val and bit_rdy:
            bit_packets.append(words_from_payload(parse_hex_token(values[bit_idx]), BIT_WORDS))
            cmds.append(("BIT", len(bit_packets) - 1))

    out = []
    out.append("#pragma once")
    out.append("#include <stdint.h>")
    out.append(f"#define STEP_META_WORDS {META_WORDS}")
    out.append(f"#define STEP_BIT_WORDS {BIT_WORDS}")
    out.append(f"#define STEP_META_PACKET_COUNT {len(meta_packets)}")
    out.append(f"#define STEP_BIT_PACKET_COUNT {len(bit_packets)}")
    out.append(f"#define STEP_CMD_COUNT {len(cmds)}")
    out.append("typedef enum { STEP_HOST_CMD_META = 1, STEP_HOST_CMD_BIT = 2 } step_host_cmd_type_t;")
    out.append("typedef struct { uint32_t type; uint32_t index; } step_host_cmd_t;")
    out.append(f"static const uint32_t step_meta_packets[{len(meta_packets)}][{META_WORDS}] = {{")
    for pkt in meta_packets:
        out.append("  {" + ", ".join(f"0x{w:08x}u" for w in pkt) + "},")
    out.append("};")
    out.append(f"static const uint32_t step_bit_packets[{len(bit_packets)}][{BIT_WORDS}] = {{")
    for pkt in bit_packets:
        out.append("  {" + ", ".join(f"0x{w:08x}u" for w in pkt) + "},")
    out.append("};")
    out.append(f"static const step_host_cmd_t step_host_cmds[{len(cmds)}] = {{")
    for typ, idx in cmds:
        out.append(f"  {{ STEP_HOST_CMD_{typ}, {idx}u }},")
    out.append("};")

    Path(args.out).write_text("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
