"""Trim a JSONL trace file to the first N lines."""

import sys
import os

def trim(input_path, max_lines=500):
    output_path = input_path + ".trimmed"
    with open(input_path, 'r') as fin, open(output_path, 'w') as fout:
        for i, line in enumerate(fin):
            if i >= max_lines:
                break
            fout.write(line)
    os.replace(output_path, input_path)
    print(f"Trimmed {input_path} to {min(max_lines, i+1)} lines (was {i+1} lines).")

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "trace_fir4x4_4x4_Mesh.jsonl")
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 500
    trim(path, n)
