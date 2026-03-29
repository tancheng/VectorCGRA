#!/usr/bin/env python3

import argparse
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bin", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    data = Path(args.bin).read_bytes()
    if len(data) % 8:
        data += b"\x00" * (8 - (len(data) % 8))

    lines = []
    for i in range(0, len(data), 8):
        word = int.from_bytes(data[i:i+8], "little")
        lines.append(f"{word:016x}")

    Path(args.out).write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
