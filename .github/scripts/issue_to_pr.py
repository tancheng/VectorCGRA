import os, sys, subprocess, json
from openai import OpenAI

issue_number = sys.argv[1]
repo = sys.argv[2]
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# Get issue data from GitHub event
event_path = os.environ["GITHUB_EVENT_PATH"]
with open(event_path) as f:
    event = json.load(f)
issue = event["issue"]

prompt = f"""
You are a GitHub issue-to-PR assistant.
Issue title: {issue['title']}
Issue body:
{issue['body']}

Please return JSON describing code edits:
{{
 "files": [
   {{ "path": "example.txt", "content": "new file contents here" }}
 ],
 "commit_message": "commit message"
}}
Respond with JSON only.
"""

resp = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": prompt}],
    temperature=0.2,
)
reply = resp.choices[0].message.content.strip()

data = json.loads(reply)
branch = f"auto/issue-{issue_number}"
subprocess.run(["git", "checkout", "-b", branch], check=True)

for f in data["files"]:
    os.makedirs(os.path.dirname(f["path"]) or ".", exist_ok=True)
    with open(f["path"], "w") as out:
        out.write(f["content"])
    subprocess.run(["git", "add", f["path"]], check=True)

subprocess.run(["git", "commit", "-m", data["commit_message"]], check=True)
