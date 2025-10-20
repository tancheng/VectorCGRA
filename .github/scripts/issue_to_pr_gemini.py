#!/usr/bin/env python3
import os
import sys
import json
import subprocess
import textwrap
from datetime import datetime
import argparse

ALLOWED_PREFIXES = ("src/", "lib/", "include/", "tests/", "docs/", "README.md")
MAX_FILE_BYTES = 200_000

def run(cmd, **kwargs):
    print("> " + " ".join(cmd))
    return subprocess.run(cmd, **kwargs)

def extract_json_object(s: str) -> str:
    start = s.find("{")
    if start == -1:
        raise ValueError("No JSON object found")
    depth = 0
    for i in range(start, len(s)):
        ch = s[i]
        if ch == "{": depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return s[start:i+1]
    raise ValueError("No balanced JSON object found")

def safe_json_load(s: str):
    try:
        return json.loads(s)
    except Exception as e:
        print("JSON parse error:", e)
        print("JSON candidate head:", s[:4000])
        raise

def is_path_allowed(path: str) -> bool:
    if path in ALLOWED_PREFIXES: return True
    for p in ALLOWED_PREFIXES:
        if path == p or path.startswith(p):
            return True
    return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("issue_number")
    parser.add_argument("repo")
    parser.add_argument("--from-file", help="read model output from file (raw text containing JSON)")
    args = parser.parse_args()

    issue_number = args.issue_number
    repo = args.repo

    event_path = os.environ.get("GITHUB_EVENT_PATH", "/github/workflow/event.json")
    if os.path.isfile(event_path):
        with open(event_path, "r", encoding="utf-8") as f:
            event = json.load(f)
    else:
        event = {}

    issue = event.get("issue", {})
    issue_title = issue.get("title", f"Issue #{issue_number}")
    issue_body = issue.get("body", "")

    print(f"Issue #{issue_number}: {issue_title!r}")

    # Acquire model output: from file if provided, else try environment variable (for fallback)
    raw = None
    if args.from_file:
        if not os.path.isfile(args.from_file):
            print("Model output file not found:", args.from_file)
            sys.exit(1)
        with open(args.from_file, "r", encoding="utf-8") as fh:
            raw = fh.read().strip()
    else:
        # fallback: read from env var MODEL_OUTPUT if present
        raw = os.environ.get("MODEL_OUTPUT", "").strip()
        if not raw:
            print("No model output found (no --from-file and no MODEL_OUTPUT). Exiting.")
            sys.exit(1)

    print("Model raw output head:")
    print(raw[:4000])

    # Extract JSON
    try:
        json_candidate = extract_json_object(raw)
    except Exception:
        json_candidate = raw

    try:
        data = safe_json_load(json_candidate)
    except Exception:
        print("Failed to parse JSON from model output. Exiting.")
        sys.exit(1)

    files = data.get("files", [])
    commit_message = data.get("commit_message", f"Auto changes for issue #{issue_number}")

    branch = f"auto/issue-{issue_number}"
    run(["git", "checkout", "-b", branch], check=True)

    actor = os.environ.get("GITHUB_ACTOR", "github-actions[bot]")
    email = f"{actor}@users.noreply.github.com"
    run(["git", "config", "user.name", actor], check=True)
    run(["git", "config", "user.email", email], check=True)

    for entry in files:
        path = entry.get("path")
        content = entry.get("content", "")
        if not path:
            print("Skipping entry with missing path:", entry)
            continue
        if not is_path_allowed(path):
            print(f"Refusing to modify {path} — not in allowed prefixes. Skipping.")
            continue
        if "\x00" in content:
            print(f"Skipping binary-looking content for {path}")
            continue
        if len(content.encode("utf-8")) > MAX_FILE_BYTES:
            print(f"Skipping {path}: content too large.")
            continue
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        run(["git", "add", path], check=True)

    status = run(["git", "status", "--porcelain"], capture_output=True, text=True)
    if not status.stdout.strip():
        print("No changes to commit. Exiting.")
        sys.exit(0)

    try:
        run(["git", "commit", "-m", commit_message], check=True)
    except Exception as e:
        print("git commit failed:", e)
        sys.exit(1)
    try:
        run(["git", "push", "--set-upstream", "origin", branch], check=True)
    except Exception as e:
        print("git push failed:", e)
        sys.exit(1)

    print("Committed & pushed:", branch)

if __name__ == "__main__":
    main()

