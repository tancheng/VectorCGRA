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
    pc_idx = arg_names.index("ref_pc_req")
    pc_trigger_idx = arg_names.index("ref_pc_req_trigger")
    pc_trigger_count_idx = arg_names.index("ref_pc_req_trigger_count")

    meta_packets = []
    bit_group_packets = {}
    bit_group_order = []

    prev_meta_active = 0
    prev_meta_msg = 0
    prev_pc_trigger = 0
    capture_bit_key = None
    capture_bit_remaining = 0

    for raw_line in lines:
        line = raw_line.strip()
        if not line.startswith("`T("):
            continue
        values = parse_case_line(line)
        meta_val = parse_hex_token(values[meta_val_idx])
        meta_rdy = parse_hex_token(values[meta_rdy_idx])
        meta_msg = parse_hex_token(values[meta_idx])
        bit_val = parse_hex_token(values[bit_val_idx])
        bit_rdy = parse_hex_token(values[bit_rdy_idx])
        bit_msg = parse_hex_token(values[bit_idx])
        pc = parse_hex_token(values[pc_idx])
        pc_trigger = parse_hex_token(values[pc_trigger_idx])
        pc_trigger_count = parse_hex_token(values[pc_trigger_count_idx])
        meta_active = 1 if (meta_val and meta_rdy) else 0
        bit_active = 1 if (bit_val and bit_rdy) else 0
        if meta_active and ((not prev_meta_active) or (meta_msg != prev_meta_msg)):
            meta_packets.append(words_from_payload(meta_msg, META_WORDS))
        if pc_trigger and not prev_pc_trigger:
            key = (pc, pc_trigger_count)
            if (pc_trigger_count > 0) and (key not in bit_group_packets):
                bit_group_packets[key] = []
                bit_group_order.append(key)
                capture_bit_key = key
                capture_bit_remaining = pc_trigger_count
            else:
                capture_bit_key = None
                capture_bit_remaining = 0
        if capture_bit_key is not None and bit_active and (bit_msg != 0):
            bit_group_packets[capture_bit_key].append(words_from_payload(bit_msg, BIT_WORDS))
            capture_bit_remaining -= 1
            if capture_bit_remaining == 0:
                capture_bit_key = None
        prev_meta_active = meta_active
        prev_meta_msg = meta_msg
        prev_pc_trigger = pc_trigger

    bit_packets = []
    cmds = []
    for idx in range(len(meta_packets)):
        cmds.append(("META", idx))
    for key in bit_group_order:
        packets = bit_group_packets[key]
        if len(packets) != key[1]:
            raise RuntimeError(
                f"bitstream group pc={key[0]} count={key[1]} captured {len(packets)} packets"
            )
        start_idx = len(bit_packets)
        bit_packets.extend(packets)
        for pkt_idx in range(len(packets)):
            cmds.append(("BIT", start_idx + pkt_idx))

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
