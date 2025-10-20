#!/usr/bin/env python3
# scripts/generate_patch.py
# Robust caller for Google's Gemini generateContent API that validates patches with git.
# Exits non-zero on error so your GitHub Action fails early.

from __future__ import annotations
import os
import sys
import time
import json
import re
import logging
import subprocess
from typing import Optional
import requests

# Configuration
MAX_RETRIES = 3
INITIAL_BACKOFF = 2  # seconds
TIMEOUT_SECONDS = 60
PATCH_PATH = "ai_fix.patch"
RAW_OUTPUT_PATH = "ai_fix_raw_output.txt"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def get_env_var(name: str, required: bool = True, default: Optional[str] = None) -> Optional[str]:
    value = os.environ.get(name, default)
    if required and not value:
        logger.error("Missing required environment variable: %s", name)
        sys.exit(2)
    return value

import textwrap

MAX_BODY_LEN = 4000  # tune for your token budget

def _sanitize(s: str) -> str:
    if s is None:
        return ""
    s = s.replace("\r\n", "\n").replace("\r", "\n").strip()
    if len(s) > MAX_BODY_LEN:
        return s[:MAX_BODY_LEN] + "\n\n...(truncated)..."
    return s

def build_prompt(title: str, body: str) -> str:
    title = _sanitize(title)
    body = _sanitize(body)

    prompt = textwrap.dedent(f"""
        You are an expert software developer and GitHub bot.
        Read the following GitHub issue and generate the code changes required to fix it.

        ISSUE TITLE: "{title}"

        ISSUE BODY:
        "{body}"

        IMPORTANT (STRICT FORMAT REQUIREMENT):
        - Respond ONLY with the code changes in a unified git diff / patch format.
        - The response MUST start exactly with a diff header, e.g.:
            diff --git a/path/to/file b/path/to/file
          or
            --- a/path/to/file
        - Include proper unified hunk headers (lines beginning with @@ -old, +new @@).
        - Do NOT include any explanatory text, headings, or Markdown code fences (no ```).
        - Output only the raw patch content — nothing else.
    """).strip()

    return prompt

def call_gemini(api_key: str, prompt: str, model: str) -> str:
    """
    Call the Gemini (Generative Language) API and return the raw text response.
    Retries on transient network errors.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    backoff = INITIAL_BACKOFF
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info("Calling Gemini API (attempt %d/%d)...", attempt, MAX_RETRIES)
            resp = requests.post(url, json=payload, timeout=TIMEOUT_SECONDS)
            resp.raise_for_status()
            return resp.text
        except requests.exceptions.RequestException as exc:
            logger.warning("Request attempt %d failed: %s", attempt, exc)
            if attempt == MAX_RETRIES:
                logger.error("Exceeded max retries calling Gemini API.")
                raise
            logger.info("Sleeping %s seconds before retrying...", backoff)
            time.sleep(backoff)
            backoff *= 2
    raise RuntimeError("Unreachable code in call_gemini")


def parse_gemini_response_text(response_text: str) -> str:
    """Parse the JSON returned by Gemini and extract the candidate text."""
    try:
        response_json = json.loads(response_text)
    except json.JSONDecodeError:
        logger.exception("Failed to decode Gemini response as JSON.")
        raise

    try:
        candidates = response_json.get("candidates")
        if not candidates or not isinstance(candidates, list):
            raise KeyError("No 'candidates' list in response")

        first = candidates[0]
        content = first.get("content", {})
        parts = content.get("parts")
        if not parts or not isinstance(parts, list):
            raise KeyError("No 'content.parts' list in response")

        text = parts[0].get("text")
        if not isinstance(text, str):
            raise KeyError("'text' field missing or not a string")

        return text
    except Exception as e:
        logger.error("Unexpected Gemini response structure: %s", e)
        logger.debug("Full response JSON: %s", json.dumps(response_json, indent=2)[:2000])
        raise


def sanitize_line_endings(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if text.startswith("\ufeff"):
        text = text.lstrip("\ufeff")
    return text


def strip_fenced_code(text: str) -> str:
    # Remove fenced code blocks if present (```patch ... ```), non-greedy.
    m = re.search(r"```(?:patch|diff)?\n([\s\S]+?)\n```", text, re.IGNORECASE)
    if m:
        logger.debug("Removed fenced code block wrapper.")
        return m.group(1).strip()
    return text


def find_first_diff_index(text: str) -> int:
    m = re.search(r'(^|\n)(diff --git |--- a/)', text)
    if m:
        # return index of 'diff' or '--- a/'
        return m.start(2) if m.start(2) >= 0 else m.start(1)
    return 0


def attempt_repair_patch(candidate: str) -> str:
    """
    Best-effort repairs:
      - normalize line endings,
      - strip fences,
      - remove leading text before first diff header.
    """
    candidate = sanitize_line_endings(candidate).strip()
    candidate = strip_fenced_code(candidate)
    idx = find_first_diff_index(candidate)
    if idx > 0:
        candidate = candidate[idx:].lstrip("\n")
    # Final trim
    candidate = candidate.strip("\n")
    return candidate


def write_file(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)


def git_apply_check(patch_path: str) -> bool:
    """
    Returns True if `git apply --check patch_path` succeeds.
    """
    try:
        subprocess.run(["git", "apply", "--check", patch_path],
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode(errors="replace") if e.stderr else ""
        logger.warning("git apply --check failed: %s", stderr.strip()[:2000])
        return False
    except FileNotFoundError:
        logger.error("git not found on PATH; cannot validate patch with git.")
        return False


def validate_and_save_patch(candidate: str) -> None:
    """
    Validate candidate patch using git; if valid, save to PATCH_PATH.
    Otherwise save raw output to RAW_OUTPUT_PATH and exit non-zero.
    """
    candidate = attempt_repair_patch(candidate)

    # quick heuristic: must contain a diff header
    if not (candidate.startswith("diff --git") or candidate.startswith("--- a/")):
        logger.error("Candidate patch does not start with a recognized diff header.")
        logger.debug("Top of candidate (200 chars): %s", candidate[:200])
        write_file(RAW_OUTPUT_PATH, candidate)
        logger.info("Saved raw model output to %s for inspection.", RAW_OUTPUT_PATH)
        sys.exit(3)

    # write to temp path for checking
    temp_path = PATCH_PATH + ".tmp"
    write_file(temp_path, candidate)

    # run git apply --check
    if git_apply_check(temp_path):
        # move into final path
        write_file(PATCH_PATH, candidate)
        logger.info("Patch validated and written to %s (size %d bytes).", PATCH_PATH, len(candidate.encode("utf-8")))
    else:
        # attempt a permissive whitespace fix check (optional)
        try:
            subprocess.run(["git", "apply", "--check", "--whitespace=fix", temp_path],
                           check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            write_file(PATCH_PATH, candidate)
            logger.info("Patch passed permissive whitespace check and was written to %s.", PATCH_PATH)
            return
        except subprocess.CalledProcessError:
            logger.warning("Permissive whitespace check failed.")

        # final fallback: save raw output and fail
        write_file(RAW_OUTPUT_PATH, candidate)
        logger.error("Patch failed validation. Saved raw model output to %s for inspection.", RAW_OUTPUT_PATH)
        # Print a diagnostic snippet (safe)
        snippet = candidate[:2000] + ("..." if len(candidate) > 2000 else "")
        logger.error("Diagnostic snippet (first 2000 chars):\n%s", snippet)
        sys.exit(4)


def extract_patch(raw_text: str) -> Optional[str]:
    """
    Keep the original extraction logic but then run the validator.
    """
    text = raw_text.strip()
    code_block_match = re.search(r"```(?:patch|diff|\s)?\n([\s\S]+?)\n```", text, re.IGNORECASE)
    if code_block_match:
        candidate = code_block_match.group(1).strip()
        logger.debug("Extracted content from fenced code block.")
    else:
        candidate = text

    # try to find 'diff --git' block
    diff_match = re.search(r"(diff --git[\s\S]+)$", candidate, re.MULTILINE)
    if diff_match:
        return diff_match.group(1).strip()

    alt_match = re.search(r"(^--- a/[\s\S]+)$", candidate, re.MULTILINE)
    if alt_match:
        return alt_match.group(1).strip()

    if candidate.startswith("diff --git") or candidate.startswith("--- a/"):
        return candidate.strip()

    return None


def main() -> None:
    api_key = get_env_var("GEMINI_API_KEY")
    issue_title = get_env_var("ISSUE_TITLE", required=True)
    issue_body = get_env_var("ISSUE_BODY", required=True)
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

    prompt = build_prompt(issue_title, issue_body)

    try:
        raw_response_text = call_gemini(api_key, prompt, model)
    except Exception as exc:
        logger.exception("Failed to get a response from Gemini: %s", exc)
        sys.exit(1)

    try:
        candidate_text = parse_gemini_response_text(raw_response_text)
    except Exception:
        logger.error("Could not parse Gemini JSON response.")
        # Save raw for debugging
        try:
            write_file(RAW_OUTPUT_PATH, raw_response_text)
            logger.info("Saved raw API response to %s for inspection.", RAW_OUTPUT_PATH)
        except Exception:
            logger.exception("Failed to save raw API response.")
        sys.exit(1)

    patch_candidate = extract_patch(candidate_text)

    if not patch_candidate:
        logger.error("Response did not contain a recognizable patch/diff header.")
        # Save raw model output for inspection
        try:
            write_file(RAW_OUTPUT_PATH, candidate_text)
            logger.info("Saved raw model output to %s for inspection.", RAW_OUTPUT_PATH)
        except Exception:
            logger.exception("Failed to save raw model output.")
        sys.exit(3)

    # Validate and save (this will exit non-zero if invalid)
    validate_and_save_patch(patch_candidate)

    logger.info("Successfully generated %s.", PATCH_PATH)
    sys.exit(0)


if __name__ == "__main__":
    main()

