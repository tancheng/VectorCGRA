#!/usr/bin/env python3
import os
import sys
import json
import subprocess
import textwrap
from datetime import datetime

# New OpenAI v1+ client
from openai import OpenAI

# Configuration: tune these as you like
ALLOWED_PREFIXES = (
    "src/",
    "lib/",
    "include/",
    "tests/",
    "docs/",
    "README.md",
    "README.rst",
    "README.md",
)
MAX_FILE_BYTES = 200_000  # reject file contents larger than this
MODEL = "gpt-4o"   # change to preferred model (gpt-4o-mini, gpt-4, etc.)

def run(cmd, **kwargs):
    print("> " + " ".join(cmd))
    return subprocess.run(cmd, **kwargs)

def extract_json_object(s: str) -> str:
    """
    Find the first top-level JSON object in s by scanning braces and returning the
    substring that contains a balanced JSON object. Raises ValueError if none found.
    """
    start = s.find("{")
    if start == -1:
        raise ValueError("No JSON object found in string")
    depth = 0
    for i in range(start, len(s)):
        ch = s[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return s[start:i+1]
    raise ValueError("Could not find matching closing brace for JSON object")

def safe_json_load(s: str):
    try:
        return json.loads(s)
    except Exception as e:
        print("Failed to parse JSON from model output:", e)
        print("Raw JSON candidate:")
        print(s[:4000])
        raise

def is_path_allowed(path: str) -> bool:
    # Exact filename or allowed prefix
    if path in ALLOWED_PREFIXES:
        return True
    for p in ALLOWED_PREFIXES:
        if path == p or path.startswith(p):
            return True
    return False

def main():
    if len(sys.argv) < 3:
        print("Usage: issue_to_pr.py <issue-number> <repo>")
        sys.exit(2)

    issue_number = sys.argv[1]
    repo = sys.argv[2]

    # Load the GitHub event JSON (if present)
    event_path = os.environ.get("GITHUB_EVENT_PATH", "/github/workflow/event.json")
    if os.path.isfile(event_path):
        with open(event_path, "r", encoding="utf-8") as f:
            event = json.load(f)
    else:
        print("Event JSON not found at:", event_path)
        event = {}

    issue = event.get("issue", {})
    issue_title = issue.get("title", f"Issue #{issue_number}")
    issue_body = issue.get("body", "")

    print(f"Issue #{issue_number}: {issue_title!r}")

    # Configure OpenAI v1+ client
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        print("OPENAI_API_KEY not found in environment. Exiting.")
        sys.exit(1)

    client = OpenAI(api_key=openai_api_key)

    # Compose prompt
    prompt = textwrap.dedent(f"""
    You are an assistant that converts a GitHub issue into a set of concrete code changes.
    Return ONLY a JSON object (no surrounding text) with this exact schema:

    {{
      "files": [
        {{
          "path": "relative/path/to/file",
          "content": "full file contents as a single string (newline characters allowed)"
        }}
      ],
      "commit_message": "A concise commit message"
    }}

    Issue title: {issue_title}

    Issue body:
    {issue_body}

    Constraints / hints:
    - If you create or change source files, include full file contents (complete files).
    - Keep changes minimal and focused on the issue.
    - Do not include binary files.
    - If no code changes are necessary, return an empty "files" list and an informative commit_message.
    - Only modify source/docs/tests in the repository. Avoid touching CI/workflow files.
    - Respond with valid JSON only.
    """)

    print("Sending prompt to OpenAI (truncated)...")
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=1500,
        )
    except Exception as e:
        print("OpenAI request failed:", e)
        sys.exit(1)

    # Extract model reply robustly
    raw = ""
    try:
        # resp may be a dict-like or object; try multiple access patterns
        choice0 = resp.choices[0]
        # common new-style shapes:
        if hasattr(choice0, "message") and getattr(choice0.message, "content", None) is not None:
            raw = choice0.message.content
        elif isinstance(choice0, dict) and "message" in choice0 and "content" in choice0["message"]:
            raw = choice0["message"]["content"]
        elif hasattr(choice0, "text"):
            raw = choice0.text
        else:
            raw = str(resp)
    except Exception:
        raw = str(resp)

    raw = raw.strip()
    print("Model response (truncated):")
    print(raw[:4000])

    # Extract a JSON object from raw text robustly
    try:
        json_candidate = extract_json_object(raw)
    except ValueError:
        # fallback: try to treat the entire raw as JSON
        json_candidate = raw

    try:
        data = safe_json_load(json_candidate)
    except Exception:
        print("Failed to decode JSON from model output. Exiting.")
        sys.exit(1)

    files = data.get("files", [])
    commit_message = data.get("commit_message", f"Auto changes for issue #{issue_number}")

    branch = f"auto/issue-{issue_number}"

    # Create branch
    run(["git", "checkout", "-b", branch], check=True)

    # Ensure local git identity (redundant with workflow but safe)
    actor = os.environ.get("GITHUB_ACTOR", "github-actions[bot]")
    email = f"{actor}@users.noreply.github.com"
    run(["git", "config", "user.name", actor], check=True)
    run(["git", "config", "user.email", email], check=True)

    # Write files (with whitelist and basic validation)
    for entry in files:
        path = entry.get("path")
        content = entry.get("content", "")
        if not path:
            print("Skipping entry with no path:", entry)
            continue

        # Whitelist check
        if not is_path_allowed(path):
            print(f"Refusing to modify {path} — not in allowed prefixes. Skipping.")
            continue

        # Size / binary checks
        if isinstance(content, str) and len(content.encode("utf-8")) > MAX_FILE_BYTES:
            print(f"Refusing to write {path} — content too large ({len(content)} chars).")
            continue
        if "\x00" in content:
            print(f"Refusing to write {path} — binary content detected.")
            continue

        # Create directories if necessary and write file
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        run(["git", "add", path], check=True)

    # Detect whether any changes are staged
    status = run(["git", "status", "--porcelain"], capture_output=True, text=True)
    if not status.stdout.strip():
        print("No changes to commit. Exiting successfully.")
        sys.exit(0)

    # Commit & push
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

    print("Files committed and pushed to branch:", branch)
    print("Action complete.")

if __name__ == "__main__":
    main()

