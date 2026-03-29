#!/usr/bin/env python3

import argparse
import re
from pathlib import Path


MMIO_WR = 0x01
WAIT_DONE = 0x02
FINISH = 0xFF

META_DATA = 0x0010
META_COMMIT = 0x0014
BIT_DATA = 0x0018
BIT_COMMIT = 0x001C

META_BITS = 779
BIT_BITS = 155
META_WORDS = (META_BITS + 31) // 32
BIT_WORDS = (BIT_BITS + 31) // 32


def parse_task_args(tb_text: str):
    match = re.search(r"task\s+t\((.*?)integer\s+lineno", tb_text, re.S)
    if not match:
      raise RuntimeError("failed to locate task signature in tb")
    block = match.group(1)
    names = []
    for raw_line in block.splitlines():
        line = raw_line.strip().rstrip(",")
        if not line.startswith("input "):
            continue
        name = line.split()[-1]
        names.append(name)
    return names


def parse_case_line(line: str):
    start = line.find("(")
    end = line.rfind(")")
    payload = line[start + 1:end]
    parts = [p.strip() for p in payload.split(",")]
    return parts


def parse_hex_token(token: str) -> int:
    token = token.strip()
    if token.startswith("'h"):
        token = token[2:]
    elif token.startswith("32'h"):
        token = token[4:]
    elif token.startswith("64'h"):
        token = token[4:]
    return int(token, 16) if token else 0


def emit_write(out_lines, addr, data):
    packed = (MMIO_WR << 56) | ((addr & 0xFFFF) << 32) | (data & 0xFFFFFFFF)
    out_lines.append(f"{packed:016x}")


def emit_packet(out_lines, payload, word_count, data_addr, commit_addr):
    for idx in range(word_count):
        word = (payload >> (idx * 32)) & 0xFFFFFFFF
        emit_write(out_lines, data_addr, word)
    emit_write(out_lines, commit_addr, word_count)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tb", required=True)
    ap.add_argument("--cases", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    tb_text = Path(args.tb).read_text()
    case_text = Path(args.cases).read_text().splitlines()
    arg_names = parse_task_args(tb_text)

    meta_idx = arg_names.index("inp_recv_from_cpu_metadata_pkt__msg")
    meta_val_idx = arg_names.index("inp_recv_from_cpu_metadata_pkt__val")
    bit_idx = arg_names.index("inp_recv_from_cpu_bitstream_pkt__msg")
    bit_val_idx = arg_names.index("inp_recv_from_cpu_bitstream_pkt__val")

    prev_meta_val = 0
    prev_bit_val = 0
    out_lines = []

    for raw_line in case_text:
        line = raw_line.strip()
        if not line.startswith("`T("):
            continue
        values = parse_case_line(line)
        meta_val = parse_hex_token(values[meta_val_idx])
        bit_val = parse_hex_token(values[bit_val_idx])

        if meta_val and not prev_meta_val:
            emit_packet(
                out_lines,
                parse_hex_token(values[meta_idx]),
                META_WORDS,
                META_DATA,
                META_COMMIT,
            )
        if bit_val and not prev_bit_val:
            emit_packet(
                out_lines,
                parse_hex_token(values[bit_idx]),
                BIT_WORDS,
                BIT_DATA,
                BIT_COMMIT,
            )

        prev_meta_val = meta_val
        prev_bit_val = bit_val

    out_lines.append(f"{(WAIT_DONE << 56):016x}")
    out_lines.append(f"{(FINISH << 56):016x}")
    Path(args.out).write_text("\n".join(out_lines) + "\n")


if __name__ == "__main__":
    main()
