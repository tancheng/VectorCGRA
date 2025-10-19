#!/usr/bin/env python3
import os
import sys
import json
import subprocess
import textwrap
import openai
from datetime import datetime

def run(cmd, **kwargs):
    print("> " + " ".join(cmd))
    return subprocess.run(cmd, **kwargs)

def safe_json_load(s):
    try:
        return json.loads(s)
    except Exception as e:
        print("Failed to parse JSON from model output:", e)
        print("Raw output:")
        print(s)
        raise

def main():
    if len(sys.argv) < 3:
        print("Usage: issue_to_pr.py <issue-number> <repo>")
        sys.exit(2)

    issue_number = sys.argv[1]
    repo = sys.argv[2]

    # Load the event payload that triggered the action
    event_path = os.environ.get("GITHUB_EVENT_PATH", "/github/workflow/event.json")
    if not os.path.isfile(event_path):
        print("Event JSON not found at:", event_path)
        # keep going — some debug runs might not have it
        event = {}
    else:
        with open(event_path, "r", encoding="utf-8") as f:
            event = json.load(f)

    issue = event.get("issue", {})
    issue_title = issue.get("title", f"Issue #{issue_number}")
    issue_body = issue.get("body", "")

    print(f"Issue #{issue_number}: {issue_title}")

    # Configure OpenAI client
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        print("OPENAI_API_KEY not found in environment. Exiting.")
        sys.exit(1)
    openai.api_key = openai_api_key

    # Compose prompt for the model
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
    - If you create or change source files, include full file contents.
    - Keep changes minimal and focused on the issue.
    - Do not include binary files.
    - If no code changes are necessary, return an empty "files" list and an informative commit_message.
    - Respond with valid JSON only.
    """)

    print("Sending prompt to OpenAI (truncated)...")
    # Use a capable, reasonably-priced model. Adjust model name as desired.
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=1500,
        )
    except Exception as e:
        print("OpenAI request failed:", e)
        sys.exit(1)

    raw = resp["choices"][0]["message"]["content"].strip()
    print("Model response (truncated):")
    print(raw[:2000])

    # Try to find JSON in the output (sometimes models add code fences)
    json_start = raw.find("{")
    json_text = raw[json_start:] if json_start != -1 else raw
    data = safe_json_load(json_text)

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

    # Write files
    for f in files:
        path = f.get("path")
        content = f.get("content", "")
        if not path:
            print("Skipping entry with no path:", f)
            continue
        # Create directories if necessary
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        run(["git", "add", path], check=True)

    # If no files were returned, don't attempt to commit
    # But we still want to surface that the model suggested no changes.
    status = run(["git", "status", "--porcelain"], capture_output=True, text=True)
    if not status.stdout.strip():
        print("No changes to commit. Exiting successfully.")
        # Clean up the created empty branch locally (optional). We will exit 0 so create-pull-request sees nothing to do.
        # Optionally delete branch: git checkout - && git branch -D <branch> (skipped to avoid unexpected remote deletion)
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

